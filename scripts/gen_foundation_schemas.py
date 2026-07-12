#!/usr/bin/env python3
"""Regenerate schemas/foundation/*.json from the Pydantic Foundation contracts.

Usage: python scripts/gen_foundation_schemas.py

Pydantic (packages/aos_core/aos_core/foundation/contracts.py) is the single
source; this writes the derived JSON Schema artifact consumed by later
slices' UI/external tooling. Run after any contract change so the schema-drift
test (apps/api/tests/test_foundation_schema_drift.py) passes.
"""
from __future__ import annotations

from pathlib import Path

from aos_core.foundation.schema_gen import write_schemas

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST = REPO_ROOT / "schemas" / "foundation"


def main() -> None:
    write_schemas(DEST)
    print(f"Wrote foundation schemas to {DEST}")


if __name__ == "__main__":
    main()
