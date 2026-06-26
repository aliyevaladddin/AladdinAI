# NOTICE: This file is protected under RCF-PL
"""
Excel Reader — Agent Tools

Three tools registered into the global REGISTRY:
  - excel_read          : summary + 5-row preview + numeric stats
  - excel_query         : filter rows by column value
  - excel_import_contacts : auto-detect columns (incl. Russian headers) → import to CRM

Files are read from local disk (the media/attachments directory used by the
existing attachment system). Pass the relative path returned by the upload
endpoint, e.g. "1234/report.xlsx".
"""
from __future__ import annotations

import io
import os
from typing import Any

import pandas as pd

from app.tools.base import ToolContext, tool

# Root of the local attachments store (same path as crm_activities.py uses)
_ATTACHMENTS_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "media", "attachments")
)


# ── Helper: load a DataFrame from a local attachment path ────────────────────

def _load_df(rel_path: str, sheet: str | None = None) -> tuple[pd.DataFrame | None, str | None]:
    """
    Load a DataFrame from a relative attachment path.
    Returns (df, error_message).  One of the two will always be None.
    """
    safe = os.path.realpath(os.path.join(_ATTACHMENTS_ROOT, rel_path))
    if not safe.startswith(_ATTACHMENTS_ROOT + os.sep):
        return None, "Invalid file path"
    if not os.path.isfile(safe):
        return None, f"File not found: {rel_path}"

    try:
        if safe.lower().endswith(".csv"):
            df = pd.read_csv(safe)
        else:
            kwargs: dict[str, Any] = {}
            if sheet:
                kwargs["sheet_name"] = sheet
            df = pd.read_excel(safe, **kwargs)
        return df, None
    except Exception as e:
        return None, f"Could not parse file: {e}"


def _safe_str(val: Any) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()


def _summarize_df(df: pd.DataFrame) -> dict[str, Any]:
    """Compact summary an LLM can reason over without token bloat."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    summary: dict[str, Any] = {
        "rows": len(df),
        "columns": df.columns.tolist(),
        "preview": df.head(5).fillna("").astype(str).to_dict(orient="records"),
    }
    if numeric_cols:
        stats = df[numeric_cols].describe().round(2)
        summary["numeric_summary"] = stats.to_dict()
    return summary


# ── Tool 1: Read & analyse ────────────────────────────────────────────────────

@tool(
    name="excel_read",
    description=(
        "Read an Excel (.xlsx / .xls) or CSV file from the attachments store and return "
        "a structured summary: column names, row count, a 5-row preview, and numeric stats. "
        "Use this when the user uploads a spreadsheet and wants analysis or insights."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Relative path to the uploaded file inside the attachments directory, "
                    "e.g. '42/contacts.xlsx' (activity_id/filename)."
                ),
            },
            "sheet": {
                "type": "string",
                "description": "Sheet name to read (optional; defaults to the first sheet).",
            },
        },
        "required": ["file_path"],
    },
)
async def excel_read(ctx: ToolContext, file_path: str, sheet: str | None = None) -> dict[str, Any]:
    df, error = _load_df(file_path, sheet)
    if error:
        return {"error": error}
    return _summarize_df(df)  # type: ignore[arg-type]


# ── Tool 2: Query / filter rows ───────────────────────────────────────────────

@tool(
    name="excel_query",
    description=(
        "Filter rows from an Excel or CSV file by a column value (case-insensitive substring match). "
        "Use when the user asks to search or filter data inside a spreadsheet. "
        "Example: 'show rows where Status is Closed' or 'find contacts from Acme Corp'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative attachment path, e.g. '42/data.xlsx'.",
            },
            "column": {"type": "string", "description": "Column name to filter on."},
            "value": {"type": "string", "description": "Value to match (case-insensitive substring)."},
            "sheet": {"type": "string", "description": "Sheet name (optional)."},
            "limit": {"type": "integer", "description": "Max rows to return (default 20, max 200)."},
        },
        "required": ["file_path", "column", "value"],
    },
)
async def excel_query(
    ctx: ToolContext,
    file_path: str,
    column: str,
    value: str,
    sheet: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    df, error = _load_df(file_path, sheet)
    if error:
        return {"error": error}

    if column not in df.columns:  # type: ignore[union-attr]
        return {"error": f"Column '{column}' not found. Available: {df.columns.tolist()}"}  # type: ignore[union-attr]

    limit = min(max(1, limit), 200)
    mask = df[column].astype(str).str.contains(value, case=False, na=False)  # type: ignore[index]
    filtered = df[mask].head(limit).fillna("").astype(str)  # type: ignore[index]
    return {
        "matched_rows": int(mask.sum()),
        "returned": len(filtered),
        "rows": filtered.to_dict(orient="records"),
    }


# ── Tool 3: Import Excel → CRM contacts ──────────────────────────────────────

@tool(
    name="excel_import_contacts",
    description=(
        "Parse an uploaded Excel file and import rows as CRM contacts. "
        "Columns are auto-detected from common header names including Russian headers "
        "(имя, почта, телефон, компания, теги, заметки). "
        "Use when the user says 'import this Excel to CRM' or 'add these contacts from the file'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative attachment path, e.g. '42/contacts.xlsx'.",
            },
            "sheet": {"type": "string", "description": "Sheet name (optional)."},
        },
        "required": ["file_path"],
    },
)
async def excel_import_contacts(
    ctx: ToolContext,
    file_path: str,
    sheet: str | None = None,
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models.contact import Contact

    df, error = _load_df(file_path, sheet)
    if error:
        return {"error": error}

    # Auto-detect column names (case-insensitive, EN + RU aliases)
    ALIASES: dict[str, list[str]] = {
        "name":    ["name", "full name", "fullname", "contact name", "имя", "полное имя"],
        "email":   ["email", "e-mail", "email address", "почта", "электронная почта"],
        "phone":   ["phone", "phone number", "mobile", "tel", "телефон", "мобильный"],
        "company": ["company", "organization", "org", "компания", "организация"],
        "tags":    ["tags", "tag", "labels", "теги", "метки"],
        "notes":   ["notes", "note", "comments", "заметки", "примечания"],
    }
    lower_cols = {c.lower(): c for c in df.columns}  # type: ignore[union-attr]
    col_map: dict[str, str] = {}
    for field, names in ALIASES.items():
        for n in names:
            if n in lower_cols:
                col_map[field] = lower_cols[n]
                break

    if "name" not in col_map:
        return {
            "error": "Could not find a 'name' column. "
                     f"Available columns: {df.columns.tolist()}"  # type: ignore[union-attr]
        }

    created, skipped = 0, 0
    for _, row in df.iterrows():  # type: ignore[union-attr]
        name = _safe_str(row.get(col_map["name"], ""))
        if not name:
            skipped += 1
            continue

        email = _safe_str(row[col_map["email"]]) if "email" in col_map else None

        # Skip duplicate emails per user
        if email:
            existing = await ctx.db.execute(
                select(Contact).where(
                    Contact.user_id == ctx.user_id,
                    Contact.email == email,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

        raw_tags = _safe_str(row[col_map["tags"]]) if "tags" in col_map else None
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else None

        contact = Contact(
            user_id=ctx.user_id,
            name=name,
            email=email or None,
            phone=_safe_str(row[col_map["phone"]]) if "phone" in col_map else None,
            company=_safe_str(row[col_map["company"]]) if "company" in col_map else None,
            tags=tags,
            notes=_safe_str(row[col_map["notes"]]) if "notes" in col_map else None,
            source="excel_agent_import",
        )
        ctx.db.add(contact)
        created += 1

    await ctx.db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "total_rows": len(df),  # type: ignore[arg-type]
        "detected_columns": col_map,
        "message": f"Successfully imported {created} contacts from Excel.",
    }
