#!/usr/bin/env python3
# NOTICE: This file is protected under RCF-PL
"""Generate OpenAPI schema from FastAPI app."""
import json
import sys
from pathlib import Path

# `python scripts/generate_openapi.py` puts scripts/ on sys.path, not the
# backend root, so `import app...` raised ModuleNotFoundError unless the caller
# remembered PYTHONPATH=. Adding the package root here keeps the plain command
# working on its own.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402 — must run after sys.path setup


# [RCF:PROTECTED]
def main():
    """Generate and save OpenAPI schema."""
    schema = app.openapi()

    # Save to docs directory
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    output_file = docs_dir / "openapi.json"
    with open(output_file, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"✅ OpenAPI schema generated: {output_file}")
    print(f"📊 Endpoints: {len([p for p in schema.get('paths', {}).values()])}")
    print(f"🏷️  Tags: {len(schema.get('tags', []))}")
    print("\n📖 View docs at: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
