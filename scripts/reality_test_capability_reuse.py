#!/usr/bin/env python
"""Portfolio benchmark for capability-level reuse matching (RFC-0013 §8 acceptance gate).

The regression gate for the *capability* Transfer path. It reuses the distillation
harness's ingest (scan + distill) — so with a real reasoned provider, distillation
now also persists per-repository ``RepositoryCapability`` rows + embeddings — then
runs the RFC-0013 §8 acceptance needs through ``recommend_reuse`` and prints, per
need, the ranked repos AND the specific capability + provenance file each rec cites.

This is a *manual* harness (NOT collected by pytest — it needs the cloned portfolio
on disk). It is the counterpart to ``scripts/reality_test_distillation.py``: that one
gates the distilled *purpose*; this one gates whether a reuse *need* lands on the
right named *capability* — the granularity fix RFC-0013 exists to make.

RFC-0013 §8 acceptance (the gate this harness checks, on ``--provider claude_code``
against the 5-repo shakedown portfolio — Recall, ArchetypeOS, AiGentOS, insta-ntly,
tali-api):
  * ``"agent framework with tool calling"`` → **AiGentOS #1**.
  * ``"LLM provider abstraction and model routing"`` → **ArchetypeOS #1** (AiGentOS #2 ok).
  * ``"HTTP routing and middleware for a web API"`` → a FastAPI web service #1.
  * each recommendation **cites the specific reusable capability + its file**.

Important: the **deterministic** provider (the default, hermetic) extracts NO
capabilities (it fabricates nothing), so the capability path stays empty and
``recommend_reuse`` falls back to the repo-level lexical floor — the acceptance gate
above therefore requires the real reasoned tier AND a postgres + fastembed backend
for the semantic path (sqlite/deterministic prints the honest floor instead). Run::

    # honest floor (hermetic, no capabilities extracted — sanity/plumbing only):
    PYTHONPATH=packages/aos_core python scripts/reality_test_capability_reuse.py
    # the real capability gate (Orchestrator-only; invokes the local `claude` CLI +
    # a real embedder + postgres for the semantic <=> path):
    AOS_REALITY_PROVIDER=claude_code EMBEDDING_PROVIDER=fastembed \\
      AOS_DATABASE_URL=postgresql+psycopg://… \\
      PYTHONPATH=packages/aos_core python scripts/reality_test_capability_reuse.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.config import get_settings
from aos_core.database import Base
from aos_core.models import Repository, RepositoryCapability
from aos_core.services.transfer import recommend_reuse

# Reuse the distillation harness's ingest + arg plumbing (same-dir sibling import;
# scripts/ is sys.path[0] when run as `python scripts/reality_test_capability_reuse.py`).
from reality_test_distillation import (  # noqa: E402
    _apply_provider_setting,
    _ingest,
    _parse_args,
    _repo_dirs,
)

# The RFC-0013 §8 acceptance needs (the capability-matching gate).
NEEDS = [
    "agent framework with tool calling",
    "LLM provider abstraction and model routing",
    "HTTP routing and middleware for a web API",
]


def main(argv: list[str]) -> int:
    provider_name, requested = _parse_args(argv)
    _apply_provider_setting(provider_name)
    settings = get_settings()
    repository_root = Path(settings.repository_root)
    knowledge_root = Path(settings.knowledge_root or "./knowledge")
    dirs = _repo_dirs(repository_root, requested)
    if not dirs:
        print(f"No repositories found under {repository_root}. Clone the portfolio first.")
        return 1

    # Prefer the configured DB (postgres → the semantic <=> path); fall back to a
    # scratch sqlite (lexical path) so the harness always runs.
    db_url = settings.database_url
    if db_url.startswith("postgres"):
        engine = create_engine(db_url, pool_pre_ping=True)
    else:
        scratch_db = Path(tempfile.mkdtemp(prefix="aos-cap-reality-")) / "reality.db"
        engine = create_engine(
            f"sqlite:///{scratch_db}", connect_args={"check_same_thread": False}, pool_pre_ping=True
        )
        print(f"Scratch sqlite DB: {scratch_db} (lexical capability path)")
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    print(f"Capability reuse benchmark over {len(dirs)} repo(s) under {repository_root}")
    print(f"Provider: {provider_name}  |  embedder: {settings.embedding_provider}  |  dialect: {engine.dialect.name}\n")

    with session_local() as session:
        print(f"== Ingest (scan + distill + persist capabilities, {provider_name} provider) ==")
        for dirname in dirs:
            try:
                _ingest(session, repository_root, knowledge_root, dirname)
            except Exception as exc:  # noqa: BLE001 - a bad repo must not abort the harness
                print(f"  ! {dirname}: ingest failed ({exc.__class__.__name__}: {exc})")

        print("\n== Extracted capabilities (per repo) ==")
        total_caps = session.query(RepositoryCapability).count()
        if total_caps == 0:
            print("  (none — the deterministic floor extracts no capabilities; run --provider claude_code)")
        else:
            for cap in session.query(RepositoryCapability).all():
                repo = session.get(Repository, cap.repository_id)
                name = repo.name if repo is not None else cap.repository_id
                where = (cap.provenance or [None])[0]
                print(f"  - {name}: {cap.name}  ({where})")

        print("\n== Rankings (RFC-0013 §8 gate) ==")
        for need in NEEDS:
            print(f"\nNeed: {need!r}")
            results = recommend_reuse(session, need=need, limit=10)
            if not results:
                print("  (no matches)")
                continue
            for rank, result in enumerate(results, start=1):
                capability = result.get("capability", "(repo-level fallback)")
                provenance = result.get("capability_provenance") or []
                where = provenance[0] if provenance else "—"
                marker = "  #%d" % rank
                print(
                    f"{marker:>6} {result['source_repository']:<24} conf={result['confidence']:.4f}  "
                    f"capability={capability!r} @ {where}"
                )

    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
