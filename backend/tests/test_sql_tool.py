# NOTICE: This file is protected under RCF-PL
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.tools.base import ToolContext
from app.tools.sql import _sanitize_sql, execute_sql_query, validate_sql_query


def test_sanitize_sql_comments_and_strings():
    query = """
    -- This is a line comment
    SELECT id, name /* inline block comment */
    FROM users /* multi-line
    block comment */
    WHERE status = 'DELETED' AND note = 'Contains ; semicolon'
    """
    exec_sql, code_sql, err = _sanitize_sql(query)
    assert err is None
    assert "inline block comment" not in exec_sql
    assert "line comment" not in exec_sql
    assert "status = 'DELETED'" in exec_sql
    assert "status = '" in code_sql
    # Code-only SQL should have spaces inside literal so DELETED keyword is hidden
    assert "DELETED" not in code_sql


def test_sanitize_sql_dollar_quotes():
    query = "SELECT $$DELETE FROM users$$ AS code_sample FROM agents;"
    exec_sql, code_sql, err = _sanitize_sql(query)
    assert err is None
    assert "$$DELETE FROM users$$" in exec_sql
    assert "DELETE" not in code_sql


def test_sanitize_sql_unclosed_comment_or_string():
    _, _, err1 = _sanitize_sql("SELECT * FROM users /* unclosed comment")
    assert err1 == "Unclosed block comment in SQL query"

    _, _, err2 = _sanitize_sql("SELECT * FROM users WHERE name = 'unclosed string")
    assert err2 == "Unclosed string literal in SQL query"

    _, _, err3 = _sanitize_sql("SELECT $tag$ unclosed dollar quote")
    assert err3 == "Unclosed dollar-quoted string in SQL query"


def test_validate_sql_query_valid_select():
    valid, err = validate_sql_query("SELECT id, name FROM users WHERE is_active = true;")
    assert valid is True
    assert err == ""


def test_validate_sql_query_valid_cte():
    query = """
    WITH active_agents AS (
        SELECT id, name FROM agents WHERE status = 'active'
    )
    SELECT * FROM active_agents;
    """
    valid, err = validate_sql_query(query)
    assert valid is True
    assert err == ""


def test_validate_sql_query_blocks_cte_mutations():
    cte_delete = "WITH deleted AS (DELETE FROM users RETURNING *) SELECT * FROM deleted;"
    valid, err = validate_sql_query(cte_delete)
    assert valid is False
    assert "DELETE" in err

    cte_update = "WITH updated AS (UPDATE users SET name = 'admin' RETURNING *) SELECT * FROM updated;"
    valid, err = validate_sql_query(cte_update)
    assert valid is False
    assert "UPDATE" in err

    cte_insert = "WITH inserted AS (INSERT INTO users (email) VALUES ('x') RETURNING *) SELECT * FROM inserted;"
    valid, err = validate_sql_query(cte_insert)
    assert valid is False
    assert "INSERT" in err


def test_validate_sql_query_keywords_in_literals_allowed():
    query = "SELECT id, status FROM agents WHERE status = 'DELETED' OR description = 'DROP TABLE';"
    valid, err = validate_sql_query(query)
    assert valid is True
    assert err == ""


def test_validate_sql_query_semicolon_in_literal_allowed():
    query = "SELECT 'one;two' AS pair, 'three;four' AS next_pair;"
    valid, err = validate_sql_query(query)
    assert valid is True
    assert err == ""


def test_validate_sql_query_blocks_multistatements():
    query = "SELECT 1; DROP TABLE users;"
    valid, err = validate_sql_query(query)
    assert valid is False
    assert "Multiple statements not allowed" in err


def test_validate_sql_query_blocks_dangerous_functions_and_catalogs():
    queries = [
        "SELECT PG_SLEEP(10);",
        "SELECT * FROM pg_shadow;",
        "SELECT * FROM pg_authid;",
        "SELECT PG_READ_FILE('/etc/passwd');",
        "COPY users TO '/tmp/dump';",
    ]
    for q in queries:
        valid, err = validate_sql_query(q)
        assert valid is False, f"Query '{q}' should have been blocked"


def test_validate_sql_query_write_mode():
    valid, err = validate_sql_query("INSERT INTO logs (msg) VALUES ('test');", read_only=False)
    assert valid is True

    valid, err = validate_sql_query("DROP TABLE users;", read_only=False)
    assert valid is False
    assert "DROP" in err


@pytest.mark.asyncio
async def test_execute_sql_query_redaction():
    # Mock result with sensitive columns
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.keys.return_value = ["id", "email", "password_hash", "webhook_secret"]
    mock_result.fetchall.return_value = [
        (1, "user@example.com", "$2b$12$secret_hash", "sec_abc123"),
    ]

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.get_bind = MagicMock(return_value=MagicMock(dialect=MagicMock(name="sqlite")))

    ctx = ToolContext(agent_id=1, user_id=1, db=mock_db)
    res = await execute_sql_query(ctx, "SELECT id, email, password_hash, webhook_secret FROM users;")

    assert res["success"] is True
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["id"] == 1
    assert row["email"] == "user@example.com"
    assert row["password_hash"] == "[REDACTED]"
    assert row["webhook_secret"] == "[REDACTED]"
