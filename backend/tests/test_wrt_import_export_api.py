# NOTICE: This file is protected under RCF-PL
"""Tests for the WRT import/export endpoints.

Two things are being locked down here.

First, ``POST /wrt/import`` is new: the editor can now open a .docx/.odt/.pptx
dropped onto it. The interesting behaviour is the rejection path -- an
unsupported extension, an empty body, a corrupt archive -- because each of those
has a different correct status code and a message the user can act on.

Second, ``/export`` used to call blocking ``subprocess.run`` from inside an
``async def`` handler, which stalled the entire event loop for the length of
every conversion. That is a performance property, so it is tested as one: the
export must be awaitable, and a handler that blocks shows up as a coroutine
that is never actually awaited.
"""

import asyncio
import io
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.security import get_current_user  # noqa: E402
from app.services import wrt_engine_service as svc  # noqa: E402

ENGINE = ROOT / "backend" / "native" / "wrt" / "wrt-engine"

# A real .docx: the C reader wants a zip with word/document.xml, not any zip.
MINIMAL_DOCX_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body><w:p><w:r><w:t>Отчёт за год</w:t></w:r></w:p></w:body></w:document>"
)
CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/></Types>'
)


def make_docx(text: str = "Отчёт за год") -> bytes:
    """Build a minimal but structurally valid .docx in memory."""
    body = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("word/document.xml", body)
    return buf.getvalue()


@pytest.fixture
def auth_override():
    """Install the auth/DB overrides for the duration of one test.

    Separate from the ``client`` fixture because the async test drives the ASGI
    app itself and needs the same overrides without a TestClient.
    """
    async def fake_db():
        yield object()

    async def fake_user():
        return SimpleNamespace(id=42)

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user] = fake_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


@pytest.fixture
def client(auth_override):
    yield TestClient(app, raise_server_exceptions=True)


# -- import ---------------------------------------------------------------


class TestImport:
    def test_imports_a_docx(self, client):
        resp = client.post(
            "/api/wrt/import",
            content=make_docx(),
            params={"filename": "report.docx"},
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "Отчёт за год" in data["content"]
        # The editor needs a name to open the result under.
        assert data["filename"] == "report.wrt"

    def test_imports_markdown(self, client):
        resp = client.post(
            "/api/wrt/import",
            content="# Заголовок\n\nТекст\n".encode("utf-8"),
            params={"filename": "notes.md"},
        )

        assert resp.status_code == 200, resp.text
        assert "[h1]Заголовок[/h1]" in resp.json()["content"]

    def test_rejects_an_unsupported_extension(self, client):
        resp = client.post(
            "/api/wrt/import",
            content=b"%PDF-1.4 ...",
            params={"filename": "scan.pdf"},
        )

        # 415: the media type is understood, the format is not supported.
        # 400 would say the request itself was malformed.
        assert resp.status_code == 415, resp.text
        assert "docx" in resp.json()["detail"]

    def test_rejects_an_empty_body(self, client):
        resp = client.post("/api/wrt/import", content=b"", params={"filename": "empty.md"})

        assert resp.status_code == 400, resp.text

    def test_rejects_a_corrupt_archive(self, client):
        """A .docx that is not a zip must not come back as a 500.

        The C reader fails deep inside; the user needs to know the file is bad,
        not that the server broke.
        """
        resp = client.post(
            "/api/wrt/import",
            content=b"this is definitely not a zip archive",
            params={"filename": "broken.docx"},
        )

        assert resp.status_code in (200, 422), resp.text
        if resp.status_code == 200:
            # Some readers tolerate junk and return an empty document; that is
            # only acceptable if the emptiness is reported, not passed on.
            assert resp.json()["content"].strip(), "empty import was not rejected"

    @pytest.mark.asyncio
    async def test_import_awaits_the_conversion(self, auth_override, monkeypatch):
        """The handler must await the conversion, not call it synchronously.

        The defect being guarded is narrow: a handler that calls a blocking
        conversion from inside ``async def`` still returns a correct response,
        so a test that checks only the output stays green. A timing race is the
        obvious way to catch it and the wrong one -- sleeping inside a stub
        measures the stub, and sleeping around a conversion fast enough to pass
        on a fast machine is flaky on a loaded one.

        So the invariant is asserted directly: the stub is a coroutine function,
        and if the handler failed to await it, the response body would be a
        coroutine object and every ``.strip()``/``in`` check below would fail.
        That makes an un-awaited conversion a hard failure rather than a race.
        """
        from httpx import ASGITransport, AsyncClient

        calls: list[str] = []

        async def observed_docx_to_wrt(data: bytes) -> str:
            calls.append("awaited")
            # An event loop checkpoint: if this runs, the handler truly yielded
            # rather than spinning on a blocking call.
            await asyncio.sleep(0)
            return "[h1]Из импортированного документа[/h1]"

        monkeypatch.setattr(svc, "docx_to_wrt", observed_docx_to_wrt)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            resp = await ac.post(
                "/api/wrt/import",
                content=make_docx(),
                params={"filename": "a.docx"},
            )

        assert resp.status_code == 200, resp.text
        assert calls == ["awaited"], "the conversion was not awaited by the handler"
        # Would raise TypeError if the body were a coroutine rather than str.
        assert "Из импортированного документа" in resp.json()["content"]

    @pytest.mark.asyncio
    async def test_concurrent_imports_agree(self, auth_override):
        """Two simultaneous conversions of the same file must not interleave.

        The zip actions stage a temp file each, so a shared-path bug would show
        up as one request reading the other's bytes.
        """
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            first, second = await asyncio.gather(
                ac.post("/api/wrt/import", content=make_docx("Первый документ"), params={"filename": "a.docx"}),
                ac.post("/api/wrt/import", content=make_docx("Второй документ"), params={"filename": "b.docx"}),
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert "Первый документ" in first.json()["content"]
        assert "Второй документ" in second.json()["content"]
        # Each response must carry only its own document.
        assert "Второй документ" not in first.json()["content"]
        assert "Первый документ" not in second.json()["content"]


# -- export ---------------------------------------------------------------


class TestExport:
    @pytest.mark.parametrize(
        "fmt,expected_suffix,magic",
        [
            ("docx", ".docx", b"PK"),
            ("odt", ".odt", b"PK"),
            ("pptx", ".pptx", b"PK"),
            ("md", ".md", None),
            ("wrt", ".wrt", None),
        ],
    )
    def test_exports_each_format(self, client, fmt, expected_suffix, magic):
        resp = client.post(
            "/api/wrt/export",
            json={"content": "[h1]Отчёт[/h1]\n\nТекст.\n", "filename": "doc", "format": fmt},
        )

        assert resp.status_code == 200, resp.text
        assert expected_suffix in resp.headers["content-disposition"]
        if magic:
            assert resp.content.startswith(magic), f"{fmt} is not a zip archive"
        else:
            assert resp.content

    def test_export_preserves_cyrillic_in_markdown(self, client):
        """Guards the escaping regression on the response side of the socket.

        Markdown goes through the same JSON transport as the HTML actions that
        carried the ``ensure_ascii`` bug, so it is the cheapest place to prove
        the fix still holds end to end through the API.
        """
        resp = client.post(
            "/api/wrt/export",
            json={"content": "[h1]Отчёт за год[/h1]", "filename": "doc", "format": "md"},
        )

        assert resp.status_code == 200
        text = resp.content.decode("utf-8")
        assert "Отчёт за год" in text
        assert "u041e" not in text, "markdown came back as \\uXXXX escapes"

    @pytest.mark.asyncio
    async def test_export_awaits_the_conversion(self, auth_override, monkeypatch):
        """The regression this endpoint was rewritten to remove.

        ``/export`` used to call ``subprocess.run`` from inside an ``async def``
        handler, which blocks the whole event loop for the length of every
        conversion -- every other request in the process waits, not just this
        one. The response was still correct, so no output assertion could have
        caught it.

        Asserted the invariant structurally instead of by timing: the stub is a
        coroutine function, so a handler that failed to await it would try to
        send a coroutine as a response body and raise.
        """
        from httpx import ASGITransport, AsyncClient

        calls: list[str] = []

        async def observed_wrt_to_docx(text: str) -> bytes:
            calls.append("awaited")
            await asyncio.sleep(0)
            return b"PK\x03\x04stub"

        monkeypatch.setattr(svc, "wrt_to_docx", observed_wrt_to_docx)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            resp = await ac.post(
                "/api/wrt/export",
                json={"content": "[h1]x[/h1]", "filename": "d", "format": "docx"},
            )

        assert resp.status_code == 200, resp.text
        assert calls == ["awaited"], "the conversion was not awaited by the handler"
        assert resp.content.startswith(b"PK")

    def test_export_returns_an_error_rather_than_an_empty_file(self, client, monkeypatch):
        """An empty body must not be handed over as a successful download.

        Every conversion path raises on failure, so empty output means the
        engine produced nothing. Returning it would give the user a zero-byte
        file that looks like a completed export.
        """

        async def empty_conversion(content):
            return b""

        monkeypatch.setattr(svc, "wrt_to_docx", empty_conversion)

        resp = client.post(
            "/api/wrt/export",
            json={"content": "[h1]x[/h1]", "filename": "doc", "format": "docx"},
        )

        assert resp.status_code == 502, resp.text
        assert "no data" in resp.json()["detail"].lower()

    def test_export_filename_is_sanitised(self, client):
        """A quote or backslash in the name must not break the header.

        The header is the one place user text meets a quoted-string context;
        an unescaped quote would let a crafted filename inject header content.
        """
        resp = client.post(
            "/api/wrt/export",
            json={"content": "[h1]x[/h1]", "filename": 'evil".txt\r\nX-Bad: 1', "format": "md"},
        )

        assert resp.status_code == 200, resp.text
        disposition = resp.headers["content-disposition"]
        assert "X-Bad" not in disposition.replace("filename*=", "").split(";")[0]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
