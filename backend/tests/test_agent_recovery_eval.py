from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.services.agent_runner import run_agent


@pytest.fixture
def base_agent():
    db = AsyncMock()
    provider_mock = MagicMock()
    provider_mock.type = "openai"
    db.execute.return_value.scalar_one_or_none.return_value = provider_mock
    db.execute.return_value.scalars.return_value.all.return_value = []

    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.user_id = 1
    agent.llm_provider_id = 1
    agent.model = "gpt-4o"
    agent.role = "assistant"
    agent.tools_config = {"allowed": ["recall"], "max_iterations": 3}
    return db, agent


@pytest.fixture
def base_messages():
    return [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "Execute test command."},
    ]


@pytest.fixture
def mock_agent_runner(base_agent, base_messages):
    db, agent = base_agent

    async def _run(llm_turns: list[dict], tool_results: list[dict]):
        messages = list(base_messages)
        with (
            patch("app.services.agent_runner.safety_ingress", new_callable=AsyncMock, return_value={"safe": True, "reason": "ok"}),
            patch("app.services.agent_runner.safety_egress", new_callable=AsyncMock, return_value={"safe": True, "reason": "ok"}),
            patch("app.services.agent_runner.chat_completion", new_callable=AsyncMock, side_effect=llm_turns),
            patch("app.services.agent_runner.execute", new_callable=AsyncMock, side_effect=tool_results),
            patch("app.services.agent_runner.openai_schemas", return_value=[{"type": "function"}]),
            patch("app.services.agent_runner.model_supports_tools", return_value=True),
            patch("app.services.agent_runner.schedule_extraction"),
            patch("app.services.agent_runner.schedule_trace_capture") as trace_mock,
        ):
            final_text = await run_agent(db, agent, messages)
            payload = trace_mock.call_args.kwargs["payload"]
            return final_text, payload

    return _run


@pytest.mark.asyncio
async def test_successful_tool_call(mock_agent_runner):
    llm_turns = [
        {
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
        {"content": "I found the data.", "tool_calls": None},
    ]
    tool_results = [{"result": "expected data"}]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"


@pytest.mark.asyncio
async def test_temporary_failure(mock_agent_runner):
    llm_turns = [
        {
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
        {
            "content": None,
            "tool_calls": [{"id": "call_2", "function": {"name": "recall", "arguments": '{"query": "data_retry"}'}}],
        },
        {"content": "I found the data after retrying.", "tool_calls": None},
    ]
    tool_results = [
        {"error": "timeout"},
        {"result": "expected data"},
    ]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 1
    assert len(payload["tool_calls"]) == 2
    assert payload["tool_calls"][0]["is_error"] is True
    assert payload["tool_calls"][1]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"


@pytest.mark.asyncio
async def test_persistent_failure(mock_agent_runner):
    llm_turns = [
        {
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
        {
            "content": None,
            "tool_calls": [{"id": "call_2", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
        {
            "content": None,
            "tool_calls": [{"id": "call_3", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
    ]
    tool_results = [
        {"error": "access denied"},
        {"error": "access denied"},
        {"error": "access denied"},
    ]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 3
    assert payload["outcome"] == "max_iterations_exhausted"
    assert payload["hit_max_iterations"] is True


@pytest.mark.asyncio
async def test_unexpected_tool_result(mock_agent_runner):
    llm_turns = [
        {
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "recall", "arguments": '{"query": "data"}'}}],
        },
        {"content": "The returned data was unusable.", "tool_calls": None},
    ]
    tool_results = [{"unrelated_field": "useless info"}]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"
    assert "unusable" in final_text


@pytest.mark.asyncio
async def test_incidental_nested_error_key(mock_agent_runner):
    llm_turns = [
        {
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "recall", "arguments": '{"query": "test"}'}}],
        },
        {"content": "Result processed successfully.", "tool_calls": None},
    ]
    tool_results = [
        {"result": {"value": "ok", "metadata": {"error": "historical warning"}}}
    ]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert len(payload["tool_calls"]) == 1
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"