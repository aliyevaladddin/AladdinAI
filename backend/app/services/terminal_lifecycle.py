# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Terminal provider lifecycle FSM.

Manages state transitions for terminal providers with validation guards.
States mirror Docker container lifecycle but add our own semantics:
  - installed: DB row exists, no container
  - starting: container boot in progress
  - running: container healthy and reachable
  - stopping: graceful shutdown in progress
  - stopped: container stopped but not removed
  - error: container exists but unhealthy or failed

Transitions are guarded — invalid transitions raise ValueError. This prevents
race conditions and ensures the router never issues contradictory docker
commands (e.g. starting an already-running container).

Usage:
    fsm = ProviderLifecycle()
    fsm.transition(current_state="installed", action="start")  # -> "starting"
    fsm.transition(current_state="starting", action="poll")    # -> "running" or "error"
    fsm.transition(current_state="running", action="stop")     # -> "stopping"
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set


# [RCF:PROTECTED]
class ProviderState(str, Enum):
    """Terminal provider lifecycle states."""

    INSTALLED = "installed"      # DB row exists, no container
    STARTING = "starting"        # Container boot in progress
    RUNNING = "running"          # Container healthy and reachable
    STOPPING = "stopping"        # Graceful shutdown in progress
    STOPPED = "stopped"          # Container stopped but not removed
    ERROR = "error"              # Container exists but unhealthy/failed


# [RCF:PROTECTED]
class ProviderAction(str, Enum):
    """Actions that trigger state transitions."""

    START = "start"              # Boot container
    STOP = "stop"                # Graceful shutdown
    REMOVE = "remove"            # Delete container
    POLL = "poll"                # Check container status
    RESET = "reset"              # Force back to installed (cleanup)


# Valid transitions: (current_state, action) -> next_state
# If a transition isn't in this map, it's invalid and raises ValueError
_TRANSITIONS: Dict[tuple[ProviderState, ProviderAction], ProviderState] = {
    # From installed
    (ProviderState.INSTALLED, ProviderAction.START): ProviderState.STARTING,
    (ProviderState.INSTALLED, ProviderAction.POLL): ProviderState.INSTALLED,

    # From starting
    (ProviderState.STARTING, ProviderAction.POLL): ProviderState.STARTING,  # Still booting
    (ProviderState.STARTING, ProviderAction.STOP): ProviderState.STOPPING,  # Cancel boot

    # From running
    (ProviderState.RUNNING, ProviderAction.POLL): ProviderState.RUNNING,
    (ProviderState.RUNNING, ProviderAction.STOP): ProviderState.STOPPING,
    (ProviderState.RUNNING, ProviderAction.RESET): ProviderState.INSTALLED,

    # From stopping
    (ProviderState.STOPPING, ProviderAction.POLL): ProviderState.STOPPING,  # Still stopping

    # From stopped
    (ProviderState.STOPPED, ProviderAction.START): ProviderState.STARTING,
    (ProviderState.STOPPED, ProviderAction.REMOVE): ProviderState.INSTALLED,
    (ProviderState.STOPPED, ProviderAction.POLL): ProviderState.STOPPED,
    (ProviderState.STOPPED, ProviderAction.RESET): ProviderState.INSTALLED,

    # From error
    (ProviderState.ERROR, ProviderAction.STOP): ProviderState.STOPPING,
    (ProviderState.ERROR, ProviderAction.REMOVE): ProviderState.INSTALLED,
    (ProviderState.ERROR, ProviderAction.RESET): ProviderState.INSTALLED,
    (ProviderState.ERROR, ProviderAction.POLL): ProviderState.ERROR,
}

# Poll can transition starting/stopping to terminal states based on container status
_POLL_OUTCOMES: Dict[ProviderState, Set[ProviderState]] = {
    ProviderState.STARTING: {ProviderState.RUNNING, ProviderState.ERROR},
    ProviderState.STOPPING: {ProviderState.STOPPED, ProviderState.ERROR},
}


# [RCF:PROTECTED]
class ProviderLifecycle:
    """FSM for terminal provider lifecycle."""

# [RCF:PROTECTED]
    def transition(
        self,
        current_state: ProviderState | str,
        action: ProviderAction | str,
        *,
        poll_outcome: ProviderState | str | None = None,
    ) -> ProviderState:
        """Validate and execute a state transition.

        Args:
            current_state: Current provider state
            action: Action to perform
            poll_outcome: For POLL actions, the observed container state
                         (e.g. "running", "error"). If None, stays in current state.

        Returns:
            Next state after transition

        Raises:
            ValueError: If transition is invalid
        """
        # Normalize to enums
        if isinstance(current_state, str):
            current_state = ProviderState(current_state)
        if isinstance(action, str):
            action = ProviderAction(action)
        if poll_outcome and isinstance(poll_outcome, str):
            poll_outcome = ProviderState(poll_outcome)

        # Special handling for POLL with outcome
        if action == ProviderAction.POLL and poll_outcome:
            allowed = _POLL_OUTCOMES.get(current_state, {current_state})
            if poll_outcome not in allowed:
                raise ValueError(
                    f"Invalid poll outcome: {current_state} cannot transition to {poll_outcome}"
                )
            return poll_outcome

        # Standard transition lookup
        key = (current_state, action)
        if key not in _TRANSITIONS:
            raise ValueError(
                f"Invalid transition: {current_state} + {action}. "
                f"Allowed actions from {current_state}: "
                f"{[a.value for s, a in _TRANSITIONS.keys() if s == current_state]}"
            )

        return _TRANSITIONS[key]

# [RCF:PROTECTED]
    def can_start(self, current_state: ProviderState | str) -> bool:
        """Check if START action is valid from current state."""
        if isinstance(current_state, str):
            current_state = ProviderState(current_state)
        return (current_state, ProviderAction.START) in _TRANSITIONS

# [RCF:PROTECTED]
    def can_stop(self, current_state: ProviderState | str) -> bool:
        """Check if STOP action is valid from current state."""
        if isinstance(current_state, str):
            current_state = ProviderState(current_state)
        return (current_state, ProviderAction.STOP) in _TRANSITIONS

# [RCF:PROTECTED]
    def is_terminal(self, state: ProviderState | str) -> bool:
        """Check if state is terminal (no automatic transitions out)."""
        if isinstance(state, str):
            state = ProviderState(state)
        return state in {ProviderState.INSTALLED, ProviderState.STOPPED, ProviderState.ERROR}
