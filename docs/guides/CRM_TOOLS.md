// NOTICE: This file is protected under RCF-PL
# CRM Agent Tools & Pipeline Automation

AladdinAI equips AI agents with native function-calling tools to manage customers, sales deals, and orders directly in the CRM database without requiring manual human data entry.

---

## Architecture & Scope

All CRM tools operate within the authenticated agent's user context (`ctx.user_id`). Agents cannot access or mutate CRM entities belonging to other tenants.

Actions automatically trigger system events and outgoing webhooks (e.g., `contact_created`, `deal_created`, `deal_updated`).

---

## Available Tools

### 1. Contacts & Clients

| Tool Name | Type | Description | Key Parameters |
|---|---|---|---|
| `create_contact` | Write | Creates a single customer or client profile. | `name` (required), `email`, `phone`, `company`, `tags`, `source`, `notes` |
| `create_contacts_batch` | Write | Batch imports multiple contacts in a single tool call. Recommended batch size: 5–10 items per invocation. | `contacts` (array of contact objects with `name`) |
| `list_contacts` | Read | Searches and filters existing contacts. | `search` (text search across name, email, company), `tag`, `limit` (default 20, max 100) |
| `get_contact` | Read | Retrieves the complete profile of a contact. | `contact_id` (required) |

### 2. Deals & Sales Pipeline

The sales pipeline supports standard deal stages: `lead`, `qualified`, `proposal`, `negotiation`, `won`, `lost`.

| Tool Name | Type | Description | Key Parameters |
|---|---|---|---|
| `create_deal` | Write | Creates a deal linked to an existing or auto-created contact. | `title` (required), `contact_id` (or `email`/`phone`/`name`), `amount`, `stage`, `currency` (default USD/RUB), `probability`, `notes` |
| `create_deals_batch` | Write | Batch creates multiple deals linked to customer IDs or new contacts. | `deals` (array of deal objects with `title` and contact reference) |
| `list_deals` | Read | Filters deals by pipeline stage or specific contact. | `stage` (e.g. `lead`, `proposal`, `won`), `contact_id`, `limit` |
| `update_deal_stage` | Write | Advances or closes a deal in the sales funnel. | `deal_id`, `stage`, `notes` |

### 3. Orders & Commerce

| Tool Name | Type | Description |
|---|---|---|
| `list_orders` | Read | Lists orders filtered by fulfillment status (`pending`, `processing`, `shipped`, `delivered`, `cancelled`). |
| `get_order_summary` | Read | Line-item detail, price snapshots, and customer reference for an order. |
| `get_sales_metrics` | Read | KPI overview: realized revenue, booked revenue, status breakdown. |
| `create_order` | Write | Places a customer order with line items (`product_id`/`sku`, `quantity`, `unit_price`). |
| `update_order_status` | Write | Advances delivery lifecycle adhering to legal state-machine transitions. |

---

## Role Assignment & Availability

In `app.services.agent_runner.DEFAULT_TOOLS_BY_ROLE`:
- **`_default` (all agents)**: Includes `list_contacts`, `get_contact`, `create_contact`, `create_contacts_batch`, `list_deals`, `create_deal`, `create_deals_batch`, `update_deal_stage`, `list_orders`, `get_order_summary`, `get_sales_metrics`, `create_order`, `update_order_status`.
- **`sales`**: All default tools plus catalog mutation (`create_product`).

---

## Recommended Patterns for Agents

1. **Batch Sizing**: When populating or syncing multiple records, LLMs maintain clean JSON syntax when generating batches of **5–7 items** per call. Exceeding 15 items in a single tool call may risk token generation truncation.
2. **Contact Association**: When creating deals, pass existing `contact_id`s discovered via `list_contacts` to maintain clean CRM graph relations.
3. **Pipeline Analytics**: Agents can pair `list_deals` with `get_sales_metrics` to calculate stage-to-stage conversion rates, weighted pipeline forecasts, and identify stale leads.
