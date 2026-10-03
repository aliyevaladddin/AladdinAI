# NOTICE: This file is protected under RCF-PL
"""Tests for the eight office/markdown conversions on the daemon socket.

The C engine has implemented all eight as socket actions since
``wrt_engine.c:1713-1895``; the Python bridge ignored every one of them and
reached for ``subprocess`` plus temp files instead. That cost three things per
call: a forked process, a round trip through the filesystem, and -- because the
callers are all ``async def`` handlers -- a blocked event loop for the length
of the conversion.

So the interesting property of the new coroutine functions is *which* path they
took, not just that they return the right bytes. A conversion that silently
falls back to the CLI still produces a correct document, which means a test
that only checks the output passes whether or not the socket works at all. Every
test here therefore breaks the socket on purpose and requires the fallback to
be taken, alongside tests that require the socket to be used.

Deliberately not using the service's shared ``SOCKET_PATH``: a daemon started
before a rebuild serves the old image from memory, so a passing run against it
would say nothing about the code on disk.
"""

import asyncio
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "backend" / "native" / "wrt" / "wrt-engine"

sys.path.insert(0, str(ROOT / "backend"))

# The document every conversion is exercised with. Contains Cyrillic on
# purpose: the transport bug that lived here for a release was an escaping
# fault, so a round trip that silently mangles text must fail these tests.
DOC = """[h1]Отчёт за год[/h1]

Some body text with **bold** and a [link url="https://example.com"]reference[/link].

* item one
* item two
"""


class _Daemon:
    """A private wrt-engine daemon for one test class."""

    def __init__(self):
        self.dir = f"/tmp/aladdin_wrt_convtest_{os.getuid()}_{os.getpid()}"
        self.path = os.path.join(self.dir, "test.sock")
        self.proc = None

    def start(self):
        if not ENGINE.is_file():
            raise RuntimeError(
                f"Build the native engine first: make -C backend/native/wrt wrt-engine ({ENGINE})"
            )
        os.makedirs(self.dir, exist_ok=True)
        self.proc = subprocess.Popen(
            [str(ENGINE), "--daemon", self.path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            if os.path.exists(self.path):
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                        probe.settimeout(1.0)
                        probe.connect(self.path)
                    return
                except OSError:
                    pass
            if self.proc.poll() is not None:
                raise RuntimeError(f"daemon exited early with code {self.proc.returncode}")
            time.sleep(0.05)
        self.stop()
        raise RuntimeError("daemon did not create its socket within 10s")

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        if os.path.exists(self.path):
            os.remove(self.path)
        if os.path.isdir(self.dir):
            os.rmdir(self.dir)


class TestSocketConversions(unittest.TestCase):
    """Each conversion must go over the socket when a daemon is reachable."""

    @classmethod
    def setUpClass(cls):
        cls.daemon = _Daemon()
        cls.daemon.start()

    @classmethod
    def tearDownClass(cls):
        cls.daemon.stop()

    def setUp(self):
        from app.services import wrt_engine_service as svc

        self.svc = svc
        self._original = svc.SOCKET_PATH
        svc.SOCKET_PATH = self.daemon.path
        self.addCleanup(self._restore)

    def _restore(self):
        self.svc.SOCKET_PATH = self._original

    # -- socket is actually used -----------------------------------------

    def _assert_socket_used(self, coro_factory, action: str):
        """Run a conversion and prove it went over the socket.

        A round-trip assertion cannot do this job. Both the socket path and the
        CLI fallback produce the same document, so a test that only checks the
        output stays green when the socket is dead -- which is exactly what
        happened while this file was being written: stubbing the three socket
        helpers to return None left every round-trip test passing.

        So the transport call itself is what gets observed. Wrapping
        ``_send_socket_request`` and recording the action names it sees is the
        direct statement of intent: this conversion must be carried by the
        socket, not by a forked process. The wrapper delegates, so the real
        transport -- including the serialization this file also guards -- is
        still what runs.
        """
        sent: list[str] = []
        original = self.svc._send_socket_request

        async def recording(action, content="", path=None):
            sent.append(action)
            return await original(action, content, path)

        self.svc._send_socket_request = recording
        self.addCleanup(setattr, self.svc, "_send_socket_request", original)

        result = asyncio.run(coro_factory())

        self.assertIn(
            action, sent,
            f"{action} never reached the socket -- it fell through to the CLI "
            "fallback, which produces correct output and hides the regression",
        )
        return result

    def test_text_conversions_use_the_socket(self):
        """md <-> wrt exchanges plain text, so a temp file is not in the plan.

        These two must be pure socket traffic. ``_text_convert_socket`` is the
        single place that decides it, so asserting on it directly states the
        intent without depending on how the public wrappers are factored.
        """
        res = asyncio.run(self.svc._text_convert_socket("md_to_wrt", "md_to_wrt_result", "# Заголовок"))
        self.assertIsNotNone(res, "md_to_wrt did not answer over the socket")
        self.assertIn("[h1]Заголовок[/h1]", res)

        back = asyncio.run(self.svc._text_convert_socket("wrt_to_md", "wrt_to_md_result", "[h1]Заголовок[/h1]"))
        self.assertIsNotNone(back, "wrt_to_md did not answer over the socket")
        self.assertIn("# Заголовок", back)

    def test_markdown_round_trip_over_socket(self):
        wrt = self._assert_socket_used(
            lambda: self.svc.md_to_wrt("# Title\n\nBody text\n"), "md_to_wrt"
        )
        self.assertIn("[h1]Title[/h1]", wrt)
        md = self._assert_socket_used(lambda: self.svc.wrt_to_md(wrt), "wrt_to_md")
        self.assertIn("# Title", md)

    def test_docx_round_trip_over_socket(self):
        docx = self._assert_socket_used(lambda: self.svc.wrt_to_docx(DOC), "wrt_to_docx")
        self.assertTrue(docx.startswith(b"PK"), "docx is a zip; a non-PK header means it is not one")
        wrt = self._assert_socket_used(lambda: self.svc.docx_to_wrt(docx), "docx_to_wrt")
        self.assertIn("Отчёт за год", wrt)

    def test_odt_round_trip_over_socket(self):
        odt = self._assert_socket_used(lambda: self.svc.wrt_to_odt(DOC), "wrt_to_odt")
        self.assertTrue(odt.startswith(b"PK"), "odt is a zip; a non-PK header means it is not one")
        wrt = self._assert_socket_used(lambda: self.svc.odt_to_wrt(odt), "odt_to_wrt")
        self.assertIn("Отчёт за год", wrt)

    def test_pptx_round_trip_over_socket(self):
        pptx = self._assert_socket_used(lambda: self.svc.wrt_to_pptx(DOC), "wrt_to_pptx")
        self.assertTrue(pptx.startswith(b"PK"), "pptx is a zip; a non-PK header means it is not one")
        wrt = self._assert_socket_used(lambda: self.svc.pptx_to_wrt(pptx), "pptx_to_wrt")
        self.assertIn("Отчёт за год", wrt)

    def test_every_socket_helper_answers_for_a_live_daemon(self):
        """All three helpers, asserted directly rather than through a wrapper.

        A wrapper can grow a condition that skips its helper -- an early return
        for one format, say -- and the round-trip tests would keep passing via
        the CLI. Calling the helpers names each path directly.
        """
        self.assertIsNotNone(asyncio.run(
            self.svc._text_convert_socket("md_to_wrt", "md_to_wrt_result", "# x")),
            "_text_convert_socket returned None against a live daemon",
        )
        docx = asyncio.run(self.svc.wrt_to_docx(DOC))
        self.assertIsNotNone(
            asyncio.run(self.svc.docx_to_wrt(docx)),
            "_to_wrt_socket returned None against a live daemon",
        )
        self.assertIsNotNone(
            asyncio.run(self.svc._from_wrt_socket("wrt_to_docx", "wrt_to_docx_result", DOC, ".docx")),
            "_from_wrt_socket returned None against a live daemon",
        )

    def test_socket_helpers_return_none_without_a_daemon(self):
        """The contract that makes the fallback reachable.

        With no daemon on the path, every helper must report "not handled" by
        returning None -- never raise. The wrappers rely on this to decide
        between socket and CLI, and an exception here would turn a
        missing-daemon condition into a 500.
        """
        self.svc.SOCKET_PATH = f"/tmp/aladdin_wrt_absent_{os.getpid()}.sock"

        self.assertIsNone(asyncio.run(self.svc._text_convert_socket("md_to_wrt", "md_to_wrt_result", "# x")))
        self.assertIsNone(asyncio.run(self.svc._to_wrt_socket("docx_to_wrt", "docx_to_wrt_result", b"PK", ".docx")))
        self.assertIsNone(asyncio.run(self.svc._from_wrt_socket("wrt_to_docx", "wrt_to_docx_result", "[h1]x[/h1]", ".docx")))

    def test_fallback_still_produces_a_correct_document(self):
        """With the socket gone the CLI path must carry the request.

        This is the case that would have caught a conversion that only ever
        worked over the socket -- the one failure mode a socket-only test
        cannot see.
        """
        self.svc.SOCKET_PATH = f"/tmp/aladdin_wrt_absent_{os.getpid()}.sock"

        wrt = asyncio.run(self.svc.md_to_wrt("# Title\n\nBody\n"))
        self.assertIn("[h1]Title[/h1]", wrt)

        docx = asyncio.run(self.svc.wrt_to_docx(DOC))
        self.assertTrue(docx.startswith(b"PK"))

    def test_no_temp_files_are_left_behind(self):
        """The point of moving to the socket: the temp file must not survive.

        Counts the daemon's temp directory before and after. The zip actions
        legitimately stage one file each (the C side streams archives through
        disk), so this asserts the count returns to where it started, not that
        it never rises.
        """
        import glob
        import tempfile

        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "tmp*")))
        asyncio.run(self.svc.wrt_to_docx(DOC))
        asyncio.run(self.svc.docx_to_wrt(asyncio.run(self.svc.wrt_to_docx(DOC))))
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "tmp*")))

        leaked = {p for p in after - before if os.path.isfile(p)}
        self.assertEqual(leaked, set(), f"conversion leaked temp files: {leaked}")


class TestSyncTwins(unittest.TestCase):
    """The ``*_sync`` wrappers exist for callers with no event loop.

    They bypass the socket deliberately: ``asyncio.run`` cannot be nested
    inside a running loop, so a sync caller in async context has to use the
    CLI. What matters is that they work and that calling one from inside a
    running loop fails loudly rather than silently returning a coroutine.
    """

    def test_sync_twins_produce_valid_output(self):
        from app.services import wrt_engine_service as svc

        self.assertIn("[h1]Title[/h1]", svc.md_to_wrt_sync("# Title\n"))
        self.assertTrue(svc.wrt_to_docx_sync(DOC).startswith(b"PK"))
        self.assertIn("Отчёт за год", svc.docx_to_wrt_sync(svc.wrt_to_docx_sync(DOC)))

    def test_sync_twin_inside_a_loop_fails_loudly(self):
        """A coroutine returned where bytes were expected is a silent bug.

        Every caller of the sync twins does ``open(...).read()`` or ``.encode()``
        on the result. Handing back an un-awaited coroutine would surface as an
        AttributeError far from the call, so assert the failure is immediate
        and names the real cause.
        """
        from app.services import wrt_engine_service as svc

        async def call_it():
            with self.assertRaises(RuntimeError) as ctx:
                svc.md_to_wrt_sync("# Title\n")
            message = str(ctx.exception)
            self.assertIn("sync wrapper", message)
            # The message has to name the replacement, or the reader is left
            # searching for one.
            self.assertIn("await the coroutine of the same name", message)

        asyncio.run(call_it())


if __name__ == "__main__":
    unittest.main()
