"""Inter-agent communication tools.

`delegate` queues an async handoff (writes a row to `agent_messages` with
status=pending; a worker processes it later). `ask_agent` is the synchronous
sibling — runs the target agent inline and returns its reply text.

Both tools resolve `target` either by integer agent id or by role string
(case-insensitive). Resolution is scoped to `ctx.user_id` so an agent
cannot reach across tenants.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.llm_provider import LLMProvider
from app.services.llm_service import LLMError, chat_completion
from app.tools.base import ToolContext, tool


async def _resolve_target(ctx: ToolContext, target: str | int) -> Agent | None:
    if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
        q = select(Agent).where(Agent.id == int(target), Agent.user_id == ctx.user_id)
    else:
        q = select(Agent).where(Agent.user_id == ctx.user_id).where(
            Agent.role.ilike(str(target))
        )
    result = await ctx.db.execute(q)
    return result.scalars().first()


@tool(
    name="delegate",
    description=(
        "Queue a task for another agent to handle asynchronously. Use when the "
        "task needs deeper work (writing, research, multi-step) and you can "
        "continue without waiting for the result. Returns a message_id you can "
        "reference later."
    ),
    parameters={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target agent — either numeric id ('7') or role ('sales', 'support').",
            },
            "task": {
                "type": "string",
                "description": "Plain-language description of what the target agent should do.",
            },
            "context": {
                "type": "object",
                "description": "Optional structured context (contact_id, facts, prior messages).",
                "additionalProperties": True,
            },
        },
        "required": ["target", "task"],
    },
)
async def delegate(ctx: ToolContext, target: str, task: str, context: dict | None = None) -> dict:
    target_agent = await _resolve_target(ctx, target)
    if not target_agent:
        return {"error": f"No agent found for target={target!r}"}

    msg = AgentMessage(
        user_id=ctx.user_id,
        from_agent_id=ctx.agent_id,
        to_agent_id=target_agent.id,
        parent_session_id=ctx.session_id,
        task=task,
        context=context,
        status="pending",
    )
    ctx.db.add(msg)
    await ctx.db.flush()
    return {
        "message_id": msg.id,
        "to_agent_id": target_agent.id,
        "to_agent_name": target_agent.name,
        "status": "pending",
    }


@tool(
    name="ask_agent",
    description=(
        "Synchronously ask another agent a question and get its answer back "
        "as text. Use for quick lookups where you need the answer to continue "
        "your own response. For longer work prefer `delegate`."
    ),
    parameters={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target agent — either numeric id ('7') or role ('sales', 'support').",
            },
            "question": {
                "type": "string",
                "description": "The question to ask the target agent.",
            },
        },
        "required": ["target", "question"],
    },
)
async def ask_agent(ctx: ToolContext, target: str, question: str) -> dict:
    target_agent = await _resolve_target(ctx, target)
    if not target_agent:
        return {"error": f"No agent found for target={target!r}"}
    if not target_agent.llm_provider_id:
        return {"error": f"Agent {target_agent.name} has no LLM provider configured"}

    provider_q = select(LLMProvider).where(LLMProvider.id == target_agent.llm_provider_id)
    provider = (await ctx.db.execute(provider_q)).scalar_one_or_none()
    if not provider:
        return {"error": "Target agent's provider not found"}

    messages = [
        {"role": "system", "content": target_agent.system_prompt},
        {"role": "user", "content": question},
    ]

    log = AgentMessage(
        user_id=ctx.user_id,
        from_agent_id=ctx.agent_id,
        to_agent_id=target_agent.id,
        parent_session_id=ctx.session_id,
        task=question,
        status="in_progress",
    )
    ctx.db.add(log)
    await ctx.db.flush()

    try:
        res = await chat_completion(provider, target_agent.model, messages)
        answer = res["content"] or ""
        log.status = "done"
        log.result = answer
        log.completed_at = datetime.now(timezone.utc)
        await ctx.db.flush()
        return {
            "message_id": log.id,
            "from_agent_name": target_agent.name,
            "answer": answer,
        }
    except LLMError as e:
        log.status = "failed"
        log.error = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await ctx.db.flush()
        return {"error": str(e)}
