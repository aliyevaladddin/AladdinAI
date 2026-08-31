# WRT Editor — In-Browser Editing for `.wrt` Files

**Added in:** PR #790 (31 Aug 2026)

---

## Overview

The **WRT Editor** is a Monaco-based in-browser editor integrated into the File Workspace, allowing users to edit `.wrt` (tagged text) files directly in the Files page without downloading them.

Key features:
- **Syntax highlighting** for `.wrt` tags (headings, bold, italic, lists, tables, etc.)
- **Light/Dark theme** support with automatic detection
- **Keyboard shortcuts** — `Ctrl+S` / `Cmd+S` to save
- **Version control** — each save creates a new file version with audit trail
- **Zero external dependencies** — Monaco loaded from CDN, no build changes

---

## What is `.wrt`?

`.wrt` (pronounced "writ") is AladdinAI's lightweight tagged-text format for AI-editable documents. It serves as the intermediate representation for office documents (`.docx`, `.pdf`) that agents read and edit.

See [`PULL_REQUEST_DOCX_WRT.md`](../PULL_REQUEST_DOCX_WRT.md) for the full format specification and converter architecture.

---

## User Flow

1. **Open a `.wrt` file** in `/dashboard/files`
2. **Click "Edit"** button (only visible for `.wrt` files when user has edit permissions)
3. **Edit in Monaco editor** with syntax highlighting
4. **Save changes**:
   - Click "Save Version" button, OR
   - Press `Ctrl+S` (Windows/Linux) / `Cmd+S` (Mac)
5. **New version created** — saved as a new file version with comment "Edited in browser"
6. **Audit trail preserved** — version history shows who edited what, when

---

## Technical Architecture

### Frontend Components

#### `wrt-editor.tsx`
Location: `frontend/src/components/wrt-editor.tsx`

Monaco-based editor component with:
- Custom language tokenizer for `.wrt` syntax
- Theme definitions (`wrt-light` / `wrt-dark`) matching system theme
- Keyboard shortcut registration (`Ctrl/Cmd+S`)
- Props: `content`, `onChange`, `onSave`, `readOnly`, `className`

**Tokenizer rules:**
```typescript
[/\[h[123]\]/, "tag.heading.open"],          // [h1] [h2] [h3]
[/\[(b|i|u|s|code)\]/, "tag.inline.open"],  // [b] [i] [u] [s] [code]
[/\[(quote|list|table)\]/, "tag.block.open"], // [quote] [list] [table]
[/\[img\s+alt="[^"]*"\]/, "tag.image"],      // [img alt="..."]
[/^\*\s+/, "list.item"],                     // * list items
[/^\|.*\|$/, "table.row"],                   // | table | rows |
```

**Theme colors:**
- Light: blue headings, green inline tags, purple block tags
- Dark: VS Code-style colors (569CD6, 4EC9B0, C586C0)

#### Files Page Integration
Location: `frontend/src/app/(dashboard)/dashboard/files/page.tsx`

State management:
```typescript
const [isEditing, setIsEditing] = useState(false);
const [editedContent, setEditedContent] = useState("");
const [saving, setSaving] = useState(false);
```

Conditional rendering:
- **Edit button** — only shown for `.wrt` files when `canEdit && isWrtContent(fileContent)`
- **Editor view** — replaces preview when `isEditing === true`
- **Cancel/Save buttons** — Save calls `uploadTextVersion()` API

#### API Layer
Location: `frontend/src/app/(dashboard)/dashboard/files/api.ts`

```typescript
export async function uploadTextVersion(
  fileId: number,
  content: string,
  filename: string,
  comment?: string,
): Promise<FileVersion> {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const file = new File([blob], filename, { type: "text/plain" });
  return uploadNewVersion(fileId, file, comment);
}
```

Converts in-memory text → Blob → File → multipart upload.

---

## Backend Changes (None Required)

The editor reuses **existing endpoints**:
- `GET /api/files/{file_id}/content` — loads file content for editor
- `POST /api/files/{file_id}/upload_version` — saves new version via multipart upload

No backend changes were needed — the editor works with the existing File Workspace API.

---

## Embedding Model Fallback (Same PR)

PR #790 also included **embedding model fallback chains** to handle deprecated/unavailable models gracefully.

### Changes in `backend/app/services/memory.py`:

**Before:**
```python
EMBEDDING_MODELS = {
    "nvidia_nim": "nvidia/llama-nemotron-embed-1b-v2",  # Single model
    "openai": "text-embedding-3-large",
}
```

**After:**
```python
EMBEDDING_MODELS = {
    "nvidia_nim": [
        "nvidia/nv-embedqa-e5-v5",      # Current recommended (2048 dim)
        "nvidia/nv-embed-v2",            # Alternative (4096 dim)
        "baai/bge-m3",                   # Fallback (1024 dim)
    ],
    "openai": [
        "text-embedding-3-large",        # 3072 dim
        "text-embedding-3-small",        # 1536 dim
        "text-embedding-ada-002",        # Legacy fallback
    ],
}
```

**Retry logic:**
```python
for attempt_model in model_chain:
    payload["model"] = attempt_model
    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        break  # Success!
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 410):  # Model EOL or not found
            log.warning(f"Model {attempt_model} unavailable, trying fallback...")
            continue
        raise
```

### PII Detection Fallbacks

Also added in `backend/app/services/recommended_models.py`:

```python
SAFETY_RECOMMENDATIONS = {
    "pii": [
        "gliner",
        "piiranha",
        "deberta-pii",
        # Fallback: general-purpose LLMs for PII detection
        "llama-3.1-8b-instruct",
        "llama-3.2-3b-instruct",
        "mistral-7b-instruct",
    ],
}
```

---

## Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/test_memory.py -v
```
Result: **28 passed** ✅

Tests updated to use new default model:
```python
provider.embedding_model = "nvidia/nv-embedqa-e5-v5"  # Was llama-nemotron-embed-1b-v2
```

### Frontend Type Checking
```bash
cd frontend
npx tsc --noEmit
```
Result: **0 errors** ✅

### Manual Testing Checklist
- [ ] Open `.wrt` file in Files page
- [ ] Click Edit button
- [ ] Verify syntax highlighting (light/dark themes)
- [ ] Modify content
- [ ] Save with `Ctrl+S` / `Cmd+S`
- [ ] Verify new version created
- [ ] Check audit timeline shows "Edited in browser"

---

## Known Issues

- **ESLint broken** — `eslint-plugin-react` compatibility issue with ESLint 10.x (not related to this PR, pre-existing)
- **Monaco bundle size** — `@monaco-editor/react` adds ~2MB to frontend bundle (lazy-loaded)

---

## Future Enhancements

- [ ] **Markdown mode** — syntax highlighting for `.md` files
- [ ] **Diff view** — compare current edit with last version before saving
- [ ] **Collaborative editing** — real-time multi-user editing via WebSockets
- [ ] **Mobile support** — responsive editor layout for tablets
- [ ] **Vim/Emacs keybindings** — optional keybinding modes

---

## Related Documentation

- [`.wrt` Format Spec](../PULL_REQUEST_DOCX_WRT.md) — tag syntax, converter architecture
- [File Workspace Architecture](../adr/0013-file-workspace-append-only-agent-safety.md) — append-only versioning, audit trail
- [UI Feature Guide](../UI_FEATURE_GUIDE.md) — command palette, keyboard shortcuts

---

## Commit History

PR #790: `feat/wrt-editor-embedding-fallback`

**Commit:** `1650b63`
```
feat: add WRT editor and embedding model fallback chains

Backend changes:
- Add fallback chains for embedding models (nvidia_nim, openai, huggingface)
- Implement retry logic for embedding requests on 404/410 errors
- Update default NIM model to nv-embedqa-e5-v5
- Add LLM fallbacks for PII detection in safety recommendations

Frontend changes:
- Add Monaco-based WRT editor with syntax highlighting
- Integrate WRT editor into Files page with Edit button
- Add uploadTextVersion API for saving editor content as new file version
- Support Ctrl+S/Cmd+S shortcuts for saving changes

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Files changed:** 6 files | +381 / −26 lines
- `backend/app/services/memory.py` — fallback chains
- `backend/app/services/recommended_models.py` — PII fallbacks
- `backend/tests/test_memory.py` — updated model names
- `frontend/src/components/wrt-editor.tsx` — NEW
- `frontend/src/app/(dashboard)/dashboard/files/api.ts` — uploadTextVersion
- `frontend/src/app/(dashboard)/dashboard/files/page.tsx` — editor integration
