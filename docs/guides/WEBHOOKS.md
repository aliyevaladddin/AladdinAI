// NOTICE: This file is protected under RCF-PL
# Outgoing Webhooks (Zapier & friends)

Outgoing webhooks push a JSON event to an external URL whenever something
happens in AladdinAI — a new contact, a closed deal, a placed order, a chat
message. Point them at Zapier, Make, n8n, or any HTTP endpoint to wire your
workspace into external automations.

Two delivery modes:

| Mode | When | What the receiver gets |
|---|---|---|
| **Unsigned** | webhook has **no secret** | plain JSON body — works with Zapier catch hooks out of the box |
| **RCF-signed** | webhook has a **secret** | JSON body + `X-RCF-*` headers forming a verifiable marker chain |

## 📡 Events

| Event | Fired when | Payload fields |
|---|---|---|
| `contact_created` | a CRM contact is created | `contact_id`, `name`, `email`, `phone`, `company` |
| `deal_created` | a deal is created | `deal_id`, `title`, `amount`, `stage` |
| `deal_updated` | a deal changes stage | `deal_id`, `title`, `new_stage` |
| `order_created` | an order is placed | `order_id`, `contact_id`, `total`, `status` |
| `order_status_changed` | an order moves through its lifecycle | `order_id`, `old_status`, `new_status` |
| `message_received` | an inbound channel message arrives | `contact_id`, `contact_name`, `channel`, `text` |
| `message_sent` | an agent/user reply goes out | `contact_id`, `channel`, `reply` |

A webhook only receives the events it subscribed to. The one exception is an
explicit agent send (`send_webhook` tool) — see below.

## 📦 Delivery format

```json
{
  "event": "contact_created",
  "timestamp": "2026-08-18T09:30:00.000000+00:00",
  "payload": { "contact_id": 42, "name": "Jane Doe", "email": "jane@example.com", "phone": null, "company": "Acme" }
}
```

- `Content-Type: application/json`, 10 s timeout.
- Retries on transient failures (`408, 425, 429, 500, 502, 503, 504`) after
  **0.5 s / 2 s / 5 s** — 4 attempts total. Other 4xx fail immediately.

## 🔐 RCF signing (optional)

When a secret is configured, every delivery carries headers:

| Header | Meaning |
|---|---|
| `X-RCF-Correlation-ID` | unique id of this delivery |
| `X-RCF-Marker` | marker generated from the secret + previous marker + body |
| `X-RCF-Timestamp` | generation timestamp |
| `X-RCF-Chain-Root` | previous marker (absent on the very first delivery) |

The chain advances **only after confirmed delivery** — a failed send never
moves the marker, so the receiver-side chain stays verifiable. Leave the
secret empty for receivers that don't verify signatures (Zapier).

## ⚡ Zapier recipe

1. In Zapier: **Create Zap → Trigger: Webhooks by Zapier → Catch Hook** → copy the hook URL.
2. In AladdinAI: **Settings → Outgoing Webhooks → Add Webhook** — paste the URL,
   pick events, leave **Secret empty**.
3. Press the **⚡ test button** on the webhook row — Zapier should record a
   `test` event ("Test event from AladdinAI webhook settings").
4. Finish the Zap. From now on subscribed events flow in automatically.

## 🤖 Agent tools

Agents can see and fire webhooks — they are not invisible plumbing:

| Tool | What it does |
|---|---|
| `list_webhooks` | list the user's webhooks: id, name, url, events, active flag |
| `send_webhook` | deliver `{event, timestamp, payload}` to one webhook by id or name |

Both are in the default and `sales` tool sets. An explicit `send_webhook`
bypasses the event subscription list on purpose: subscriptions govern
*automatic* fan-out, an agent send is a deliberate point-to-point delivery.
Inactive webhooks are rejected.

Example agent prompt: *"When the client confirms the order, send a
`deal_closed` event to my Zapier hook."*

## 🔌 API

All endpoints are under `/api/webhooks/outgoing` and require a bearer token.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | list your webhooks |
| `POST` | `/` | create (`name`, `url`, `events`, optional `secret`, `is_active`) |
| `PUT` | `/{id}` | partial update; `secret` is three-state: **omitted** → keep current, **empty string** → remove signing, **value** → rotate |
| `DELETE` | `/{id}` | delete |
| `POST` | `/{id}/test` | deliver a one-off `test` event; `200 {"ok": true, "signed": bool}` or `502` on delivery failure |

Webhooks are strictly scoped per user — you can never read, fire, or modify
another user's webhook.
