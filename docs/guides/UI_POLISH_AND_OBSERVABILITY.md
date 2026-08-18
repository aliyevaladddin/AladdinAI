// NOTICE: This file is protected under RCF-PL
# UI Polish, Chat Performance & Observability Upgrade

A summary of changes across three feature branches (August 2026):
`feat/ui-polish-chat-perf`, `feat/traces-forging-ui`, and PR #640.

---

## Table of Contents

1. [Design Token Fix](#1-design-token-fix)
2. [Dead Code Removal](#2-dead-code-removal)
3. [Hardcoded Hexes → Tokens](#3-hardcoded-hexes--tokens)
4. [Chat Streaming Performance](#4-chat-streaming-performance)
5. [Live Status Bar](#5-live-status-bar)
6. [Tracing Toggle](#6-tracing-toggle)
7. [Global Traces Page](#7-global-traces-page)
8. [Trace Feedback (👍/👎)](#8-trace-feedback-)
9. [Self-Forging UI](#9-self-forging-ui)
10. [SegmentedTabs](#10-segmentedtabs)
11. [Shared UI Components](#11-shared-ui-components)
12. [Agent Detail Page Tab Bar](#12-agent-detail-page-tab-bar)

---

## 1. Design Token Fix

**Problem:** After the Tailwind 4 migration (2026-05-22), shadcn-semantic tokens (`primary`, `muted`, `card`, `background`, `foreground`, `destructive`, `input`, `ring`) were never mapped to the new `@theme inline` system. This left **382 class usages in 29 files** compiling to zero CSS rules — buttons, badges, bubbles, and error states all rendered without background or text color.

**Fix:** Added missing token definitions to `frontend/src/app/globals.css` inside the `@theme inline` block:

```css
--color-primary: var(--violet);
--color-primary-foreground: var(--bg-0);
--color-muted: var(--bg-3);
--color-muted-foreground: var(--fg-2);
--color-card: var(--bg-2);
--color-background: var(--bg-0);
--color-foreground: var(--fg);
--color-destructive: var(--err);
--color-input: var(--line);
--color-ring: var(--violet);
--color-info: var(--info);
--color-info-soft: var(--info-soft);
```

All 12 themes now automatically pick up the new tokens via the existing `--violet`/`--bg-*`/`--fg-*` system.

**Verification:** `next build` → `text-primary` generates 4 rules, `bg-muted` generates 15, `ring-ring/50` compiles to `var(--violet)`.

---

## 2. Dead Code Removal

**`AppSidebar.tsx`** and **`AppHeader.tsx`** were legacy shell components (~700 lines) that nobody imported. Confirmed via grep — only self-references in comments. The active shell lives in `components/shell/` (AppShell, Titlebar, ActivityBar, StatusBar). Both files deleted.

---

## 3. Hardcoded Hexes → Tokens

Replaced hardcoded color palettes across 12 files:

| File | Before | After |
|---|---|---|
| `search/page.tsx` | `indigo-500`, `purple-600`, `cyan-400`, `#a855f7`, `#ef4444` | `primary`, `info`, `success`, `danger` |
| Agent panels (7 files) | `green/red/amber/zinc/blue-400/500` | `success/danger/warning/info` + `muted` |
| `agents/page.tsx` | `green-500`, `zinc-500` status dots | `success`, `muted` |
| `comms/page.tsx` | `bg-green-500/20 text-green-400` | `bg-success-soft text-success` |
| `deals/page.tsx` | `STAGE_COLORS` hex map | Semantic tokens |

This ensures all themes (especially light themes) render correctly — previously `green-400` text on a white background was unreadable.

---

## 4. Chat Streaming Performance

During agent streaming, every token frame (~35ms) rebuilt all `ChatMessageItem` instances, re-parsed markdown, and re-highlighted code for every message. The fix targets four layers:

### 4a. React.memo + Stable Keys

`ChatMessageItem` and `ChatSidebar` are wrapped in `React.memo`. During streaming, only the last message re-renders; all previous messages are skipped.

Stable keys use a client-side ID (`msg.clientId ?? msg.id ?? i`):

```typescript
// chat/page.tsx
let clientMsgSeq = 0;
const nextClientId = (): string => `c-${++clientMsgSeq}`;
```

Without `clientId`, the streaming message's key would change from index to server-assigned `id` at stream end, causing a DOM remount and replaying the `mpIn` animation.

### 4b. Stable Callbacks (useCallback)

Every callback passed to `ChatMessageItem` or `ChatSidebar` is memoized:

| Callback | Pattern | Why |
|---|---|---|
| `copyToClipboard` | `useCallback([], ...)` | Stable identity |
| `editPrompt` / `selectSuggestion` | `useCallback([], ...)` | Calls `setInput` (stable) |
| `sendFeedback` | `useCallback([], ...)` via `feedbackRef` | Reads feedback for rollback but doesn't depend on it |
| `onRegenerate` | Latest-ref pattern (`regenerateRef`) | Reads `messages` which changes every frame |
| `newChat` / `openSession` / etc. | `useCallback([deps], ...)` | Stable during streaming (deps don't change mid-stream) |
| `formatTime` | `useCallback([], ...)` | Pure function, no deps |

The `feedbackRef` pattern avoids depending on the `feedback` state object:

```typescript
const feedbackRef = useRef<Record<number, string>>({});
useEffect(() => { feedbackRef.current = feedback; }, [feedback]);
const sendFeedback = useCallback(async (id, type) => {
  const prev = feedbackRef.current[id];
  setFeedback(prev => ({ ...prev, [id]: type }));
  // ... api call, rollback on error
}, []);
```

### 4c. Memoized Parsing

Inside `ChatMessageItem`:

```typescript
const parsedContent = useMemo(() => parseThoughtsAndCleanText(msg.content || ""), [msg.content]);
const markdownParts = useMemo(() => parseMarkdownTables(cleanText || ""), [cleanText]);
const markdownComponents = useMemo<Components>(() => ({
  code({ node, className, children, ...props }) { /* ... */ }
}), [copiedCode, onCopy, msg.role, assistantStreaming, isLast]);
```

Previously, `parseThoughtsAndCleanText` and `parseMarkdownTables` ran on every render of every message, and the `components` object for `ReactMarkdown` was recreated each time (defeating react-markdown's internal memoization).

### 4d. SyntaxHighlighter Out of Streaming Path

`MemoizedCodeBlock` now accepts a `streaming` prop:

```tsx
{streaming ? (
  <pre className="...">{codeString}</pre>  // cheap: no Prism
) : (
  <SyntaxHighlighter style={oneDark} ...>{codeString}</SyntaxHighlighter>
)}
```

While the block is still streaming, code renders as plain text (one highlight pass runs when the stream finishes). This eliminates Prism's per-frame highlighting cost during the streaming hot path.

### 4e. Per-Message Feedback Prop

Changed from `feedback: Record<number, string>` (all messages re-render on any thumb click) to `feedbackValue?: string` (only the clicked message re-renders).

---

## 5. Live Status Bar

New component `components/shell/LiveStatusBar.tsx` replaces the static `StatusBar` in the dashboard layout. It polls `/api/dashboard/stats` (bypassing cache) every 30 seconds and displays:

- Orchestrator status (up/down)
- Active agents (N running / M total)
- Channel health (ok · error count)
- Gate decisions (24h pass · block)
- RCF chain status

The original `StatusBar` and its tests are untouched — `LiveStatusBar` wraps it.

---

## 6. Tracing Toggle

Per-agent trace capture was previously only configurable via raw API calls (`tools_config.tracing.enabled: true`). Now it has a proper UI.

### Backend

Two new endpoints on the agents router:

```http
GET  /api/agents/{id}/tracing
→ { "enabled": false, "redact_pii": false }

PATCH /api/agents/{id}/tracing
Body: { "enabled": true }
→ { "enabled": true, "redact_pii": false }
```

Follows the same pattern as `GET/PATCH /agents/{id}/extraction` and `gates`.

### Frontend

The toggle appears in `AgentTracesPanel`:

- **When no traces exist:** a prominent card with toggle + explanation text.
- **When traces exist:** a compact bar at the top of the list showing ON/OFF status with a toggle switch.

Clicking the toggle writes through `PATCH /agents/{id}/tracing`, which updates `tools_config.tracing` in Postgres. The next agent turn checks `_tracing_enabled(agent)` in `tracing.py` and begins (or stops) writing to `agent_traces`.

### Tests

5 new tests in `test_agent_traces.py`:

- `test_get_tracing_config_defaults_to_off` — new agent, config defaults to disabled
- `test_patch_tracing_toggle_enabled` — enable persists and GET reflects it
- `test_patch_tracing_toggle_redact_pii` — PII flag independent of enabled
- `test_patch_tracing_disable_after_enable` — round-trip
- `test_tracing_config_agent_404` — unknown agent

---

## 7. Global Traces Page

A new top-level page at `/dashboard/traces` shows traces across **all** of the user's agents in a single paginated view.

### Backend

New router `backend/app/routers/traces.py`:

```http
GET /api/traces?limit=50&offset=0&outcome=completed_with_tools&agent_id=3
→ {
    "total": 123,
    "offset": 0,
    "limit": 50,
    "items": [
      {
        "id": "...",
        "agent_id": 3,
        "agent_name": "Sales Bot",
        "input_user_text": "...",
        "final_text": "...",
        "outcome": "completed_with_tools",
        "quality_label": "good",
        ...
      }
    ]
  }
```

Each item is enriched with `agent_name` (resolved from Postgres). The Mongo query is scoped to `user_id` and optionally narrowed to a single `agent_id`.

Registered in `main.py` as `app.include_router(traces.router, prefix="/api")`.

### Frontend

The page includes:
- Outcome filter dropdown
- Refresh button
- Paginated list with agent name links (clickable → agent detail page)
- Expandable trace details (tool calls, conversation, final answer)
- 👍/👎 feedback buttons on each trace

Navigation entry added to `dashboard-nav.ts` (Activity icon, between Playground and Self-Forging).

### Tests

6 new tests in `test_global_traces.py`:

- List returns items with agent_name enrichment
- Filters by agent_id
- Filters by outcome
- Empty agents list returns empty
- No MongoDB → friendly error
- Unknown agent → 404

---

## 8. Trace Feedback (👍/👎)

Directly rate a trace from the trace panel — no need to go back to the chat where the original reply lives.

### Backend

```http
POST /api/agents/{id}/traces/{trace_id}/feedback
Body: { "value": "thumbs_up" }  // or "thumbs_down"
→ { "ok": true, "reward": 1.0, "quality_label": "good" }
```

Uses `tracing.human_score()` to map value → reward/label, then updates the trace document in MongoDB with `human_labeled: true` and a timestamp.

### Frontend

Thumbs up/down buttons appear in both:
- **Agent-specific trace panel** (`AgentTracesPanel`) — inline in the metadata row
- **Global traces page** (`/dashboard/traces`) — same position

Both use optimistic updates: the button highlights immediately, rolling back on API failure.

### Tests

4 new tests in `test_agent_traces.py`:

- thumbs_up → reward 1.0, quality_label "good"
- thumbs_down → reward -1.0, quality_label "bad"
- Invalid value → 400
- Trace not found → 404

---

## 9. Self-Forging UI

New page at `/dashboard/forging` providing a visual interface for the self-forging pipeline (layers 2–3).

### Features

- **Golden set viewer:** lists frozen examples (input, expected, reward), first 50 inline with "Export to see all"
- **Freeze controls:** min_reward slider, human_only toggle, "Freeze Golden Set" button → `POST /forging/golden-set`
- **JSONL export:** "Export JSONL" button downloads `golden-set-sft.jsonl` directly
- **Edition gating:** community edition shows "Self-Forging unavailable" with explanation

### Backend

No new endpoints — the page uses existing `GET/POST /api/forging/golden-set`, `GET /api/forging/golden-set/export`, and `POST /api/forging/harness`.

### Navigation

Added to `dashboard-nav.ts` as "Self-Forging" with FlaskConical icon, after Traces.

---

## 10. SegmentedTabs

Reusable `SegmentedTabs` component (`components/ui/segmented-tabs.tsx`) replacing ad-hoc tab bars.

```tsx
<SegmentedTabs
  tabs={[
    { id: "overview", label: "Overview", icon: Zap },
    { id: "memory", label: "Memory", icon: Database },
    // ...
  ]}
  active={activeTab}
  onChange={setActiveTab}
/>
```

Renders a pill-group with active highlight (surface bg + shadow). Also exports `TabSection` for pages that want a title + description above the tabs.

---

## 11. Shared UI Components

### EmptyState

`components/ui/empty-state.tsx` — consistent empty/error state card (icon + title + description + optional action). Applied in:
- Agent traces panel (error + empty)
- Global traces page
- Agent list page
- Search page (replaced local `EmptyState` function)

### SkeletonRow

`components/ui/skeleton-row.tsx` — reusable animated skeleton placeholder with optional avatar circle and configurable line count. Available for future use in list loading states.

---

## 12. Agent Detail Page Tab Bar

The tab bar in `agents/[id]/page.tsx` was a hand-rolled button list with underline styling. Now uses `SegmentedTabs` for consistency with Automations and other pages that already use the component.

**Before:** custom buttons with `border-b-2 bg-accent` underline.

**After:** `SegmentedTabs` pill-group (pill bg, shadow, accent icon).

---

## Checking

### Backend

```bash
cd backend && python -m pytest tests/ -q
# 333 passed
```

### Frontend

```bash
cd frontend && npx tsc --noEmit   # 0 errors
cd frontend && npx jest            # 4/4
cd frontend && npx next build      # successful
```

---

## Branches & Commits

| Branch | Commit | Description |
|---|---|---|
| `feat/ui-polish-chat-perf` | `c35e4d0` | Design tokens fix + dead code + hex→tokens + LiveStatusBar + EmptyState + SegmentedTabs |
| (same) | `4193a53` | Chat streaming performance (memo, useCallback, useMemo, SyntaxHighlighter skip) |
| (same) | merged as PR #640 | |
| `feat/traces-forging-ui` | `a5c4cbe` | Tracing toggle + global traces + trace feedback + Self-Forging UI + SkeletonRow + per-message feedback |

---

## See Also

- `docs/guides/SELF_FORGING.md` — the self-forging loop (capture → label → freeze → export → harness)
- `docs/adr/0009-golden-set-and-harness.md` — golden set + harness design
- `backend/app/services/tracing.py` — trace capture, scoring, and feedback labeling
- `frontend/src/app/globals.css` — token definitions in `@theme inline`
