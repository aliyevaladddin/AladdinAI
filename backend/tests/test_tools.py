"""Test tool registry and execution."""
import pytest
from app.tools.base import REGISTRY, Tool, ToolContext, execute, openai_schemas


def test_registry_contains_tools():
    """Test that tools are registered in REGISTRY."""
    assert len(REGISTRY) > 0
    # Check some known tools exist
    assert "recall" in REGISTRY
    assert "remember" in REGISTRY
    assert "forget" in REGISTRY


def test_tool_structure():
    """Test that registered tools have correct structure."""
    recall_tool = REGISTRY["recall"]
    assert isinstance(recall_tool, Tool)
    assert recall_tool.name == "recall"
    assert recall_tool.description != ""
    assert isinstance(recall_tool.parameters, dict)
    assert "type" in recall_tool.parameters
    assert "properties" in recall_tool.parameters


def test_openai_schema():
    """Test OpenAI-compatible schema generation."""
    recall_tool = REGISTRY["recall"]
    schema = recall_tool.openai_schema()

    assert schema["type"] == "function"
    assert "function" in schema
    assert schema["function"]["name"] == "recall"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]


def test_openai_schemas_all():
    """Test getting all tool schemas."""
    schemas = openai_schemas()
    assert len(schemas) > 0
    assert all(s["type"] == "function" for s in schemas)
    assert all("function" in s for s in schemas)


def test_openai_schemas_filtered():
    """Test getting filtered tool schemas."""
    allowed = ["recall", "remember"]
    schemas = openai_schemas(allowed)
    assert len(schemas) == 2
    names = {s["function"]["name"] for s in schemas}
    assert names == {"recall", "remember"}


def test_openai_schemas_with_invalid_tool():
    """Test filtering schemas with non-existent tool name."""
    allowed = ["recall", "nonexistent_tool"]
    schemas = openai_schemas(allowed)
    # Should only return existing tools
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "recall"


@pytest.mark.asyncio
async def test_execute_recall_tool(db_session, test_user):
    """Test executing recall tool through the registry."""
    ctx = ToolContext(
        db=db_session,
        user_id=test_user["user_id"],
        agent_id=None
    )

    # Execute recall - should not crash even if MongoDB is not available
    result = await execute("recall", {"query": "test query", "limit": 5}, ctx)
    assert isinstance(result, dict)
    assert "results" in result or "error" in result


@pytest.mark.asyncio
async def test_execute_nonexistent_tool(db_session):
    """Test executing a tool that doesn't exist raises KeyError."""
    ctx = ToolContext(db=db_session, user_id=1, agent_id=None)

    with pytest.raises(KeyError):
        await execute("nonexistent_tool", {}, ctx)


def test_tool_parameters_have_required_fields():
    """Test that tool parameters follow JSON schema conventions."""
    for tool_name, tool in REGISTRY.items():
        params = tool.parameters
        # Some tools may have non-standard parameter structures
        if "type" not in params:
            # Should at least have properties dict
            assert isinstance(params, dict), f"{tool_name}: parameters should be a dict"
            continue
        assert params["type"] == "object", f"{tool_name}: parameters type should be 'object'"
        assert "properties" in params, f"{tool_name}: parameters missing 'properties'"


def test_recall_tool_parameters():
    """Test recall tool has correct parameter structure."""
    recall = REGISTRY["recall"]
    params = recall.parameters

    assert "query" in params["properties"]
    assert params["properties"]["query"]["type"] == "string"

    assert "scope" in params["properties"]
    assert params["properties"]["scope"]["type"] == "string"
    assert "enum" in params["properties"]["scope"]

    assert "limit" in params["properties"]
    assert params["properties"]["limit"]["type"] == "integer"

    assert "required" in params
    assert "query" in params["required"]


def test_remember_tool_parameters():
    """Test remember tool has correct parameter structure."""
    remember = REGISTRY["remember"]
    params = remember.parameters

    assert "fact" in params["properties"]
    assert params["properties"]["fact"]["type"] == "string"

    assert "visibility" in params["properties"]
    assert params["properties"]["visibility"]["type"] == "string"
    assert set(params["properties"]["visibility"]["enum"]) == {"private", "shared"}

    assert "tags" in params["properties"]
    assert params["properties"]["tags"]["type"] == "array"

    assert "required" in params
    assert "fact" in params["required"]


def test_forget_tool_parameters():
    """Test forget tool has correct parameter structure."""
    forget = REGISTRY["forget"]
    params = forget.parameters

    assert "memory_id" in params["properties"]
    assert params["properties"]["memory_id"]["type"] == "string"

    assert "required" in params
    assert "memory_id" in params["required"]


def test_tool_context_structure():
    """Test ToolContext dataclass structure."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from unittest.mock import MagicMock

    mock_db = MagicMock(spec=AsyncSession)
    ctx = ToolContext(db=mock_db, user_id=123, agent_id=456, session_id=789)

    assert ctx.db == mock_db
    assert ctx.user_id == 123
    assert ctx.agent_id == 456
    assert ctx.session_id == 789
    assert isinstance(ctx.extra, dict)


def test_tool_context_with_extra():
    """Test ToolContext with extra metadata."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from unittest.mock import MagicMock

    mock_db = MagicMock(spec=AsyncSession)
    extra = {"channel_type": "telegram", "channel_id": "123"}
    ctx = ToolContext(db=mock_db, user_id=1, extra=extra)

    assert ctx.extra["channel_type"] == "telegram"
    assert ctx.extra["channel_id"] == "123"


def test_all_registered_tools_are_callable():
    """Test that all registered tools are async callables."""
    import inspect

    for tool_name, tool in REGISTRY.items():
        assert callable(tool.func), f"{tool_name} func is not callable"
        assert inspect.iscoroutinefunction(tool.func), f"{tool_name} func is not async"
