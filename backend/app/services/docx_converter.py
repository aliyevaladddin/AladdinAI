# NOTICE: This file is protected under RCF-PL v2.0.3
"""WRT format converter — bidirectional .docx ↔ .wrt.

.wrt is a lightweight tagged-text format designed for AI editing of
office documents.  The agent works with .wrt (plain text + semantic
tags), while the user downloads/uploads real .docx files.

Format specification (v1):
    [h1]...[/h1]  [h2]...[/h2]  [h3]...[/h3]  — headings
    [b]...[/b]    — bold
    [i]...[/i]    — italic
    [u]...[/u]    — underline
    [s]...[/s]    — strikethrough
    [code]...[/code] — monospace / code
    [quote]...[/quote] — block quote
    [list]         — unordered list (items start with * )
    [/list]        — end list
    [table]        — table (pipe-delimited rows)
    [/table]       — end table
    [img alt="..."] — image placeholder (binary images can't round-trip)

    Everything outside tags is plain paragraph text.
    Blank lines separate paragraphs.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any

log = logging.getLogger(__name__)


# ── .docx → .wrt ────────────────────────────────────────────────────────────

def _para_tag(para: Any) -> str | None:
    """Map a python-docx paragraph style to a .wrt tag."""
    style = (para.style.name or "").lower()
    if "heading 1" in style or style == "title":
        return "h1"
    if "heading 2" in style:
        return "h2"
    if "heading 3" in style or "heading" in style:
        return "h3"
    if "quote" in style or "block" in style:
        return "quote"
    if "list" in style:
        return None  # handled via list items
    return None


def _run_markup(run: Any) -> str:
    """Wrap a single run's text with .wrt inline tags."""
    text = run.text or ""
    if not text:
        return ""
    if run.bold:
        text = f"[b]{text}[/b]"
    if run.italic:
        text = f"[i]{text}[/i]"
    if run.underline:
        text = f"[u]{text}[/u]"
    if run.font.strike:
        text = f"[s]{text}[/s]"
    # Monospace / code font
    font_name = (run.font.name or "").lower()
    if "mono" in font_name or "courier" in font_name or "code" in font_name:
        if not run.bold and not run.italic:
            text = f"[code]{text}[/code]"
    return text


def docx_to_wrt(docx_bytes: bytes) -> str:
    """Convert a .docx file (bytes) to .wrt text format."""
    from docx import Document

    doc = Document(io.BytesIO(docx_bytes))
    lines: list[str] = []

    for para in doc.paragraphs:
        # Check if this is a list item
        pstyle = (para.style.name or "").lower()
        is_list = "list" in pstyle

        if is_list:
            # Build inline markup from runs
            inner = "".join(_run_markup(r) for r in para.runs)
            lines.append(f"* {inner.strip()}")
            continue

        # Regular paragraph or heading
        tag = _para_tag(para)
        inner = "".join(_run_markup(r) for r in para.runs)

        if not inner.strip():
            lines.append("")
            continue

        if tag:
            lines.append(f"[{tag}]{inner.strip()}[/{tag}]")
        else:
            lines.append(inner.strip())

    # Extract tables
    for table in doc.tables:
        lines.append("[table]")
        for row in table.rows:
            cells = [cell.text.strip().replace("|", "\\|") for cell in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("[/table]")

    # Clean up multiple blank lines
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# ── .wrt → .docx ────────────────────────────────────────────────────────────

_TAG_RE = re.compile(
    r"\[(b|i|u|s|h1|h2|h3|code|quote)\](.*?)\[/\1\]",
    re.DOTALL,
)


def _apply_inline_tags(doc: Any, paragraph: Any, text: str) -> None:
    """Parse inline .wrt tags and add runs to a paragraph."""
    pos = 0
    for m in _TAG_RE.finditer(text):
        # Plain text before the tag
        if m.start() > pos:
            paragraph.add_run(text[pos : m.start()])

        tag = m.group(1)
        inner = m.group(2)
        run = paragraph.add_run(inner)

        if tag == "b":
            run.bold = True
        elif tag == "i":
            run.italic = True
        elif tag == "u":
            run.underline = True
        elif tag == "s":
            run.font.strike = True
        elif tag == "code":
            run.font.name = "Courier New"
            run.font.size = __import__("docx.shared").Pt(9)
        elif tag in ("h1", "h2", "h3"):
            run.bold = True

        pos = m.end()

    # Remaining plain text
    if pos < len(text):
        paragraph.add_run(text[pos:])


def wrt_to_docx(wrt_text: str) -> bytes:
    """Convert .wrt text format to a .docx file (bytes)."""
    from docx import Document

    doc = Document()
    lines = wrt_text.split("\n")

    i = 0
    in_table = False
    in_list = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Table
        if stripped == "[table]":
            in_table = True
            i += 1
            continue
        if stripped == "[/table]":
            in_table = False
            i += 1
            continue
        if in_table and stripped.startswith("|"):
            # Parse table row — first row = header
            cells = [c.strip().replace("\\|", "|") for c in stripped.split("|")[1:-1]]
            if not doc.tables:
                doc.add_table(rows=1, cols=max(len(cells), 1))
            table = doc.tables[-1]
            if len(table.rows) == 1 and all(c == "" for c in cells):
                i += 1
                continue
            row = table.add_row()
            for j, cell_text in enumerate(cells):
                row.cells[j].text = cell_text
            i += 1
            continue

        # List
        if stripped == "[list]":
            in_list = True
            i += 1
            continue
        if stripped == "[/list]":
            in_list = False
            i += 1
            continue
        if in_list and stripped.startswith("* "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
            i += 1
            continue

        # Headings
        heading_match = re.match(r"\[(h[1-3])\](.*?)\[/\1\]", stripped)
        if heading_match:
            tag = heading_match.group(1)
            inner = heading_match.group(2)
            level = int(tag[1])
            doc.add_heading(inner, level=level)
            i += 1
            continue

        # Block quote
        if stripped.startswith("[quote]") and stripped.endswith("[/quote]"):
            inner = stripped[7:-8]
            doc.add_paragraph(inner, style="Quote")
            i += 1
            continue

        # Empty line = paragraph break
        if not stripped:
            i += 1
            continue

        # Regular paragraph with inline tags
        para = doc.add_paragraph()
        _apply_inline_tags(doc, para, stripped)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
