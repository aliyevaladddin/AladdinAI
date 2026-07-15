# NOTICE: This file is protected under RCF-PL
"""Guard rails for the Alembic revision graph.

These tests do NOT run `alembic upgrade` — a couple of historical migrations use
Postgres-only `information_schema` guards that can't execute on the sqlite test
harness (CI runs migrations against real Postgres). Instead they check the
*shape* of the revision graph and that every ORM table is created by some
migration. That is enough to catch the two failure modes we've actually hit:

  * two heads after parallel branches merge into main (breaks `upgrade head`);
  * a new model shipped without a matching migration (schema drift).
"""
import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.database import Base
import app.models  # noqa: F401  — registers every model on Base.metadata

_BACKEND = Path(__file__).resolve().parent.parent


def _script() -> ScriptDirectory:
    cfg = Config(str(_BACKEND / "alembic.ini"))
    return ScriptDirectory.from_config(cfg)


def test_single_head():
    """Exactly one head — otherwise `alembic upgrade head` fails with
    'multiple heads'. This is the regression that the merge migration fixed."""
    heads = _script().get_heads()
    assert len(heads) == 1, f"Expected a single Alembic head, found {len(heads)}: {heads}"


def test_single_base():
    """One starting revision — the graph is a single connected history."""
    assert len(_script().get_bases()) == 1


def test_graph_is_walkable():
    """Every revision resolves; no dangling down_revision. walk_revisions()
    raises if a revision points at a parent that doesn't exist."""
    revs = list(_script().walk_revisions())
    assert len(revs) > 0


def test_every_model_table_has_a_migration():
    """Each table declared on Base.metadata must be created by some migration.
    Catches 'added a model but forgot to write the migration'."""
    versions_dir = _BACKEND / "alembic" / "versions"
    text = "\n".join(p.read_text(encoding="utf-8") for p in versions_dir.glob("*.py"))
    # Match create_table('name', ...) / create_table("name", ...)
    created = set(re.findall(r"create_table\(\s*['\"]([a-zA-Z0-9_]+)['\"]", text))

    model_tables = set(Base.metadata.tables.keys())
    missing = model_tables - created
    assert not missing, f"Model tables with no create_table migration: {sorted(missing)}"
