---
adr: 0014
status: accepted
date: 2026-09-05
---

# ADR 0014: WRT Editor Visual Mode

## Context & Problem
The WRT Editor exposed raw `[b]`, `[i]`, etc., tags directly to users, complicating document authoring for non-technical users. We needed a Visual (WYSIWYG-like) mode while preserving the canonical WRT source for agents and backend storage.

## Decision
Implemented a bi-directional WRT ↔ HTML parser/serializer using `contentEditable`.
- Added **Visual Mode** (default): Uses semantic HTML (`<strong>`, `<em>`, etc.) for visual editing.
- Added **WRT Code Mode**: Maintains the raw source for advanced users.
- UI Layout: Moved to a centered canvas (`max-w-3xl`) and removed the split-pane preview.

## Consequences
- **Positive**: Seamless authoring for document-focused users; format tags are hidden; layout is cleaner.
- **Negative**: Adds complexity to maintenance of the bi-directional serializer in `frontend/src/lib/wrt.ts`.
- **Preservation**: All existing `.wrt` files and backend audit trails remain fully compatible.
