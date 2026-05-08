# Frontend

Next.js 15 (App Router) dashboard for AladdinAI. TypeScript + Tailwind +
shadcn/ui primitives + sonner for toasts. Talks to the FastAPI backend over
REST and a single SSE endpoint for chat streaming.

> ⚠ Read [`AGENTS.md`](AGENTS.md) before writing code. This Next.js version
> has breaking changes from older releases — check
> `node_modules/next/dist/docs/` for the relevant guide.

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/             login/register routes
│   │   ├── (dashboard)/        authenticated app shell + pages
│   │   ├── terminal/           full-screen SSH terminal
│   │   ├── layout.tsx          root html + providers
│   │   └── page.tsx            landing → redirect to /dashboard
│   ├── components/
│   │   ├── AppHeader.tsx
│   │   ├── AppSidebar.tsx      nav, grouped by section
│   │   ├── agent-*-panel.tsx   per-agent feature panels
│   │   └── ui/                 shadcn primitives (button, toast, …)
│   └── lib/
│       ├── api.ts              fetch wrapper with auth + error handling
│       └── utils.ts            cn(), small helpers
└── package.json
```

---

## Pages

All authenticated pages live under `(dashboard)/dashboard/`:

| Route                       | Purpose                                       |
|-----------------------------|-----------------------------------------------|
| `/dashboard`                | Overview / activity                           |
| `/dashboard/crm`            | Contacts                                      |
| `/dashboard/deals`          | Deals                                         |
| `/dashboard/comms`          | Inbox + connected channels and email accounts |
| `/dashboard/channels`       | Telegram / WhatsApp / SMS providers           |
| `/dashboard/webhooks`       | Outgoing webhook subscriptions                |
| `/dashboard/agents`         | Create/configure agents (the main surface)    |
| `/dashboard/triggers`       | Cron-scheduled fan-out tasks                  |
| `/dashboard/chat`           | Playground for arbitrary chat                 |
| `/dashboard/router`         | Default model + routing rules                 |
| `/dashboard/providers`      | LLM provider connections                      |
| `/dashboard/vms`            | Cloud VMs (SSH credentials)                   |
| `/dashboard/mongodb`        | MongoDB cluster connections                   |
| `/dashboard/bentoml`        | BentoML deploy targets                        |
| `/terminal`                 | Full-screen WebSocket terminal                |

When adding a page, also add an entry to `components/AppSidebar.tsx`.

---

## The "agent panel" pattern

Agent configuration is split into focused panels:

- `agent-memory-panel.tsx`     — list/search/add/delete memory facts
- `agent-extraction-panel.tsx` — extraction prompt + behavior toggles
- `agent-gates-panel.tsx`      — handoff / memory-write / recall gates
- `agent-safety-panel.tsx`     — moderation + PII per phase
- `agent-triggers-panel.tsx`   — (lives on `/dashboard/triggers`, not per-agent)

Each panel is a self-contained client component that:

1. Loads its own data on mount via `api.get(...)`.
2. Owns its draft/edit state.
3. Calls back into the API on save and re-fetches.
4. Reports success/failure with `toast.success` / `toast.error` from sonner.

When a new feature needs configuration on the agent screen, follow this
pattern — don't bolt it onto an existing panel.

---

## API client

`src/lib/api.ts` is the only place that talks to the backend. It:

- Reads `NEXT_PUBLIC_API_URL` (set in root `.env`) to build URLs.
- Attaches the JWT from `localStorage` as `Authorization: Bearer …`.
- Refreshes the access token on 401 using the refresh token, then retries.
- Throws on non-2xx responses with a parsed error message.

Use the typed helpers — don't call `fetch` directly:

```ts
import { api } from "@/lib/api";

const triggers = await api.get<Trigger[]>("/triggers");
await api.post("/triggers", body);
await api.patch(`/triggers/${id}`, { enabled: false });
await api.delete(`/triggers/${id}`);
```

---

## Styling

- Tailwind utility classes everywhere; `cn()` from `lib/utils.ts` for
  conditional class merging.
- Theme tokens (`--color-bg`, `--color-fg`, `--color-border`, …) defined in
  `globals.css`. Prefer them over raw Tailwind colors so dark/light stays
  consistent.
- shadcn primitives (`Button`, `Toast`) live in `components/ui/`. Add more
  with `npx shadcn@latest add <component>` and they land there.

---

## Dev workflow

```bash
npm install
npm run dev     # http://localhost:3000
npm run build
npm run lint
```

Backend must be running on the URL pointed to by `NEXT_PUBLIC_API_URL`
(default `http://localhost:8000/api`). Auth state is stored in
`localStorage`; clear it if you see persistent 401s after rotating
`JWT_SECRET`.

---

## Adding a new feature

1. Add an endpoint in `backend/app/routers/<resource>.py` (and a service if
   non-trivial).
2. If it's per-agent configuration, create
   `components/agent-<name>-panel.tsx` and mount it from
   `app/(dashboard)/dashboard/agents/page.tsx`.
3. If it's a top-level surface, add a page under
   `app/(dashboard)/dashboard/<name>/page.tsx` and a sidebar entry in
   `AppSidebar.tsx`.
4. Use `api.*` helpers; don't reinvent auth or error handling.
5. Toast feedback with sonner: success on writes, error in `catch` blocks.
