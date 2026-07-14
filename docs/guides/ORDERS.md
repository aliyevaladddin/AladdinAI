// NOTICE: This file is protected under RCF-PL
# Orders, Product Catalog & Sales/Marketing

The Orders layer turns AladdinAI's CRM from a *contact tracker* into a system
that records real sales. It adds a product catalog, orders with line items and
a delivery lifecycle, dashboard metrics for sales and marketing, and agent
tools so an AI agent can take and move orders on your behalf.

## 🎯 Deal vs Order

These are deliberately **two different things**:

| | **Deal** | **Order** |
|---|---|---|
| Meaning | A pipeline *opportunity* | A *committed* sale |
| May it fall through? | Yes | No — it's already placed |
| Lifecycle | `lead → … → won / lost` | `pending → … → delivered / cancelled` |
| Has line items? | No | Yes (products + quantities) |

They link only through an optional `deal_id` on the order — there is **no
auto-conversion** from a won deal into an order. You (or an agent) create the
order explicitly.

## 🏗️ Data model

```
Product  (catalog: sku, name, price, currency, active)
   │  referenced by
   ▼
Order  (status, total, currency, contact, source, campaign, assigned_agent)
   │  has many
   ▼
OrderItem  (product_name, quantity, unit_price, line_total)
```

Two design choices worth knowing:

- **`total` is computed, never set by hand.** It is the sum of every line's
  `line_total` and is recomputed automatically whenever items change.
- **Line items snapshot the product.** When an item is created it copies the
  product's `name` and `price` into the line. Editing the catalog later
  (e.g. raising a price) **never rewrites an order that was already placed**.

## 🔄 Order status lifecycle

Orders move through a fixed graph. Illegal jumps are rejected with `400`.

```
pending ──▶ processing ──▶ shipped ──▶ delivered   (terminal)
   │             │            │
   └─────────────┴────────────┴────────▶ cancelled (terminal)
```

- `delivered` and `cancelled` are **terminal** — nothing leaves them.
- Any non-terminal status can go straight to `cancelled`.
- You cannot skip forward (e.g. `pending → delivered`) or move backward.

Every transition is appended to the CRM activity timeline as an
`order_status_changed` activity and is retrievable via `/history`.

## 📚 REST API

Full request/response schemas live in the [API reference](../API.md). Summary:

### Products — `/api/crm/products`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/crm/products` | List products (`?search=`, `?active=`) |
| `POST` | `/api/crm/products` | Create a product (duplicate SKU → `400`) |
| `GET` | `/api/crm/products/{id}` | Get one product |
| `PUT` | `/api/crm/products/{id}` | Update a product |
| `DELETE` | `/api/crm/products/{id}` | Delete a product |

SKU is unique **per user**.

### Orders — `/api/crm/orders`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/crm/orders` | List orders (`?status=`, `?assigned_agent_id=`, `?mine=true`, `?source=`, `?campaign=`) |
| `POST` | `/api/crm/orders` | Create an order with line items |
| `GET` | `/api/crm/orders/metrics` | Sales & marketing metrics (see below) |
| `GET` | `/api/crm/orders/{id}` | Get one order with items |
| `PUT` | `/api/crm/orders/{id}` | Update order fields (not status/total) |
| `DELETE` | `/api/crm/orders/{id}` | Delete an order |
| `PUT` | `/api/crm/orders/{id}/status?status=` | Move the order status (validated) |
| `GET` | `/api/crm/orders/{id}/history` | Status change history |
| `POST` | `/api/crm/orders/{id}/items` | Add a line item (recomputes total) |
| `PUT` | `/api/crm/orders/{id}/items/{item_id}` | Update a line item |
| `DELETE` | `/api/crm/orders/{id}/items/{item_id}` | Remove a line item |

> **Note:** `/metrics` is declared before `/{order_id}` so the router does not
> try to parse `"metrics"` as an order id.

### Example — create an order

```bash
curl -X POST http://localhost:8000/api/crm/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "contact_id": 12,
        "source": "newsletter",
        "campaign": "summer-sale",
        "items": [
          {"product_id": 3, "quantity": 2},
          {"product_id": 7, "quantity": 1}
        ]
      }'
# → 201 { "id": 45, "status": "pending", "total": 59.97, "items": [...] }
```

Then advance it:

```bash
curl -X PUT "http://localhost:8000/api/crm/orders/45/status?status=processing" \
  -H "Authorization: Bearer $TOKEN"
```

## 📊 Sales & marketing metrics

`GET /api/crm/orders/metrics` returns, all scoped to the current user:

| Field | Meaning |
|---|---|
| `realized_revenue` | Σ total of **delivered** orders |
| `booked_revenue` | Σ total of **non-cancelled** orders |
| `order_count` | Total number of orders |
| `count_by_status` | Order count per status |
| `revenue_by_status` | Revenue per status |
| `pipeline_value` | Σ of open deal amounts (`lead`/`qualified`/`proposal`/`negotiation`) |
| `funnel` | Deal count per stage |
| `win_rate` | `won / (won + lost)` |
| `revenue_by_source` | Revenue attributed by `source` |
| `revenue_by_campaign` | Revenue attributed by `campaign` |

Fill `source` and `campaign` on orders to make attribution meaningful.

## 🤖 Agent tools

Orders are also driven by agents. Tools split by intent:

**Read — available to every agent** (in the `_default` tool set):

- `list_orders` — list orders, optionally filtered by status
- `get_order_summary` — full detail of one order
- `get_sales_metrics` — realized/booked revenue and status breakdown

**Write — gated behind the `sales` role** (`DEFAULT_TOOLS_BY_ROLE["sales"]`):

- `create_order` — create an order; identify the customer by `contact_id`, or
  by `email`/`phone` (a contact is created if none exists); items by `sku` or
  `product_id` + `quantity`
- `update_order_status` — move an order through the status graph
- `create_product` — add a product to the catalog

To let an agent place and move orders, give it the role `sales` (or set an
explicit `tools_config.allowed` list). Status changes made by an agent record
the calling `agent_id` in the history log, so you can see who moved what.

See [Tool Development](TOOL_DEVELOPMENT.md) for how the tool registry works.

## 🖥️ Frontend

The dashboard page lives at **`/dashboard/orders`**:

- A metrics band (realized revenue, booked revenue, open pipeline, order count)
- A create form (pick a customer, add product + quantity rows, set source/campaign)
- A per-order status dropdown that only offers **legal next-states**
- A "My orders" filter (orders that have an assigned agent)

## 🗄️ Migration

Schema is created by Alembic migration `e5a1b7c93f24`
(`products` → `orders` → `order_items`). It uses a dialect-agnostic
table-existence guard, so it is safe on both Postgres and SQLite.

```bash
cd backend
alembic upgrade head
```

## 🚫 Out of scope (for now)

Payments/invoicing, campaign email sending, product variations, and per-user
(human) RBAC are intentionally not part of this layer — order ownership is by
*agent*, not by person. These can build on top of what's here.

## See also

- [API Reference](../API.md) — full schemas for every endpoint above
- [Tool Development](TOOL_DEVELOPMENT.md) — how agent tools are built
- [Agent Development](AGENT_DEVELOPMENT.md) — assigning the `sales` role to an agent
