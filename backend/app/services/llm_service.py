# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Unified LLM provider client.

Supports the three families currently registered as provider types:
- OpenAI-compatible (`openai`, `nvidia_nim`, `ollama`, `custom`) — POST {base}/v1/chat/completions
- Anthropic (`anthropic`)                                       — POST {base}/v1/messages
- HuggingFace Inference (`huggingface`)                         — POST {base}/models/{model}

`chat_completion` returns a dict:
    {"content": str|None, "tool_calls": list|None, "finish_reason": str, "raw": dict}

`tool_calls` is OpenAI-style: [{"id": str, "type": "function",
"function": {"name": str, "arguments": str_json}}]. Anthropic and HF
always return tool_calls=None — they fall back to text-only.
"""
from __future__ import annotations

import logging
from typing import Any, Callable


import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt
from app.models.llm_provider import LLMProvider

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 180.0
DEFAULT_MAX_TOKENS = 1024

OPENAI_COMPATIBLE = {"openai", "nvidia_nim", "ollama", "custom"}
# Provider families that currently honor `tools=` in chat_completion.
# Keep in sync with the branches in chat_completion below.
TOOL_CALLING_SUPPORTED = OPENAI_COMPATIBLE

# Provider priority for auto-selection
# Tool-calling providers first, then fallbacks
LLM_PROVIDER_PRIORITY = ["nvidia_nim", "openai", "ollama", "custom", "anthropic", "huggingface"]


# [RCF:PROTECTED]
class LLMError(Exception):
    """Raised when the upstream provider call fails."""


# [RCF:PROTECTED]
async def resolve_llm_provider(
    db: AsyncSession,
    user_id: int,
    *,
    require_tools: bool = False,
) -> LLMProvider:
    """Select first available LLM provider by priority.

    Args:
        db: Database session
        user_id: User ID
        require_tools: If True, only return providers that support tool calling

    Returns:
        First available provider with status='connected'

    Raises:
        LLMError: If no suitable provider found
    """
    priority = LLM_PROVIDER_PRIORITY if not require_tools else [
        p for p in LLM_PROVIDER_PRIORITY if p in TOOL_CALLING_SUPPORTED
    ]

    for provider_type in priority:
        result = await db.execute(
            select(LLMProvider).where(
                LLMProvider.user_id == user_id,
                LLMProvider.type == provider_type,
                LLMProvider.status == "connected",
            )
        )
        provider = result.scalars().first()
        if provider:
            return provider

    if require_tools:
        raise LLMError(
            f"No tool-calling LLM provider configured. Need one of: {', '.join(TOOL_CALLING_SUPPORTED)}"
        )
    else:
        raise LLMError(
            f"No LLM provider configured. Need one of: {', '.join(LLM_PROVIDER_PRIORITY)}"
        )


# [RCF:PROTECTED]
async def chat_completion(
    provider: LLMProvider,
    model: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    tool_choice: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
    on_token: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Send a chat-completion request and return a structured response.

    Returns a dict with keys: `content`, `tool_calls`, `finish_reason`, `raw`.
    `tools` and `tool_choice` are honored only by OpenAI-compatible providers.
    """
    ptype = (provider.type or "").lower()
# [RCF:PROTECTED]
    api_key = decrypt(provider.api_key_encrypted) if provider.api_key_encrypted else None

    if ptype in OPENAI_COMPATIBLE:
        return await _openai_compatible(
            provider.base_url, api_key, model, messages, max_tokens, timeout, tools, tool_choice, on_token
        )

    # Below branches don't currently support tool calling — make the loss explicit.
    if tools:
        log.warning(
            "Provider %r (model %r) does not support tool calling; "
            "dropping %d tool(s) and falling back to text-only.",
            ptype, model, len(tools),
        )

    if ptype == "anthropic":
        text = await _anthropic(provider.base_url, api_key, model, messages, max_tokens, timeout)
        return {"content": text, "tool_calls": None, "finish_reason": "stop", "raw": {}}
    if ptype == "huggingface":
        text = await _huggingface(provider.base_url, api_key, model, messages, max_tokens, timeout)
        return {"content": text, "tool_calls": None, "finish_reason": "stop", "raw": {}}

    raise LLMError(f"Unsupported provider type: {provider.type}")


# [RCF:PROTECTED]
async def _openai_compatible(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    max_tokens: int,
    timeout: float,
    tools: list[dict] | None,
    tool_choice: str | None,
    on_token: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if tools:
        payload["tools"] = tools
        payload["parallel_tool_calls"] = False  # NIM supports only single tool-call at once
        if tool_choice:
            payload["tool_choice"] = tool_choice

    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    if on_token:
        import json
        import inspect
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                content_parts = []
                tool_calls_map = {}
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        response.raise_for_status()
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choice = chunk["choices"][0]
                                delta = choice.get("delta", {})
                                
                                content = delta.get("content")
                                if content:
                                    content_parts.append(content)
                                    if inspect.iscoroutinefunction(on_token):
                                        await on_token(content)
                                    else:
                                        on_token(content)
                                        
                                tool_calls = delta.get("tool_calls")
                                if tool_calls:
                                    for tc in tool_calls:
                                        idx = tc.get("index", 0)
                                        if idx not in tool_calls_map:
                                            tool_calls_map[idx] = {
                                                "id": tc.get("id"),
                                                "type": "function",
                                                "function": {
                                                    "name": tc.get("function", {}).get("name", ""),
                                                    "arguments": ""
                                                }
                                            }
                                        if tc.get("id"):
                                            tool_calls_map[idx]["id"] = tc.get("id")
                                        fn_delta = tc.get("function", {})
                                        if fn_delta.get("name"):
                                            tool_calls_map[idx]["function"]["name"] = fn_delta["name"]
                                        if fn_delta.get("arguments"):
                                            tool_calls_map[idx]["function"]["arguments"] += fn_delta["arguments"]
                            except Exception:
                                pass
                
                final_content = "".join(content_parts) if content_parts else None
                final_tool_calls = list(tool_calls_map.values()) if tool_calls_map else None
                return {
                    "content": final_content,
                    "tool_calls": final_tool_calls,
                    "finish_reason": "stop",
                    "raw": {}
                }
            except httpx.HTTPStatusError as e:
                raise LLMError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e
            except httpx.HTTPError as e:
                raise LLMError(str(e)) from e

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(str(e)) from e

    data = resp.json()
    try:
        choice = data["choices"][0]
        msg = choice.get("message", {})
        return {
            "content": msg.get("content"),
            "tool_calls": msg.get("tool_calls"),
            "finish_reason": choice.get("finish_reason", "stop"),
            "raw": data,
        }
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape: {str(data)[:200]}") from e


# [RCF:PROTECTED]
async def _anthropic(
    base_url: str, api_key: str | None, model: str, messages: list[dict], max_tokens: int, timeout: float
) -> str:
    if not api_key:
        raise LLMError("Anthropic requires an API key")

    system_parts: list[str] = []
    convo: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            convo.append({"role": role, "content": content})

    payload: dict = {"model": model, "max_tokens": max_tokens, "messages": convo}
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    url = f"{(base_url or 'https://api.anthropic.com').rstrip('/')}/v1/messages"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(str(e)) from e

    data = resp.json()
    try:
        blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (AttributeError, TypeError) as e:
        raise LLMError(f"Unexpected Anthropic response: {str(data)[:200]}") from e


# [RCF:PROTECTED]
async def _huggingface(
    base_url: str, api_key: str | None, model: str, messages: list[dict], max_tokens: int, timeout: float
) -> str:
    if not api_key:
        raise LLMError("HuggingFace requires an API token")

    prompt = _messages_to_prompt(messages)
    base = (base_url or "https://api-inference.huggingface.co").rstrip("/")
    url = f"{base}/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "return_full_text": False},
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(str(e)) from e

    data = resp.json()
    if isinstance(data, list) and data:
        return data[0].get("generated_text", "")
    if isinstance(data, dict):
        return data.get("generated_text", "") or str(data)
    return str(data)


# [RCF:PROTECTED]
def _messages_to_prompt(messages: list[dict]) -> str:
    """Flatten chat messages into a single prompt for completion-only endpoints."""
    parts: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)
