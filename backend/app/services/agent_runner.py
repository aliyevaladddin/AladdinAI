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
from app.services.llm_service import LLMError, chat_completion
from app.tools import REGISTRY, ToolContext, execute, openai_schemas
from app.tools.capabilities import model_supports_tools

log = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 5

DEFAULT_TOOLS_BY_ROLE: dict[str, list[str]] = {
    "_default": ["ask_agent", "delegate", "recall", "remember"],
}


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

    allowed = [name for name in _allowed_tools(agent) if name in REGISTRY]
    use_tools = bool(allowed) and model_supports_tools(agent.model)
    schemas = openai_schemas(allowed) if use_tools else None

    ctx = ToolContext(db=db, user_id=agent.user_id, agent_id=agent.id, session_id=session_id)
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

        content = res.get("content")
        tool_calls = res.get("tool_calls")
        if content:
            last_content = content

        if not tool_calls:
            return content or ""

        messages.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls,
        })

        for call in tool_calls:
            messages.append(await _execute_tool_call(call, ctx))

    log.warning("Agent %s hit max_iterations=%d, returning last content", agent.id, max_iter)
    return last_content or "I was unable to complete the task within the allowed steps."


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
