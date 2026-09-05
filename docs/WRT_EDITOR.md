# WRT Editor — Lightweight Document Editing Mode

**Location:** `backend/native/wrt_editor.c` + `backend/native/wrt-edit.c`  
**Status:** ✅ Implemented (Sept 2026)  
**Purpose:** Native C-based terminal editor for `.wrt` files (AladdinAI's tagged-text format)

---

## Overview

WRT Editor is a lightweight terminal-based editor for `.wrt` documents, written in pure C. It allows editing documents directly in the terminal without the need to convert them to `.docx` and back.

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

## Visual Editor Mode (Frontend)

**Status:** ✅ Implemented (Sept 2026)  
**Location:** `/frontend/src/app/(dashboard)/dashboard/wrt-editor/`  

For normal document authors who do not want to manage raw WRT tags (`[b]`, `[i]`), a **Visual mode** is available in the web dashboard.

### Key Features
- **WYSIWYG Editing:** Edit formatted text directly without seeing WRT markup.
- **Seamless Sync:** Bi-directional conversion (`ContentEditable` HTML ↔ `.wrt`) preserves semantic structure.
- **Integrated Layout:** Centered document canvas with collapsible side drawer (Versions, Timeline).
- **Mode Switching:** Easily toggle between **Visual** and **WRT Code** modes.

### Usage
1. Open any `.wrt` or `.docx` file in the Dashboard.
2. The document appears in **Visual** mode by default.
3. Use the toolbar buttons to format text (Bold, Italic, etc.).
4. Use the toggle to switch to **WRT Code** mode if you need direct tag control for agents.

---

### ✨ Core Functionality

- **Line-based editing** — simple and fast interface
- **Tag highlighting** — `.wrt` tags displayed in color for better visibility
- **Navigation** — arrow keys, Home/End, Page Up/Down
- **Insert/delete** — full text editing support
- **Auto-save status** — modified indicator `[+]` for unsaved changes

### ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+B** | Insert `[b]bold[/b]` |
| **Ctrl+I** | Insert `[i]italic[/i]` |
| **Ctrl+U** | Insert `[u]underline[/u]` |
| **Ctrl+K** | Insert `[code]code[/code]` |
| **Ctrl+S** | Save file |
| **Ctrl+Q** | Quit (with confirmation if modified) |
| **Arrow keys** | Navigate text |
| **Home** | Go to line start |
| **End** | Go to line end |
| **Backspace** | Delete character to the left |
| **Enter** | New line |

### 🎨 Interface

```
[h1]My Document[/h1]                    ← tags highlighted in color
This is regular text with [b]bold[/b].
~                                       ← empty lines marked with ~
~
─────────────────────────────────────────────────────────────────────
 document.wrt [+] | Line 2/15 Col 24 | ^S:Save ^Q:Quit ^B:Bold...
 WRT Editor - Lightweight document editing
```

---

## Build and Installation

### Requirements

- GCC (C11)
- Linux/Unix system with termios
- Make

### Compilation

```bash
cd backend/native
make wrt-edit
```

This creates the `wrt-edit` executable in `backend/native/`.

### Installation (optional)

```bash
# Copy to system path
sudo cp wrt-edit /usr/local/bin/
```

---

## Usage

### Basic Usage

```bash
# Open existing file
./wrt-edit document.wrt

# Create new file
./wrt-edit new_document.wrt
```

### Typical Workflow

1. **Open file:**
   ```bash
   ./wrt-edit my_document.wrt
   ```

2. **Edit text:**
   - Use arrow keys for navigation
   - Type text as usual
   - Insert tags with Ctrl+B, Ctrl+I, etc.

3. **Save:**
   - Press `Ctrl+S` to save
   - `[+]` status disappears after successful save

4. **Exit:**
   - Press `Ctrl+Q`
   - If there are unsaved changes, the editor will ask for confirmation

---

## Architecture

### File Structure

```
backend/native/
├── wrt_editor.h       — header file, structures and prototypes
├── wrt_editor.c       — core editor logic
├── wrt-edit.c         — CLI wrapper (main entry point)
├── Makefile           — build script
└── wrt-edit           — compiled binary
```

### Key Components

#### `wrt_editor_t` — Editor State

```c
typedef struct {
    char **lines;         // Array of document lines
    int num_lines;        // Number of lines
    int capacity;         // Array capacity
    int cursor_x;         // Cursor position X (column)
    int cursor_y;         // Cursor position Y (row)
    int offset_y;         // Viewport offset (scrolling)
    int screen_rows;      // Screen height
    int screen_cols;      // Screen width
    char *filename;       // File name
    int modified;         // Unsaved changes flag
} wrt_editor_t;
```

#### Main Functions

- `wrt_editor_run()` — main editor loop
- `wrt_editor_load()` — load file into memory
- `wrt_editor_save()` — save to file
- `wrt_editor_render()` — render screen
- `wrt_editor_insert_char()` — insert character
- `wrt_editor_delete_char()` — delete character
- `wrt_editor_insert_tag()` — quick tag insertion
- `wrt_editor_move_cursor()` — cursor navigation
- `wrt_editor_process_key()` — key processing

### Implementation Details

#### Raw Terminal Mode

The editor uses raw mode for character-by-character input:

```c
static void enable_raw_mode(void) {
    struct termios raw = orig_termios;
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    // ... other flags
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}
```

#### ANSI Escape Sequences

ANSI codes are used for terminal control:

```c
#define CLEAR_SCREEN "\033[2J"
#define CURSOR_HOME "\033[H"
#define COLOR_CYAN "\033[36m"
```

#### Tag Highlighting

`.wrt` tags are automatically highlighted during rendering:

```c
if (line[i] == '[' && (i == 0 || line[i-1] != '\\')) {
    // Find closing ]
    // Highlight tag in cyan
    len += snprintf(buf + len, sizeof(buf) - len, COLOR_CYAN);
    // ... insert tag
    len += snprintf(buf + len, sizeof(buf) - len, COLOR_RESET);
}
```

---

## Limitations

### Current Limitations

- **Maximum 10,000 lines** (`WRT_MAX_LINES`)
- **Maximum 4,096 characters per line** (`WRT_MAX_LINE_LENGTH`)
- **No Undo/Redo** — manual editing only
- **No search/replace** — planned for future
- **UTF-8 only** — no support for other encodings
- **Linux/Unix only** — Windows requires separate implementation

### Not Supported

- ❌ Tag syntax validation (can create `[b]` without `[/b]`)
- ❌ Rendering preview (raw tags only)
- ❌ Tag autocompletion
- ❌ Mouse support (keyboard only)
- ❌ Copy/paste via system clipboard

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
4. Agent edits .wrt text
   ↓
5. New version saved as .wrt to storage
   ↓
6. On download: .wrt → auto-convert → .docx
```

### Where WRT Editor Is Used

1. **Backend development** — quick `.wrt` file editing when debugging converters
2. **Testing** — manually creating test documents
3. **Agent debugging** — viewing what the agent sees after conversion
4. **Direct editing** — alternative to editing through UI

### Example: Debugging Converter

```bash
# 1. Convert docx to wrt
python -c "
from app.services.docx_converter import docx_to_wrt
with open('test.docx', 'rb') as f:
    wrt = docx_to_wrt(f.read())
with open('test.wrt', 'w') as f:
    f.write(wrt)
"

# 2. Edit manually
./wrt-edit test.wrt

# 3. Convert back
python -c "
from app.services.docx_converter import wrt_to_docx
with open('test.wrt') as f:
    wrt = f.read()
with open('test_out.docx', 'wb') as f:
    f.write(wrt_to_docx(wrt))
"

# 4. Check result
libreoffice test_out.docx
```

---

## Roadmap

### Near-Term Plans

- [ ] **Ctrl+F** — text search
- [ ] **Ctrl+H** — find and replace
- [ ] **Ctrl+Z/Ctrl+Y** — Undo/Redo
- [ ] **Syntax validation** — highlight unclosed tags
- [ ] **Tag autocomplete** — autocomplete `[b` → `[b][/b]`
- [ ] **Mouse support** — mouse navigation
- [ ] **Line numbers** — optional line numbering

### Long-Term Plans

- [ ] **Syntax highlighting** — full syntax highlighting
- [ ] **Live preview** — rendering preview in adjacent panel
- [ ] **Vim bindings** — Vim mode for power users
- [ ] **Windows support** — port to Windows via PDCurses
- [ ] **Integration with aladdin_term** — launch from PTY daemon

---

## Comparison with Alternatives

| Editor | Size | Dependencies | `.wrt` tags | Speed |
|--------|------|--------------|-------------|-------|
| **wrt-edit** | ~70KB | 0 | ✅ Highlighting | ⚡ Instant |
| nano | ~600KB | ncurses | ❌ No | 🐢 Fast |
| vim | ~3MB | ncurses | ❌ No | 🐢 Fast |
| VSCode | ~500MB | Electron | ✅ Can configure | 🐌 Slow |

### Advantages of wrt-edit

✅ **Minimal size** — 70KB vs 600KB+ for other editors  
✅ **Zero dependencies** — only libc, no ncurses  
✅ **Built-in `.wrt` support** — tags highlighted out of the box  
✅ **Fast startup** — instant even on large files  
✅ **Simplicity** — only essential features, no plugins  

### When to Use nano/vim Instead of wrt-edit

- Files > 10,000 lines
- Need complex operations (macros, regex replacements)
- Need code syntax highlighting (not `.wrt` tags)
- Require mouse support

---

## FAQ

### How to open file with spaces in name?

```bash
./wrt-edit "my document.wrt"
```

### Can I edit `.docx` directly?

No. First convert `.docx` → `.wrt` via `docx_converter.py`:

```bash
python -c "
from app.services.docx_converter import docx_to_wrt
with open('document.docx', 'rb') as f:
    wrt = docx_to_wrt(f.read())
with open('document.wrt', 'w') as f:
    f.write(wrt)
"
./wrt-edit document.wrt
```

### What if file is too large?

Editor supports up to 10,000 lines. For larger files use vim/emacs or split into parts.

### How to insert h1/h2/h3 headings?

Type manually:
```
[h1]Title[/h1]
```

Or use keyboard shortcuts (if added in future version).

### Are images supported?

Editor displays `[img ...]` tags as-is (text). Editing base64 data inside tags is supported but not recommended (lines too long).

### How to exit without saving?

`Ctrl+Q` → `n` (no) when asked for confirmation.

---

## Troubleshooting

### Problem: Editor doesn't compile

**Error:**
```
wrt_editor.c:387:28: error: 'errno' undeclared
```

**Solution:**
Ensure `#include <errno.h>` is present in `wrt_editor.c`.

---

### Problem: Tags not highlighted

**Cause:** Terminal doesn't support ANSI colors.

**Solution:**
```bash
export TERM=xterm-256color
./wrt-edit document.wrt
```

---

### Problem: Cursor "jumps" during editing

**Cause:** Unicode characters counted as multiple bytes.

**Solution:** WRT Editor is designed for ASCII + basic Unicode. For complex Unicode use GUI editor.

---

### Problem: Can't insert Tab

**Cause:** `Ctrl+I` is captured for `[i]` tag insertion.

**Solution:** Type spaces instead of Tab (`.wrt` format recommends spaces).

---

## Contributing

### How to Add New Keyboard Shortcut

1. Find free Ctrl code (see `wrt_editor_process_key()`)
2. Add case in switch:
```c
case 7: // Ctrl+G — new function
    wrt_editor_insert_tag(ed, "[quote]");
    break;
```
3. Update documentation in `wrt-edit.c` and `WRT_EDITOR.md`

### How to Add New Tag

1. Update supported tags list in `docx_converter.py`
2. Add highlighting in `wrt_editor_render()` (if needed)
3. Update documentation

---

## License

**RCF-PL v2.0.3** — like all AladdinAI code.

---

## Authors

- **Initial implementation** — Claude (Sonnet 4), September 2026
- **Project** — AladdinAI Team

---

## See Also

- [`PULL_REQUEST_DOCX_WRT.md`](PULL_REQUEST_DOCX_WRT.md) — documentation on `.wrt` format and converters
- [`backend/app/services/docx_converter.py`](../backend/app/services/docx_converter.py) — Python converters `.docx` ↔ `.wrt`
- [`backend/native/aladdin_term.c`](../backend/native/aladdin_term.c) — PTY daemon (future integration)

---

**Last updated:** September 5, 2026
