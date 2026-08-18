# NOTICE: This file is protected under RCF-PL
"""Outgoing-webhook agent tools.

Lets an agent *see* the user's configured outgoing webhooks (e.g. Zapier
catch hooks) and fire them explicitly, instead of webhooks being invisible
plumbing that only the backend routers trigger on CRM events.

- `list_webhooks` — read-only inventory (id, name, url, events, is_active).
- `send_webhook` — deliver an event to one configured webhook by id or name.
  An explicit send bypasses the event subscription list: subscriptions govern
  *automatic* fan-out, an agent send is a deliberate point-to-point delivery.

Both live in the `_default` tool set (agent_runner.DEFAULT_TOOLS_BY_ROLE) —
`http_post` is already there and is strictly more powerful than sending to a
webhook the user configured themselves.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.outgoing_webhook import OutgoingWebhook
from app.services.webhook_service import deliver_single
from app.tools.base import ToolContext, tool


@tool(
    name="list_webhooks",
    description="List the current user's configured outgoing webhooks "
                "(e.g. Zapier hooks): id, name, url, subscribed events and "
                "whether each webhook is active. Use send_webhook to fire one.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
async def list_webhooks(ctx: ToolContext) -> dict[str, Any]:
    result = await ctx.db.execute(
        select(OutgoingWebhook)
        .where(OutgoingWebhook.user_id == ctx.user_id)
        .order_by(OutgoingWebhook.id)
    )
    hooks = result.scalars().all()
    return {
        "count": len(hooks),
        "webhooks": [
            {
                "id": w.id,
                "name": w.name,
                "url": w.url,
                "events": w.events or [],
                "is_active": w.is_active,
            }
            for w in hooks
        ],
    }


@tool(
    name="send_webhook",
    description="Send an event to one of the user's configured outgoing "
                "webhooks (identify it by webhook_id or by name). The webhook "
                "receives {event, timestamp, payload}. Use this to push data "
                "to external automations such as Zapier. The webhook must be active.",
    parameters={
        "type": "object",
        "properties": {
            "webhook_id": {"type": "integer", "description": "Webhook id (from list_webhooks)"},
            "webhook_name": {"type": "string", "description": "Webhook name (alternative to webhook_id)"},
            "event": {"type": "string", "description": "Event name to send (default: agent_event)"},
            "payload": {"type": "object", "description": "JSON payload to deliver"},
        },
    },
)
async def send_webhook(
    ctx: ToolContext,
    webhook_id: int | None = None,
    webhook_name: str | None = None,
    event: str = "agent_event",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if webhook_id is None and not webhook_name:
        return {"error": "Provide webhook_id or webhook_name (see list_webhooks)"}

    q = select(OutgoingWebhook).where(OutgoingWebhook.user_id == ctx.user_id)
    if webhook_id is not None:
        q = q.where(OutgoingWebhook.id == webhook_id)
    else:
        q = q.where(OutgoingWebhook.name == webhook_name)
    result = await ctx.db.execute(q)
    webhook = result.scalars().first()

    if webhook is None:
        return {"error": "Webhook not found — call list_webhooks to see what is configured"}
    if not webhook.is_active:
        return {"error": f"Webhook '{webhook.name}' is inactive"}

    ok = await deliver_single(webhook, event, payload or {})
    if not ok:
        return {"error": f"Delivery to webhook '{webhook.name}' failed (see backend logs)"}
    return {
        "ok": True,
        "webhook_id": webhook.id,
        "name": webhook.name,
        "event": event,
        "signed": bool(webhook.secret),
    }
