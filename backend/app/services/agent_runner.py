"""Run an agent's reply with tool-call iteration.

Cycle:
    1. Call LLM with messages + tools (if model supports them).
    2. If reply has tool_calls, execute each via the registry, append a
       `tool` role message per call, and loop.
    3. If reply has no tool_calls, return content.
    4. Bail out after `max_iterations` to avoid infinite loops.

Per-agent config is read from `agent.tools_config`:
    {"allowed": ["delegate", "ask_agent", ...], "max_iterations": 5}
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services.extraction import schedule_extraction
from app.services.llm_service import LLMError, chat_completion
from app.services.memory import build_shared_context_block
from app.services.safety import block_response, safety_egress, safety_ingress
from app.tools import REGISTRY, ToolContext, execute, openai_schemas
from app.tools.capabilities import model_supports_tools

log = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 5

DEFAULT_TOOLS_BY_ROLE: dict[str, list[str]] = {
    "_default": [
        "ask_agent", "delegate", "recall", "remember",
        "analyze_image", "send_image", "generate_image",
        "send_email",
    ],
}


def _text_of(content: Any) -> str:
    """Extract text from a message's content — handles both string and OpenAI
    multimodal list form `[{type:"text",text:...}, {type:"image_url",...}]`.
    Returns an empty string for None / empty input.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text") or ""
                if t:
                    parts.append(t)
        return "\n".join(parts)
    return str(content)


def _allowed_tools(agent: Agent) -> list[str]:
    cfg = agent.tools_config or {}
    if isinstance(cfg, dict) and "allowed" in cfg:
        return list(cfg["allowed"])
    role = (agent.role or "").lower()
    return DEFAULT_TOOLS_BY_ROLE.get(role, DEFAULT_TOOLS_BY_ROLE["_default"])


def _max_iterations(agent: Agent) -> int:
    cfg = agent.tools_config or {}
    if isinstance(cfg, dict) and isinstance(cfg.get("max_iterations"), int):
        return max(1, min(20, cfg["max_iterations"]))
    return DEFAULT_MAX_ITERATIONS


async def run_agent(
    db: AsyncSession,
    agent: Agent,
    messages: list[dict],
    *,
    session_id: int | None = None,
    extras: dict | None = None,
) -> str:
    """Execute one agent turn with tool support.

    `messages` should already contain the system prompt + conversation
    history + the new user message. Returns the assistant's final text.
    """
    if not agent.llm_provider_id:
        raise LLMError("Agent has no LLM provider configured")

    provider = (await db.execute(
        select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
    )).scalar_one_or_none()
    if not provider:
        raise LLMError("Agent's LLM provider not found")

    last_user = _text_of(next(
        (m.get("content") for m in reversed(messages) if m.get("role") == "user"),
        "",
    ))
    if last_user:
        ingress = await safety_ingress(db, agent=agent, text=last_user)
        if not ingress["safe"]:
            log.info("Agent %s ingress blocked: %s", agent.id, ingress.get("reason"))
            return block_response(agent)

        try:
            shared_block = await build_shared_context_block(
                db, user_id=agent.user_id, query=last_user, limit=5
            )
        except Exception as e:  # noqa: BLE001
            log.warning("shared_context injection failed for agent %s: %s", agent.id, e)
            shared_block = ""
        if shared_block:
            sys_idx = next(
                (i for i, m in enumerate(messages) if m.get("role") == "system"),
                None,
            )
            if sys_idx is None:
                messages = [{"role": "system", "content": shared_block}, *messages]
            else:
                base = _text_of(messages[sys_idx].get("content"))
                messages[sys_idx] = {
                    "role": "system",
                    "content": f"{base}\n\n{shared_block}" if base else shared_block,
                }

    allowed = [name for name in _allowed_tools(agent) if name in REGISTRY]
    use_tools = bool(allowed) and model_supports_tools(agent.model)
    schemas = openai_schemas(allowed) if use_tools else None

    ctx = ToolContext(
        db=db, user_id=agent.user_id, agent_id=agent.id,
        session_id=session_id, extra=dict(extras or {}),
    )
    max_iter = _max_iterations(agent)

    last_content: str | None = None

    for iteration in range(max_iter):
        try:
            res = await chat_completion(provider, agent.model, messages, tools=schemas)
        except LLMError as e:
            if use_tools and "tool" in str(e).lower():
                log.warning("Model %s rejected tools, retrying without: %s", agent.model, e)
                schemas = None
                use_tools = False
                continue
            raise

        content = _text_of(res.get("content"))
        tool_calls = res.get("tool_calls")
        if content:
            last_content = content

        if not tool_calls:
            final = content or ""
            if final:
                egress = await safety_egress(db, agent=agent, text=final)
                if not egress["safe"]:
                    log.info("Agent %s egress blocked: %s", agent.id, egress.get("reason"))
                    return block_response(agent)
                schedule_extraction(
                    agent_id=agent.id,
                    user_text=last_user,
                    assistant_text=final,
                    session_id=session_id,
                )
            return final

        messages.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls,
        })

        for call in tool_calls:
            messages.append(await _execute_tool_call(call, ctx))

    log.warning("Agent %s hit max_iterations=%d, returning last content", agent.id, max_iter)
    final = last_content or "I was unable to complete the task within the allowed steps."
    if final:
        egress = await safety_egress(db, agent=agent, text=final)
        if not egress["safe"]:
            return block_response(agent)
        if last_content:
            schedule_extraction(
                agent_id=agent.id,
                user_text=last_user,
                assistant_text=final,
                session_id=session_id,
            )
    return final


async def _execute_tool_call(call: dict, ctx: ToolContext) -> dict[str, Any]:
    """Run one tool call and return the `tool` role message to append."""
    call_id = call.get("id", "")
    fn = call.get("function") or {}
    name = fn.get("name", "")
    raw_args = fn.get("arguments") or "{}"

    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
    except json.JSONDecodeError as e:
        result: Any = {"error": f"Invalid JSON arguments: {e}"}
    else:
        if name not in REGISTRY:
            result = {"error": f"Unknown tool: {name}"}
        else:
            try:
                result = await execute(name, args, ctx)
            except Exception as e:  # noqa: BLE001
                log.exception("Tool %s failed", name)
                result = {"error": str(e)}

    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(result, default=str),
    }
