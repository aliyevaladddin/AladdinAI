from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services.agent_runner import run_agent


@pytest.mark.asyncio
async def test_success_with_nested_error_key_is_not_tool_failure():
    db = AsyncMock()
    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.user_id = 1
    agent.llm_provider_id = 1
    agent.model = "gpt-4o"
    agent.role = "assistant"
    agent.tools_config = {"allowed": ["recall"], "max_iterations": 5}

    messages = [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "Test nested error key."},
    ]

    scripted_llm_turns = [
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "recall",
                        "arguments": '{"query": "test"}',
                    },
                }
            ],
        },
        {
            "content": "Result processed successfully.",
            "tool_calls": None,
        },
    ]

    scripted_tool_results = [
        {
            "content": '{"result": {"value": "ok", "metadata": {"error": "historical warning from an earlier attempt"}}}'
        }
    ]

    with (
        patch(
            "app.services.agent_runner.safety_ingress",
            new_callable=AsyncMock,
            return_value={"safe": True, "reason": "ok"},
        ),
        patch(
            "app.services.agent_runner.safety_egress",
            new_callable=AsyncMock,
            return_value={"safe": True, "reason": "ok"},
        ),
        patch(
            "app.services.agent_runner.chat_completion",
            new_callable=AsyncMock,
            side_effect=scripted_llm_turns,
        ),
        patch(
            "app.services.agent_runner.execute",
            new_callable=AsyncMock,
            side_effect=scripted_tool_results,
        ),
        patch(
            "app.services.agent_runner.openai_schemas",
            return_value=[{"type": "function"}],
        ),
        patch(
            "app.services.agent_runner.model_supports_tools",
            return_value=True,
        ),
        patch("app.services.agent_runner.schedule_extraction"),
        patch("app.services.agent_runner.schedule_trace_capture") as trace_mock,
    ):
        await run_agent(db, agent, messages)

        payload = trace_mock.call_args.kwargs["payload"]
        assert payload["tool_error_count"] == 0
        assert len(payload["tool_calls"]) == 1
        assert payload["tool_calls"][0]["is_error"] is False
