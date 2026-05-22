# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Terminal adapter registry — one adapter per provider `type`.

All builtin plugins in the MVP are HTTP-behind-Traefik, so they share the
`GenericHttpAdapter`. The map is still keyed by `type` because future plugins
(Guacamole, SSH-proxy) will diverge and need their own adapter classes.
"""

from typing import Dict

from app.services.terminal_adapters.base import TerminalAdapter
from app.services.terminal_adapters.generic_http import GenericHttpAdapter
from app.services.terminal_adapters.ttyd import TtydAdapter

# Keyed by `TerminalProvider.type` (the manifest's `type:`). Add new entries
# here as new builtin adapters land.
_ADAPTERS: Dict[str, TerminalAdapter] = {
    "ttyd": TtydAdapter(),
    "wetty": GenericHttpAdapter(adapter_label="wetty"),
    "code-server": GenericHttpAdapter(adapter_label="code-server"),
}


def get_adapter(provider_type: str) -> TerminalAdapter:
    try:
        return _ADAPTERS[provider_type]
    except KeyError as exc:
        raise ValueError(f"No adapter registered for provider type {provider_type!r}") from exc


__all__ = ["TerminalAdapter", "GenericHttpAdapter", "get_adapter"]
