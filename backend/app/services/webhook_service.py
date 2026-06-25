# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update

from app.crypto import decrypt
from app.database import async_session
from app.models.outgoing_webhook import OutgoingWebhook
from app.services.rcf_service import RCFProtocol

log = logging.getLogger(__name__)

# Retry policy for transient delivery failures. Tuned conservatively because
# every retry advances the RCF chain — a runaway loop would shred the
# correlation history. Chain integrity is preserved by only committing
# last_marker after success.
_RETRY_DELAYS = (0.5, 2.0, 5.0)  # seconds; 3 attempts total
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


# [RCF:PROTECTED]
async def trigger_webhooks(user_id: int, event_type: str, payload: Any):
    """Find all active webhooks for a user subscribed to event_type and send payload."""
    async with async_session() as db:
        result = await db.execute(
            select(OutgoingWebhook).where(
                OutgoingWebhook.user_id == user_id,
                OutgoingWebhook.is_active == True,  # noqa: E712
            )
        )
        webhooks = result.scalars().all()

    # Filter by event_type in Python (JSON columns can be tricky to query across dialects)
    subscribed_webhooks = [w for w in webhooks if event_type in w.events]

    if not subscribed_webhooks:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [
            _send_webhook(client, webhook, event_type, payload)
            for webhook in subscribed_webhooks
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


# [RCF:PROTECTED]
async def _send_webhook(
    client: httpx.AsyncClient,
    webhook: OutgoingWebhook,
    event_type: str,
    payload: Any,
):
    """Sign a single webhook, deliver it with retries, and advance the RCF chain.

    Without a per-webhook secret we cannot produce a verifiable marker — we
    refuse to fall back to a public default (that would let anyone forge
    a chain). The delivery is skipped with a loud warning instead.
    """
    raw_secret = webhook.secret
    if not raw_secret:
        log.warning(
            "webhook %s (%s) has no secret — refusing to sign (would expose chain)",
            webhook.id, webhook.url,
        )
        return

    secret = decrypt(raw_secret)

    data = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    body = json.dumps(data)

    new_marker, ts = RCFProtocol.generate_marker(secret, webhook.last_marker, body)
    correlation_id = str(uuid.uuid4())

    headers = {
        "Content-Type": "application/json",
        "X-RCF-Correlation-ID": correlation_id,
        "X-RCF-Marker": new_marker,
        "X-RCF-Timestamp": ts,
    }
    if webhook.last_marker:
        headers["X-RCF-Chain-Root"] = webhook.last_marker

    success = await _deliver_with_retries(client, webhook, body, headers, correlation_id)
    if not success:
        return

    # Advance the chain only after delivery confirms — a torn marker would
    # break verifiability on the receiver side.
    async with async_session() as db:
        await db.execute(
            update(OutgoingWebhook)
            .where(OutgoingWebhook.id == webhook.id)
            .values(last_marker=new_marker)
        )
        await db.commit()


# [RCF:PROTECTED]
async def _deliver_with_retries(
    client: httpx.AsyncClient,
    webhook: OutgoingWebhook,
    body: str,
    headers: dict[str, str],
    correlation_id: str,
) -> bool:
    """POST with bounded retries on transient failures.

    Returns True on success, False if every attempt failed. Non-retryable
    HTTP errors (4xx that aren't 408/425/429) fail immediately.
    """
    last_err: str | None = None
    for attempt, delay in enumerate([0.0, *_RETRY_DELAYS]):
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await client.post(webhook.url, content=body, headers=headers)
            if resp.status_code < 400:
                return True
            if resp.status_code in _RETRYABLE_STATUS:
                last_err = f"HTTP {resp.status_code}"
                log.warning(
                    "webhook %s attempt %d/%d: %s — retrying",
                    webhook.id, attempt + 1, len(_RETRY_DELAYS) + 1, last_err,
                )
                continue
            log.warning(
                "webhook %s rejected with HTTP %d (corr=%s) — not retrying",
                webhook.id, resp.status_code, correlation_id,
            )
            return False
        except httpx.HTTPError as e:
            last_err = str(e) or e.__class__.__name__
            log.warning(
                "webhook %s attempt %d/%d failed: %s",
                webhook.id, attempt + 1, len(_RETRY_DELAYS) + 1, last_err,
            )

    log.error(
        "webhook %s delivery failed after %d attempts (corr=%s): %s",
        webhook.id, len(_RETRY_DELAYS) + 1, correlation_id, last_err,
    )
    return False
