// NOTICE: This file is protected under RCF-PL v2.0.3
# ADR-0013: File Workspace — Append-Only Versions & Agent Actions Under Human Membership

**Status**: Accepted

**Date**: 2026-08-25

**Deciders**: Aladdin AI Inc. development team

**Tags**: backend, frontend, security, documents

## Context

Until now, files in AladdinAI existed only as chat/media attachments —
ephemeral blobs with no structure around them. Departments using the platform
need document workflow: shared folders, controlled multi-user access, and a
trustworthy answer to *"who changed this file, and when?"* — including what
was changed by an AI agent rather than a person.

Three forces shaped the design:

1. **Audit is the product.** A version history that can be rewritten (edit
   in place, rollback overwriting data, hard delete) cannot answer "what did
   the document look like before?" with confidence.
2. **Agents must be able to work with documents** — read reports, draft new
   versions, keep things tidy — but an LLM tool loop is exactly the kind of
   actor that must never destroy data or escalate privileges.
3. **Two entry points, one rulebook.** The same operation is reachable via
   REST and via agent tools; if authorization lives in two places they will
   drift.

## Decision

1. **Spaces are the access boundary; roles are coarse.**
   `WorkspaceSpace` + `SpaceMember` (`owner > editor > viewer`). Every request
   re-checks membership via `require_member(db, user_id, space_id, min_role)`
   from `app/services/file_workspace.py`; mutations require editor, space and
   member management require owner. The last owner of a space is irremovable.
   Non-membership and insufficient role return the **identical 403** so error
   messages leak no layout.

2. **History is append-only by construction.** `file_versions` and
   `file_events` receive `INSERT`s only:
   - uploading/editing appends a new `FileVersion`;
   - **restore = append** a new version pointing at the original's
     `storage_ref` (nothing is rolled back);
   - **delete is soft** (`files.deleted_at`) and history outlives it;
   - a unique constraint on `(file_id, version_no)` turns edit races into a
     clean `409`.

3. **Blob scope travels with the version.** Each `FileVersion` stores its
   `uploader_user_id`; downloads resolve bytes through *that* user's media
   scope ([ADR-0005](0005-media-storage-abstraction.md) abstraction). The blob
   reference is pinned to whoever produced the version, independent of later
   actors.

4. **One authorization/audit layer for both entry points.** Router and agent
   tools both call `app/services/file_workspace.py` (`require_member`,
   `_require_file`, `_add_event`, `_commit_version`, `blob_handle`) — the same
   pattern as `crm_service`. There is exactly one implementation of the rules.

5. **Agents get the safe set, acting as the chatting human.** Five tools in
   `app/tools/files_ws.py`: `files_list`, `files_read`, `files_upload_version`,
   `files_move`, `files_rename`.
   - `ToolContext.user_id` is the human who is chatting; every call re-checks
     *that* user's membership — an agent cannot exceed its driver's rights.
   - Mutating tools additionally require editor.
   - Every action lands in the timeline with `actor_type="agent"`; versions
     carry `agent_run_id` back to the run that wrote them.
   - **There is deliberately no delete tool.**
   - The surface is text-only and capped at 256 KB per read/write, refusing
     binaries — one tool call can neither flood model context nor bypass the
     UI upload path.

## Consequences

### Positive
- *"Who changed what"* has a definitive answer, per human vs AI agent.
- No code path can rewrite or erase history — bugs degrade to missing new
  data, never corrupted old data.
- Agents became useful inside Files without a single new privilege risk:
  worst case equals what the chatting user could do anyway.
- Adding a future entry point (CLI, webhook) inherits correct rules by
  calling the service layer.

### Negative
- Storage grows monotonically: repeated edits accumulate versions with no
  built-in pruning/quota yet.
- Soft-deleted rows linger by design; reporting queries must remember
  `deleted_at`.
- The safe set is small on purpose — agents cannot create files or spaces,
  only work within existing ones (a `files_upload_new` remains future work).
- Text-only tool writes mean binary formats (xlsx, pdf) are invisible to
  agent editing until an extraction layer exists.

### Neutral
- UI upload/download flows behave exactly as before; the workspace sits next
  to, not inside, chat attachments.
- Timeline events reuse the generic event-row shape; new event types are
  additive.

## Alternatives Considered

### Alternative 1: Agents act under their own service identity
- **Description**: Give each agent its own membership row / role and audit it
  directly.
- **Pros**: Clean attribution without `actor_type`; permissions independent
  of the driver.
- **Cons**: Requires inventing agent-identity management (invites, roles for
  bots), doubles the membership surface, and lets a runaway loop hold rights
  even when no human is watching.
- **Why not chosen**: Acting under the chatting human's existing membership
  gives identical capability with zero new privilege surface; attribution is
  preserved via `actor_type="agent"` + `agent_run_id`.

### Alternative 2: Hard delete + trash bin
- **Description**: Real deletes with a restore window.
- **Pros**: Familiar UX; storage bounded.
- **Cons**: The trash window is a second, weaker history system; "deleted"
  blobs still referenced by audit rows become dangling unless history is
  deleted too — which breaks decision 2.
- **Why not chosen**: Append-only soft delete achieves the same UX
  (disappear → restore) while keeping one immutable ledger.

### Alternative 3: Per-file ACLs
- **Description**: Fine-grained share-per-file permissions like Google Docs.
- **Pros**: Maximum flexibility for ad-hoc sharing.
- **Cons**: Heavy model + UI, and the actual need is departmental: people
  collaborate in units, not per spreadsheet.
- **Why not chosen**: Spaces cover the real workflow; per-file sharing can
  layer on top later without breaking the contract.

### Alternative 4: Agent tools proxy the HTTP API
- **Description**: Tools that call `http_post("/api/files/...")` with the
  user's session.
- **Pros**: Zero new backend code.
- **Cons**: Requires handling auth transport inside tools, couples agents to
  HTTP semantics/error shapes, and hides logic behind two hops.
- **Why not chosen**: Native tools calling the shared service layer get
  typed errors and identical guarantees with less machinery — consistent with
  ADR-0010's native-tools doctrine.

### Alternative 5: Delete tool behind an approval gate
- **Description**: Include `files_delete` but require explicit human approval
  per call.
- **Pros**: Full symmetry with human capability.
- **Cons**: Approval gates add friction to the most destructive op, and the
  legitimate agent use cases (drafting versions, organizing) never need it.
- **Why not chosen**: Asymmetry here is the feature — deletion stays a human
  hand on the API/UI.

## Implementation Notes

- Models & migration: `spaces`, `space_members`, `folders`, `workspace_files`,
  `file_versions`, `file_events` — migration `a7c3e91b4d52` (dialect-agnostic
  table checks).
- Service: `backend/app/services/file_workspace.py`; router:
  `backend/app/routers/workspace.py` (mounted under `/api`); tools:
  `backend/app/tools/files_ws.py`, enabled in `DEFAULT_TOOLS_BY_ROLE`
  (`_default`, `sales`).
- Frontend: `/dashboard/files` page (space switcher, folder tree, drag-n-drop,
  breadcrumbs, type icons, Changed column), details panel with Versions /
  Timeline tabs, and the assistant slide-over panel — a thin client over the
  streaming `/chat` endpoint injecting current space/folder/file context.
- Tests: `test_files_workspace.py` (14 — isolation, roles, roundtrip,
  multi-version, restore, history-outlives-delete, timeline) +
  `test_files_tools.py` (7 — registry shape, reads, non-member errors,
  agent-authored versions, viewer cannot mutate). Backend suite green
  (401 passed); ruff/tsc/jest/build clean; full CI green on PR #742.

## References

- [ADR-0005](0005-media-storage-abstraction.md) — media-storage abstraction the
  blob-scope decision builds on
- [ADR-0011](0011-multi-agent-swarm-and-tools.md) — swarm/tool architecture the
  agent tools plug into
- [File Workspace guide](../guides/FILE_WORKSPACE.md) — user-level tour
- `backend/app/services/file_workspace.py`,
  `backend/app/tools/files_ws.py`,
  `frontend/src/app/(dashboard)/dashboard/files/`
