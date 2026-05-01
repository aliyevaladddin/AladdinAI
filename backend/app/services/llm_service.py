# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Unified LLM provider client.

Supports the three families currently registered as provider types:
- OpenAI-compatible (`openai`, `nvidia_nim`, `ollama`, `custom`) — POST {base}/v1/chat/completions
- Anthropic (`anthropic`)                                       — POST {base}/v1/messages
- HuggingFace Inference (`huggingface`)                         — POST {base}/models/{model}

The caller passes a provider row, the target model id, and a list of
`{role, content}` messages where the first one is typically the system prompt.
"""
from __future__ import annotations

import httpx

from app.models.llm_provider import LLMProvider

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_TOKENS = 1024

OPENAI_COMPATIBLE = {"openai", "nvidia_nim", "ollama", "custom"}


class LLMError(Exception):
    """Raised when the upstream provider call fails."""


async def chat_completion(
    provider: LLMProvider,
    model: str,
    messages: list[dict],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Send a chat-completion request to the provider and return assistant text."""
    ptype = (provider.type or "").lower()
    api_key = provider.api_key_encrypted

    if ptype in OPENAI_COMPATIBLE:
        return await _openai_compatible(provider.base_url, api_key, model, messages, max_tokens, timeout)
    if ptype == "anthropic":
        return await _anthropic(provider.base_url, api_key, model, messages, max_tokens, timeout)
    if ptype == "huggingface":
        return await _huggingface(provider.base_url, api_key, model, messages, max_tokens, timeout)

    raise LLMError(f"Unsupported provider type: {provider.type}")


async def _openai_compatible(
    base_url: str, api_key: str | None, model: str, messages: list[dict], max_tokens: int, timeout: float
) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

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
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape: {str(data)[:200]}") from e


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


def _messages_to_prompt(messages: list[dict]) -> str:
    """Flatten chat messages into a single prompt for completion-only endpoints."""
    parts: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)
