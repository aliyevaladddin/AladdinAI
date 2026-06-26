# NOTICE: This file is protected under RCF-PL
"""Workspace management tools for AladdinAI.

Allows authorized agents to list, create, and manage agents, triggers,
and execution tasks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.agent import Agent
from app.models.agent_trigger import AgentTrigger
from app.models.llm_provider import LLMProvider
from app.services import triggers as triggers_service
from app.services.trigger_presets import resolve as resolve_preset
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="list_agents",
    description="List all configured AI agents in the workspace, including their ID, name, role, model, and status.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
# [RCF:PROTECTED]
async def list_agents(ctx: ToolContext) -> dict:
    try:
        q = select(Agent).where(Agent.user_id == ctx.user_id)
        result = await ctx.db.execute(q)
        agents = result.scalars().all()
        return {
            "status": "success",
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "model": a.model,
                    "status": a.status,
                    "llm_provider_id": a.llm_provider_id,
                }
                for a in agents
            ],
        }
    except Exception as e:
        log.exception("list_agents tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="create_agent",
    description=(
        "Create a new AI Agent in AladdinAI. By default, it will be started immediately. "
        "If llm_provider_id is omitted, the tool will automatically attempt to find a connected "
        "Nvidia NIM provider (type='nvidia_nim') or fallback to any connected provider."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name of the new agent (e.g., 'CRM Analyst')."},
            "role": {"type": "string", "description": "The role/category of the agent (e.g., 'sales', 'support')."},
            "model": {"type": "string", "description": "The LLM model name (e.g., 'nvidia/llama-3.1-nemotron-70b-instruct' or 'meta/llama-3.1-8b-instruct')."},
            "system_prompt": {"type": "string", "description": "Instructions / System prompt for the agent's behavior."},
            "llm_provider_id": {"type": "integer", "description": "Optional specific LLM provider ID. If omitted, the tool will auto-select one."},
        },
        "required": ["name", "role", "model", "system_prompt"],
    },
)
# [RCF:PROTECTED]
async def create_agent(
    ctx: ToolContext,
    name: str,
    role: str,
    model: str,
    system_prompt: str,
    llm_provider_id: int | None = None,
) -> dict:
    try:
        # Check if agent with this name already exists
        existing = await ctx.db.execute(
            select(Agent).where(Agent.name == name, Agent.user_id == ctx.user_id)
        )
        if existing.scalar_one_or_none():
            return {"status": "error", "message": f"Agent with name '{name}' already exists."}

        # If llm_provider_id is not provided, try to find a suitable provider
        if not llm_provider_id:
            # Look for nvidia_nim first
            provider_q = select(LLMProvider).where(
                LLMProvider.user_id == ctx.user_id,
                LLMProvider.status == "connected",
                LLMProvider.type == "nvidia_nim"
            )
            provider = (await ctx.db.execute(provider_q)).scalar_one_or_none()
            if not provider:
                # Fallback to any connected provider
                provider_q = select(LLMProvider).where(
                    LLMProvider.user_id == ctx.user_id,
                    LLMProvider.status == "connected"
                )
                provider = (await ctx.db.execute(provider_q)).scalar_one_or_none()

            if not provider:
                return {
                    "status": "error",
                    "message": "No connected LLM providers found. Please connect an LLM provider first.",
                }
            llm_provider_id = provider.id

        agent = Agent(
            user_id=ctx.user_id,
            name=name,
            role=role,
            model=model,
            system_prompt=system_prompt,
            llm_provider_id=llm_provider_id,
            status="running",
        )
        ctx.db.add(agent)
        await ctx.db.flush()  # populate ID
        return {
            "status": "success",
            "agent_id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "model": agent.model,
            "llm_provider_id": agent.llm_provider_id,
            "status_state": agent.status,
        }
    except Exception as e:
        log.exception("create_agent tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="start_agent",
    description="Start a stopped agent in AladdinAI by ID.",
    parameters={
        "type": "object",
        "properties": {
            "agent_id": {"type": "integer", "description": "The ID of the agent to start."},
        },
        "required": ["agent_id"],
    },
)
# [RCF:PROTECTED]
async def start_agent(ctx: ToolContext, agent_id: int) -> dict:
    try:
        q = select(Agent).where(Agent.id == agent_id, Agent.user_id == ctx.user_id)
        agent = (await ctx.db.execute(q)).scalar_one_or_none()
        if not agent:
            return {"status": "error", "message": f"Agent {agent_id} not found."}
        agent.status = "running"
        await ctx.db.flush()
        return {"status": "success", "agent_id": agent.id, "state": agent.status}
    except Exception as e:
        log.exception("start_agent tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="stop_agent",
    description="Stop a running agent in AladdinAI by ID.",
    parameters={
        "type": "object",
        "properties": {
            "agent_id": {"type": "integer", "description": "The ID of the agent to stop."},
        },
        "required": ["agent_id"],
    },
)
# [RCF:PROTECTED]
async def stop_agent(ctx: ToolContext, agent_id: int) -> dict:
    try:
        q = select(Agent).where(Agent.id == agent_id, Agent.user_id == ctx.user_id)
        agent = (await ctx.db.execute(q)).scalar_one_or_none()
        if not agent:
            return {"status": "error", "message": f"Agent {agent_id} not found."}
        agent.status = "stopped"
        await ctx.db.flush()
        return {"status": "success", "agent_id": agent.id, "state": agent.status}
    except Exception as e:
        log.exception("stop_agent tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="list_triggers",
    description="List all configured automation triggers/schedules.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
# [RCF:PROTECTED]
async def list_triggers(ctx: ToolContext) -> dict:
    try:
        q = select(AgentTrigger).where(AgentTrigger.user_id == ctx.user_id)
        result = await ctx.db.execute(q)
        triggers = result.scalars().all()
        return {
            "status": "success",
            "triggers": [
                {
                    "id": t.id,
                    "name": t.name,
                    "schedule_kind": t.schedule_kind,
                    "schedule_preset": t.schedule_preset,
                    "cron": t.cron,
                    "agent_ids": t.agent_ids,
                    "task_template": t.task_template,
                    "enabled": t.enabled,
                }
                for t in triggers
            ],
        }
    except Exception as e:
        log.exception("list_triggers tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="create_trigger",
    description=(
        "Create a new automation trigger/schedule in AladdinAI. "
        "Allows periodic tasks to be fanned out to agents. "
        "Requires schedule_kind: 'preset' (using schedule_preset like 'every_morning_9', 'every_hour') "
        "or 'cron' (using a standard cron expression in `cron` parameter)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Descriptive name for the trigger (e.g., 'Daily CRM Check')."},
            "schedule_kind": {"type": "string", "enum": ["preset", "cron"], "description": "Kind of schedule ('preset' or 'cron')."},
            "schedule_preset": {"type": "string", "description": "Preset name (e.g., 'every_morning_9', 'every_hour', 'every_midnight', 'every_monday_morning_9'). Required if schedule_kind='preset'."},
            "cron": {"type": "string", "description": "Standard 5-field cron expression. Required if schedule_kind='cron'."},
            "agent_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "IDs of the agents that should receive the task when the trigger fires.",
            },
            "task_template": {"type": "string", "description": "The task prompt instructions that will be sent to the agents when fired."},
            "context_template": {
                "type": "object",
                "description": "Optional dict containing static context data/instructions for the task.",
                "additionalProperties": True,
            },
        },
        "required": ["name", "schedule_kind", "agent_ids", "task_template"],
    },
)
# [RCF:PROTECTED]
async def create_trigger(
    ctx: ToolContext,
    name: str,
    schedule_kind: str,
    agent_ids: list[int],
    task_template: str,
    schedule_preset: str | None = None,
    cron: str | None = None,
    context_template: dict | None = None,
) -> dict:
    try:
        # Validate agents exist
        if not agent_ids:
            return {"status": "error", "message": "agent_ids list cannot be empty"}
        agent_rows = (await ctx.db.execute(
            select(Agent.id).where(Agent.user_id == ctx.user_id, Agent.id.in_(agent_ids))
        )).scalars().all()
        found = set(agent_rows)
        missing = [aid for aid in agent_ids if aid not in found]
        if missing:
            return {"status": "error", "message": f"Agents not found or unauthorized: {missing}"}

        # Resolve cron
        try:
            if schedule_kind == "preset":
                if not schedule_preset:
                    return {"status": "error", "message": "schedule_preset is required when schedule_kind='preset'"}
                resolved_cron = resolve_preset(schedule_preset)
                if not resolved_cron:
                    return {"status": "error", "message": f"unknown schedule preset: {schedule_preset}"}
            else:
                if not cron:
                    return {"status": "error", "message": "cron expression is required when schedule_kind='cron'"}
                triggers_service.validate_cron(cron)
                resolved_cron = cron
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        trig = AgentTrigger(
            user_id=ctx.user_id,
            name=name,
            schedule_kind=schedule_kind,
            schedule_preset=schedule_preset if schedule_kind == "preset" else None,
            cron=resolved_cron,
            agent_ids=agent_ids,
            task_template=task_template,
            context_template=context_template,
            enabled=True,
            next_fire_at=triggers_service.next_fire(resolved_cron),
        )
        ctx.db.add(trig)
        await ctx.db.flush()

        # Update planning service
        triggers_service.upsert(trig)

        return {
            "status": "success",
            "trigger_id": trig.id,
            "name": trig.name,
            "cron": trig.cron,
            "next_fire_at": trig.next_fire_at.isoformat() if trig.next_fire_at else None,
        }
    except Exception as e:
        log.exception("create_trigger tool failed")
        return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="run_trigger",
    description="Run a trigger/automation now manually by ID.",
    parameters={
        "type": "object",
        "properties": {
            "trigger_id": {"type": "integer", "description": "The ID of the trigger to fire now."},
        },
        "required": ["trigger_id"],
    },
)
# [RCF:PROTECTED]
async def run_trigger(ctx: ToolContext, trigger_id: int) -> dict:
    try:
        # Check ownership
        q = select(AgentTrigger).where(AgentTrigger.id == trigger_id, AgentTrigger.user_id == ctx.user_id)
        trig = (await ctx.db.execute(q)).scalar_one_or_none()
        if not trig:
            return {"status": "error", "message": f"Trigger {trigger_id} not found."}

        message_ids = await triggers_service.run_now(trig.id)
        return {
            "status": "success",
            "message_ids": message_ids,
            "fired_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.exception("run_trigger tool failed")
        return {"status": "error", "message": str(e)}
