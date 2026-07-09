"""Deterministic contract-coherence probe for the self-learn loop (AOS-SELFHEAL-005).

The third self-learn probe (sibling of ``conflict_digest.py`` and
``toil_digest.py``). Where those harvest merge friction and git toil, this one
harvests **contract-lag**: a frontend TypeScript type that is *thinner* than the
backend Pydantic schema it mirrors — the exact class of gap the system evaluation
found by hand (e.g. the API dropped the DNA ``purpose``/``maturity`` fields
because the frontend ``RepositoryDna`` type never surfaced them). Caught
automatically, this drift is a signal the reasoned tier can turn into a fix.

How it works, deterministically and hermetically (the harvest functions take the
two source strings, so tests never read the real tree):

- Parse the backend Pydantic response schemas from ``apps/api/app/schemas.py``:
  every ``class XRead(BaseModel):`` (and other ``*Read`` response models) and its
  field names.
- Parse the frontend response types from ``apps/web/src/api.ts``: every
  ``export type X = { ... }`` and its field names.
- Pair a backend ``XRead`` with the frontend ``X`` (drop the ``Read`` suffix).
  When the frontend type exists but is missing fields the backend schema exposes,
  that pair is contract-lag; the missing fields are the signal.

Only *thin* pairs are a signal (frontend type present but drifted). A backend
schema with no frontend counterpart at all is not flagged — many response models
are backend-internal, so absence is not drift. State-drift (canonical docs lagging
git) is already covered by the doc-staleness / state-refresh workflows; this probe
is contract-lag only, on purpose.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_SCHEMAS_PATH = REPO_ROOT / "apps" / "api" / "app" / "schemas.py"
_FRONTEND_PATH = REPO_ROOT / "apps" / "web" / "src" / "api.ts"

# A Pydantic class header: `class ResearchPlanRead(BaseModel):`.
_PY_CLASS_RE = re.compile(r"^class\s+(\w+)\((?:[\w., ]*\b)?BaseModel\):\s*$")
# A Pydantic field line at class-body indent: `    required_source_types: list`.
_PY_FIELD_RE = re.compile(r"^    (\w+)\s*:\s*\S")
# A TS type header: `export type ResearchPlan = {`.
_TS_TYPE_RE = re.compile(r"^export\s+type\s+(\w+)\s*=\s*\{\s*$")
# A TS field line: `  required_source_types: string[];` or `  freshness?: string | null;`.
_TS_FIELD_RE = re.compile(r"^  (\w+)\??\s*:")


# AuditMixin envelope fields the frontend consistently (and correctly) omits —
# pure metadata with no domain meaning for the UI. Excluding them keeps the probe
# focused on domain/relationship drift (the class of gap the eval found) instead
# of alarming on universally-dropped boilerplate.
_ENVELOPE_FIELDS = frozenset(
    {"status", "version", "created_at", "updated_at", "created_by", "updated_by", "metadata"}
)


@dataclass
class ContractLag:
    """One frontend type that is thinner than its backend schema."""

    schema: str  # backend Pydantic class, e.g. ResearchPlanRead
    frontend_type: str  # frontend TS type, e.g. ResearchPlan
    missing_fields: list[str]  # backend fields absent from the frontend type


def parse_pydantic_read_schemas(text: str) -> dict[str, list[str]]:
    """Map each ``*Read`` Pydantic response schema to its field names.

    Only response schemas (class name ending in ``Read``) are considered — those
    are the shapes the frontend consumes. ``model_config`` and blank/comment lines
    are ignored; a field must sit at the four-space class-body indent.
    """
    schemas: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        header = _PY_CLASS_RE.match(line)
        if header:
            name = header.group(1)
            current = name if name.endswith("Read") else None
            if current:
                schemas[current] = []
            continue
        if current is None:
            continue
        # A non-indented, non-blank line ends the class body.
        if line and not line.startswith(" "):
            current = None
            continue
        field = _PY_FIELD_RE.match(line)
        if field and field.group(1) != "model_config":
            schemas[current].append(field.group(1))
    return schemas


def parse_ts_types(text: str) -> dict[str, list[str]]:
    """Map each ``export type X = { ... }`` frontend type to its field names."""
    types: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        header = _TS_TYPE_RE.match(line)
        if header:
            current = header.group(1)
            types[current] = []
            continue
        if current is None:
            continue
        if line.startswith("}"):  # end of the type literal
            current = None
            continue
        field = _TS_FIELD_RE.match(line)
        if field:
            types[current].append(field.group(1))
    return types


def find_contract_lag(
    backend: dict[str, list[str]], frontend: dict[str, list[str]]
) -> list[ContractLag]:
    """Pair backend ``XRead`` with frontend ``X`` and report thinner frontends.

    A pair is reported only when the frontend type exists and is missing one or
    more fields the backend schema exposes. Deterministic: results are sorted by
    schema name, missing fields sorted within each.
    """
    lags: list[ContractLag] = []
    for schema in sorted(backend):
        frontend_name = schema[: -len("Read")]  # XRead -> X
        if frontend_name not in frontend:
            continue
        missing = sorted(
            (set(backend[schema]) - set(frontend[frontend_name])) - _ENVELOPE_FIELDS
        )
        if missing:
            lags.append(ContractLag(schema=schema, frontend_type=frontend_name, missing_fields=missing))
    return lags


def has_signal(lags: list[ContractLag]) -> bool:
    return bool(lags)


def digest_payload(*, lags: list[ContractLag], day_label: str) -> dict:
    """Machine-readable digest for the reasoned tier / skill queue."""
    return {
        "probe": "coherence",
        "day": day_label,
        "signal": has_signal(lags),
        "contract_lag": [
            {
                "schema": lag.schema,
                "frontend_type": lag.frontend_type,
                "missing_fields": lag.missing_fields,
            }
            for lag in lags
        ],
    }


def build_digest(*, lags: list[ContractLag], day_label: str) -> str:
    """Human-readable markdown digest of the day's contract-lag."""
    lines = [f"# Coherence digest — {day_label}", ""]
    if not has_signal(lags):
        lines.append("No contract-lag detected: every mirrored frontend type covers its backend schema.")
        lines.append("")
        return "\n".join(lines)
    lines.append(
        f"Detected **{len(lags)}** frontend type(s) thinner than their backend schema "
        "(contract-lag). Each dropped field is a place the API can silently lose data."
    )
    lines.append("")
    for lag in lags:
        fields = ", ".join(f"`{field}`" for field in lag.missing_fields)
        lines.append(
            f"- **{lag.frontend_type}** (frontend) is missing {len(lag.missing_fields)} field(s) "
            f"from **{lag.schema}** (backend): {fields}"
        )
    lines.append("")
    return "\n".join(lines)


def _today(repo_root: Path) -> str:
    # No wall-clock in the harvest path; the day label comes from git's last commit
    # date (deterministic + hermetic), falling back to a static marker.
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cs"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip() or "undated"
    except Exception:
        return "undated"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect frontend/backend contract-lag (AOS-SELFHEAL-005)."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--schemas", type=Path, default=None, help="Backend schemas.py (default: apps/api/app/schemas.py).")
    parser.add_argument("--frontend", type=Path, default=None, help="Frontend api.ts (default: apps/web/src/api.ts).")
    parser.add_argument("--day-label", default=None, help="Override the digest date label.")
    parser.add_argument("--out", type=Path, default=None, help="Markdown output path (default: .archetype/coherence/<day>.md).")
    parser.add_argument("--json", type=Path, default=None, help="Also write the JSON payload here.")
    args = parser.parse_args(argv)

    schemas_path = args.schemas or (args.repo_root / "apps" / "api" / "app" / "schemas.py")
    frontend_path = args.frontend or (args.repo_root / "apps" / "web" / "src" / "api.ts")

    backend = parse_pydantic_read_schemas(schemas_path.read_text(encoding="utf-8"))
    frontend = parse_ts_types(frontend_path.read_text(encoding="utf-8"))
    lags = find_contract_lag(backend, frontend)

    day_label = args.day_label or _today(args.repo_root)
    digest = build_digest(lags=lags, day_label=day_label)

    out = args.out or (args.repo_root / ".archetype" / "coherence" / f"{day_label}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(digest, encoding="utf-8")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(digest_payload(lags=lags, day_label=day_label), indent=2),
            encoding="utf-8",
        )

    print(f"Wrote coherence digest: {out}")
    print(f"signal={'true' if has_signal(lags) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
