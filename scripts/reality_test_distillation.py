#!/usr/bin/env python
"""Portfolio reality-test harness for distillation + transfer (AOS-DISTILL-003).

This is the **regression gate** for the mature-state distillation sequence. It is
a *manual* harness (NOT collected by pytest — it needs the cloned repos on disk),
adapted from the Orchestrator's first end-to-end reality test (2026-07-06) that
proved the intelligence loop connects but distillation quality was starving the
Knowledge Transfer Engine ("right engine, wrong evidence").

What it does, per repo directory under ``settings.repository_root``:
  1. registers a Project + Repository (``local_path=<dirname>``) in a scratch
     sqlite DB (idempotent — a repo whose slug already exists is skipped),
  2. runs the real ``run_scan`` (populating ``DNA.frameworks`` from manifests),
  3. runs ``distill_repository`` with the **deterministic** provider (hermetic —
     no real model is ever invoked), stamping the cleaned ``DNA.purpose``,
then runs a FIXED set of ``recommend_reuse`` needs across the whole portfolio and
prints each repo's ``DNA.purpose``/frameworks and the per-need rankings.

Expected post-fix rankings (the gate this package must restore):
  * ``kubernetes`` ranks **#1** for "container orchestration and scheduling"
    (previously: no matches — its purpose was raw badge markdown).
  * ``gin`` ranks **#1** for "HTTP routing and middleware for a web API"
    (previously: 3rd, behind free-llm/pydantic-ai matching on generic api/web noise).
  * ``pydantic-ai``'s purpose is the "Pydantic AI is a Python agent framework …"
    sentence, NOT the "FastAPI revolutionized web development …" analogy that
    previously produced false ``web`` matches.

Usage (run from the repo root so ``./repositories`` and ``./knowledge`` resolve)::

    PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py
    PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py gin kubernetes

An optional list of repo directory names may be passed as argv (default: all
directories under ``settings.repository_root``).

By default the harness runs the **deterministic** provider (hermetic — no real
model, the reproducible Package-1 ranking gate). An **opt-in real-provider mode**
distills with the LES-021-isolated ``ClaudeCodeProvider`` for the live quality
check (Orchestrator-only; it invokes the local ``claude`` CLI)::

    PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py --provider claude_code
    AOS_REALITY_PROVIDER=claude_code PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py gin

The provider may be set via ``--provider <name>`` / ``--provider=<name>`` or the
``AOS_REALITY_PROVIDER`` env var (the flag wins); default stays ``deterministic``.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.config import get_settings
from aos_core.database import Base
from aos_core.llm import ClaudeCodeProvider, DeterministicProvider
from aos_core.models import Project, Repository, RepositoryDNA
from aos_core.services.distillation import _repo_slug, distill_repository
from aos_core.services.scan import run_scan
from aos_core.services.transfer import recommend_reuse

# The fixed reality-test needs. The first two are the ranking GATE.
NEEDS = [
    "container orchestration and scheduling",
    "HTTP routing and middleware for a web API",
    "LLM provider abstraction and model routing",
    "agent framework with tool calling",
]


def _repo_dirs(repository_root: Path, requested: list[str]) -> list[str]:
    if requested:
        return requested
    if not repository_root.is_dir():
        return []
    return sorted(p.name for p in repository_root.iterdir() if p.is_dir() and not p.name.startswith("."))


def _select_provider(name: str):
    """Resolve the reality-test provider by name (default deterministic/hermetic).

    ``deterministic`` (the DEFAULT — keeps the Package-1 ranking gate reproducible
    and never invokes a real model) → :class:`DeterministicProvider`; the opt-in
    ``claude_code`` → the LES-021-isolated :class:`ClaudeCodeProvider` for the live
    quality check (Orchestrator-only). Anything else is a hard error.
    """
    if name == "deterministic":
        return DeterministicProvider()
    if name == "claude_code":
        return ClaudeCodeProvider()
    raise SystemExit(f"Unknown --provider {name!r} (expected 'deterministic' or 'claude_code')")


def _parse_args(argv: list[str]) -> tuple[str, list[str]]:
    """Split argv into (provider_name, repo_dirs). Opt-in real-provider mode.

    The provider defaults to ``deterministic`` (hermetic) and may be overridden via
    ``--provider <name>`` / ``--provider=<name>`` or the ``AOS_REALITY_PROVIDER``
    environment variable; the flag wins over the env var. All remaining positional
    args are repo directory names (unchanged default behavior).
    """
    provider = os.environ.get("AOS_REALITY_PROVIDER", "deterministic") or "deterministic"
    dirs: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--provider":
            if i + 1 >= len(argv):
                raise SystemExit("--provider requires a value ('deterministic' or 'claude_code')")
            provider = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--provider="):
            provider = arg.split("=", 1)[1]
            i += 1
            continue
        dirs.append(arg)
        i += 1
    return provider, dirs


def _ingest(session, repository_root: Path, knowledge_root: Path, dirname: str, provider) -> str | None:
    """Idempotently register + scan + distill one repo. Returns the repo id (or None on skip)."""
    slug = _repo_slug(dirname)
    existing = (
        session.query(Repository).join(Project).filter(Project.slug == f"rt-{slug}").first()
    )
    if existing is not None:
        return existing.id
    if not (repository_root / dirname).is_dir():
        print(f"  ! {dirname}: not a directory under {repository_root}; skipping")
        return None

    project = Project(name=dirname, slug=f"rt-{slug}")
    session.add(project)
    session.flush()
    repository = Repository(project_id=project.id, name=dirname, local_path=dirname)
    session.add(repository)
    session.commit()

    run_scan(repository.id, session)
    # run_scan creates the DNA row via a fresh relationship; in this single
    # long-lived session (expire_on_commit=False) the repository's ``dna``
    # relationship was cached as None before the row existed. Expire so distill
    # reloads it and can stamp ``DNA.purpose`` (the app uses per-request sessions,
    # where this does not arise).
    session.expire_all()
    distill_repository(
        session,
        repository_id=repository.id,
        knowledge_root=knowledge_root,
        provider=provider,
    )
    return repository.id


def main(argv: list[str]) -> int:
    settings = get_settings()
    repository_root = Path(settings.repository_root)
    knowledge_root = Path(settings.knowledge_root or "./knowledge")
    provider_name, requested = _parse_args(argv)
    provider = _select_provider(provider_name)
    dirs = _repo_dirs(repository_root, requested)
    if not dirs:
        print(f"No repositories found under {repository_root}. Clone the portfolio first.")
        return 1

    scratch_db = Path(tempfile.mkdtemp(prefix="aos-reality-")) / "reality.db"
    engine = create_engine(
        f"sqlite:///{scratch_db}", connect_args={"check_same_thread": False}, pool_pre_ping=True
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    print(f"Reality test over {len(dirs)} repo(s) under {repository_root}")
    print(f"Provider: {provider_name}")
    print(f"Scratch DB: {scratch_db}\n")

    with session_local() as session:
        print(f"== Ingest (scan + distill, {provider_name} provider) ==")
        for dirname in dirs:
            try:
                _ingest(session, repository_root, knowledge_root, dirname, provider)
            except Exception as exc:  # noqa: BLE001 - a bad repo must not abort the harness
                print(f"  ! {dirname}: ingest failed ({exc.__class__.__name__}: {exc})")

        print("\n== Distilled DNA (purpose + frameworks) ==")
        for dna in session.query(RepositoryDNA).all():
            repo = session.get(Repository, dna.repository_id)
            name = repo.name if repo is not None else dna.repository_id
            purpose = (dna.purpose or "").replace("\n", " ")
            if len(purpose) > 160:
                purpose = purpose[:157] + "…"
            print(f"  - {name}: frameworks={dna.frameworks or []}")
            print(f"      purpose: {purpose}")

        print("\n== Rankings ==")
        for need in NEEDS:
            print(f"\nNeed: {need!r}")
            results = recommend_reuse(session, need=need, limit=10)
            if not results:
                print("  (no matches)")
                continue
            for rank, result in enumerate(results, start=1):
                marker = "  #%d" % rank
                print(
                    f"{marker:>6} {result['source_repository']:<28} "
                    f"conf={result['confidence']:.4f}  matched={result['matched_terms']}"
                )

    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
