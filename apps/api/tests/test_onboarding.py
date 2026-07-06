"""Tests for the repo-acquisition step (AOS-PORTFOLIO-001 / Plane AOS-21).

Covers ``clone_repo``: a real ``file://`` clone (real git, NO network) that is
idempotent on re-run; single-path-segment name safety; and the exact argv the
runner receives (injectable runner keeps this hermetic).
"""

from __future__ import annotations

import subprocess

import pytest

from aos_core.services.onboarding import clone_repo


def _make_git_repo(src) -> None:
    """Create a tiny committed git repo at ``src`` with no global git config."""
    src.mkdir(parents=True, exist_ok=True)
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    run = lambda args: subprocess.run(  # noqa: E731 - terse local helper
        args, cwd=src, env={**_os_environ(), **env}, capture_output=True, text=True, check=True
    )
    run(["git", "init", "-q"])
    run(["git", "config", "user.email", "test@example.com"])
    run(["git", "config", "user.name", "Test"])
    (src / "README.md").write_text("hello onboarding\n", encoding="utf-8")
    run(["git", "add", "README.md"])
    run(["git", "commit", "-q", "-m", "initial"])


def _os_environ() -> dict:
    import os

    return dict(os.environ)


class _FakeCompleted:
    """Stand-in for a subprocess.CompletedProcess with a given returncode."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = "boom" if returncode else ""


def test_clone_repo_real_file_url(tmp_path) -> None:
    src = tmp_path / "src"
    _make_git_repo(src)
    root = tmp_path / "root"

    dest = clone_repo(f"file://{src}", "cloned", root)

    assert dest == root / "cloned"
    assert dest.is_dir()
    assert (dest / "README.md").read_text(encoding="utf-8") == "hello onboarding\n"

    # Idempotent: a second call returns the same dest without recloning/erroring.
    dest2 = clone_repo(f"file://{src}", "cloned", root)
    assert dest2 == dest
    assert (dest2 / "README.md").exists()


def test_clone_repo_rejects_unsafe_name(tmp_path) -> None:
    root = tmp_path / "root"
    for bad in ("..", "a/b", "", ".hidden"):
        with pytest.raises(ValueError):
            clone_repo("file:///nope", bad, root)


def test_clone_repo_builds_expected_argv(tmp_path) -> None:
    root = tmp_path / "root"
    captured: dict = {}

    def fake_runner(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _FakeCompleted(0)

    dest = clone_repo("https://example.com/x.git", "x", root, runner=fake_runner)
    assert dest == root / "x"
    assert captured["argv"] == ["git", "clone", "--depth", "1", "https://example.com/x.git", str(dest)]
    assert captured["kwargs"] == {"capture_output": True, "text": True}

    # With a ref, argv includes --branch <ref>.
    captured.clear()
    clone_repo("https://example.com/x.git", "y", root, ref="v1.2.3", runner=fake_runner)
    assert captured["argv"] == [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        "v1.2.3",
        "https://example.com/x.git",
        str(root / "y"),
    ]

    # A non-zero returncode surfaces as RuntimeError.
    with pytest.raises(RuntimeError):
        clone_repo("https://example.com/x.git", "z", root, runner=lambda *a, **k: _FakeCompleted(1))
