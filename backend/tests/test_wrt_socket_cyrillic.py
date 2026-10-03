# NOTICE: This file is protected under RCF-PL
"""Regression tests for the WRT daemon socket transport.

Every other WRT test in this suite drives the ``wrt-engine`` binary directly over
CLI. That is the right call for testing the engine -- and it is exactly why a
transport bug lived unnoticed: the socket path is exercised by nothing.

The bug this file locks down: ``_send_socket_request`` serialized requests with
``json.dumps(req_data)``, whose default ``ensure_ascii=True`` turns every
Cyrillic character into a ``\\uXXXX`` escape. The C daemon has no unescape step,
so it returned the literal text. Measured, on the same input:

    via socket : u041fu0440u0438u0432u0435u0442
    via CLI    : Привет

A Russian user typing in the Visual editor had their document silently mangled on
every save. The C engine was never at fault; the Python bridge was.

These tests start a real daemon on a private socket and talk to it over a real
connection. They deliberately do not go through the service's shared SOCKET_PATH
constant -- that path may be held by an already-running daemon, and a daemon
started before a rebuild serves the old image from memory, which would make a
passing run say nothing about the code on disk.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "backend" / "native" / "wrt" / "wrt-engine"

# Text that exercises the whole failure: mixed ASCII + Cyrillic + punctuation.
# If any single code path re-escapes, the assertion on the full string catches it.
RUSSIAN = "Привет, мир"
MIXED = "Отчёт за 2026 год — 15.4 МБ / 96 мс"

# Actions whose response carries document text back over the wire. A transport
# bug corrupts all of them identically, so each is worth its own case.
# "validate" is deliberately absent: it answers with counters, not text, so it
# has no document to compare. It is covered by the char_count test instead.
TEXT_ACTIONS = ["to-editable-html", "to-html", "from-editable-html"]


class TestWrtSocketTransport(unittest.TestCase):
    """Starts one daemon in setUpClass and reuses it for the whole class."""

    daemon: subprocess.Popen
    sock_path: str
    sock_dir: str

    @classmethod
    def setUpClass(cls):
        if not ENGINE.is_file():
            raise RuntimeError(
                f"Build the native engine first: make -C backend/native/wrt wrt-engine ({ENGINE})"
            )

        # A private directory keeps this independent of any daemon already
        # running for the developer's live backend.
        cls.sock_dir = f"/tmp/aladdin_wrt_test_{os.getuid()}_{os.getpid()}"
        os.makedirs(cls.sock_dir, exist_ok=True)
        cls.sock_path = os.path.join(cls.sock_dir, "test.sock")

        cls.daemon = subprocess.Popen(
            [str(ENGINE), "--daemon", cls.sock_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.time() + 10
        while time.time() < deadline:
            if os.path.exists(cls.sock_path):
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                        probe.settimeout(1.0)
                        probe.connect(cls.sock_path)
                    return
                except OSError:
                    pass
            if cls.daemon.poll() is not None:
                raise RuntimeError(f"daemon exited early with code {cls.daemon.returncode}")
            time.sleep(0.05)

        cls.daemon.kill()
        raise RuntimeError("daemon did not create its socket within 10s")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "daemon", None) is not None:
            cls.daemon.terminate()
            try:
                cls.daemon.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.daemon.kill()
        sock = getattr(cls, "sock_path", None)
        if sock and os.path.exists(sock):
            os.remove(sock)
        d = getattr(cls, "sock_dir", None)
        if d and os.path.isdir(d):
            os.rmdir(d)

    # -- helpers ---------------------------------------------------------

    def request(self, action: str, content: str) -> dict:
        """Send one request the way the service does and return the parsed reply.

        The serialization is spelled out here rather than imported from the
        service on purpose: this is the exact line that regressed, and a test
        that called the buggy helper would have gone green with the bug.
        """
        payload = json.dumps({"action": action, "content": content}, ensure_ascii=False) + "\n"
        # The wire bytes must be UTF-8, not ASCII-with-escapes.
        payload.encode("utf-8")

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(10.0)
            sock.connect(self.sock_path)
            sock.sendall(payload.encode("utf-8"))
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break

        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        self.assertTrue(raw, f"{action} returned an empty response")
        return json.loads(raw)

    # -- the regression ---------------------------------------------------

    def test_russian_survives_to_editable_html(self):
        """The defect in its purest form."""
        res = self.request("to-editable-html", f"[h1]{RUSSIAN}[/h1]")

        self.assertIn(RUSSIAN, res.get("html", ""))
        # The failure signature: the engine echoing back its own escape text.
        self.assertNotIn("u041f", res.get("html", ""), "content came back as \\uXXXX escapes")

    def test_service_layer_sends_unescaped_json(self):
        """Exercise the real production serializer, not a copy of it.

        The tests above hand-roll their own ``json.dumps(..., ensure_ascii=False)``
        to talk to the daemon directly. That proves the daemon handles raw UTF-8,
        but it would stay green if someone removed ``ensure_ascii=False`` from
        the service -- which is exactly the change that has to be guarded. So
        this case calls the actual ``_send_socket_request``, with SOCKET_PATH
        pointed at the test daemon.
        """
        sys.path.insert(0, str(ROOT / "backend"))
        from app.services import wrt_engine_service as svc

        original_path = svc.SOCKET_PATH
        svc.SOCKET_PATH = self.sock_path
        try:
            res = asyncio.run(svc._send_socket_request("to-editable-html", f"[h1]{RUSSIAN}[/h1]"))
        finally:
            svc.SOCKET_PATH = original_path

        self.assertIsNotNone(res, "service could not reach the test daemon")
        self.assertIn(RUSSIAN, res.get("html", ""))
        self.assertNotIn("u041f", res.get("html", ""), "service re-escaped the payload")

    def test_russian_survives_to_html(self):
        res = self.request("to-html", f"[h1]{RUSSIAN}[/h1]")

        self.assertIn(RUSSIAN, res.get("html", ""))
        self.assertNotIn("u041f", res.get("html", ""))

    def test_russian_survives_from_editable_html(self):
        res = self.request("from-editable-html", f"<h1>{RUSSIAN}</h1>")

        self.assertIn(RUSSIAN, res.get("content", ""))
        self.assertNotIn("u041f", res.get("content", ""))

    def test_russian_counts_are_not_inflated_by_escape_sequences(self):
        """A cheap, independent witness that does not depend on the HTML path.

        ``char_count`` is a ``strlen`` byte count, not a character count, so the
        expected value is the UTF-8 length. Escaped input is six bytes per
        Cyrillic character instead of two, so the old transport roughly tripled
        the number. This fails even if some future change starts unescaping on
        the way back out.
        """
        content = f"[h1]{RUSSIAN}[/h1]"
        res = self.request("validate", content)
        data = res.get("data", {})

        self.assertEqual(
            data.get("char_count"),
            len(content.encode("utf-8")),
            "char_count is the UTF-8 byte length; a mismatch means the daemon "
            "received \\uXXXX escapes instead of raw Cyrillic",
        )
        # The same fact as a bound, so the failure message names the cause.
        self.assertLessEqual(data.get("char_count", 10**9), len(content.encode("utf-8")))

    def test_mixed_ascii_and_cyrillic_preserved_verbatim(self):
        """ASCII next to Cyrillic is where an off-by-one in a length prefix shows."""
        res = self.request("to-editable-html", MIXED)

        self.assertIn(MIXED, res.get("html", ""))

    def test_every_text_carrying_action_round_trips_russian(self):
        for action in TEXT_ACTIONS:
            with self.subTest(action=action):
                payload = RUSSIAN if action != "from-editable-html" else f"<p>{RUSSIAN}</p>"
                res = self.request(action, payload)
                blob = json.dumps(res, ensure_ascii=False)

                self.assertIn(RUSSIAN, blob, f"{action} lost or mangled the Cyrillic text")
                self.assertNotIn("u041", blob, f"{action} returned escaped text")

    # -- the response direction -------------------------------------------

    def test_daemon_reply_is_valid_utf8_and_not_double_escaped(self):
        """Guards the other half of the contract: what comes back.

        The daemon builds its reply with a hand-rolled JSON writer. If that
        writer ever escapes its output, the breakage returns from the other
        direction and ``ensure_ascii=False`` on the Python side cannot help.
        """
        res = self.request("to-editable-html", f"[h1]{RUSSIAN}[/h1]")
        raw = json.dumps(res, ensure_ascii=False)

        self.assertIn("Привет", raw)
        self.assertNotIn("\\u04", raw, "daemon escaped its own response")

    def test_repeated_requests_are_independent(self):
        """A leftover read buffer would bleed one request into the next."""
        for _ in range(5):
            res = self.request("to-editable-html", f"[h1]{RUSSIAN}[/h1]")
            self.assertIn(RUSSIAN, res.get("html", ""))

    def test_ascii_documents_unaffected(self):
        """The fix must not regress the ASCII path it already handled."""
        res = self.request("to-editable-html", "[h1]Hello[/h1]")

        self.assertIn("Hello", res.get("html", ""))

    def test_empty_content_still_answers(self):
        res = self.request("validate", "")

        self.assertIn("type", res)


if __name__ == "__main__":
    unittest.main()
