"""Image size and caption fidelity for DOCX <-> WRT conversion.

A picture in Word carries two things the `.wrt` tag has to remember: its display
size (`wp:extent`, in EMU) and its caption (`wp:docPr/@descr`). Losing either
means the export back to .docx resizes the picture to a default box and drops the
alt text, so both are asserted here in both directions.
"""

import base64
import io
import re
import subprocess
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches
from PIL import Image

from app.services.wrt_engine_service import docx_to_wrt_sync, wrt_to_docx_sync

WRT_ENGINE_BINARY = Path(__file__).resolve().parent.parent / "native" / "wrt" / "wrt-engine"

# Word stores lengths in EMU: 914400 per inch, i.e. 9525 per CSS pixel.
EMU_PER_PX = 9525


def _image_bytes(fmt: str = "PNG", size=(40, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, format=fmt)
    return buf.getvalue()


def _docx_with_picture(width_in=0.5, descr=None) -> bytes:
    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run("before ")
    run = paragraph.add_run()
    run.add_picture(io.BytesIO(_image_bytes()), width=Inches(width_in))
    if descr is not None:
        run._element.find(".//" + qn("wp:docPr")).set("descr", descr)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _img_tag(wrt: str) -> str:
    start = wrt.index("[img ")
    end = wrt.index("]", start)
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,<b64>", wrt[start:end + 1])


def _run_engine(command: str, stdin: str) -> str:
    result = subprocess.run(
        [str(WRT_ENGINE_BINARY), command, "-"],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _read_docx(docx_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        xml = z.read("word/document.xml").decode("utf-8")
    return media, xml


def test_docx_picture_size_and_caption_are_kept_in_wrt():
    wrt = docx_to_wrt_sync(_docx_with_picture(width_in=0.5, descr="Диаграмма"))

    tag = _img_tag(wrt)
    # 0.5in = 48px; the 2:1 source keeps its aspect ratio -> 24px
    assert 'w="48"' in tag
    assert 'h="24"' in tag
    assert 'alt="Диаграмма"' in tag


def test_docx_caption_quotes_cannot_break_the_tag():
    wrt = docx_to_wrt_sync(_docx_with_picture(descr='quote "here" & more'))

    tag = _img_tag(wrt)
    # The tag is quote-delimited and single-line, so quotes are normalised and
    # the whole tag stays on one line.
    assert '"quote \'here\' & more"' in tag
    assert "\n" not in tag


def test_docx_picture_size_round_trips():
    wrt = docx_to_wrt_sync(_docx_with_picture(width_in=0.5))
    media, xml = _read_docx(wrt_to_docx_sync(wrt))

    assert media, "image bytes missing from the docx package"
    extent = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', xml)
    assert extent, xml[:500]
    assert int(extent.group(1)) == 48 * EMU_PER_PX
    assert int(extent.group(2)) == 24 * EMU_PER_PX


def test_wrt_size_becomes_docx_extent():
    b64 = base64.b64encode(_image_bytes("JPEG")).decode()
    wrt = f'[img src="data:image/jpeg;base64,{b64}" alt="photo" w="120" h="60"]'

    media, xml = _read_docx(wrt_to_docx_sync(wrt))

    # JPEG bytes must not be filed under a .png name
    assert media == ["word/media/image1.jpg"]
    assert '<wp:extent cx="{}" cy="{}"/>'.format(120 * EMU_PER_PX, 60 * EMU_PER_PX) in xml
    # DrawingML transform has to agree with the inline extent
    assert '<a:ext cx="{}" cy="{}"/>'.format(120 * EMU_PER_PX, 60 * EMU_PER_PX) in xml


def test_wrt_without_size_keeps_the_historical_default():
    b64 = base64.b64encode(_image_bytes()).decode()
    wrt = f'[img src="data:image/png;base64,{b64}" alt="image"]'

    _, xml = _read_docx(wrt_to_docx_sync(wrt))

    assert '<wp:extent cx="5486400" cy="3657600"/>' in xml


def test_html_export_maps_w_h_to_width_height():
    html = _run_engine("to-html", '[img src="data:image/png;base64,AAAA" alt="x" w="48" h="24"]')

    assert 'width="48"' in html
    assert 'height="24"' in html
    # Raw w/h would be attributes browsers ignore
    assert ' w="48"' not in html


def test_editor_round_trip_keeps_the_size():
    """HTML -> WRT -> HTML, as the visual editor does on every save."""
    html_in = (
        '<p><img src="data:image/png;base64,AAAA" alt="x" width="100" height="50"'
        ' class="wrt-image max-w-full" /></p>'
    )

    wrt = _run_engine("from-editable-html", html_in)
    assert 'w="100"' in wrt
    assert 'h="50"' in wrt

    html_out = _run_engine("to-editable-html", wrt)
    assert 'width="100"' in html_out
    assert 'height="50"' in html_out
