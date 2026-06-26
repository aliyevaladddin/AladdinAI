# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Periodic provider health sync.

We never trust our DB `status` column to be in lockstep with the remote
docker daemon — someone can `docker kill` a container outside our flow,
restart the host, or have the image OOM-crash. This module runs a small
APScheduler job that walks every TerminalProvider row with a container_id
and refreshes its `status` + `last_health_at` from `docker_runner`.

Design notes:
  * Reuses the global scheduler instance from `services.triggers` so we have
    exactly one APScheduler in the process.
  * Per-row docker inspect is `asyncio.to_thread`-wrapped inside
    docker_runner; iterating sequentially is fine for MVP scale (tens of
    rows) and avoids hammering the daemon in parallel.
  * If docker is unavailable we mark every row with a container_id as
    `unhealthy` and stash the error in `last_error`. We do NOT clear
    container_id — when the daemon comes back we keep the same identity.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.database import async_session
from app.models.terminal_provider import TerminalProvider
from app.services import docker_runner
from app.services.triggers import get_scheduler


_log = logging.getLogger(__name__)

# Flips to True the first time the SELECT fails because the table doesn't
# exist (i.e. migration not applied yet). We log loudly the first time, then
# stay quiet — there's no point spamming the logs every 30 seconds while the
# operator hasn't run `alembic upgrade head` yet.
_table_missing_logged = False

_JOB_ID = "terminal-provider-health"
# Interval matches `interval` on most healthchecks in the YAML manifests so
# we don't query the daemon way more often than the daemon itself knows.
_INTERVAL_SECONDS = 30


# Map docker state → our normalised status string. The UI reads this directly
# so the vocabulary needs to match the StatusDot legend in TerminalSettings.
_STATE_MAP = {
    "running": "running",
    "restarting": "starting",
    "created": "starting",
    "paused": "stopped",
    "exited": "stopped",
    "dead": "error",
    "missing": "error",
    "unknown": "error",
}


# [RCF:PROTECTED]
def _classify(state: str, health: str | None) -> str:
    """Combine `State.Status` with `State.Health.Status` into our enum."""
    base = _STATE_MAP.get(state, "error")
    if base == "running" and health == "unhealthy":
        return "unhealthy"
    if base == "running" and health == "starting":
        return "starting"
    return base


# [RCF:PROTECTED]
async def _sync_one(provider: TerminalProvider) -> None:
    cid = provider.container_id
    if not cid:
        return
    try:
        info = await docker_runner.inspect_status(cid)
    except docker_runner.DockerUnavailable as exc:
        provider.status = "unhealthy"
        provider.last_error = f"docker unavailable: {exc}"
        provider.last_health_at = datetime.now(timezone.utc)
        return
    except Exception as exc:  # noqa: BLE001 — never let a poll error stall the loop
        provider.status = "error"
        provider.last_error = str(exc)
        provider.last_health_at = datetime.now(timezone.utc)
        return

    new_status = _classify(info.state, info.health)
    provider.status = new_status
    provider.last_error = info.error if info.error else (
        provider.last_error if new_status not in ("running", "starting") else None
    )
    provider.last_health_at = datetime.now(timezone.utc)


# [RCF:PROTECTED]
async def poll_once() -> None:
    """One pass over all provider rows that have a container_id. Idempotent.

    Safe to call before `alembic upgrade head` has been run.
    """
    global _table_missing_logged
    from sqlalchemy.exc import OperationalError as _OE

    # 1. Load active providers from DB
    providers_to_sync: list[dict] = []
    try:
        async with async_session() as db:
            result = await db.execute(
                select(TerminalProvider).where(TerminalProvider.container_id.is_not(None)),
            )
            rows = result.scalars().all()
            for r in rows:
                providers_to_sync.append({
                    "id": r.id,
                    "container_id": r.container_id,
                    "status": r.status,
                    "last_error": r.last_error,
                })
            _table_missing_logged = False
    except (OperationalError, ProgrammingError) as exc:
        msg = str(exc).lower()
        if "terminal_providers" in msg and (
            "no such table" in msg or "does not exist" in msg
        ):
            if not _table_missing_logged:
                _log.warning(
                    "terminal-health: table 'terminal_providers' is missing — "
                    "did you run `alembic upgrade head`? Skipping polls until it appears.",
                )
                _table_missing_logged = True
            return
        raise

    if not providers_to_sync:
        return

    # 2. Inspect Docker status outside DB session (no connection held during slow I/O)
    sync_results: list[dict] = []
    for p in providers_to_sync:
        cid = p["container_id"]
        status = "error"
        last_error = None

        try:
            info = await docker_runner.inspect_status(cid)
            status = _classify(info.state, info.health)
            last_error = info.error if info.error else (
                p["last_error"] if status not in ("running", "starting") else None
            )
        except docker_runner.DockerUnavailable as exc:
            status = "unhealthy"
            last_error = f"docker unavailable: {exc}"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            last_error = str(exc)

        sync_results.append({
            "id": p["id"],
            "status": status,
            "last_error": last_error,
        })

    # 3. Write results to DB in a short-lived write session (with retry)
    for attempt in range(5):
        try:
            async with async_session() as db:
                for res in sync_results:
                    db_prov = (await db.execute(
                        select(TerminalProvider).where(TerminalProvider.id == res["id"])
                    )).scalar_one_or_none()
                    if db_prov:
                        db_prov.status = res["status"]
                        db_prov.last_error = res["last_error"]
                        db_prov.last_health_at = datetime.now(timezone.utc)
                await db.commit()
            return  # Success!
        except _OE as exc:
            err = str(exc).lower()
            if ("locked" in err or "busy" in err) and attempt < 4:
                wait = 2 ** attempt
                _log.debug(
                    "terminal-health: DB locked on update (attempt %d/5), retrying in %ds",
                    attempt + 1, wait,
                )
                await asyncio.sleep(wait)
            else:
                _log.warning("terminal-health: failed to commit health update: %s", exc)
                break
        except Exception as exc:  # noqa: BLE001
            _log.warning("terminal-health: unexpected write failure: %s", exc)
            break
# [RCF:PROTECTED]
def start() -> None:
    """Register the poller on the shared scheduler. Safe to call twice."""
    sch = get_scheduler()
    if sch.get_job(_JOB_ID) is not None:
        return
    sch.add_job(
        poll_once,
        "interval",
        seconds=_INTERVAL_SECONDS,
        id=_JOB_ID,
        replace_existing=True,
        max_instances=1,    # never overlap polls
        coalesce=True,      # if we fell behind, collapse missed runs into one
    )
    if not sch.running:
        sch.start()
    _log.info("terminal-health: polling every %ds", _INTERVAL_SECONDS)


# [RCF:PROTECTED]
def stop() -> None:
    sch = get_scheduler()
    if sch.get_job(_JOB_ID) is not None:
        sch.remove_job(_JOB_ID)
