# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Terminal adapter registry — one adapter per provider `type`.

Adapters self-register via @terminal_adapter decorator. Import all adapter
modules here so their decorators fire at startup and populate the registry.
"""

from app.services.terminal_adapters.base import TerminalAdapter
from app.services.terminal_adapters.registry import get_adapter, list_adapters

# Import all adapter modules to trigger @terminal_adapter registration
from app.services.terminal_adapters.ttyd import TtydAdapter
from app.services.terminal_adapters.wetty import WettyAdapter

__all__ = [
    "TerminalAdapter",
    "TtydAdapter",
    "WettyAdapter",
    "get_adapter",
    "list_adapters",
]
