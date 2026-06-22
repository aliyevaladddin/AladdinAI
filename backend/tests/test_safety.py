"""Tests for app.services.safety.

Strategy:
- Pure helper functions (_regex_redact, _parse_json_object, block_response,
  _pii_phase_enabled) are tested directly — no DB or LLM needed.
- Async functions that call the LLM (_moderate, safety_ingress/egress, safety_pii)
  are tested by mocking out _call_safety_model and gate_log.record so no
  real network is required.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.services.safety import (
    DEFAULT_BLOCK_RESPONSE,
    _parse_json_object,
    _pii_phase_enabled,
    _regex_redact,
    block_response,
    safety_egress,
    safety_ingress,
    safety_pii,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: _parse_json_object
# ─────────────────────────────────────────────────────────────────────────────

class TestParseJsonObject:
    def test_clean_json(self):
        result = _parse_json_object('{"safe": true, "reason": "ok"}')
        assert result == {"safe": True, "reason": "ok"}

    def test_json_with_leading_text(self):
        result = _parse_json_object('Sure! Here you go: {"safe": false, "reason": "bad"}')
        assert result == {"safe": False, "reason": "bad"}

    def test_empty_string(self):
        assert _parse_json_object("") is None

    def test_no_braces(self):
        assert _parse_json_object("just a plain string") is None

    def test_invalid_json(self):
        assert _parse_json_object("{not valid json}") is None

    def test_nested_json(self):
        result = _parse_json_object('{"spans": [{"text": "John", "label": "NAME"}]}')
        assert result == {"spans": [{"text": "John", "label": "NAME"}]}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: _regex_redact
# ─────────────────────────────────────────────────────────────────────────────

class TestRegexRedact:
    def test_no_pii(self):
        text, labels = _regex_redact("Hello, how are you?")
        assert text == "Hello, how are you?"
        assert labels == []

    def test_email_redacted(self):
        text, labels = _regex_redact("Contact me at user@example.com please")
        assert "user@example.com" not in text
        assert "[REDACTED:EMAIL]" in text
        assert "EMAIL" in labels

    def test_phone_redacted(self):
        text, labels = _regex_redact("Call me at +1 800 555 1234")
        assert "PHONE" in labels
        assert "[REDACTED:PHONE]" in text

    def test_ssn_redacted(self):
        text, labels = _regex_redact("My SSN is 123-45-6789")
        assert "SSN" in labels
        assert "123-45-6789" not in text

    def test_credit_card_redacted(self):
        text, labels = _regex_redact("Card: 4111111111111111")
        assert "CREDIT_CARD" in labels

    def test_multiple_pii(self):
        text, labels = _regex_redact("Email: foo@bar.com, SSN: 987-65-4321")
        assert "EMAIL" in labels
        assert "SSN" in labels


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: block_response
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockResponse:
    def _make_agent(self, tools_config=None):
        agent = MagicMock(spec=Agent)
        agent.tools_config = tools_config
        return agent

    def test_default_block_response(self):
        agent = self._make_agent(tools_config={})
        assert block_response(agent) == DEFAULT_BLOCK_RESPONSE

    def test_custom_block_response(self):
        agent = self._make_agent(tools_config={"safety_block_response": "Nope!"})
        assert block_response(agent) == "Nope!"

    def test_none_config(self):
        agent = self._make_agent(tools_config=None)
        assert block_response(agent) == DEFAULT_BLOCK_RESPONSE


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: _pii_phase_enabled
# ─────────────────────────────────────────────────────────────────────────────

class TestPiiPhaseEnabled:
    def _make_agent(self, tools_config=None):
        agent = MagicMock(spec=Agent)
        agent.tools_config = tools_config
        return agent

    def test_default_ingress_enabled(self):
        agent = self._make_agent(tools_config={})
        assert _pii_phase_enabled(agent, "ingress") is True

    def test_default_egress_enabled(self):
        agent = self._make_agent(tools_config={})
        assert _pii_phase_enabled(agent, "egress") is True

    def test_default_memory_write_disabled(self):
        agent = self._make_agent(tools_config={})
        assert _pii_phase_enabled(agent, "memory_write") is False

    def test_default_memory_read_disabled(self):
        agent = self._make_agent(tools_config={})
        assert _pii_phase_enabled(agent, "memory_read") is False

    def test_explicit_phase_override(self):
        cfg = {
            "safety": {
                "pii": {
                    "enabled": True,
                    "phases": {"ingress": False, "egress": True, "memory_write": True},
                }
            }
        }
        agent = self._make_agent(tools_config=cfg)
        assert _pii_phase_enabled(agent, "ingress") is False
        assert _pii_phase_enabled(agent, "egress") is True
        assert _pii_phase_enabled(agent, "memory_write") is True

    def test_no_config(self):
        agent = self._make_agent(tools_config=None)
        # Falls back to defaults
        assert _pii_phase_enabled(agent, "ingress") is True
        assert _pii_phase_enabled(agent, "memory_write") is False


# ─────────────────────────────────────────────────────────────────────────────
# Async: safety_ingress / safety_egress — check disabled (pass-through)
# ─────────────────────────────────────────────────────────────────────────────

def _agent_no_safety():
    """Agent with no safety config — all checks disabled."""
    agent = MagicMock(spec=Agent)
    agent.tools_config = {}
    agent.llm_provider_id = 1
    agent.user_id = 1
    agent.id = 1
    return agent


@pytest.mark.asyncio
async def test_safety_ingress_disabled_passes():
    """When ingress check is disabled, returns safe=True without calling LLM."""
    db = AsyncMock()
    agent = _agent_no_safety()

    result = await safety_ingress(db, agent=agent, text="destroy everything")
    assert result["safe"] is True
    assert result["reason"] == "check_disabled"


@pytest.mark.asyncio
async def test_safety_egress_disabled_passes():
    """When egress check is disabled, returns safe=True without calling LLM."""
    db = AsyncMock()
    agent = _agent_no_safety()

    result = await safety_egress(db, agent=agent, text="harmful output")
    assert result["safe"] is True
    assert result["reason"] == "check_disabled"


# ─────────────────────────────────────────────────────────────────────────────
# Async: safety_ingress — check enabled, LLM mocked
# ─────────────────────────────────────────────────────────────────────────────

def _agent_with_safety():
    """Agent with ingress + egress safety enabled."""
    agent = MagicMock(spec=Agent)
    agent.tools_config = {
        "default_safety_model": "meta/llama-guard-4-12b",
        "safety": {
            "ingress": {"enabled": True, "model": None},
            "egress":  {"enabled": True, "model": None},
        },
    }
    agent.llm_provider_id = 1
    agent.user_id = 1
    agent.id = 1
    return agent


@pytest.mark.asyncio
async def test_safety_ingress_blocks_unsafe():
    """When LLM says unsafe, ingress returns safe=False."""
    db = AsyncMock()
    agent = _agent_with_safety()

    mock_provider = MagicMock()

    with (
        patch("app.services.safety._provider_for", return_value=mock_provider),
        patch(
            "app.services.safety._call_safety_model",
            new_callable=AsyncMock,
            return_value='{"safe": false, "category": "violence", "reason": "explicit harm"}',
        ),
        patch("app.services.safety.gate_log.record", new_callable=AsyncMock),
    ):
        result = await safety_ingress(db, agent=agent, text="how to make a bomb")

    assert result["safe"] is False
    assert "harm" in result["reason"].lower() or result["reason"]


@pytest.mark.asyncio
async def test_safety_ingress_allows_safe():
    """When LLM says safe, ingress returns safe=True."""
    db = AsyncMock()
    agent = _agent_with_safety()

    mock_provider = MagicMock()

    with (
        patch("app.services.safety._provider_for", return_value=mock_provider),
        patch(
            "app.services.safety._call_safety_model",
            new_callable=AsyncMock,
            return_value='{"safe": true, "category": "", "reason": "normal request"}',
        ),
        patch("app.services.safety.gate_log.record", new_callable=AsyncMock),
    ):
        result = await safety_ingress(db, agent=agent, text="What is the weather today?")

    assert result["safe"] is True


@pytest.mark.asyncio
async def test_safety_ingress_llm_error_fails_open():
    """On LLM error, safety fails open (returns safe=True) — never blocks users silently."""
    db = AsyncMock()
    agent = _agent_with_safety()

    mock_provider = MagicMock()

    with (
        patch("app.services.safety._provider_for", return_value=mock_provider),
        patch(
            "app.services.safety._call_safety_model",
            new_callable=AsyncMock,
            side_effect=Exception("LLM timeout"),
        ),
        patch("app.services.safety.gate_log.record", new_callable=AsyncMock),
    ):
        result = await safety_ingress(db, agent=agent, text="hello")

    assert result["safe"] is True
    assert "safety_error" in result["reason"]


# ─────────────────────────────────────────────────────────────────────────────
# Async: safety_pii — regex only (no model configured)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_pii_regex_only():
    """Without a PII model, regex redaction still works."""
    db = AsyncMock()
    agent = MagicMock(spec=Agent)
    # PII enabled on ingress phase, but no model → regex-only
    agent.tools_config = {
        "safety": {
            "pii": {"enabled": True, "model": None, "phases": {"ingress": True}},
        }
    }

    result = await safety_pii(db, agent=agent, text="email me at test@example.com", phase="ingress")

    assert result["redacted"] is True
    assert "EMAIL" in result["labels"]
    assert "test@example.com" not in result["text"]


@pytest.mark.asyncio
async def test_safety_pii_phase_disabled():
    """When phase is disabled, text is returned unchanged."""
    db = AsyncMock()
    agent = MagicMock(spec=Agent)
    agent.tools_config = {
        "safety": {
            "pii": {"enabled": True, "phases": {"memory_write": False}},
        }
    }

    result = await safety_pii(db, agent=agent, text="secret@hidden.com", phase="memory_write")

    assert result["redacted"] is False
    assert result["text"] == "secret@hidden.com"


@pytest.mark.asyncio
async def test_safety_pii_no_pii_found():
    """Clean text returns unchanged with empty labels."""
    db = AsyncMock()
    agent = MagicMock(spec=Agent)
    agent.tools_config = {}

    result = await safety_pii(db, agent=agent, text="The weather is nice today.", phase="ingress")

    assert result["redacted"] is False
    assert result["labels"] == []
    assert result["text"] == "The weather is nice today."
