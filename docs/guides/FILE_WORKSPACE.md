// NOTICE: This file is protected under RCF-PL
# File Workspace — Spaces, Versions & Audit

The File Workspace turns AladdinAI from a chat with attachments into a place
where departments keep their documents. Every change is attributable — the
timeline answers *who changed what, and when*, including what an AI agent
changed and on whose behalf.

You will learn how spaces and roles gate access, why version history is
append-only, which file operations AI agents are allowed to perform, and how
the `/dashboard/files` page ties it together.

## 🗂️ Spaces & roles

A **space** is the access boundary. Files, folders, versions and events all
belong to a space; nothing crosses that line. Membership is explicit — being
able to see one space says nothing about another.

Every member has one of three roles:

| | Viewer | Editor | Owner |
|---|---|---|---|
| List / read / download files & history | ✅ | ✅ | ✅ |
| Upload, add versions, rename, move | ❌ | ✅ | ✅ |
| Soft-delete & restore files | ❌ | ✅ | ✅ |
| Create / delete folders | ❌ | ✅ | ✅ |
| Manage members (add, change role, remove) | ❌ | ❌ | ✅ |
| Rename / delete the space | ❌ | ❌ | ✅ |

Two rules worth knowing:

- **The last owner is irremovable.** A space always keeps at least one owner.
- **403 is 403.** "Not a member" and "member without a sufficient role"
  return the identical error, so error messages never leak whether a space
  or file exists.

Authorization lives in `app/services/file_workspace.py` (`require_member`,
role checks, audit helpers). The REST router and the agent tools call the
**same** functions — there is exactly one access-control implementation, not
one per entry point.

## 📁 Folders

Folders form a tree inside a space (`parent_id`). Moving a folder is
cycle-safe: you cannot drop a folder into its own descendant. Folder moves
and renames are ordinary operations; files record folder changes as timeline
events.

## 🔒 The append-only contract

History is immutable by construction. Two tables — `file_versions` and
`file_events` — only ever receive `INSERT`s:

```
upload v1 ──▶ upload v2 ──▶ restore v1 ──▶ upload v3     (versions)
   │             │             │              │
   ▼             ▼             ▼              ▼
  created    version_added  restored     version_added   (events)
```

- **Editing a file appends a new version.** Old bytes stay byte-for-byte
  readable at their original version number, forever.
- **Restoring is appending.** "Restore v1" does not roll anything back — it
  appends a new version pointing at v1's stored blob. The timeline shows the
  restore as an event; no data was overwritten to produce it.
- **Deleting is soft.** A deleted file gets `deleted_at` set and disappears
  from listings, but its rows remain; history outlives deletion, and an
  editor can restore the file afterwards.
- **Concurrent edits surface as `409`, not corruption.** A unique constraint
  on `(file_id, version_no)` turns a race into a clean conflict response.

Blob storage keeps this honest: each version stores the `uploader_user_id`
who produced it, and downloads read through *that* user's media scope. A
version's bytes therefore survive even if the person who restored it has
different media permissions — the blob reference travels with the version
that created it.

## 🧾 Audit timeline

Every meaningful action writes an event row:

| Event | Written when |
|---|---|
| `created` | file uploaded (first version) |
| `version_added` | new version appended (upload, restore, agent write) |
| `downloaded` | content read via download endpoint **or** `files_read` tool |
| `restored` | old version restored as new head |
| `moved` | file moved between folders (or to root) |
| `renamed` | file renamed |
| `deleted` | soft-deleted |

Each event records `actor_type` (`human`, `agent`, or `system`) plus the
acting user; display names are resolved server-side. This is the feature's
core promise for departments: the timeline distinguishes *"Anna uploaded v3"*
from *"🤖 AI agent updated v4 on Anna's behalf"*.

## 🤖 AI agents in Files

Agents get a deliberately small, safe tool set — registered in the normal
tool registry and enabled in the default tool sets:

| Tool | Arguments | Effect |
|---|---|---|
| `files_list` | `space_id`, `folder_id?` | list files of a space/folder |
| `files_read` | `file_id`, `version_no?` | read text content (any version) |
| `files_upload_version` | `file_id`, `content`, `comment?` | append a new version |
| `files_move` | `file_id`, `folder_id` (null = root) | move between folders |
| `files_rename` | `file_id`, `name` | rename |

Four rules make this safe to hand to an LLM:

1. **Agents act under the chatting human's membership.** `ToolContext.user_id`
   is the person talking to the agent; every tool re-checks that user's space
   membership on every call. An agent can never exceed the rights of whoever
   is driving it.
2. **Mutations need editor.** A viewer chatting with an agent gets read-only
   behaviour from the very same tools.
3. **Everything lands in the timeline as `actor_type="agent"`.** Version
   metadata also carries the `agent_run_id`, so an AI-authored version is
   traceable to the run that wrote it.
4. **There is no delete tool — deliberately.** An AI must not be able to
   remove a department's documents. Soft-delete exists only through the API/UI,
   under a human hand.

The tools are text-only by design: reads and writes are capped at 256 KB and
binary content is refused, so a single tool call can neither flood the model
context nor smuggle binaries past the UI upload path. Errors follow the
registry convention `{"status": "error", "message": …}` — the agent sees a
sentence like "editor role required", not a stack trace.

### Document format support

`files_read` auto-converts office documents to text the agent can work with:

| Format | Conversion |
|--------|-----------|
| `.docx` | → `.wrt` tagged text (our lightweight format) |
| `.pdf` | → plain text (via pypdf) |
| `.xlsx` / `.xls` | → tab-separated text per sheet (via openpyxl) |
| `.txt`, `.md`, `.json`, `.csv`, `.html`, etc. | → raw text (unchanged) |
| Binary (images, zip, etc.) | → error: download via UI |

**The `.wrt` format** is a lightweight tagged-text representation of documents:

```
[h1]Chapter Title[/h1]
This is a paragraph with [b]bold[/b] and [i]italic[/i] text.

[list]
* First item
* Second item with [b]bold[/b]
[/list]

[table]
| Header 1 | Header 2 |
| Cell 1   | Cell 2   |
[/table]
```

Supported tags: `[h1]`–`[h3]`, `[b]`, `[i]`, `[u]`, `[s]`, `[code]`,
`[quote]`, `[list]`, `[table]`.

**Round-trip flow:**
1. User uploads `report.docx` → stored as-is in workspace.
2. Agent calls `files_read` → backend converts `.docx` to `.wrt` on-the-fly.
3. Agent edits the `.wrt` text and uploads a new version via `files_upload_version`.
4. User downloads `report.docx` → backend detects `.wrt` content, converts back to `.docx`.

The agent never needs to know about binary formats — it works entirely with
`.wrt` tagged text. The conversion is transparent.

Converter: `backend/app/services/docx_converter.py`
Frontend viewer: `frontend/src/components/wrt-viewer.tsx`

### The assistant panel

The Files page has a floating 🤖 button opening a slide-over chat with any of
your agents. It is a thin client over the existing streaming `/chat`
endpoint — agents keep running server-side in the orchestrator; the panel
injects the current space/folder/file as context chips, so "update this
report" means the file you are looking at. When the agent calls a file tool,
the result appears in the table and timeline immediately after.

## 🖥️ The Files page

`/dashboard/files` is the single UI over all of this:

- **Space switcher** (+ create) and your effective role per space.
- **Folder tree** on the left; drag-n-drop upload onto the table.
- **File table** with size, current version and a relative-time *Changed*
  column (computed server-side from version timestamps).
- **Breadcrumbs** `🏠 > Space > Folder > Subfolder` above the table — every
  segment is clickable navigation.
- **Colored type icons**: PDFs, documents, spreadsheets, images, archives,
  code, audio and video each get a stable color at a glance.
- **Details panel** per file with *Versions* and *Timeline* tabs: download or
  restore any version (agent-authored versions carry a 🤖 AI badge), rename,
  move, soft-delete.

## 🔌 REST API surface

All endpoints live under `/api` (see [API.md](../API.md) for generated
reference):

| Group | Endpoints |
|---|---|
| Spaces | `POST/GET /spaces`, `PATCH/DELETE /spaces/{id}` |
| Members | `POST/GET /spaces/{id}/members`, `PATCH/DELETE .../members/{user_id}` |
| Folders | `POST/GET /spaces/{id}/folders`, `PATCH/DELETE /folders/{id}` |
| Files | `GET /spaces/{id}/files`, `POST /spaces/{id}/files/upload` |
| File ops | `GET /files/{id}/download?version=N`, `GET /files/{id}/content`, `POST /files/{id}/upload_version`, `PATCH /files/{id}` (rename), `PATCH /files/{id}/move`, `POST /files/{id}/restore`, `DELETE /files/{id}` (soft) |
| History | `GET /files/{id}/versions`, `GET /files/{id}/events` |

## 🗺️ Where things live

| Path | Role |
|---|---|
| `backend/app/services/file_workspace.py` | shared authorization + audit layer (single source of truth) |
| `backend/app/routers/workspace.py` | REST endpoints, thin over the service |
| `backend/app/tools/files_ws.py` | the five agent tools |
| `backend/app/models/*.py` | `WorkspaceSpace`, `SpaceMember`, `Folder`, `WorkspaceFile`, `FileVersion`, `FileEvent` |
| `backend/app/services/docx_converter.py` | `.docx` ↔ `.wrt` bidirectional converter |
| `frontend/src/components/wrt-viewer.tsx` | `.wrt` format renderer |
| `frontend/src/app/(dashboard)/dashboard/files/` | page, assistant panel, type icons |
| `backend/tests/test_files_workspace.py`, `test_files_tools.py` | isolation/roles/history tests + agent-tool tests |

Design rationale (why append-only, why no delete tool, alternatives
considered) is recorded in [ADR-0013](../adr/0013-file-workspace-append-only-agent-safety.md).
