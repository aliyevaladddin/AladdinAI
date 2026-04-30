# NOTICE: This file is protected under RCF-PL v1.2.8
# [RCF:PROTECTED]
import hmac
import hashlib
import json
import httpx
import asyncio
from typing import Any
from sqlalchemy import select
from app.database import async_session
from app.models.outgoing_webhook import OutgoingWebhook

async def trigger_webhooks(user_id: int, event_type: str, payload: Any):
    """
    Finds all active webhooks for a user subscribed to event_type and sends payload.
    """
    async with async_session() as db:
        result = await db.execute(
            select(OutgoingWebhook).where(
                OutgoingWebhook.user_id == user_id,
                OutgoingWebhook.is_active == True
            )
        )
        webhooks = result.scalars().all()

    # Filter by event_type in Python (JSON columns can be tricky to query across dialects)
    subscribed_webhooks = [w for w in webhooks if event_type in w.events]
    
    if not subscribed_webhooks:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = []
        for webhook in subscribed_webhooks:
            tasks.append(_send_webhook(client, webhook, event_type, payload))
        
        await asyncio.gather(*tasks, return_exceptions=True)

async def _send_webhook(client: httpx.AsyncClient, webhook: OutgoingWebhook, event_type: str, payload: Any):
    data = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    }
    body = json.dumps(data)
    headers = {"Content-Type": "application/json"}
    
    # Restricted Correlation Framework (RCF) Implementation
    from app.services.rcf_service import RCFProtocol
    import uuid
    
    # Use webhook secret for RCF
    secret = webhook.secret or "rcf_default_secret_aladdin"
    new_marker, ts = RCFProtocol.generate_marker(secret, webhook.last_marker, body)
    
    correlation_id = str(uuid.uuid4())
    headers["X-RCF-Correlation-ID"] = correlation_id
    headers["X-RCF-Marker"] = new_marker
    headers["X-RCF-Timestamp"] = ts
    if webhook.last_marker:
        headers["X-RCF-Chain-Root"] = webhook.last_marker

    try:
        resp = await client.post(webhook.url, content=body, headers=headers)
        resp.raise_for_status()
        
        # Lock the correlation chain in the DB after successful delivery
        async with async_session() as db:
            from sqlalchemy import update
            await db.execute(
                update(OutgoingWebhook)
                .where(OutgoingWebhook.id == webhook.id)
                .values(last_marker=new_marker)
            )
            await db.commit()
            
    except Exception as e:
        print(f"RCF Correlation failure for {webhook.url}: {e}")

from datetime import datetime, timezone
