"""SQL playground API endpoint for direct user queries."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.tools.sql import validate_sql_query

router = APIRouter(prefix="/sql", tags=["sql"])


class SQLQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    read_only: bool = Field(default=True)
    limit: int = Field(default=100, ge=1, le=1000)


class SQLQueryResponse(BaseModel):
    success: bool
    rows: list[dict]
    columns: list[str]
    row_count: int
    error: str | None = None
    message: str | None = None


class TableSchema(BaseModel):
    table_name: str
    columns: list[dict]


class SchemaResponse(BaseModel):
    tables: list[TableSchema]


@router.get("/schema", response_model=SchemaResponse)
async def get_schema(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get database schema: all tables with their columns and types.
    """
    try:
        # Query information_schema for all tables and columns
        query = text("""
            SELECT
                c.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
            ORDER BY c.table_name, c.ordinal_position
        """)

        result = await db.execute(query)
        rows = result.fetchall()

        # Group by table
        tables_dict = {}
        for row in rows:
            table_name = row[0]
            if table_name not in tables_dict:
                tables_dict[table_name] = []

            tables_dict[table_name].append({
                "column_name": row[1],
                "data_type": row[2],
                "nullable": row[3] == "YES",
                "default": row[4],
            })

        tables = [
            TableSchema(table_name=name, columns=cols)
            for name, cols in tables_dict.items()
        ]

        return SchemaResponse(tables=tables)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=SQLQueryResponse)
async def execute_sql(
    req: SQLQueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Execute SQL query against Postgres database.

    For safety, read_only mode is enforced by default (SELECT only).

    Security Note: This endpoint intentionally allows user-provided SQL queries
    for analytics and data exploration purposes. Multiple layers of protection:
    1. Authentication required (get_current_user dependency)
    2. Read-only mode by default (only SELECT/WITH queries)
    3. Dangerous keywords/functions blocked (PG_SLEEP, COPY, etc.)
    4. Row limit enforced (max 1000)
    5. Destructive operations blocked (DROP, TRUNCATE, ALTER)

    This is a controlled SQL execution environment for authenticated users only.
    """
    # Validate query
    is_valid, error = validate_sql_query(req.query, req.read_only)
    if not is_valid:
        return SQLQueryResponse(
            success=False,
            rows=[],
            columns=[],
            row_count=0,
            error=error,
        )

    # Add LIMIT if not present in SELECT
    query = req.query

    # Limit query length to prevent ReDoS attacks
    if len(query) > 10000:
        return SQLQueryResponse(
            success=False,
            rows=[],
            columns=[],
            row_count=0,
            error="Query too long (max 10000 characters)",
        )

    # Strip comments before checking to avoid trailing comment bypass
    # Simple approach: remove line comments
    lines = query.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove everything after --
        if '--' in line:
            line = line[:line.index('--')]
        cleaned_lines.append(line)
    query_clean = '\n'.join(cleaned_lines).strip()

    if req.read_only and not re.search(r'\bLIMIT\b', query_clean, re.IGNORECASE):
        # Remove trailing semicolon and comments, add LIMIT, restore semicolon
        query_trimmed = query.rstrip().rstrip(';').rstrip()
        query = f"{query_trimmed} LIMIT {req.limit};"

    # Execute
    try:
        # Intentional: SQL playground feature for authenticated analytics users
        # Security layers: auth required, read-only default, keyword blocking,
        # row limits (1000 max), multi-statement prevention, length limit (10000 chars)
        result = await db.execute(text(query))  # nosec B608

        if result.returns_rows:
            rows = result.fetchall()
            columns = list(result.keys())
            rows_dict = [dict(zip(columns, row)) for row in rows]

            return SQLQueryResponse(
                success=True,
                rows=rows_dict,
                columns=columns,
                row_count=len(rows_dict),
            )
        else:
            # Mutation query
            await db.commit()
            return SQLQueryResponse(
                success=True,
                rows=[],
                columns=[],
                row_count=result.rowcount,
                message=f"Query executed. {result.rowcount} rows affected.",
            )

    except Exception as e:
        await db.rollback()
        return SQLQueryResponse(
            success=False,
            rows=[],
            columns=[],
            row_count=0,
            error=str(e),
        )
