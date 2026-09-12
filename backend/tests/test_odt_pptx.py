# NOTICE: This file is protected under RCF-PL 
"""Comprehensive unit and integration tests for Native C ODT and PPTX engines."""

import os
import json
import socket
import pytest
from app.services.wrt_engine_service import (
    odt_to_wrt,
    wrt_to_odt,
    pptx_to_wrt,
    wrt_to_pptx,
    SOCKET_PATH,
)


def test_odt_round_trip():
    """Test full round-trip conversion for OpenDocument Text (.odt)."""
    original_wrt = """[h1]Project Aurora Architecture[/h1]

[h2]System Overview[/h2]

This paragraph features [b]bold text[/b], [i]italic styling[/i], [u]underlined text[/u], and [s]strikethrough[/s].

[quote]Sentient computing demands deterministic execution and data sovereignty.[/quote]

[list]
* Zero-latency memory subsystem
* Native C document acceleration
* Secure enclave isolation
[/list]

[table]
| Module | Technology | Latency |
| Core Kernel | Native C | 0.4ms |
| Memory Layer | Vector RAM | 1.2ms |
| Transport | Unix Socket | 0.1ms |
[/table]
"""
    odt_bytes = wrt_to_odt(original_wrt)
    assert isinstance(odt_bytes, bytes)
    assert len(odt_bytes) > 0
    assert odt_bytes[:4] == b"PK\x03\x04"  # Valid ZIP archive

    converted_wrt = odt_to_wrt(odt_bytes)
    assert "[h1]Project Aurora Architecture[/h1]" in converted_wrt
    assert "[h2]System Overview[/h2]" in converted_wrt
    assert "[b]bold text[/b]" in converted_wrt
    assert "[i]italic styling[/i]" in converted_wrt
    assert "[u]underlined text[/u]" in converted_wrt
    assert "[s]strikethrough[/s]" in converted_wrt
    assert "[quote]Sentient computing demands deterministic execution and data sovereignty.[/quote]" in converted_wrt
    assert "[list]" in converted_wrt
    assert "* Zero-latency memory subsystem" in converted_wrt
    assert "[table]" in converted_wrt
    assert "Core Kernel" in converted_wrt
    assert "0.4ms" in converted_wrt


def test_odt_markdown_auto_detection():
    """Test that Markdown inside ODT files is automatically converted to WRT tags."""
    md_content = """# AladdinAI Sovereign Engine

**Author**: Aladdin Aliyev
*Version*: 2.0.4

### Abstract
> A high-performance dOS architecture for cognitive agent workflows.

| Feature | Support |
| Markdown | Auto-detected |
| OpenDocument | Native C |

* Fast compilation
* Microsecond socket RPC
"""
    odt_bytes = wrt_to_odt(md_content)
    converted_wrt = odt_to_wrt(odt_bytes)

    # Verify Markdown was parsed into proper WRT tags
    assert "[h1]AladdinAI Sovereign Engine[/h1]" in converted_wrt
    assert "[b]Author[/b]" in converted_wrt
    assert "[i]Version[/i]" in converted_wrt
    assert "[h3]Abstract[/h3]" in converted_wrt
    assert "[quote]" in converted_wrt
    assert "[table]" in converted_wrt
    assert "[code]" not in converted_wrt  # Must not falsely wrap in code blocks


def test_pptx_round_trip():
    """Test full round-trip conversion for PowerPoint (.pptx)."""
    original_wrt = """[slide 1]
[h1]Aurora OS: Keynote[/h1]
Welcome to the next generation of [b]deterministic computing[/b].
Presented by [i]Aladdin Aliyev[/i].
[/slide]

[slide 2]
[h1]Benchmark Results[/h1]
[table]
| Metric | Python Engine | Native C Engine |
| Throughput | 45 req/sec | 3,200 req/sec |
| Memory RSS | 185 MB | 4 MB |
[/table]
[/slide]

[slide 3]
[h1]Summary[/h1]
* 70x performance gain
* Instant file round-trip
[/slide]
"""
    pptx_bytes = wrt_to_pptx(original_wrt)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 0
    assert pptx_bytes[:4] == b"PK\x03\x04"  # Valid ZIP / OpenXML archive

    converted_wrt = pptx_to_wrt(pptx_bytes)
    assert "[slide 1]" in converted_wrt
    assert "[h1]Aurora OS: Keynote[/h1]" in converted_wrt
    assert "[b]deterministic computing[/b]" in converted_wrt
    assert "[i]Aladdin Aliyev[/i]" in converted_wrt
    assert "[slide 2]" in converted_wrt
    assert "[h1]Benchmark Results[/h1]" in converted_wrt
    assert "[table]" in converted_wrt
    assert "Throughput" in converted_wrt
    assert "3,200 req/sec" in converted_wrt
    assert "[slide 3]" in converted_wrt
    assert "[h1]Summary[/h1]" in converted_wrt


def test_pptx_markdown_auto_detection():
    """Test that Markdown inside PPTX presentations is automatically converted."""
    md_presentation = """[slide 1]
# Sentient Intelligence Architecture

**Speaker**: Aladdin
[/slide]

[slide 2]
### Real-time Telemetry
* Sub-millisecond pipeline
* Cryptographic audit log
[/slide]
"""
    pptx_bytes = wrt_to_pptx(md_presentation)
    converted_wrt = pptx_to_wrt(pptx_bytes)

    assert "[slide 1]" in converted_wrt
    assert "[h1]Sentient Intelligence Architecture[/h1]" in converted_wrt
    assert "[b]Speaker[/b]" in converted_wrt
    assert "[slide 2]" in converted_wrt
    assert "Real-time Telemetry" in converted_wrt


def test_socket_odt_and_pptx_actions():
    """Test that the Native C Engine daemon handles ODT and PPTX actions over Unix socket."""
    if not os.path.exists(SOCKET_PATH):
        pytest.skip("Daemon socket not active")

    def query_socket(payload: dict) -> dict:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(payload).encode() + b"\n")
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            raw += chunk
        sock.close()
        return json.loads(raw.decode())

    # 1. Test ping
    pong = query_socket({"action": "ping"})
    assert pong.get("type") == "pong"

    # 2. Test wrt_to_odt via socket
    out_odt = "/tmp/socket_test.odt"
    resp = query_socket({
        "action": "wrt_to_odt",
        "content": "[h1]Socket ODT Test[/h1]\nParagraph text\n",
        "path": out_odt,
    })
    assert resp.get("type") == "wrt_to_odt_result"
    assert os.path.exists(out_odt)

    # 3. Test odt_to_wrt via socket
    resp2 = query_socket({
        "action": "odt_to_wrt",
        "path": out_odt,
    })
    assert resp2.get("type") == "odt_to_wrt_result"
    assert "[h1]Socket ODT Test[/h1]" in resp2.get("content", "")

    # 4. Test wrt_to_pptx via socket
    out_pptx = "/tmp/socket_test.pptx"
    resp3 = query_socket({
        "action": "wrt_to_pptx",
        "content": "[slide 1]\n[h1]Socket PPTX Test[/h1]\n[/slide]\n",
        "path": out_pptx,
    })
    assert resp3.get("type") == "wrt_to_pptx_result"
    assert os.path.exists(out_pptx)

    # 5. Test pptx_to_wrt via socket
    resp4 = query_socket({
        "action": "pptx_to_wrt",
        "path": out_pptx,
    })
    assert resp4.get("type") == "pptx_to_wrt_result"
    assert "[h1]Socket PPTX Test[/h1]" in resp4.get("content", "")

    # Clean up temp files
    for p in (out_odt, out_pptx):
        try:
            os.remove(p)
        except Exception:
            pass
