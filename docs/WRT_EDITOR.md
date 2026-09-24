# WRT Editor — Lightweight Document Editing Mode

**Location:** `backend/native/wrt/` (C engine) + `frontend/src/app/(dashboard)/dashboard/wrt-editor/` (TSX frontend)  
**Status:** ✅ Implemented (Sept 2026) — **Refactored to pure C backend + thin TSX frontend**  
**Purpose:** Native C-based WRT parsing/validation/serialization with web-based Visual (contentEditable) editor

---

## Overview

WRT Editor is a lightweight document editor for `.wrt` documents with a **pure C backend** (`wrt-engine`) and a **thin TypeScript/React frontend** using `contentEditable` for WYSIWYG editing.

### What is `.wrt`?

`.wrt` (Word Rich Text) is AladdinAI's proprietary format for representing office documents as plain text with semantic tags. Agents work with `.wrt`, while users upload/download real `.docx` files.

**Example `.wrt` document:**
```
[h1]Chapter Title[/h1]
This is a paragraph with [b]bold[/b] and [i]italic[/i] text.

[h2]Section 2[/h2]
More content with [u]underlined[/u] and [code]monospace[/code] text.

[list]
* First item
* Second item with [b]bold[/b]
[/list]

[table]
| Header 1 | Header 2 |
| Cell 1   | Cell 2   |
[/table]
```

### Supported Tags

- `[h1]...[/h1]`, `[h2]...[/h2]`, `[h3]...[/h3]` — headings
- `[b]...[/b]` — bold text
- `[i]...[/i]` — italic
- `[u]...[/u]` — underline
- `[s]...[/s]` — strikethrough
- `[code]...[/code]` — monospace/code
- `[quote]...[/quote]` — block quote
- `[list]...[/list]` — unordered list (items start with `*`)
- `[table]...[/table]` — table (pipe-delimited)
- `[img src="..." alt="..."]` — embedded image (base64)

---

## Architecture: C Engine + TSX Frontend (NEW)

### C Engine (`backend/native/wrt/`)

The C engine is the **single source of truth** for all WRT parsing, validation, serialization, and conversion.

**Files:**
```
backend/native/wrt/
├── wrt_engine.h       — public API (structs, function prototypes)
├── wrt_engine.c       — core implementation (~1800 lines)
├── test_wrt.c         — pytest-integrated unit tests (19 test functions)
├── test_standalone.c  — standalone HTML→WRT conversion tests
└── Makefile           — build script
```

**Key API Functions:**
```c
// Validation & fixing
void wrt_validate(const char *text, wrt_report_t *out);
char *wrt_fix(const char *text);

// Conversion: WRT → HTML
char *wrt_to_html(const char *text);
char *wrt_to_editable_html(const char *text);

// Conversion: contentEditable HTML → WRT
char *wrt_from_editable_html(const char *html);

// CLI / Daemon
int wrt_engine_cli(int argc, char **argv);
int wrt_engine_daemon(const char *socket_path);
```

**Build:**
```bash
cd backend/native/wrt
make          # builds wrt-engine binary
make test     # runs C test suite
```

### Python REST API (`backend/app/services/wrt_engine_service.py`)

Thin wrapper around C engine via `subprocess`:
- `POST /wrt/validate` — validate WRT document
- `POST /wrt/fix` — auto-fix common issues
- `POST /wrt/to-html` — convert WRT → HTML
- `POST /wrt/to-editable-html` — convert WRT → contentEditable HTML
- `POST /wrt/from-editable-html` — convert contentEditable HTML → WRT
- `POST /wrt/stats` — document statistics
- `POST /wrt/list-files` / `read-file` / `save-file` / `recent-files` — file operations

### Frontend TypeScript (`frontend/src/app/(dashboard)/dashboard/wrt-editor/`)

**Components:**
- `page.tsx` — main editor page, mode switching (Visual / WRT Code / C IDE)
- `WrtEngineClient` (`@/lib/wrt-engine-client.ts`) — async client for C API
- `contentEditable` div — WYSIWYG editing surface

**Key Features:**
- **Visual Mode** (default): contentEditable with semantic HTML, toolbar for formatting
- **WRT Code Mode**: raw WRT source with syntax highlighting (Monaco)
- **C IDE Mode**: terminal-based C editor for `.wrt` files (only for `.wrt` files)
- **Seamless Sync**: Bi-directional conversion preserves semantic structure
- **Auto-save**: File-specific localStorage drafts (`wrt-draft-{source}-{hash}`)

---

## Visual Editor Mode (Frontend)

**Status:** ✅ Implemented (Sept 2026) — rewritten with C backend  
**Location:** `/frontend/src/app/(dashboard)/dashboard/wrt-editor/`

For normal document authors who do not want to manage raw WRT tags (`[b]`, `[i]`), a **Visual mode** is available in the web dashboard.

### Key Features
- **WYSIWYG Editing:** Edit formatted text directly without seeing WRT markup.
- **Seamless Sync:** Bi-directional conversion (`ContentEditable` HTML ↔ `.wrt`) via C engine.
- **Integrated Layout:** Centered document canvas with collapsible side drawer (Versions, Timeline).
- **Mode Switching:** Easily toggle between **Visual**, **WRT Code**, and **C IDE** modes.

### Usage
1. Open any `.wrt` or `.docx` file in the Dashboard.
2. The document appears in **Visual** mode by default.
3. Use the toolbar buttons to format text (Bold, Italic, Underline, Strikethrough, Code, Quote, Headings, Lists, Tables).
4. Use the toggle to switch to **WRT Code** mode if you need direct tag control for agents.
5. Use **C IDE** mode (for `.wrt` files only) for terminal-based editing with ANSI highlighting.

---

## C Engine: Core Functionality

### Validation (`wrt_validate`)
- Checks tag matching (open/close pairs)
- Detects unknown tags
- Detects empty tags `[]`
- Reports word count, char count, line count, tag count
- Issues have severity: `0 = error`, `1 = warning`

### Fixing (`wrt_fix`)
- Auto-closes unclosed tags
- Removes empty tags
- Preserves valid content

### WRT → HTML (`wrt_to_html`)
- Converts all WRT tags to semantic HTML
- Tables, lists, quotes, headings
- Inline tags: `[b]`→`<strong>`, `[i]`→`<em>`, `[u]`→`<u>`, `[s]`→``, `[code]`→`<code>`

### WRT → contentEditable HTML (`wrt_to_editable_html`)
- Wraps output in `<div class="wrt-editable">`
- Ensures block-level structure for contentEditable
- Adds CSS classes for styling

### contentEditable HTML → WRT (`wrt_from_editable_html`)
- **Critical fix:** Boundary checks to prevent false matches (e.g., `<blockquote>` → `[b]lockquote`)
- Handles HTML entities (`&` → `&`, `<` → `<`)
- Strips unknown tags, preserves known semantic tags
- Converts back to canonical WRT format

---

## C Test Suite + pytest Integration

Three C test programs integrated into `pytest` via `backend/tests/test_native_wrt.py`. Pytest compiles and runs binaries via `subprocess`.

### Test Programs

| Program | Description | Tests |
|---------|-------------|-------|
| `test_wrt.c` | Full engine test suite (linked with `-DWRT_ENGINE_NO_MAIN`) | 19 functions, 54 assertions |
| `test_standalone.c` | Standalone HTML→WRT conversion tests | 16 functions, 31 assertions |
| `wrt-engine` CLI | Integration tests via subprocess | 11 test functions |

**Total: 49 pytest tests, all passing (0.16s)**

### Run Tests
```bash
cd backend
python -m pytest tests/test_native_wrt.py -v
```

### Key Regression Tests Added (Sept 24, 2026)
- `test_from_editable_html_blockquote` — verifies `<blockquote>` not corrupted to `[b]lockquote`
- `test_roundtrip_editable_html` — full WRT → editable HTML → WRT round-trip
- `test_cli_roundtrip_blockquote_regression` — CLI regression test

---

## Build and Installation

### Requirements
- GCC (C11)
- Linux/Unix system
- Make
- Python 3.11+ (for pytest integration)
- libzip, zlib (for C engine)

### Compilation
```bash
cd backend/native/wrt
make
```
Creates `wrt-engine` binary in `backend/native/wrt/`.

### Run CLI
```bash
# Validate
./wrt-engine validate document.wrt

# Fix
./wrt-engine fix document.wrt

# Convert to HTML
./wrt-engine to-html document.wrt

# Convert to contentEditable HTML
./wrt-engine to-editable-html document.wrt

# Convert from contentEditable HTML
./wrt-engine from-editable-html input.html
```

---

## Integration with AladdinAI

### Document Editing Workflow
```
1. User uploads document.docx
   ↓
2. File saved as-is to storage
   ↓
3. Agent reads via files_read → auto-convert .docx → .wrt
   ↓
4. Agent edits .wrt text (or user edits via Visual Mode)
   ↓
5. New version saved as .wrt to storage
   ↓
6. On download: .wrt → auto-convert → .docx
```

### Where WRT Editor Is Used
1. **Backend development** — quick `.wrt` file editing when debugging converters
2. **Testing** — manually creating test documents
3. **Agent debugging** — viewing what the agent sees after conversion
4. **Direct editing** — alternative to editing through UI (C IDE mode)
5. **Web dashboard** — Visual mode for document authors

---

## Fixed Bugs (Code Review Bot — Sept 24, 2026)

### 1. CRITICAL: `<blockquote>` → `[b]lockquote` corruption
**File:** `wrt_from_editable_html()` (lines ~707, 727, 747, 763)
**Fix:** Boundary checks — verify next char is `>` or whitespace/attribute

### 2. WARNING: Empty tag severity 1→0
**File:** `wrt_validate()` (line 141)
**Fix:** `severity = 0` (error) for empty tags, consistent with header

### 3. SUGGESTION: `malloc+snprintf` → `strdup`
**File:** `wrt_to_editable_html()` (lines 606, 616)
**Fix:** `strdup("[code]")` and `strdup("[/code]")` for constants

### 4. REGRESSION: Inline tags after block elements broken
**File:** `wrt_to_html()` (lines 544-554)
**Fix:** Auto-open paragraph when inline tag encountered outside paragraph

### 5. BUILD WARNINGS: Unused variables
**File:** `wrt_from_editable_html()` (lines 794, 810, 893, 910, 918, 928, 936, 945, 953)
**Fix:** Removed declarations, replaced usages with `(void)var` casts

---

## Roadmap

### Near-Term Plans
- [ ] **Ctrl+F** — text search in Visual Mode
- [ ] **Ctrl+H** — find and replace
- [ ] **Undo/Redo** — history stack for contentEditable
- [ ] **Syntax validation** — real-time validation indicator in Visual Mode
- [ ] **Tag autocomplete** — autocomplete `[b` → `[b][/b]` in Code Mode
- [ ] **Mobile support** — responsive editor layout

### Long-Term Plans
- [ ] **Collaborative editing** — real-time multi-user via WebSockets
- [ ] **Vim/Emacs keybindings** — optional keybinding modes in Code Mode
- [ ] **Integration with aladdin_term** — launch C IDE from PTY daemon
- [ ] **JSON-RPC protocol** — AI agent control of editor

---

## Comparison with Previous Implementations

| Editor | Backend | Frontend | `.wrt` Support | Size |
|--------|---------|----------|----------------|------|
| **Current (C + contentEditable)** | Pure C (`wrt-engine`) | React + contentEditable | ✅ Full (single source) | ~1800 LOC C |
| Monaco Editor (PR #790) | Python | Monaco | ✅ Highlighting only | ~2MB JS |
| Terminal `wrt-edit` | C (separate) | ANSI terminal | ✅ Highlighting | ~70KB |

### Advantages of Current Architecture
✅ **Single source of truth** — C engine handles all parsing/serialization  
✅ **Zero JS parsing logic** — TSX only renders and proxies to C API  
✅ **Fast, correct round-trips** — contentEditable HTML ↔ WRT via C  
✅ **Testable** — 49 pytest tests covering C engine + CLI + integration  
✅ **Minimal frontend** — thin client, easy to maintain  

---

## FAQ

### How to open file with spaces in name?
```bash
./wrt-engine validate "my document.wrt"
```

### Can I edit `.docx` directly?
No. Convert `.docx` → `.wrt` first via Python:
```bash
python -c "
from app.services.docx_converter import docx_to_wrt
with open('document.docx', 'rb') as f:
    wrt = docx_to_wrt(f.read())
with open('document.wrt', 'w') as f:
    f.write(wrt)
"
./wrt-engine validate document.wrt
```

### What if file is too large?
C engine has no hard line limit (dynamic allocation). For very large files, CLI or REST API recommended.

### How to insert headings in Visual Mode?
Use toolbar dropdown: H1, H2, H3.

### Are images supported?
Yes: `[img src="data:image/png;base64,..." alt="..."]` — rendered in Visual Mode.

---

## Troubleshooting

### Problem: C engine doesn't compile
**Error:** Missing libzip/zlib
**Solution:**
```bash
sudo apt-get install libzip-dev zlib1g-dev
cd backend/native/wrt && make
```

### Problem: Tests fail with "binary not found"
**Cause:** Engine not built
**Solution:**
```bash
cd backend/native/wrt && make
python -m pytest tests/test_native_wrt.py -v
```

### Problem: Visual Mode not editable after C IDE
**Cause:** Fixed — now requests fresh HTML from C engine on mode switch.

### Problem: localStorage conflicts between files
**Cause:** Fixed — keys now file-specific: `wrt-draft-{source}-{hash}`

---

## Contributing

### How to Add New Tag
1. Add token type in `wrt_engine.c` (`wrt_token_type_t`)
2. Add parsing in `wrt_validate()` / `wrt_to_html()`
3. Add conversion in `wrt_to_editable_html()` / `wrt_from_editable_html()`
4. Add test in `test_wrt.c`
5. Update frontend toolbar in `page.tsx`
6. Update this documentation

### How to Modify HTML↔WRT Conversion
- Edit `wrt_to_editable_html()` for WRT→HTML
- Edit `wrt_from_editable_html()` for HTML→WRT
- **Always add regression test** for blockquote/nested/table edge cases

---

## License
**RCF-PL v2.0.3** — like all AladdinAI code.

---

## Authors
- **C Engine implementation** — Claude (Sonnet 4), September 2026
- **Frontend integration** — Claude (Sonnet 4), September 2026
- **Project** — AladdinAI Team

---

## See Also
- [`PULL_REQUEST_DOCX_WRT.md`](PULL_REQUEST_DOCX_WRT.md) — `.wrt` format and converters
- [`backend/app/services/wrt_engine_service.py`](../backend/app/services/wrt_engine_service.py) — Python REST wrapper
- [`backend/native/wrt/wrt_engine.c`](../backend/native/wrt/wrt_engine.c) — C engine source
- [`backend/tests/test_native_wrt.py`](../backend/tests/test_native_wrt.py) — pytest integration
- [`docs/adr/0014-wrt-visual-editor.md`](adr/0014-wrt-visual-editor.md) — ADR for Visual Mode

---

**Last updated:** September 24, 2026