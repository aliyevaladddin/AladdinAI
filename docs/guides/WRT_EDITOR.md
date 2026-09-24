# WRT Editor — In-Browser Editing for `.wrt` Files

**Added in:** PR #790 (31 Aug 2026) | **Updated:** Sept 24, 2026 (Pure C Backend Refactoring)

---

## Overview

The **WRT Editor** is a multi-mode document editor for `.wrt` (Word Rich Text) files in AladdinAI:
- **Visual Mode** (default): WYSIWYG editing via `contentEditable` with semantic toolbar
- **WRT Code Mode**: Monaco-based raw tag editor with custom syntax highlighting
- **C IDE Mode**: Terminal-based C editor with ANSI highlighting (for `.wrt` files)

### Key Architectural Principle
**Pure C Backend as Single Source of Truth:** All parsing, validation, serialization, and WRT ↔ HTML conversion are handled by the native C engine (`backend/native/wrt/wrt_engine.c`). The TypeScript frontend (`page.tsx`) is a thin client that handles UI rendering and proxies operations to the C engine via `WrtEngineClient`.

---

## What is `.wrt`?

`.wrt` (pronounced "writ") is AladdinAI's lightweight tagged-text format for AI-editable documents. It serves as the intermediate representation for office documents (`.docx`, `.pdf`) that agents read and edit.

See [`PULL_REQUEST_DOCX_WRT.md`](../PULL_REQUEST_DOCX_WRT.md) for the full format specification.

---

## Supported Tags

| Tag | Rendered HTML | Description |
|-----|---------------|-------------|
| `[h1]...[/h1]` | `<h1 class="wrt-heading">` | Main Heading |
| `[h2]...[/h2]` | `<h2 class="wrt-heading">` | Subheading |
| `[h3]...[/h3]` | `<h3 class="wrt-heading">` | Section Heading |
| `[b]...[/b]` | `<strong>` | Bold |
| `[i]...[/i]` | `<em>` | Italic |
| `[u]...[/u]` | `<u>` | Underline |
| `[s]...[/s]` | `<s>` | Strikethrough |
| `[code]...[/code]` | `<code>` | Inline Code / Monospace |
| `[quote]...[/quote]` | `<blockquote class="wrt-quote">` | Block Quote |
| `[list]...[/list]` | `<ul class="wrt-list">` | Unordered List (`* Item`) |
| `[table]...[/table]` | `<table class="wrt-table">` | Table (Pipe-delimited) |
| `[img src="..." alt="..."]` | `<img class="wrt-image">` | Base64 Embedded Image |

---

## Editor Modes

### 1. Visual Mode (Default)
- **WYSIWYG document editing** via `contentEditable`
- **Formatting toolbar:** Bold, Italic, Underline, Strikethrough, Code, Quote, Headings, Lists, Tables
- **Bi-directional conversion:** HTML ↔ WRT handled by C engine (`wrt_to_editable_html`, `wrt_from_editable_html`)
- **Centered document canvas** (`max-w-3xl`) with collapsible side drawer (Versions, Timeline)

### 2. WRT Code Mode
- Monaco-based code editor for raw WRT tags
- Custom syntax highlighting rules for `.wrt` syntax
- Dark / Light theme support matching dashboard theme
- Real-time syntax validation via C engine (`wrt_validate`)

### 3. C IDE Mode (Terminal)
- Native terminal editor (`wrt_edit.c`) with ANSI color highlighting
- Direct keyboard shortcuts (`Ctrl+B`, `Ctrl+I`, `Ctrl+S`, `Ctrl+Q`)
- Accessible only for `.wrt` files
- Seamless state reload on switching back to Visual/Code mode

---

## Technical Architecture

### 1. C Engine Layer (`backend/native/wrt/`)
- `wrt_engine.c` — ~1800 LOC pure C11 engine
- `wrt_validate()` — structural tag validation, severity levels (0=error, 1=warning)
- `wrt_fix()` — auto-repair unclosed tags and empty tag cleanups
- `wrt_to_html()` / `wrt_to_editable_html()` — WRT to semantic HTML
- `wrt_from_editable_html()` — contentEditable HTML back to canonical WRT (with boundary checks)
- Daemon & CLI support for standalone usage

### 2. Python REST API Layer (`backend/app/services/wrt_engine_service.py`)
- `POST /wrt/validate` — document validation
- `POST /wrt/fix` — auto-fix document
- `POST /wrt/to-html` — WRT to standard HTML
- `POST /wrt/to-editable-html` — WRT to contentEditable HTML
- `POST /wrt/from-editable-html` — contentEditable HTML to WRT
- `POST /wrt/stats` — word, line, character, and tag counts

### 3. Frontend Client (`frontend/src/lib/wrt-engine-client.ts`)
- Async TypeScript client `WrtEngineClient` for all C engine endpoints
- Transparent error handling and fallback behavior
- Zero client-side parsing logic

### 4. Storage & Drafts
- File-specific `localStorage` draft keys: `wrt-draft-{source}-{hash}`
- Prevents cross-file draft contamination
- Drafts cleared upon successful save to backend

---

## Testing & Verification

### C Test Suite & Pytest Integration
The C engine tests are fully integrated into the project's `pytest` suite:

```bash
# Run all WRT tests (C unit tests + standalone tests + CLI integration)
cd backend
python -m pytest tests/test_native_wrt.py -v
```

**Results:** **49 tests passing** in 0.16s:
- `TestWRTEngineC`: 21 unit tests linked against `wrt_engine.c` (validation, fix, HTML conversion, round-trips, entities, unicode)
- `TestStandaloneWRT`: 17 standalone HTML→WRT parser tests
- `TestWRTEngineCLI`: 11 subprocess integration tests (CLI commands, file operations, recent files)

### Key Edge Cases Covered
- **Tag boundary checking:** `<blockquote>` is never misidentified as `[b]lockquote`
- **Inline tag auto-paragraphs:** Inline tags outside block elements are wrapped in `<p>`
- **HTML entity decoding:** `&amp;`, `&lt;`, `&gt;`, `&quot;` decoded correctly
- **Full round-trip integrity:** `WRT → HTML → WRT` preserves all structure

---

## Related Documentation

- [WRT Editor Architecture & CLI Guide](../WRT_EDITOR.md)
- [ADR 0014: WRT Editor Visual Mode](../adr/0014-wrt-visual-editor.md)
- [Format Specification (`PULL_REQUEST_DOCX_WRT.md`)](../PULL_REQUEST_DOCX_WRT.md)
- [Testing Setup Guide](../TESTING_SETUP.md)
