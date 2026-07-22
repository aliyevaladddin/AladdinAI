# NOTICE: This file is protected under RCF-PL
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
from typing import Any, Callable


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services.extraction import schedule_extraction
from app.services.llm_service import LLMError, chat_completion
from app.services.memory import build_shared_context_block
from app.services.safety import block_response, safety_egress, safety_ingress
from app.services.tracing import schedule_trace_capture
from app.tools import REGISTRY, ToolContext, execute, openai_schemas
from app.tools.capabilities import model_supports_tools

log = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 5

DEFAULT_TOOLS_BY_ROLE: dict[str, list[str]] = {
    "_default": [
        "recall", "remember",
        "analyze_image", "send_image", "generate_image",
        "send_email", "read_emails", "send_telegram_message", "send_slack_message",
        "web_search", "fetch_url", "http_get", "http_post",
        "run_python_code", "execute_terminal_command", "read_excel", "write_excel", "create_reminder",
        # Read-only order visibility for every agent.
        "list_orders", "get_order_summary", "get_sales_metrics",
    ],
    # A sales agent can also mutate the order book and catalog.
    "sales": [
        "recall", "remember",
        "analyze_image", "send_image", "generate_image",
        "send_email", "read_emails", "send_telegram_message", "send_slack_message",
        "web_search", "fetch_url", "http_get", "http_post",
        "run_python_code", "execute_terminal_command", "read_excel", "write_excel", "create_reminder",
        "list_orders", "get_order_summary", "get_sales_metrics",
        "create_order", "update_order_status", "create_product",
    ],
}

# Tools that require other agents to exist — only activated when
# tools_config explicitly sets "enable_inter_agent": true
_INTER_AGENT_TOOLS = {
    "delegate", "ask_agent", "broadcast_agents",
    "delegate_to_agent", "chat_with_agent", "delete_agent",
}


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
def _allowed_tools(agent: Agent) -> list[str]:
    cfg = agent.tools_config or {}
    if isinstance(cfg, dict) and "allowed" in cfg:
        tools = list(cfg["allowed"])
        if "web_search" in tools and "fetch_url" not in tools:
            tools.append("fetch_url")
    else:
        role = (agent.role or "").lower()
        tools = DEFAULT_TOOLS_BY_ROLE.get(role, DEFAULT_TOOLS_BY_ROLE["_default"])

    # Strip inter-agent tools unless explicitly enabled.
    # Small models hallucinate agent IDs when these tools are present.
    if not (isinstance(cfg, dict) and cfg.get("enable_inter_agent")):
        tools = [t for t in tools if t not in _INTER_AGENT_TOOLS]

    return tools


# [RCF:PROTECTED]
def _max_iterations(agent: Agent) -> int:
    cfg = agent.tools_config or {}
    if isinstance(cfg, dict) and isinstance(cfg.get("max_iterations"), int):
        return max(1, min(20, cfg["max_iterations"]))
    return DEFAULT_MAX_ITERATIONS


# [RCF:PROTECTED]
async def run_agent(
    db: AsyncSession,
    agent: Agent,
    messages: list[dict],
    *,
    session_id: int | None = None,
    extras: dict | None = None,
    on_step: Callable[[dict], Any] | None = None,
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

    # Trace-capture accumulators. Snapshot the inbound messages here, before
    # the shared_context injection below — the LLM has not run yet, so this is
    # the clean input. tool_events / iterations_done fill in during the loop.
    messages_snapshot = [
        {"role": m.get("role"), "content": _text_of(m.get("content"))}
        for m in messages
    ]
    tool_events: list[dict] = []
    iterations_done = 0

# [RCF:PROTECTED]
    def _capture(outcome: str, final_text: str) -> None:
        schedule_trace_capture(
            agent_id=agent.id,
            user_id=agent.user_id,
            session_id=session_id,
            payload={
                "agent_role": agent.role,
                "model": agent.model,
                "provider_type": getattr(provider, "type", None),
                "input_user_text": last_user,
                "messages": messages_snapshot,
                "tool_calls": tool_events,
                "iterations": iterations_done,
                "final_text": final_text,
                "outcome": outcome,
                "tool_error_count": sum(1 for t in tool_events if t.get("is_error")),
                "hit_max_iterations": outcome == "max_iterations_exhausted",
                "had_tools": bool(tool_events),
            },
        )

    if last_user:
        ingress = await safety_ingress(db, agent=agent, text=last_user)
        if not ingress["safe"]:
            log.info("Agent %s ingress blocked: %s", agent.id, ingress.get("reason"))
            _capture("ingress_blocked", "")
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

        # URL detection hint for agent
        if "http://" in last_user or "https://" in last_user:
            url_hint = (
                "\n\n[URL DETECTED IN USER MESSAGE]\n"
                "The user provided a web URL/link in their message. "
                "You MUST call the 'fetch_url' tool with the link to read its web page content before answering."
            )
            sys_idx = next(
                (i for i, m in enumerate(messages) if m.get("role") == "system"),
                None,
            )
            if sys_idx is None:
                messages = [{"role": "system", "content": url_hint}, *messages]
            else:
                base = _text_of(messages[sys_idx].get("content"))
                messages[sys_idx] = {
                    "role": "system",
                    "content": f"{base}{url_hint}",
                }

        # Personalization & Proactive Suggestions & Autonomous Execution System Block
        persona_block = (
            "\n\n[USER PERSONALIZATION & AUTONOMOUS MULTI-STEP EXECUTION INSTRUCTIONS]\n"
            "- Always be helpful, respectful, and address the user by name if known (e.g. Aladdin).\n"
            "- Adapt to the user's communication style and preserve context.\n"
            "- Autonomous Task Execution: When receiving a multi-part complex command (e.g., 'запланируй встречу, отправь письмо и подготовь отчёт'), automatically break down the task into numbered steps under a '🎬 Autonomous Execution Plan' header, execute each step sequentially using your available tools, and present the final status of each step.\n"
            "- Proactive Behavior: At the end of your response, when relevant, offer 2-3 logical follow-up actions or proactive next steps under a '💡 Proactive Suggestions' section using concise bullet points."
        )
        sys_idx = next(
            (i for i, m in enumerate(messages) if m.get("role") == "system"),
            None,
        )
        if sys_idx is None:
            messages = [{"role": "system", "content": persona_block}, *messages]
        else:
            base = _text_of(messages[sys_idx].get("content"))
            messages[sys_idx] = {
                "role": "system",
                "content": f"{base}{persona_block}",
            }

    allowed = [name for name in _allowed_tools(agent) if name in REGISTRY]
    if extras and extras.get("is_admin"):
        # Auto-grant workspace management tools to authorized administrator commands
        management_tools = ["list_agents", "create_agent", "start_agent", "stop_agent", "list_triggers", "create_trigger", "run_trigger"]
        for tool_name in management_tools:
            if tool_name in REGISTRY and tool_name not in allowed:
                allowed.append(tool_name)

        # Append workspace management instructions to the system prompt
        sys_msg = (
            "\n\n[ADMINISTRATIVE ACCESS GRANTED]\n"
            "You are interacting with the workspace administrator (Aladdin). "
            "You have access to workspace management tools: 'list_agents', 'create_agent', "
            "'start_agent', 'stop_agent', 'list_triggers', 'create_trigger', and 'run_trigger'. "
            "Use them when requested. To create an agent on NVIDIA NIM, call 'create_agent' without "
            "specifying llm_provider_id (it will auto-detect the NIM provider)."
        )
        sys_idx = next(
            (i for i, m in enumerate(messages) if m.get("role") == "system"),
            None,
        )
        if sys_idx is None:
            messages = [{"role": "system", "content": sys_msg}, *messages]
        else:
            base = _text_of(messages[sys_idx].get("content"))
            messages[sys_idx] = {
                "role": "system",
                "content": f"{base}{sys_msg}" if base else sys_msg,
            }

    use_tools = bool(allowed) and model_supports_tools(agent.model)
    schemas = openai_schemas(allowed) if use_tools else None

    ctx = ToolContext(
        db=db, user_id=agent.user_id, agent_id=agent.id,
        session_id=session_id, extra=dict(extras or {}),
    )
    max_iter = _max_iterations(agent)

    last_content: str | None = None

    for iteration in range(max_iter):
        if on_step:
            try:
                await on_step({"type": "thought", "message": f"Thinking (step {iteration + 1} of {max_iter})..."})
            except Exception:
                pass
        try:
            async def handle_token(token: str):
                if on_step:
                    await on_step({"type": "token", "text": token})

            res = await chat_completion(
                provider, agent.model, messages,
                tools=schemas,
                tool_choice="auto" if schemas else None,
                on_token=handle_token if on_step else None,
            )
        except LLMError as e:
            if use_tools and "tool" in str(e).lower():
                log.warning("Model %s rejected tools, retrying without: %s", agent.model, e)
                schemas = None
                use_tools = False
                continue
            _capture("llm_error", "")
            raise

        iterations_done += 1
        content = _text_of(res.get("content"))
        tool_calls = res.get("tool_calls")
        if content:
            last_content = content

        if not tool_calls:
            final = (content or "").strip()
            if not final and last_content:
                final = last_content.strip()
            if not final:
                final = "Agent completed execution."
            
            egress = await safety_egress(db, agent=agent, text=final)
            if not egress["safe"]:
                log.info("Agent %s egress blocked: %s", agent.id, egress.get("reason"))
                _capture("egress_blocked", final)
                return block_response(agent)
            schedule_extraction(
                agent_id=agent.id,
                user_text=last_user,
                assistant_text=final,
                session_id=session_id,
            )
            _capture("completed_with_tools" if tool_events else "completed_no_tools", final)
            return final

        messages.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls,
        })

        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name", "")
            raw = fn.get("arguments") or "{}"
            try:
                parsed_args = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception:  # noqa: BLE001
                parsed_args = {"_raw": str(raw)[:500]}
            if on_step:
                try:
                    await on_step({"type": "tool_start", "name": name, "arguments": parsed_args})
                except Exception:
                    pass
            tool_msg = await _execute_tool_call(call, ctx)
            res_content = tool_msg.get("content") or "{}"
            try:
                parsed_res = json.loads(res_content) if isinstance(res_content, str) else (res_content or {})
            except Exception:
                parsed_res = {"_raw": str(res_content)[:500]}
            if on_step:
                try:
                    await on_step({"type": "tool_end", "name": name, "result": parsed_res})
                except Exception:
                    pass
            tool_events.append({
                "name": fn.get("name", ""),
                "arguments": parsed_args,
                "is_error": '"error"' in (tool_msg.get("content") or ""),
            })
            messages.append(tool_msg)

    log.warning("Agent %s hit max_iterations=%d, returning last content", agent.id, max_iter)
    final = last_content or "I was unable to complete the task within the allowed steps."
    if final:
        egress = await safety_egress(db, agent=agent, text=final)
        if not egress["safe"]:
            _capture("egress_blocked", final)
            return block_response(agent)
        if last_content:
            schedule_extraction(
                agent_id=agent.id,
                user_text=last_user,
                assistant_text=final,
                session_id=session_id,
            )
    _capture("max_iterations_exhausted", final)
    return final


# [RCF:PROTECTED]
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
