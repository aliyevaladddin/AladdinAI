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


if __name__ == "__main__":
    unittest.main()
