"""Agent tool registry.

Each tool is a coroutine registered via `@tool(...)`. The registry exposes:
- `REGISTRY[name]` → Tool object
- `openai_schemas(allowed)` → list[dict] for NIM/OpenAI function-calling
- `execute(name, args, ctx)` → run the tool with a ToolContext

Importing the submodules below registers all built-in tools as a side effect.
"""
from app.tools.base import REGISTRY, Tool, ToolContext, execute, openai_schemas, tool

# Side-effect imports: each module registers its tools at import time.
from app.tools import inter_agent  # noqa: F401
from app.tools import memory  # noqa: F401

__all__ = ["REGISTRY", "Tool", "ToolContext", "execute", "openai_schemas", "tool"]
