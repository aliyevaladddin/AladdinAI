"""Tool registry primitives.

A Tool is a Python coroutine paired with a JSON-schema description that the
LLM sees during function-calling. Tools receive a `ToolContext` so they can
read the current user, db session, calling agent, and parent chat session
without each tool re-deriving them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolContext:
    db: AsyncSession
    user_id: int
    agent_id: int | None = None
    session_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


ToolFunc = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: ToolFunc

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict[str, Any]):
    """Decorator that registers a coroutine as a Tool.

    `parameters` follows JSON-schema; e.g.
        {"type": "object", "properties": {...}, "required": [...]}.
    """
    def wrap(func: ToolFunc) -> ToolFunc:
        REGISTRY[name] = Tool(name=name, description=description, parameters=parameters, func=func)
        return func
    return wrap


def openai_schemas(allowed: list[str] | None = None) -> list[dict[str, Any]]:
    """Return JSON schemas for `allowed` tools (or all if None)."""
    if allowed is None:
        return [t.openai_schema() for t in REGISTRY.values()]
    return [REGISTRY[name].openai_schema() for name in allowed if name in REGISTRY]


async def execute(name: str, args: dict[str, Any], ctx: ToolContext) -> Any:
    """Run a registered tool. Raises KeyError if name unknown."""
    t = REGISTRY[name]
    return await t.func(ctx, **(args or {}))
