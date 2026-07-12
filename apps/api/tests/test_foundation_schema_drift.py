"""Generated schemas/foundation/*.json must match aos_core.foundation.contracts
(RFC-0017 / AOS-FOUND-CONTRACTS-001 — the drift guard).

Run `python scripts/gen_foundation_schemas.py` after any contract change.
"""
from __future__ import annotations

import json
from pathlib import Path

from aos_core.foundation.schema_gen import generate_schemas

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "schemas" / "foundation"


def test_repo_root_resolved_correctly() -> None:
    assert (REPO_ROOT / "packages" / "aos_core" / "pyproject.toml").exists()


def test_generated_schemas_match_checked_in_files() -> None:
    in_memory = generate_schemas()
    assert in_memory, "no schemas were generated"

    on_disk_names = {p.stem for p in SCHEMA_DIR.glob("*.json")}
    assert on_disk_names == set(in_memory.keys()), (
        f"checked-in schema files do not match generated entity set: "
        f"only-on-disk={on_disk_names - set(in_memory)} only-in-memory={set(in_memory) - on_disk_names}"
    )

    for name, schema in in_memory.items():
        on_disk = json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))
        assert on_disk == schema, f"{name}.json is stale — rerun scripts/gen_foundation_schemas.py"
