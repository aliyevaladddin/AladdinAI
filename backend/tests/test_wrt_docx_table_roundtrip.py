# NOTICE: This file is protected under RCF-PL
"""Black-box DOCX <-> WRT regressions for the native table parser.

Requires python-docx and the compiled native backend/native/wrt/wrt-engine.
Run with: python -m unittest discover -s backend/tests -p test_wrt_docx_table_roundtrip.py -v
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "backend" / "native" / "wrt" / "wrt-engine"


def cell_matrix(doc):
    return [[[cell.text for cell in row.cells] for row in table.rows] for table in doc.tables]


class TestWRTDocxTableRoundtrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENGINE.is_file():
            raise RuntimeError(f"Build the native engine first: make -C backend/native/wrt wrt-engine ({ENGINE})")

    def roundtrip(self, original):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            input_doc = tmp / "input.docx"
            intermediate = tmp / "intermediate.wrt"
            output_doc = tmp / "output.docx"
            original.save(input_doc)
            for args in (("docx-to-wrt", input_doc, intermediate),
                         ("wrt-to-docx", intermediate, output_doc)):
                proc = subprocess.run([str(ENGINE), str(args[0]), str(args[1]), str(args[2])],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, f"{' '.join(map(str,args))}: {proc.stderr}")
            wrt = intermediate.read_text(encoding="utf-8")
            restored = Document(output_doc)
            return wrt, restored

    def test_plain_two_by_two_table(self):
        doc = Document()
        table = doc.add_table(rows=2, cols=2)
        for row, values in zip(table.rows, (("Header A", "Header B"), ("Value 1", "Value 2"))):
            for cell, value in zip(row.cells, values):
                cell.text = value
        expected = cell_matrix(doc)
        wrt, restored = self.roundtrip(doc)
        self.assertIn("[table]", wrt)
        self.assertNotIn("<w:", wrt, "Raw OOXML leaked into agent-visible text")
        for value in ("Header A", "Header B", "Value 1", "Value 2"):
            self.assertEqual(wrt.count(value), 1, f"Duplicated or lost cell text: {value}")
        self.assertEqual(cell_matrix(restored), expected)

    def test_table_between_paragraphs(self):
        doc = Document()
        doc.add_paragraph("Paragraph before the table")
        table = doc.add_table(rows=2, cols=2)
        for row, values in zip(table.rows, (("Name", "Score"), ("Example", "42"))):
            for cell, value in zip(row.cells, values):
                cell.text = value
        doc.add_paragraph("Paragraph after the table")
        expected = cell_matrix(doc)
        wrt, restored = self.roundtrip(doc)
        self.assertLess(wrt.index("Paragraph before the table"), wrt.index("[table]"))
        self.assertLess(wrt.index("[/table]"), wrt.index("Paragraph after the table"))
        self.assertEqual(cell_matrix(restored), expected)
        texts = [p.text for p in restored.paragraphs if p.text.strip()]
        self.assertEqual(texts, ["Paragraph before the table", "Paragraph after the table"])

    def test_text_with_xml_space_attribute_and_multiple_runs(self):
        doc = Document()
        cell = doc.add_table(rows=1, cols=2).cell(0, 0)
        cell.text = "Leading "
        cell.paragraphs[0].add_run("and trailing")
        doc.tables[0].cell(0, 1).text = "Second cell"
        expected = cell_matrix(doc)
        wrt, restored = self.roundtrip(doc)
        self.assertIn("Leading and trailing", wrt)
        self.assertNotIn("<w:", wrt)
        self.assertEqual(cell_matrix(restored), expected)

    def test_paragraph_with_xml_like_tag_names_in_text(self):
        """Verify that text containing XML-like tag-name patterns is extracted correctly.

        Previously, strstr for <w:t could match <w:tbl>, <w:tab>, etc.
        This test ensures text containing words like 'w:tbl', 'w:pStyle' etc.
        (without the angle brackets) is extracted correctly.
        """
        doc = Document()
        doc.add_paragraph("The token w:tbl is not a tag here")
        doc.add_paragraph("w:tblPr and w:tcPr are style names")
        doc.add_paragraph("Normal text with w:t and w:r in words")
        wrt, restored = self.roundtrip(doc)
        # Verify the actual text content is present (using word tokens, not tags)
        for text in (
            "The token w:tbl is not a tag here",
            "w:tblPr and w:tcPr are style names",
            "Normal text with w:t and w:r in words",
        ):
            self.assertIn(text, wrt)
        # Verify restored docx has the same text
        texts = [p.text for p in restored.paragraphs if p.text.strip()]
        self.assertEqual(texts, [
            "The token w:tbl is not a tag here",
            "w:tblPr and w:tcPr are style names",
            "Normal text with w:t and w:r in words",
        ])

    def test_paragraph_with_bold_italic_styling(self):
        """Verify that bold/italic formatting is preserved through round-trip."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run("Bold text")
        run.bold = True
        run = p.add_run(" and italic text")
        run.italic = True
        run = p.add_run(" and normal text")
        wrt, restored = self.roundtrip(doc)
        self.assertIn("[b]Bold text[/b]", wrt)
        self.assertIn("[i] and italic text[/i]", wrt)
        self.assertIn("and normal text", wrt)
        self.assertNotIn("<w:", wrt)
        # Verify restored paragraph
        restored_texts = [p.text for p in restored.paragraphs if p.text.strip()]
        self.assertEqual(restored_texts, ["Bold text and italic text and normal text"])

    def test_paragraph_with_underline_formatting(self):
        """Verify that underline formatting is preserved through round-trip.

        Uses python-docx's low-level API to set underline.
        """
        from docx.oxml.ns import qn
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run("underlined text")
        rPr = run._r.get_or_add_rPr()
        u = rPr.makeelement(qn("w:u"), {qn("w:val"): "single"})
        rPr.append(u)
        run = p.add_run(" normal text")
        wrt, restored = self.roundtrip(doc)
        self.assertIn("[u]underlined text[/u]", wrt)
        self.assertIn("normal text", wrt)
        self.assertNotIn("<w:", wrt)

    def test_heading_with_tag_name_tokens_in_text(self):
        """Verify that heading text containing tag-name tokens is handled correctly.

        The text contains 'w:t' and 'w:tbl' as words — ensure they're treated
        as plain text, not matched against XML tags.
        """
        doc = Document()
        doc.add_heading("Heading with w:t in text", level=1)
        doc.add_paragraph("Paragraph with w:tbl reference")
        wrt, restored = self.roundtrip(doc)
        # Verify the actual text content is present
        self.assertIn("Heading with w:t in text", wrt)
        self.assertIn("Paragraph with w:tbl reference", wrt)
        # Should be tagged as heading
        self.assertIn("[h1]", wrt)
        # Verify restored
        restored_headings = [p.text for p in restored.paragraphs if p.text.strip()]
        self.assertEqual(restored_headings, [
            "Heading with w:t in text",
            "Paragraph with w:tbl reference",
        ])


if __name__ == "__main__":
    unittest.main()
