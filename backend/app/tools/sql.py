# NOTICE: This file is protected under RCF-PL
"""SQL query execution tool for agents and users."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from app.tools.base import ToolContext, tool

DANGEROUS_MUTATIONS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE|GRANT|REVOKE|MERGE|CALL|DO|EXECUTE|LOCK|UPSERT)\b",
    re.IGNORECASE,
)

DANGEROUS_FUNCTIONS = re.compile(
    r"\b(PG_SLEEP|PG_READ_FILE|PG_READ_BINARY_FILE|PG_WRITE_FILE|PG_WRITE_BINARY_FILE|LO_IMPORT|LO_EXPORT|COPY|DBLINK)\b|\bINTO\s+(OUTFILE|DUMPFILE)\b",
    re.IGNORECASE,
)

SENSITIVE_CATALOGS_COLUMNS = re.compile(
    r"\b(PG_SHADOW|PG_AUTHID)\b",
    re.IGNORECASE,
)

REDACTED_COLUMNS = {
    "password_hash",
    "hashed_password",
    "webhook_secret",
}


# [RCF:PROTECTED]
def _sanitize_sql(query: str) -> tuple[str | None, str | None, str | None]:
    """Single-pass O(N) lexical scanner separating comments, strings, and code.

    Returns:
        (executable_sql, code_only_sql, error_message)
        - executable_sql: comments stripped, real strings and dollar-quotes preserved.
        - code_only_sql: comments stripped, string literals replaced with spaces so
          contained keywords or semicolons do not produce false positives.
        - error_message: str if malformed (unclosed comments/literals), else None.
    """
    if not query or not query.strip():
        return None, None, "Query cannot be empty"

    if len(query) > 10000:
        return None, None, "Query too long (max 10000 characters)"

    NORMAL = 0
    IN_LINE_COMMENT = 1
    IN_BLOCK_COMMENT = 2
    IN_STRING = 3
    IN_DOLLAR = 4

    state = NORMAL
    comment_depth = 0
    dollar_tag = ""
    i = 0
    n = len(query)

    exec_chars: list[str] = []
    code_chars: list[str] = []

    while i < n:
        c = query[i]

        if state == NORMAL:
            # Line comment: --
            if c == "-" and i + 1 < n and query[i + 1] == "-":
                state = IN_LINE_COMMENT
                i += 2
                continue
            # Block comment: /*
            elif c == "/" and i + 1 < n and query[i + 1] == "*":
                state = IN_BLOCK_COMMENT
                comment_depth = 1
                i += 2
                continue
            # Standard single-quoted string: '
            elif c == "'":
                state = IN_STRING
                exec_chars.append(c)
                code_chars.append(c)
                i += 1
                continue
            # Dollar-quoted string: $tag$ or $$
            elif c == "$":
                tag_end = query.find("$", i + 1)
                if tag_end != -1:
                    candidate_tag = query[i + 1 : tag_end]
                    if candidate_tag == "" or candidate_tag.isidentifier():
                        dollar_tag = query[i : tag_end + 1]
                        state = IN_DOLLAR
                        exec_chars.extend(dollar_tag)
                        code_chars.extend(dollar_tag)
                        i = tag_end + 1
                        continue
                exec_chars.append(c)
                code_chars.append(c)
                i += 1
                continue
            else:
                exec_chars.append(c)
                code_chars.append(c)
                i += 1
                continue

        elif state == IN_LINE_COMMENT:
            if c == "\n":
                state = NORMAL
                exec_chars.append("\n")
                code_chars.append("\n")
            i += 1
            continue

        elif state == IN_BLOCK_COMMENT:
            if c == "/" and i + 1 < n and query[i + 1] == "*":
                comment_depth += 1
                i += 2
                continue
            elif c == "*" and i + 1 < n and query[i + 1] == "/":
                comment_depth -= 1
                i += 2
                if comment_depth == 0:
                    state = NORMAL
                    exec_chars.append(" ")
                    code_chars.append(" ")
                continue
            else:
                i += 1
                continue

        elif state == IN_STRING:
            exec_chars.append(c)
            if c == "'":
                # Check for escaped single quote: ''
                if i + 1 < n and query[i + 1] == "'":
                    exec_chars.append(query[i + 1])
                    code_chars.extend([" ", " "])
                    i += 2
                    continue
                else:
                    code_chars.append(c)
                    state = NORMAL
                    i += 1
                    continue
            elif c == "\\" and i + 1 < n:
                # C-style backslash escape
                exec_chars.append(query[i + 1])
                code_chars.extend([" ", " "])
                i += 2
                continue
            else:
                code_chars.append(" ")
                i += 1
                continue

        elif state == IN_DOLLAR:
            if query.startswith(dollar_tag, i):
                exec_chars.extend(dollar_tag)
                code_chars.extend(dollar_tag)
                i += len(dollar_tag)
                state = NORMAL
                dollar_tag = ""
                continue
            else:
                exec_chars.append(c)
                code_chars.append(" ")
                i += 1
                continue

    if state == IN_BLOCK_COMMENT:
        return None, None, "Unclosed block comment in SQL query"
    if state == IN_STRING:
        return None, None, "Unclosed string literal in SQL query"
    if state == IN_DOLLAR:
        return None, None, "Unclosed dollar-quoted string in SQL query"

    return "".join(exec_chars).strip(), "".join(code_chars).strip(), None


# [RCF:PROTECTED]
def validate_sql_query(query: str, read_only: bool = True) -> tuple[bool, str]:
    """Validate SQL query for safety.

    Returns:
        (is_valid, error_message)
    """
    executable_sql, code_only_sql, error = _sanitize_sql(query)
    if error:
        return False, error

    assert code_only_sql is not None

    # Block multiple statements (semicolons not at end of code)
    semicolons = [i for i, c in enumerate(code_only_sql) if c == ";"]
    if semicolons:
        if len(semicolons) > 1 or semicolons[0] != len(code_only_sql) - 1:
            return False, "Multiple statements not allowed"

    trimmed_code = code_only_sql.rstrip(";").strip()
    if not trimmed_code:
        return False, "Query cannot be empty"

    if read_only:
        # Query must start with SELECT or WITH (CTE)
        if not re.match(r"^(SELECT|WITH)\b", trimmed_code, re.IGNORECASE):
            return False, "Only SELECT queries allowed in read-only mode"

        # Block any data-modifying or DDL keywords across the entire query
        mutation_match = DANGEROUS_MUTATIONS.search(trimmed_code)
        if mutation_match:
            return False, f"Forbidden keyword detected in read-only mode: {mutation_match.group(1).upper()}"

        # Block dangerous server-side functions/commands
        function_match = DANGEROUS_FUNCTIONS.search(trimmed_code)
        if function_match:
            return False, "Forbidden function/keyword detected"

        # Block access to sensitive system catalogs
        catalog_match = SENSITIVE_CATALOGS_COLUMNS.search(trimmed_code)
        if catalog_match:
            return False, f"Access to sensitive catalog or column forbidden: {catalog_match.group(1)}"
    else:
        # In write mode, block destructive DDL operations
        destructive = re.search(r"\b(DROP|TRUNCATE|ALTER)\b", trimmed_code, re.IGNORECASE)
        if destructive:
            return False, f"Operation not allowed: {destructive.group(1).upper()}"

    return True, ""


# [RCF:PROTECTED]
@tool(
    name="execute_sql_query",
    description=(
        "Execute SQL query against the Postgres database for analytics, reporting, and data exploration. "
        "Examples: 'Show me top 5 agents by message count', 'List all active providers', 'Count memories per agent'. "
        "Default read-only mode allows SELECT queries only."
    ),
    parameters={
        "query": {"type": "string", "description": "SQL query to execute (SELECT only by default)"},
        "read_only": {"type": "boolean", "description": "If True, only SELECT allowed. If False, INSERT/UPDATE/DELETE allowed.", "default": True},
        "limit": {"type": "integer", "description": "Maximum rows to return (default 100, max 1000)", "default": 100},
    },
)
# [RCF:PROTECTED]
async def execute_sql_query(
    ctx: ToolContext,
    query: str,
    read_only: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """Execute SQL query against the Postgres database.

    Use this for analytics, reporting, and data exploration.
    Examples:
    - "Show me top 5 agents by message count in last 24 hours"
    - "List all active providers"
    - "Count total memories per agent"

    Args:
        query: SQL query to execute (SELECT only by default)
        read_only: If True, only SELECT allowed. If False, INSERT/UPDATE/DELETE allowed.
        limit: Maximum rows to return (default 100, max 1000)

    Returns:
        {
            "rows": [...],
            "columns": ["col1", "col2", ...],
            "row_count": 10,
            "success": true
        }
    """
    executable_sql, code_only_sql, error = _sanitize_sql(query)
    if error:
        return {
            "success": False,
            "error": error,
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    is_valid, validation_error = validate_sql_query(query, read_only)
    if not is_valid:
        return {
            "success": False,
            "error": validation_error,
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    assert executable_sql is not None
    assert code_only_sql is not None

    # Enforce limit
    limit = min(max(1, limit), 1000)

    # Add LIMIT if not present (for SELECT queries)
    if read_only and not re.search(r"\bLIMIT\b", code_only_sql, re.IGNORECASE):
        query_trimmed = executable_sql.rstrip().rstrip(";").rstrip()
        executable_sql = f"{query_trimmed} LIMIT {limit};"

    # Execute
    try:
        if read_only:
            try:
                bind = ctx.db.get_bind()
                if bind and getattr(bind.dialect, "name", "") == "postgresql":
                    await ctx.db.execute(text("SET LOCAL default_transaction_read_only = 'on'"))
            except Exception:
                pass

        result = await ctx.db.execute(text(executable_sql))

        # Check if query returns rows
        if result.returns_rows:
            rows = result.fetchall()
            columns = list(result.keys())

            # Convert rows to dicts and redact sensitive fields
            rows_dict = [
                {
                    k: ("[REDACTED]" if k.lower() in REDACTED_COLUMNS else v)
                    for k, v in dict(zip(columns, row)).items()
                }
                for row in rows
            ]

            return {
                "success": True,
                "rows": rows_dict,
                "columns": columns,
                "row_count": len(rows_dict),
            }
        else:
            # INSERT/UPDATE/DELETE
            await ctx.db.commit()
            return {
                "success": True,
                "rows": [],
                "columns": [],
                "row_count": result.rowcount,
                "message": f"Query executed successfully. {result.rowcount} rows affected.",
            }

    except Exception as e:
        await ctx.db.rollback()
        return {
            "success": False,
            "error": str(e),
            "rows": [],
            "columns": [],
            "row_count": 0,
        }
