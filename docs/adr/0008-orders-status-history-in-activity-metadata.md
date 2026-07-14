// NOTICE: This file is protected under RCF-PL
# ADR-0008: Orders as a Distinct Entity; Status History in Activity Metadata

**Status**: Accepted

**Date**: 2026-07-14

**Deciders**: AladdinAI core

**Tags**: backend, crm, data-model

## Context

The CRM had contacts, deals, and activities but no representation of a *sale*.
A `Deal` models a pipeline opportunity that may never close; it has a stage
(`lead → won/lost`) but no line items and no fulfilment lifecycle. We needed to
record committed sales: what was bought, for how much, and where it is in
delivery (`pending → delivered`).

Two design questions had to be answered:

1. Should orders reuse/extend `Deal`, or be a separate entity?
2. Where do we store the **audit trail of status changes** (who moved an order
   from `shipped` to `delivered`, and when)?

A constraint shaped the second answer: the `Activity` model and its migration
are **RCF-PROTECTED** — they must not be refactored, and adding an `order_id`
column to `activities` would mean editing protected files and shipping a schema
change to a table we've committed to keeping stable.

## Decision

1. **Orders are a distinct entity**, not an extension of `Deal`. New tables:
   `products`, `orders`, `order_items`. An order links to a deal only through an
   optional `deal_id` — there is no automatic deal→order conversion.

2. **Order status history is written to the existing `activities` timeline** as
   `type = "order_status_changed"` activities, with the order linkage and the
   old/new status carried in **`metadata_json`**:

   ```json
   { "order_id": 45, "old_status": "shipped", "new_status": "delivered" }
   ```

   `GET /crm/orders/{id}/history` filters activities by
   `metadata_json.order_id`. No new column, no change to the protected model.

3. **Status transitions are validated against a fixed graph**
   (`ALLOWED_TRANSITIONS` in `crm_service.py`): `pending → processing → shipped
   → delivered`, any non-terminal state → `cancelled`; `delivered` and
   `cancelled` are terminal. Illegal transitions return `400`.

4. **Line items snapshot** `product_name` and `unit_price` at creation, and the
   order `total` is a denormalised sum recomputed from items — so later catalog
   edits never rewrite placed orders.

## Consequences

### Positive
- Deal and Order semantics stay clean and independent; neither model is
  overloaded to serve the other's lifecycle.
- The RCF-PROTECTED `Activity` model and migration are untouched.
- History reuses the existing timeline UI/queries — one place to see all
  customer interactions, including order movement.
- The status graph makes illegal states unreachable through the API.

### Negative
- Querying history requires a `metadata_json` filter applied in Python (the
  JSON field is not indexed on `order_id`). Fine at CRM data volumes; would need
  a dedicated table or a JSON index if history queries become hot.
- Order-history rows are not distinguishable from other activities at the schema
  level — only by their `type` string and metadata shape.

### Neutral
- `total` is denormalised; it is always recomputed on item mutation rather than
  derived on read.

## Alternatives Considered

### Alternative 1: Extend `Deal` with order fields
- **Description**: Add status, items, and total to the existing `Deal`.
- **Pros**: One entity, no new tables.
- **Cons**: Conflates "might happen" with "has happened"; a lost deal and a
  cancelled order would share a model with two incompatible stage vocabularies.
- **Why not chosen**: The two lifecycles are genuinely different; merging them
  produces an ambiguous model.

### Alternative 2: Dedicated `order_status_history` table
- **Description**: A new table with `order_id`, `old_status`, `new_status`, `at`.
- **Pros**: Indexable, self-describing, cleanly queryable.
- **Cons**: A second timeline parallel to `activities`; more surface to keep in
  sync; does not benefit from existing activity tooling.
- **Why not chosen**: The activity timeline already exists for exactly this kind
  of record; a parallel table duplicates it. Revisit if history queries need an
  index.

### Alternative 3: Add `order_id` column to `activities`
- **Description**: First-class foreign key on the activity table.
- **Pros**: Indexed, no JSON filtering.
- **Cons**: Requires editing the **RCF-PROTECTED** `Activity` model and its
  migration.
- **Why not chosen**: Violates the RCF-PROTECTED stability guarantee on that
  model.

## Implementation Notes

- Migration `e5a1b7c93f24` creates `products`, `orders`, `order_items` with a
  dialect-agnostic table-existence guard (`sa.inspect(bind).get_table_names()`),
  safe on Postgres and SQLite.
- Shared helpers (`recompute_order_total`, `can_transition`,
  `log_order_status_change`) live in `crm_service.py` so the REST router and the
  agent tools cannot diverge.
- Agent-driven status changes record the calling `agent_id` in the history log;
  UI-driven changes record `agent_id = None`.
- Write tools (`create_order`, `update_order_status`, `create_product`) are
  gated behind a new `sales` role; read tools are in the default set.

## References

- Guide: [`docs/guides/ORDERS.md`](../guides/ORDERS.md)
- API: [`docs/API.md`](../API.md) — `/api/crm/orders`, `/api/crm/products`
- Related: [ADR-0002](0002-mongodb-vs-postgres.md) (Postgres holds CRM data)
