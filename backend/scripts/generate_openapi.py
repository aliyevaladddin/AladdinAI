#!/usr/bin/env python3
"""Generate OpenAPI schema from FastAPI app."""
import json
from pathlib import Path

# Import app directly without sys.path manipulation
from app.main import app


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
