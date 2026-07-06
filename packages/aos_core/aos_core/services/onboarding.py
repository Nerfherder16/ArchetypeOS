"""Repo acquisition — the *acquire* step of the portfolio loop (AOS-21).

Today the pipeline assumes a repository already lives under
``repository_root/<local_path>``; there is no way to *get* a repo there.
``clone_repo`` fills that gap: it shallow-clones a git URL into a safe,
single-segment directory directly under ``repository_root`` so the existing
register (``POST /projects/{id}/repositories``) + scan
(``POST /repositories/{id}/scan``) flow can take over.

Design notes:
- stdlib only (``subprocess``); no new dependency.
- ``name`` is validated to a single, safe path segment so ``dest`` can only ever
  be a direct child of ``repository_root`` (mirrors ``safe_repo_path`` in
  ``repository_scanner.py`` — resolve-and-reject rather than trust input).
- Idempotent: an existing non-empty ``dest`` is returned as-is (no reclone).
- ``runner`` is injectable so tests stay hermetic (no network, no real git).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _validate_name(name: str) -> None:
    """Reject any ``name`` that is not a single, safe path segment.

    Goal: ``repository_root / name`` can only resolve to a *direct child* of
    ``repository_root`` — never a traversal (``..``), a nested path (``a/b``),
    or a hidden/dotfile/dash-led directory.
    """
    if not name:
        raise ValueError("Repository name must not be empty")
    if "/" in name or "\\" in name:
        raise ValueError(f"Repository name must be a single path segment (no separators): {name!r}")
    if name == ".." or ".." in name:
        raise ValueError(f"Repository name must not contain '..': {name!r}")
    if name.startswith(".") or name.startswith("-"):
        raise ValueError(f"Repository name must not start with '.' or '-': {name!r}")


def clone_repo(
    url: str,
    name: str,
    repository_root: Path | str,
    ref: str | None = None,
    runner=subprocess.run,
) -> Path:
    """Shallow-clone ``url`` into ``repository_root/name`` and return the dest.

    Args:
        url: git URL to clone (``https://``, ``git@…``, or ``file://…``).
        name: single, safe path segment; the clone lands at ``root/name``.
        repository_root: the dev repositories directory (gitignored).
        ref: optional branch/tag to clone (``git clone --branch <ref>``).
        runner: injectable ``subprocess.run``-compatible callable (for tests).

    Returns:
        The destination ``Path`` (``repository_root/name``).

    Raises:
        ValueError: ``name`` is not a safe single path segment.
        RuntimeError: git is not installed, or the clone exits non-zero.
    """
    _validate_name(name)
    dest = Path(repository_root) / name

    # Idempotent: a populated dest means the repo is already acquired.
    if dest.is_dir() and any(dest.iterdir()):
        return dest

    argv = ["git", "clone", "--depth", "1"]
    if ref:
        argv += ["--branch", ref]
    argv += [url, str(dest)]

    try:
        result = runner(argv, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("git not found on PATH; install git to acquire repositories") from exc

    if result.returncode != 0:
        raise RuntimeError(f"git clone failed ({result.returncode}): {result.stderr}")

    return dest


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m aos_core.services.onboarding <url> <name> [ref]``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or len(args) > 3:
        print("usage: python -m aos_core.services.onboarding <url> <name> [ref]", file=sys.stderr)
        return 2

    url, name = args[0], args[1]
    ref = args[2] if len(args) == 3 else None
    repository_root = Path("./repositories")

    try:
        dest = clone_repo(url, name, repository_root, ref=ref)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
