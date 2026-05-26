# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Decorator-based adapter registry.

Adapters register themselves via @terminal_adapter("type") instead of manual
dict entries in __init__.py. This keeps the registry DRY and makes adding new
adapters a one-line change in the adapter file itself.

Usage:
    @terminal_adapter("ttyd")
    class TtydAdapter(TerminalAdapter):
        ...

The decorator registers the adapter instance globally. get_adapter(type) looks
it up at runtime. If a type has no registered adapter, get_adapter raises
ValueError with a clear message listing available types.
"""

from __future__ import annotations

from typing import Dict, Type

from app.services.terminal_adapters.base import TerminalAdapter

_REGISTRY: Dict[str, TerminalAdapter] = {}


def terminal_adapter(provider_type: str):
    """Decorator to register an adapter class for a given provider type.

    Args:
        provider_type: The manifest `type:` field this adapter handles

    Example:
        @terminal_adapter("ttyd")
        class TtydAdapter(TerminalAdapter):
            ...
    """
    def decorator(cls: Type[TerminalAdapter]) -> Type[TerminalAdapter]:
        if provider_type in _REGISTRY:
            raise ValueError(
                f"Adapter for type {provider_type!r} already registered: "
                f"{_REGISTRY[provider_type].__class__.__name__}"
            )
        _REGISTRY[provider_type] = cls()
        return cls
    return decorator


def get_adapter(provider_type: str) -> TerminalAdapter:
    """Look up the adapter for a given provider type.

    Args:
        provider_type: The manifest `type:` field

    Returns:
        The registered adapter instance

    Raises:
        ValueError: If no adapter is registered for this type
    """
    try:
        return _REGISTRY[provider_type]
    except KeyError as exc:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"No adapter registered for provider type {provider_type!r}. "
            f"Available: {available or '(none)'}"
        ) from exc


def list_adapters() -> Dict[str, str]:
    """Return a map of provider_type -> adapter_class_name for debugging."""
    return {k: v.__class__.__name__ for k, v in _REGISTRY.items()}


__all__ = ["terminal_adapter", "get_adapter", "list_adapters"]
