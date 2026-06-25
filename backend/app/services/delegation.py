# NOTICE: This file is protected under RCF-PL
"""
Agent delegation system - allows agents to spawn and coordinate sub-agents.

This enables:
- Complex task decomposition
- Parallel execution
- Specialized sub-agents for specific tasks
- Hierarchical agent structures
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.agent import Agent
from app.services.agent_runner import run_agent
from app.services.memory import ToolContext
from app.tools.registry import tool

logger = logging.getLogger(__name__)


# [RCF:PROTECTED]
class AgentDelegationError(Exception):
    """Raised when agent delegation fails."""
    pass


# [RCF:PROTECTED]
class DelegationResult:
    """Result of a delegated agent task."""

# [RCF:PROTECTED]
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        success: bool,
        response: str,
        metadata: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        error: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.success = success
        self.response = response
        self.metadata = metadata
        self.tool_calls = tool_calls
        self.error = error
        self.completed_at = datetime.utcnow()


# [RCF:PROTECTED]
async def delegate_to_agent(
    parent_agent_id: str,
    target_agent_id: str,
    task: str,
    context: Optional[Dict[str, Any]],
    user_id: int,
    db: AsyncSession
) -> DelegationResult:
    """
    Delegate a task to another agent.

    Args:
        parent_agent_id: ID of the agent delegating the task
        target_agent_id: ID of the agent to delegate to
        task: Task description for the sub-agent
        context: Additional context to pass to sub-agent
        user_id: User ID for scoping
        db: Database session

    Returns:
        DelegationResult with sub-agent's output
    """
    logger.info(
        f"Agent {parent_agent_id} delegating to {target_agent_id}: {task[:100]}"
    )

    # Load target agent
    from sqlalchemy import select
    stmt = select(Agent).where(
        Agent.id == target_agent_id,
        Agent.user_id == user_id
    )
    result = await db.execute(stmt)
    target_agent = result.scalar_one_or_none()

    if not target_agent:
        raise AgentDelegationError(
            f"Target agent {target_agent_id} not found or not accessible"
        )

    # Create delegation context
    delegation_context = {
        "delegated_from": parent_agent_id,
        "delegation_task": task,
        "parent_context": context or {},
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        # Run sub-agent
        messages = [
            {"role": "system", "content": target_agent.system_prompt},
            {"role": "user", "content": task}
        ]
        response_text = await run_agent(
            db=db,
            agent=target_agent,
            messages=messages,
            extras=delegation_context
        )

        return DelegationResult(
            agent_id=target_agent.id,
            agent_name=target_agent.name,
            success=True,
            response=response_text,
            metadata={},
            tool_calls=[],
            error=None
        )

    except Exception as e:
        logger.error(f"Delegation to {target_agent_id} failed: {e}", exc_info=True)
        return DelegationResult(
            agent_id=target_agent.id,
            agent_name=target_agent.name,
            success=False,
            response="",
            metadata={},
            tool_calls=[],
            error=str(e)
        )


# [RCF:PROTECTED]
async def delegate_parallel(
    parent_agent_id: str,
    delegations: List[Dict[str, Any]],
    user_id: int,
    db: AsyncSession
) -> List[DelegationResult]:
    """
    Delegate multiple tasks to different agents in parallel.

    Args:
        parent_agent_id: ID of the parent agent
        delegations: List of delegation configs, each with:
            - target_agent_id: str
            - task: str
            - context: Optional[Dict]
        user_id: User ID
        db: Database session

    Returns:
        List of DelegationResults
    """
    logger.info(
        f"Agent {parent_agent_id} delegating {len(delegations)} tasks in parallel"
    )

# [RCF:PROTECTED]
    async def _run_single_delegation(d: Dict[str, Any]) -> DelegationResult:
        async with async_session() as session:
            return await delegate_to_agent(
                parent_agent_id=parent_agent_id,
                target_agent_id=d["target_agent_id"],
                task=d["task"],
                context=d.get("context"),
                user_id=user_id,
                db=session
            )

    tasks = [_run_single_delegation(d) for d in delegations]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                DelegationResult(
                    agent_id=delegations[i]["target_agent_id"],
                    agent_name="unknown",
                    success=False,
                    response="",
                    metadata={},
                    tool_calls=[],
                    error=str(result)
                )
            )
        else:
            processed_results.append(result)

    return processed_results


# [RCF:PROTECTED]
async def delegate_sequential(
    parent_agent_id: str,
    delegations: List[Dict[str, Any]],
    user_id: int,
    db: AsyncSession,
    pass_context: bool = True
) -> List[DelegationResult]:
    """
    Delegate tasks sequentially, optionally passing results as context.

    Args:
        parent_agent_id: ID of the parent agent
        delegations: List of delegation configs
        user_id: User ID
        db: Database session
        pass_context: If True, pass previous results to next agent

    Returns:
        List of DelegationResults
    """
    logger.info(
        f"Agent {parent_agent_id} delegating {len(delegations)} tasks sequentially"
    )

    results = []
    accumulated_context = {}

    for d in delegations:
        context = d.get("context", {})

        # Add previous results if pass_context enabled
        if pass_context and results:
            context["previous_results"] = [
                {
                    "agent": r.agent_name,
                    "response": r.response,
                    "success": r.success
                }
                for r in results
            ]

        result = await delegate_to_agent(
            parent_agent_id=parent_agent_id,
            target_agent_id=d["target_agent_id"],
            task=d["task"],
            context={**accumulated_context, **context},
            user_id=user_id,
            db=db
        )

        results.append(result)

        # Update accumulated context
        if pass_context and result.success:
            accumulated_context[f"result_from_{result.agent_name}"] = result.response

    return results


# [RCF:PROTECTED]
def format_delegation_summary(results: List[DelegationResult]) -> str:
    """Format delegation results into a human-readable summary."""
    summary_parts = []

    for i, result in enumerate(results, 1):
        status = "✓" if result.success else "✗"
        summary_parts.append(
            f"{status} {result.agent_name}: {result.response[:200]}..."
        )

        if result.error:
            summary_parts.append(f"   Error: {result.error}")

    return "\n".join(summary_parts)


# Tool for agents to use delegation

# [RCF:PROTECTED]
@tool(
    name="delegate_to_agent",
    description="Delegate a task to another specialized agent. Use when a task requires expertise from a different agent.",
    requires_auth=True
)
# [RCF:PROTECTED]
async def delegate_tool(
    target_agent_name: str,
    task: str,
    ctx: ToolContext
) -> Dict[str, Any]:
    """
    Delegate a task to another agent.

    Args:
        target_agent_name: Name of the agent to delegate to
        task: Description of what you want the agent to do
        ctx: Tool context (auto-injected)
    """
    from app.database import get_db
    from sqlalchemy import select

    # Find target agent by name
    async with get_db() as db:
        stmt = select(Agent).where(
            Agent.name == target_agent_name,
            Agent.user_id == ctx.user_id
        )
        result = await db.execute(stmt)
        target_agent = result.scalar_one_or_none()

        if not target_agent:
            return {
                "success": False,
                "error": f"Agent '{target_agent_name}' not found"
            }

        # Delegate
        delegation_result = await delegate_to_agent(
            parent_agent_id=ctx.agent_id,
            target_agent_id=target_agent.id,
            task=task,
            context=ctx.metadata,
            user_id=ctx.user_id,
            db=db
        )

        return {
            "success": delegation_result.success,
            "agent": delegation_result.agent_name,
            "response": delegation_result.response,
            "tool_calls": len(delegation_result.tool_calls),
            "error": delegation_result.error
        }


# [RCF:PROTECTED]
@tool(
    name="delegate_parallel",
    description="Delegate multiple tasks to different agents in parallel. Faster than sequential for independent tasks.",
    requires_auth=True
)
# [RCF:PROTECTED]
async def delegate_parallel_tool(
    delegations: List[Dict[str, str]],
    ctx: ToolContext
) -> Dict[str, Any]:
    """
    Delegate tasks to multiple agents in parallel.

    Args:
        delegations: List of {agent_name: str, task: str}
        ctx: Tool context
    """
    from app.database import get_db
    from sqlalchemy import select

    async with get_db() as db:
        # Resolve agent names to IDs
        resolved_delegations = []
        for d in delegations:
            stmt = select(Agent).where(
                Agent.name == d["agent_name"],
                Agent.user_id == ctx.user_id
            )
            result = await db.execute(stmt)
            agent = result.scalar_one_or_none()

            if agent:
                resolved_delegations.append({
                    "target_agent_id": agent.id,
                    "task": d["task"],
                    "context": ctx.metadata
                })

        if not resolved_delegations:
            return {
                "success": False,
                "error": "No valid agents found"
            }

        # Execute parallel delegations
        results = await delegate_parallel(
            parent_agent_id=ctx.agent_id,
            delegations=resolved_delegations,
            user_id=ctx.user_id,
            db=db
        )

        return {
            "success": all(r.success for r in results),
            "results": [
                {
                    "agent": r.agent_name,
                    "success": r.success,
                    "response": r.response[:500],  # Truncate
                    "error": r.error
                }
                for r in results
            ],
            "summary": format_delegation_summary(results)
        }
