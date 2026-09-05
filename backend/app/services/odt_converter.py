# NOTICE: This file is protected under RCF-PL v2.0.3
"""ODT format converter — bidirectional .odt ↔ .wrt.

Converts OpenDocument Text files to/from .wrt format for AI editing.
Uses the odfpy library to parse and generate ODF documents.

Format mapping:
    .wrt tags ↔ ODF styles
    [h1] ↔ heading level 1
    [b] ↔ bold text
    [table] ↔ ODF table
"""
from __future__ import annotations

import io
import logging
import re

log = logging.getLogger(__name__)


def odt_to_wrt(odt_bytes: bytes) -> str:
    """Convert a .odt file (bytes) to .wrt text format."""
    from odf.opendocument import load
    from odf.text import ListItem
    from odf.table import TableRow, TableCell
    from odf import teletype

    doc = load(io.BytesIO(odt_bytes))
    lines: list[str] = []

    # Extract all elements from document body
    for element in doc.body.childNodes:
        # Heading
        if element.qname == (u'urn:oasis:names:tc:opendocument:xmlns:text:1.0', 'h'):
            level = int(element.getAttribute('outlinelevel') or '1')
            text = teletype.extractText(element).strip()
            if text:
                tag = f"h{min(level, 3)}"  # h1, h2, or h3
                lines.append(f"[{tag}]{text}[/{tag}]")

        # Paragraph
        elif element.qname == (u'urn:oasis:names:tc:opendocument:xmlns:text:1.0', 'p'):
            text = teletype.extractText(element).strip()
            if text:
                # Check for inline formatting (bold, italic, etc.)
                # For simplicity, extract plain text for now
                lines.append(text)

        # List
        elif element.qname == (u'urn:oasis:names:tc:opendocument:xmlns:text:1.0', 'list'):
            lines.append("[list]")
            for item in element.getElementsByType(ListItem):
                text = teletype.extractText(item).strip()
                if text:
                    lines.append(f"* {text}")
            lines.append("[/list]")

        # Table
        elif element.qname == (u'urn:oasis:names:tc:opendocument:xmlns:table:1.0', 'table'):
            lines.append("[table]")
            for row in element.getElementsByType(TableRow):
                cells = row.getElementsByType(TableCell)
                cell_texts = [teletype.extractText(cell).strip() for cell in cells]
                lines.append("| " + " | ".join(cell_texts) + " |")
            lines.append("[/table]")

        lines.append("")  # Blank line between elements

    # Cleanup multiple blank lines
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def wrt_to_odt(wrt_text: str) -> bytes:
    """Convert .wrt text format to a .odt file (bytes)."""
    from odf.opendocument import OpenDocumentText
    from odf.text import P, H, List, ListItem
    from odf.table import Table, TableRow, TableCell
    from odf.style import Style, TextProperties
    from odf import teletype

    doc = OpenDocumentText()

    # Define styles
    bold_style = Style(name="Bold", family="text")
    bold_style.addElement(TextProperties(fontweight="bold"))
    doc.automaticstyles.addElement(bold_style)

    # Parse WRT content
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
            table = Table()
            doc.text.addElement(table)
            i += 1
            continue
        if stripped == "[/table]":
            in_table = False
            i += 1
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            row = TableRow()
            table.addElement(row)
            for cell_text in cells:
                cell = TableCell()
                cell.addElement(P(text=cell_text))
                row.addElement(cell)
            i += 1
            continue

        # List
        if stripped == "[list]":
            in_list = True
            list_elem = List()
            doc.text.addElement(list_elem)
            i += 1
            continue
        if stripped == "[/list]":
            in_list = False
            i += 1
            continue
        if in_list and stripped.startswith("* "):
            item = ListItem()
            item.addElement(P(text=stripped[2:]))
            list_elem.addElement(item)
            i += 1
            continue

        # Headings
        heading_match = re.match(r"\[(h[1-3])\](.*?)\[/\1\]", stripped)
        if heading_match:
            tag = heading_match.group(1)
            inner = heading_match.group(2)
            level = int(tag[1])
            h = H(outlinelevel=level, text=inner)
            doc.text.addElement(h)
            i += 1
            continue

        # Block quote
        if stripped.startswith("[quote]") and stripped.endswith("[/quote]"):
            inner = stripped[7:-8]
            p = P(text=inner)
            doc.text.addElement(p)
            i += 1
            continue

        # Empty line
        if not stripped:
            i += 1
            continue

        # Regular paragraph with inline tags
        # For simplicity, handle bold tags
        if "[b]" in stripped and "[/b]" in stripped:
            p = P()
            # Split by bold tags and add runs
            parts = re.split(r'\[b\](.*?)\[/b\]', stripped)
            for j, part in enumerate(parts):
                if j % 2 == 0:
                    # Regular text
                    if part:
                        p.addText(part)
                else:
                    # Bold text
                    p.addElement(teletype.P(text=part, stylename=bold_style))
            doc.text.addElement(p)
        else:
            # Plain paragraph
            doc.text.addElement(P(text=stripped))

        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
