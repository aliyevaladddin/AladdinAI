"""SQL query execution tool for agents and users."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from app.tools.base import ToolContext, tool


def validate_sql_query(query: str, read_only: bool = True) -> tuple[bool, str]:
    """
    Validate SQL query for safety.

    Returns:
        (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"

    # Limit query length to prevent ReDoS attacks
    if len(query) > 10000:
        return False, "Query too long (max 10000 characters)"

    # Strip comments to prevent bypasses - simple string operations
    # Remove line comments (everything after --)
    lines = query.split('\n')
    cleaned_lines = []
    for line in lines:
        if '--' in line:
            line = line[:line.index('--')]
        cleaned_lines.append(line)
    query_clean = '\n'.join(cleaned_lines).strip()

    # Block multiple statements (semicolons not at end)
    semicolons = [i for i, c in enumerate(query_clean) if c == ';']
    if semicolons:
        # Only allow single trailing semicolon
        if len(semicolons) > 1 or semicolons[0] != len(query_clean) - 1:
            return False, "Multiple statements not allowed"

    query_upper = query_clean.upper()

    if read_only:
        # Only allow SELECT and WITH (CTE)
        if not query_upper.strip().startswith(("SELECT", "WITH")):
            return False, "Only SELECT queries allowed in read-only mode"

        # Block dangerous keywords even in SELECT
        dangerous_patterns = [
            r'\bPG_SLEEP\b',
            r'\bPG_READ_FILE\b',
            r'\bLO_IMPORT\b',
            r'\bLO_EXPORT\b',
            r'\bCOPY\b',
            r'\bINTO\s+OUTFILE\b',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                return False, "Forbidden function/keyword detected"
    else:
        # Block destructive operations
        destructive = re.search(r'\b(DROP|TRUNCATE|ALTER)\b', query_upper)
        if destructive:
            return False, f"Operation not allowed: {destructive.group(1)}"

    return True, ""


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
async def execute_sql_query(
    ctx: ToolContext,
    query: str,
    read_only: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Execute SQL query against the Postgres database.

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
    # Validate
    is_valid, error = validate_sql_query(query, read_only)
    if not is_valid:
        return {
            "success": False,
            "error": error,
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    # Enforce limit
    limit = min(max(1, limit), 1000)

    # Add LIMIT if not present (for SELECT queries)
    # Strip comments before checking - simple string operations
    lines = query.split('\n')
    cleaned_lines = []
    for line in lines:
        if '--' in line:
            line = line[:line.index('--')]
        cleaned_lines.append(line)
    query_clean = '\n'.join(cleaned_lines).strip()

    if read_only and not re.search(r'\bLIMIT\b', query_clean, re.IGNORECASE):
        # Remove trailing semicolon and comments, add LIMIT, restore semicolon
        query_trimmed = query.rstrip().rstrip(';').rstrip()
        query = f"{query_trimmed} LIMIT {limit};"

    # Execute
    try:
        result = await ctx.db.execute(text(query))

        # Check if query returns rows
        if result.returns_rows:
            rows = result.fetchall()
            columns = list(result.keys())

            # Convert rows to dicts
            rows_dict = [dict(zip(columns, row)) for row in rows]

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
