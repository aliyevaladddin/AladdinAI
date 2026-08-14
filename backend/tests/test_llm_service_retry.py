# NOTICE: This file is protected under RCF-PL
"""Tests for the provider-call retry logic in llm_service.

Transient upstream statuses (429/5xx, incl. NIM's 529 "temporarily overloaded")
must be retried with backoff; everything else must fail immediately. The real
providers are exercised through a tiny fake httpx client that replays a scripted
list of status codes — no network involved. Error responses carry `Retry-After: 0`
so the backoff honours it and the suite doesn't actually sleep.
"""
from contextlib import asynccontextmanager

import httpx
import pytest

from app.services.llm_service import (
    LLMError,
    RETRY_ATTEMPTS,
    _post_with_retry,
    _retried_stream,
    _retry_delay,
)


# ── _retry_delay (pure) ──────────────────────────────────────────────────────
def test_delay_honours_retry_after():
    assert _retry_delay(0, "7") == 7.0


def test_delay_caps_retry_after_at_30s():
    assert _retry_delay(0, "999") == 30.0


def test_delay_ignores_garbage_retry_after():
    d = _retry_delay(0, "soon-ish")
    assert 1.0 <= d < 1.5  # base delay + jitter


def test_delay_grows_exponentially():
    d0 = _retry_delay(0)
    d2 = _retry_delay(2)
    assert 1.0 <= d0 < 1.5
    assert 4.0 <= d2 < 4.5


# ── fakes replaying scripted statuses ────────────────────────────────────────
def _error_response(code: int, url: str) -> httpx.Response:
    headers = {"Retry-After": "0"} if code >= 400 else {}
    return httpx.Response(code, request=httpx.Request("POST", url), headers=headers)


# [RCF:PROTECTED]
class _FakeClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    async def post(self, url, json=None, headers=None):
        self.calls += 1
        return _error_response(self.statuses.pop(0), url)


# [RCF:PROTECTED]
class _FakeStreamClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def stream(self, method, url, json=None, headers=None):
        self.calls += 1
        resp = _error_response(self.statuses.pop(0), url)

        @asynccontextmanager
        async def _ctx():
            yield resp

        return _ctx()


# ── _post_with_retry ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_retries_transient_529_then_succeeds():
    client = _FakeClient([529, 200])
    resp = await _post_with_retry(client, "http://x", {}, {}, "m")
    assert resp.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_post_does_not_retry_client_errors():
    """A 401 is our fault (bad key) — retrying it just wastes quota."""
    client = _FakeClient([401])
    with pytest.raises(LLMError, match="401"):
        await _post_with_retry(client, "http://x", {}, {}, "m")
    assert client.calls == 1


@pytest.mark.asyncio
async def test_post_gives_up_after_max_attempts():
    client = _FakeClient([529] * RETRY_ATTEMPTS)
    with pytest.raises(LLMError, match="529"):
        await _post_with_retry(client, "http://x", {}, {}, "m")
    assert client.calls == RETRY_ATTEMPTS


# ── _retried_stream ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_stream_retries_before_first_byte():
    """The overload fires at the status check, before any token — retryable."""
    client = _FakeStreamClient([529, 200])
    async with _retried_stream(client, "http://x", {}, {}, "m") as resp:
        assert resp.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_stream_propagates_non_retryable_status():
    """The caller's except clause turns the raw HTTPStatusError into LLMError."""
    client = _FakeStreamClient([403])
    with pytest.raises(httpx.HTTPStatusError):
        async with _retried_stream(client, "http://x", {}, {}, "m"):
            pass
    assert client.calls == 1
