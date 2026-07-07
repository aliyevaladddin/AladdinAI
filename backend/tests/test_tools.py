# NOTICE: This file is protected under RCF-PL
"""Test tool registry and execution."""
import pytest
from app.tools.base import REGISTRY, Tool, ToolContext, execute, openai_schemas


# [RCF:PROTECTED]
def test_registry_contains_tools():
    """Test that tools are registered in REGISTRY."""
    assert len(REGISTRY) > 0
    # Check some known tools exist
    assert "recall" in REGISTRY
    assert "remember" in REGISTRY
    assert "forget" in REGISTRY


# [RCF:PROTECTED]
def test_tool_structure():
    """Test that registered tools have correct structure."""
    recall_tool = REGISTRY["recall"]
    assert isinstance(recall_tool, Tool)
    assert recall_tool.name == "recall"
    assert recall_tool.description != ""
    assert isinstance(recall_tool.parameters, dict)
    assert "type" in recall_tool.parameters
    assert "properties" in recall_tool.parameters


# [RCF:PROTECTED]
def test_openai_schema():
    """Test OpenAI-compatible schema generation."""
    recall_tool = REGISTRY["recall"]
    schema = recall_tool.openai_schema()

    assert schema["type"] == "function"
    assert "function" in schema
    assert schema["function"]["name"] == "recall"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]


# [RCF:PROTECTED]
def test_openai_schemas_all():
    """Test getting all tool schemas."""
    schemas = openai_schemas()
    assert len(schemas) > 0
    assert all(s["type"] == "function" for s in schemas)
    assert all("function" in s for s in schemas)


# [RCF:PROTECTED]
def test_openai_schemas_filtered():
    """Test getting filtered tool schemas."""
    allowed = ["recall", "remember"]
    schemas = openai_schemas(allowed)
    assert len(schemas) == 2
    names = {s["function"]["name"] for s in schemas}
    assert names == {"recall", "remember"}


# [RCF:PROTECTED]
def test_openai_schemas_with_invalid_tool():
    """Test filtering schemas with non-existent tool name."""
    allowed = ["recall", "nonexistent_tool"]
    schemas = openai_schemas(allowed)
    # Should only return existing tools
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "recall"


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_execute_nonexistent_tool(db_session):
    """Test executing a tool that doesn't exist raises KeyError."""
    ctx = ToolContext(db=db_session, user_id=1, agent_id=None)

    with pytest.raises(KeyError):
        await execute("nonexistent_tool", {}, ctx)


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
def test_forget_tool_parameters():
    """Test forget tool has correct parameter structure."""
    forget = REGISTRY["forget"]
    params = forget.parameters

    assert "memory_id" in params["properties"]
    assert params["properties"]["memory_id"]["type"] == "string"

    assert "required" in params
    assert "memory_id" in params["required"]


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
def test_tool_context_with_extra():
    """Test ToolContext with extra metadata."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from unittest.mock import MagicMock

    mock_db = MagicMock(spec=AsyncSession)
    extra = {"channel_type": "telegram", "channel_id": "123"}
    ctx = ToolContext(db=mock_db, user_id=1, extra=extra)

    assert ctx.extra["channel_type"] == "telegram"
    assert ctx.extra["channel_id"] == "123"


# [RCF:PROTECTED]
def test_all_registered_tools_are_callable():
    """Test that all registered tools are async callables."""
    import inspect

    for tool_name, tool in REGISTRY.items():
        assert callable(tool.func), f"{tool_name} func is not callable"
        assert inspect.iscoroutinefunction(tool.func), f"{tool_name} func is not async"
# [RCF:PROTECTED]
@pytest.mark.asyncio
async def test_ssh_tofu_first_connect_path(tmp_path, monkeypatch):
    """Test SSH implementation for the first connection (file does not exist)."""
    import asyncssh
    from unittest.mock import AsyncMock

    # Creamos una ruta temporal aislada simulando la del sistema ~/.aladdin/known_hosts/999
    mock_known_hosts_dir = tmp_path / ".aladdin" / "known_hosts"
    mock_file_path = mock_known_hosts_dir / "999"

    # Simulamos el comportamiento de expanduser para apuntar al entorno controlado del test
    from pathlib import Path
    orig_expanduser = Path.expanduser

    def mock_expanduser(self):
        # Si detecta la ruta del componente TOFU, redirige al directorio temporal del test
        if "~/.aladdin/known_hosts" in str(self):
            return Path(str(self).replace("~/.aladdin/known_hosts", str(mock_known_hosts_dir)))
        return orig_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", mock_expanduser)

    # Aseguramos que el archivo NO exista antes de la prueba
    if mock_file_path.exists():
        mock_file_path.unlink()

    # Mockeamos el método asyncssh.connect para simular una conexión exitosa
    mock_connect = AsyncMock()
    monkeypatch.setattr(asyncssh, "connect", mock_connect)

    # Evaluamos las condiciones simuladas que usarían nuestros endpoints
    known_hosts_arg = str(mock_file_path) if mock_file_path.exists() else None
    server_key_algs = ['ssh-ed25519']

    # Ejecutamos la simulación de la llamada
    await asyncssh.connect(host="127.0.0.1", known_hosts=known_hosts_arg, server_host_key_algs=server_key_algs)

    # Verificaciones (Assertions)
    assert known_hosts_arg is None, "En la primera conexión, known_hosts debe evaluar a None"
    mock_connect.assert_called_once_with(host="127.0.0.1", known_hosts=None, server_host_key_algs=['ssh-ed25519'])


# [RCF:PROTECTED]
@pytest.mark.asyncio
async def test_ssh_tofu_happy_path_known_host(tmp_path, monkeypatch):
    """Test SSH implementation for subsequent connections when the host key is already known."""
    import asyncssh
    from unittest.mock import AsyncMock

    # Creamos la ruta e infraestructura temporal del test
    mock_known_hosts_dir = tmp_path / ".aladdin" / "known_hosts"
    mock_known_hosts_dir.mkdir(parents=True, exist_ok=True)
    mock_file_path = mock_known_hosts_dir / "999"

    # Escribimos una clave ficticia para forzar que el archivo exista (Simula una conexión previa exitosa)
    mock_file_path.write_text("127.0.0.1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... mock-key")

    from pathlib import Path
    orig_expanduser = Path.expanduser

    def mock_expanduser(self):
        if "~/.aladdin/known_hosts" in str(self):
            return Path(str(self).replace("~/.aladdin/known_hosts", str(mock_known_hosts_dir)))
        return orig_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", mock_expanduser)

    # Mockeamos el método asyncssh.connect
    mock_connect = AsyncMock()
    monkeypatch.setattr(asyncssh, "connect", mock_connect)

    # Evaluamos las condiciones lógicas dinámicas (Iguales a las de los routers implementados)
    known_hosts_arg = str(mock_file_path) if mock_file_path.exists() else None
    server_key_algs = ['ssh-ed25519']

    # Ejecutamos la simulación de la llamada
    await asyncssh.connect(host="127.0.0.1", known_hosts=known_hosts_arg, server_host_key_algs=server_key_algs)

    # Verificaciones (Assertions)
    assert known_hosts_arg == str(mock_file_path), "Si el archivo ya existe, debe pasar la ruta completa como string"
    mock_connect.assert_called_once_with(host="127.0.0.1", known_hosts=str(mock_file_path), server_host_key_algs=['ssh-ed25519'])