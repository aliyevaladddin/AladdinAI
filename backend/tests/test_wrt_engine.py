# NOTICE: This file is protected under RCF-PL
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.wrt_engine_service import validate_wrt, fix_wrt, wrt_to_html, wrt_stats


@pytest.mark.asyncio
async def test_native_c_validate_valid():
    content = "[h1]Architecture Document[/h1]\n[quote]Deterministic computing[/quote]\n[b]bold text[/b]"
    rep = await validate_wrt(content)
    assert rep["valid"] is True
    assert rep["tag_count"] == 6
    assert len(rep["issues"]) == 0


@pytest.mark.asyncio
async def test_native_c_validate_invalid():
    content = "[h1]Architecture[/h1]\n[b]unclosed bold tag"
    rep = await validate_wrt(content)
    assert rep["valid"] is False
    assert len(rep["issues"]) > 0
    assert rep["issues"][0]["tag"] == "b"


@pytest.mark.asyncio
async def test_native_c_fix():
    content = "[b]unclosed bold"
    fixed = await fix_wrt(content)
    assert fixed.strip().endswith("[/b]")


@pytest.mark.asyncio
async def test_native_c_to_html():
    content = "[h1]Title[/h1]\n[quote]Quote test[/quote]"
    html = await wrt_to_html(content)
    assert '<h1 class="wrt-heading">Title</h1>' in html
    assert '<blockquote class="wrt-quote' in html


@pytest.mark.asyncio
async def test_native_c_stats():
    content = "One two three four"
    stats = await wrt_stats(content)
    assert stats["words"] == 4


@pytest.mark.asyncio
async def test_wrt_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Validate endpoint
        res = await ac.post("/api/wrt/validate", json={"content": "[b]hello[/b]"})
        assert res.status_code == 200
        assert res.json()["valid"] is True

        # Fix endpoint
        res = await ac.post("/api/wrt/fix", json={"content": "[b]auto fix"})
        assert res.status_code == 200
        assert res.json()["content"].strip().endswith("[/b]")

        # To HTML endpoint
        res = await ac.post("/api/wrt/to-html", json={"content": "[h1]Header[/h1]"})
        assert res.status_code == 200
        assert '<h1 class="wrt-heading">Header</h1>' in res.json()["html"]

        # Stats endpoint
        res = await ac.post("/api/wrt/stats", json={"content": "Alpha Beta Gamma"})
        assert res.status_code == 200
        assert res.json()["words"] == 3

        # List files endpoint
        res = await ac.get("/api/wrt/files?path=/workspaces/AladdinAI/backend/native")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["files"]) > 0

        # Save file endpoint
        test_file = "/tmp/test_api_doc.wrt"
        res = await ac.post("/api/wrt/files/save", json={"path": test_file, "content": "[h1]Saved via API[/h1]"})
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Read file endpoint
        res = await ac.post("/api/wrt/files/read", json={"path": test_file})
        assert res.status_code == 200
        assert res.json()["content"] == "[h1]Saved via API[/h1]"

        # Recent files endpoint
        res = await ac.get("/api/wrt/files/recent")
        assert res.status_code == 200
        recent = res.json()
        assert recent["success"] is True
        assert any(f["path"] == test_file for f in recent["files"])


@pytest.mark.asyncio
async def test_native_c_markdown_to_wrt():
    from app.services.wrt_engine_service import md_to_wrt, wrt_to_md

    md_input = """# Document Title

## Subsection

This has **bold text**, *italic text*, ~~strike~~, and `inline code`.

> A famous blockquote

- List item 1
- List item 2

| Col 1 | Col 2 |
|---|---|
| A | B |
"""
    wrt = md_to_wrt(md_input)
    assert "[h1]Document Title[/h1]" in wrt
    assert "[h2]Subsection[/h2]" in wrt
    assert "[b]bold text[/b]" in wrt
    assert "[i]italic text[/i]" in wrt
    assert "[s]strike[/s]" in wrt
    assert "[code]inline code[/code]" in wrt
    assert "[quote]A famous blockquote[/quote]" in wrt
    assert "* List item 1" in wrt
    assert "[table]" in wrt
    assert "| A | B |" in wrt

    # Roundtrip test
    md_back = wrt_to_md(wrt)
    assert "# Document Title" in md_back
    assert "## Subsection" in md_back
    assert "**bold text**" in md_back
    assert "*italic text*" in md_back


