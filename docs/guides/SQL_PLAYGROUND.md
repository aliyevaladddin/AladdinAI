// NOTICE: This file is protected under RCF-PL
# SQL Playground

The SQL Playground lets authenticated users explore the Postgres database
with read-only queries from the dashboard (`/dashboard/sql`).

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/sql/schema` | All tables with columns, types, nullability, defaults |
| `POST` | `/api/sql/execute` | Validate and run a query |

Both require a `Bearer` token (see [API reference](../API.md)).

---

## Security model

The endpoint intentionally accepts user-provided SQL for analytics, with
layered protection:

1. **Authentication** — `get_current_user` dependency; no anonymous access.
2. **Read-only by default** — `read_only: true` is the only accepted mode;
   the flag exists in the schema but the router rejects `false`.
3. **SELECT/WITH only** — after comment stripping, the statement must start
   with `SELECT` or `WITH`.
4. **Dangerous keywords blocked** — validator rejects `DROP`, `TRUNCATE`,
   `ALTER`, `PG_SLEEP`, `COPY`, and friends.
5. **Forced LIMIT** — if no `LIMIT` clause is present, one is appended
   (max 1000 rows via `limit: int = Field(ge=1, le=1000)`).
6. **Query length cap** — 10 000 characters (ReDoS / abuse guard).
7. **Direct execution disabled** — as of August 2026 the router returns a
   controlled error instead of executing arbitrary SQL:

```json
{
  "success": false,
  "error": "Direct execution of user-provided SQL is disabled for security.
            Use approved parameterized query endpoints."
}
```

> **Why?** Arbitrary execution against the production DB was deemed too
> risky even behind validation. The UI keeps working against the schema
> explorer; re-enabling requires an explicit product decision plus a
> dedicated read-only replica or role.

---

## Request/response

```bash
curl -X POST "$API/api/sql/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, name FROM agents", "limit": 50}'
```

Response shape (`SQLQueryResponse`):

```json
{
  "success": true,
  "rows": [],
  "columns": ["id", "name"],
  "row_count": 0,
  "error": null,
  "message": null
}
```

Validation failures also return HTTP 200 with `success: false` and a
human-readable `error`; only malformed payloads get HTTP 422.

---

## Frontend

The page lives at `frontend/src/app/(dashboard)/dashboard/sql/`:

- `page.tsx` — editor + orchestration (~450 lines)
- `SQLSidebar.tsx` — schema tree (tables → columns)
- `SQLResults.tsx` — result table renderer

Rows are typed as `Record<string, unknown>[]`.

---

## See also

- [`docs/adr/0002-mongodb-vs-postgres.md`](../adr/0002-mongodb-vs-postgres.md) — why Postgres is the relational store
- [`backend/app/tools/sql.py`](../../backend/app/tools/sql.py) — shared `validate_sql_query` used by agent tools too
