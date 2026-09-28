"""Regression tests for DOCX-to-WRT inline image ordering."""

import io

from docx import Document
from docx.shared import Inches
from PIL import Image

from app.services.wrt_engine_service import docx_to_wrt


def _png_bytes() -> bytes:
    image = Image.new("RGB", (20, 20), "blue")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_inline_image_stays_between_surrounding_text_runs():
    doc = Document()
    paragraph = doc.add_paragraph()

    paragraph.add_run("before ")
    paragraph.add_run().add_picture(io.BytesIO(_png_bytes()), width=Inches(0.25))
    paragraph.add_run(" after")

    buf = io.BytesIO()
    doc.save(buf)

    wrt = docx_to_wrt(buf.getvalue())

    before = wrt.index("before")
    image = wrt.index("[img ")
    after = wrt.index("after")

    assert before < image < after


def test_inline_image_is_not_hoisted_before_paragraph_text():
    doc = Document()
    paragraph = doc.add_paragraph()

    paragraph.add_run("prefix ")
    paragraph.add_run().add_picture(io.BytesIO(_png_bytes()), width=Inches(0.25))
    paragraph.add_run(" suffix")

    buf = io.BytesIO()
    doc.save(buf)

    wrt = docx_to_wrt(buf.getvalue())

    assert not wrt.lstrip().startswith("[img ")
    assert wrt.index("prefix") < wrt.index("[img ")
    assert wrt.index("[img ") < wrt.index("suffix")
