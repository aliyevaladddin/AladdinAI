---
adr: 0014
status: accepted
date: 2026-09-05
updated: 2026-09-24
---

# ADR 0014: WRT Editor Visual Mode

## Context & Problem
The WRT Editor exposed raw `[b]`, `[i]`, etc., tags directly to users, complicating document authoring for non-technical users. We needed a Visual (WYSIWYG-like) mode while preserving the canonical WRT source for agents and backend storage.

## Decision
Implemented a **pure C backend** as the single source of truth for all WRT parsing, validation, serialization, and WRT ↔ HTML conversion, with a **thin TypeScript/React frontend** using `contentEditable` for WYSIWYG editing.

- **Visual Mode** (default): Uses semantic HTML (`<strong>`, `<em>`, `<blockquote>`, etc.) rendered via `contentEditable`. All conversion to/from canonical WRT handled by C engine (`wrt_to_editable_html`, `wrt_from_editable_html`).
- **WRT Code Mode**: Monaco-based raw source editor with custom syntax highlighting for `.wrt` tags.
- **C IDE Mode**: Terminal-based C editor with ANSI highlighting (`.wrt` files only).
- UI Layout: Centered document canvas (`max-w-3xl`) with collapsible side drawer (Versions, Timeline). Removed split-pane preview.
- **Zero client-side parsing logic** — TypeScript frontend only renders and proxies to C engine via `WrtEngineClient` and REST API.

## Consequences
- **Positive**: Seamless authoring for document-focused users; format tags hidden; clean layout; fast, correct round-trips; single source of truth eliminates sync bugs.
- **Negative**: Adds C compilation step to build; requires libzip/zlib dependencies.
- **Preservation**: All existing `.wrt` files and backend audit trails remain fully compatible.

## Migration from TypeScript Parser (Sept 24, 2026)
The original ADR described a TypeScript bi-directional serializer in `frontend/src/lib/wrt.ts`. This was **fully replaced** by the C engine:
- **Removed**: `frontend/src/lib/wrt.ts` (parser/serializer logic)
- **Added**: `backend/native/wrt/wrt_engine.c` (~1800 LOC C11)
- **Added**: Python REST wrapper (`backend/app/services/wrt_engine_service.py`)
- **Added**: TypeScript client (`frontend/src/lib/wrt-engine-client.ts`)
- **Test coverage**: 49 pytest tests (21 C unit + 16 standalone + 11 CLI integration)

## Key Technical Decisions
1. **C11 standard** — portable, no runtime dependencies beyond libc + libzip/zlib
2. **On-demand pytest compilation** — tests compile `wrt_engine.c` with `-DWRT_ENGINE_NO_MAIN` and link against `test_wrt.c`
3. **Boundary checks for HTML tag parsing** — prevents `<blockquote>` → `[b]lockquote` corruption (see CRITICAL fix in `wrt_from_editable_html`)
4. **Auto-open paragraphs for inline tags** — ensures inline tags outside block elements render correctly (regression fix in `wrt_to_html`)
5. **File-specific localStorage drafts** — keys: `wrt-draft-{source}-{hash}` prevents cross-file contamination

## Related Documentation
- [WRT Editor Architecture & CLI Guide](../WRT_EDITOR.md)
- [WRT Editor Guide (Guides)](../guides/WRT_EDITOR.md)
- [C Engine Source](../backend/native/wrt/wrt_engine.c)
- [Test Suite](../backend/tests/test_native_wrt.py)