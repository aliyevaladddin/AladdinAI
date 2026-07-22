# NOTICE: This file is protected under RCF-PL
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
from app.tools import messaging  # noqa: F401
from app.tools import vision  # noqa: F401
from app.tools import image  # noqa: F401
from app.tools import github_tools  # noqa: F401
from app.tools import workspace_management  # noqa: F401
from app.tools import orders  # noqa: F401
from app.tools import web_search  # noqa: F401
from app.tools import browser  # noqa: F401
from app.tools import excel  # noqa: F401
from app.tools import python_sandbox  # noqa: F401
from app.tools import terminal_tools  # noqa: F401
from app.tools import http_tools  # noqa: F401
from app.tools import reminders  # noqa: F401

__all__ = ["REGISTRY", "Tool", "ToolContext", "execute", "openai_schemas", "tool"]
