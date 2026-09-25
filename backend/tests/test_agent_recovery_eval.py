import pytest

@pytest.mark.asyncio
async def test_successful_tool_call(mock_agent_runner):
    llm_turns = [
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "I found expected data.", "tool_calls": None},
    ]
    tool_results = [{"result": "expected data"}]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"
    assert "expected data" in final_text.lower()
    assert payload["tool_calls"][0]["arguments"]["query"] == "data"

@pytest.mark.asyncio
async def test_temporary_failure(mock_agent_runner):
    llm_turns = [
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data_retry"}}]},
        {"content": "I found expected data after retrying.", "tool_calls": None},
    ]
    tool_results = [
        {"error": "temporary glitch"},
        {"result": "expected data"},
    ]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 1
    assert len(payload["tool_calls"]) == 2
    assert payload["tool_calls"][0]["is_error"] is True
    assert payload["tool_calls"][1]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"
    assert payload["tool_calls"][0]["arguments"]["query"] == "data"
    assert payload["tool_calls"][1]["arguments"]["query"] == "data_retry"
    assert "expected data" in final_text.lower()

@pytest.mark.asyncio
async def test_persistent_failure(mock_agent_runner):
    llm_turns = [
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "I am unable to complete the task.", "tool_calls": None},
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
    assert all(call["is_error"] for call in payload["tool_calls"])
    assert "unable to complete" in final_text.lower()
    assert "expected data" not in final_text.lower()

@pytest.mark.asyncio
async def test_unexpected_tool_result(mock_agent_runner):
    llm_turns = [
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "The returned data was unusable.", "tool_calls": None},
    ]
    tool_results = [{"result": None}]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"
    assert "unusable" in final_text.lower()
    assert "expected data" not in final_text.lower()

@pytest.mark.asyncio
async def test_incidental_nested_error_key(mock_agent_runner):
    llm_turns = [
        {"content": "", "tool_calls": [{"name": "search", "arguments": {"query": "data"}}]},
        {"content": "Result processed successfully with value ok.", "tool_calls": None},
    ]
    tool_results = [
        {"result": {"value": "ok", "metadata": {"error": "historical warning"}}}
    ]

    final_text, payload = await mock_agent_runner(llm_turns, tool_results)

    assert payload["tool_error_count"] == 0
    assert len(payload["tool_calls"]) == 1
    assert payload["tool_calls"][0]["is_error"] is False
    assert payload["outcome"] == "completed_with_tools"
    assert "value ok" in final_text.lower()
