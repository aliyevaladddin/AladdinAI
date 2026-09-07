# NOTICE: This file is protected under RCF-PL
"""Manager for the local WhatsApp bridge (Baileys) Node daemon.

One daemon per messaging channel: ``node index.js <channel_id>`` listens on a
per-channel unix socket and speaks newline-delimited JSON:

    us -> daemon : {"type":"ping"} | {"type":"get-qr"}
                 | {"type":"send-message","to":"...","text":"..."}
    daemon -> us : {"type":"pong"} | {"type":"qr","data":...}
                 | {"type":"status","status":"sent"} | {"type":"error",...}

The daemon connects to WhatsApp with Baileys and forwards incoming messages
to the backend webhook with the channel's webhook_secret in X-Bridge-Secret.

All calls here are async — never block the event loop on the socket.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

BRIDGE_DIR = Path(__file__).resolve().parent.parent / "whatsapp_bridge"
BACKEND_URL = os.getenv("ALADDIN_BACKEND_URL", "http://localhost:8000")


def socket_path(channel_id: int | str) -> str:
    """Per-channel unix socket — channels never share a daemon."""
    return f"/tmp/aladdin_whatsapp_{channel_id}.sock"


async def _request(command: dict, channel_id: int | str, timeout: float) -> dict[str, Any]:
    """Send one newline-delimited JSON command and read one reply line."""
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(socket_path(channel_id)), timeout
        )
        writer.write((json.dumps(command) + "\n").encode())
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout)
        if not line:
            return {"type": "error", "message": "bridge closed the connection"}
        return json.loads(line)
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass


async def _cleanup_stale_socket(channel_id: int | str) -> None:
    try:
        os.unlink(socket_path(channel_id))
    except OSError:
        pass


async def ping(channel_id: int | str, timeout: float = 2.0) -> bool:
    """True when a live daemon answers a ping on this channel's socket."""
    if not os.path.exists(socket_path(channel_id)):
        return False
    try:
        resp = await _request({"type": "ping"}, channel_id, timeout)
        return resp.get("type") == "pong"
    except (OSError, asyncio.TimeoutError, ValueError):
        # Socket file exists but nobody answers — stale leftover, remove it
        # so the next spawn can bind cleanly.
        await _cleanup_stale_socket(channel_id)
        return False


async def ensure_bridge(channel, timeout: float = 10.0) -> bool:
    """Ping the channel's daemon; spawn one and wait if it is not running.

    `channel` needs `.id` and `.webhook_secret` (the secret is passed to the
    daemon via env so it can sign webhook posts with X-Bridge-Secret).
    """
    if await ping(channel.id, timeout=1.5):
        return True

    env = dict(os.environ, ALADDIN_BACKEND_URL=BACKEND_URL)
    if channel.webhook_secret:
        env["BRIDGE_WEBHOOK_SECRET"] = channel.webhook_secret

    try:
        log_f = open(BRIDGE_DIR / "bridge.log", "a")
        err_f = open(BRIDGE_DIR / "bridge.err", "a")
        await asyncio.create_subprocess_exec(
            "node", "index.js", str(channel.id),
            cwd=str(BRIDGE_DIR),
            env=env,
            stdout=log_f,
            stderr=err_f,
            start_new_session=True,
        )
    except OSError:
        log.exception("failed to spawn WhatsApp bridge for channel %s", channel.id)
        return False

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        await asyncio.sleep(0.25)
        if await ping(channel.id, timeout=1.0):
            log.info("WhatsApp bridge up for channel %s on %s", channel.id, socket_path(channel.id))
            return True
    log.error("WhatsApp bridge did not come up for channel %s within %.0fs", channel.id, timeout)
    return False


async def send_command(command: dict, channel, timeout: float = 8.0) -> dict[str, Any]:
    """Send a command to the channel's daemon, starting it if needed."""
    if not await ping(channel.id, timeout=1.5):
        if not await ensure_bridge(channel, timeout=timeout / 2):
            return {"type": "error", "message": "WhatsApp bridge is not running"}
    try:
        return await _request(command, channel.id, timeout)
    except (OSError, asyncio.TimeoutError, ValueError) as e:
        log.error("[WhatsApp Bridge] command %s failed for channel %s: %s",
                  command.get("type"), channel.id, e)
        return {"type": "error", "message": str(e)}
