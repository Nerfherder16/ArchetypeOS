"""Hermetic tests for the per-project coherence dispatcher (AOS-ARCH-EDGES-001).

All seams are injected fakes — no network, no real git, no subprocess.
"""
from __future__ import annotations

import contextlib

# The dispatcher lives in tools/, which is not a package. Import via sys.path
# manipulation so PYTHONPATH=apps/api:packages/aos_core is the only requirement.
import importlib
import sys
from pathlib import Path

# tools/ sits two levels above apps/api/ — navigate from this file's location.
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"


def _load_dispatcher():
    if str(_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(_TOOLS_DIR))
    return importlib.import_module("project_audit_dispatch")


_mod = _load_dispatcher()
dispatch = _mod.dispatch


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _ok_clone(remote_url: str):
    """Fake clone that succeeds and yields a sentinel checkout path."""
    yield f"/fake/checkout/{remote_url.rsplit('/', 1)[-1]}"


@contextlib.contextmanager
def _failing_clone(remote_url: str):
    """Fake clone that always raises."""
    raise RuntimeError("git clone failed: authentication required")
    yield  # make it a generator


def _probe_clean(_checkout_dir: str) -> tuple[str, str]:
    return "clean", ""


def _probe_findings(_checkout_dir: str) -> tuple[str, str]:
    return "findings", "contract-lag detected"


def _probe_failed(_checkout_dir: str) -> tuple[str, str]:
    return "failed", "probe error"


def _probe_raises(_checkout_dir: str) -> tuple[str, str]:
    raise RuntimeError("probe subprocess crashed")


# ---------------------------------------------------------------------------
# Test 1: two enabled + one disabled
# ---------------------------------------------------------------------------


def test_dispatch_skips_disabled_projects_and_posts_two_heartbeats():
    """Dispatch posts exactly two heartbeats for enabled projects; disabled is skipped."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    projects = [
        {"id": "p1", "audits_enabled": True},
        {"id": "p2", "audits_enabled": True},
        {"id": "p3", "audits_enabled": False},
    ]

    summary = dispatch(
        list_projects=lambda: projects,
        get_repo_url=lambda pid: f"https://github.com/org/{pid}",
        run_probe=_probe_clean,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    # Exactly two heartbeats, none for disabled p3.
    assert len(calls) == 2
    posted_project_ids = {c[3] for c in calls}
    assert posted_project_ids == {"p1", "p2"}
    assert "p3" not in posted_project_ids

    # Summary also has exactly two entries.
    assert len(summary) == 2
    assert {e["project_id"] for e in summary} == {"p1", "p2"}

    # All posted with routine="coherence" and the correct day.
    for routine, status, day, project_id, _ in calls:
        assert routine == "coherence"
        assert day == "2026-07-09"


# ---------------------------------------------------------------------------
# Test 2: probe signal mapping
# ---------------------------------------------------------------------------


def test_dispatch_probe_signal_true_yields_findings():
    """signal=true from probe maps to status='findings'."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    summary = dispatch(
        list_projects=lambda: [{"id": "proj-a", "audits_enabled": True}],
        get_repo_url=lambda pid: "https://github.com/org/repo",
        run_probe=_probe_findings,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    assert len(summary) == 1
    assert summary[0]["status"] == "findings"
    assert calls[0][1] == "findings"


def test_dispatch_probe_signal_false_yields_clean():
    """signal=false from probe maps to status='clean'."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    summary = dispatch(
        list_projects=lambda: [{"id": "proj-b", "audits_enabled": True}],
        get_repo_url=lambda pid: "https://github.com/org/repo",
        run_probe=_probe_clean,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    assert len(summary) == 1
    assert summary[0]["status"] == "clean"
    assert calls[0][1] == "clean"


# ---------------------------------------------------------------------------
# Test 3: no repo URL → "failed", others continue
# ---------------------------------------------------------------------------


def test_dispatch_no_repo_url_posts_failed_and_continues():
    """A project with no repo URL posts 'failed'; the next project is still processed."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    def get_repo_url(pid: str) -> str | None:
        return None if pid == "no-url" else "https://github.com/org/repo"

    summary = dispatch(
        list_projects=lambda: [
            {"id": "no-url", "audits_enabled": True},
            {"id": "has-url", "audits_enabled": True},
        ],
        get_repo_url=get_repo_url,
        run_probe=_probe_clean,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    assert len(summary) == 2
    by_pid = {e["project_id"]: e for e in summary}

    # no-url project is failed.
    assert by_pid["no-url"]["status"] == "failed"

    # has-url project still ran and got clean.
    assert by_pid["has-url"]["status"] == "clean"

    # Both posted heartbeats.
    posted = {c[3]: c[1] for c in calls}
    assert posted["no-url"] == "failed"
    assert posted["has-url"] == "clean"

    # Post was called with routine="coherence" for both.
    for c in calls:
        assert c[0] == "coherence"


# ---------------------------------------------------------------------------
# Test 4: clone_repo raises → that project is "failed", others continue
# ---------------------------------------------------------------------------


def test_dispatch_clone_failure_posts_failed_and_continues():
    """If clone_repo raises, that project posts 'failed' and the run continues."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    def clone_repo_sometimes_fails(remote_url: str):
        if "bad-repo" in remote_url:
            return _failing_clone(remote_url)
        return _ok_clone(remote_url)

    def get_repo_url(pid: str) -> str:
        return f"https://github.com/org/{pid}"

    summary = dispatch(
        list_projects=lambda: [
            {"id": "bad-repo", "audits_enabled": True},
            {"id": "good-repo", "audits_enabled": True},
        ],
        get_repo_url=get_repo_url,
        run_probe=_probe_clean,
        clone_repo=clone_repo_sometimes_fails,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    by_pid = {e["project_id"]: e for e in summary}

    assert by_pid["bad-repo"]["status"] == "failed"
    assert "git clone failed" in (by_pid["bad-repo"]["detail"] or "")

    assert by_pid["good-repo"]["status"] == "clean"

    # Both still had heartbeats posted.
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Test 5: run_probe returns "failed" or raises → project posts "failed"
# ---------------------------------------------------------------------------


def test_dispatch_probe_returns_failed_posts_failed():
    """run_probe returning 'failed' propagates to the heartbeat."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    summary = dispatch(
        list_projects=lambda: [{"id": "p-fail", "audits_enabled": True}],
        get_repo_url=lambda pid: "https://github.com/org/repo",
        run_probe=_probe_failed,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    assert summary[0]["status"] == "failed"
    assert calls[0][1] == "failed"


def test_dispatch_probe_raises_posts_failed_and_continues():
    """run_probe raising is caught; that project posts 'failed', others continue."""
    calls: list[tuple] = []

    def post_heartbeat(routine, status, day, project_id, detail=None):
        calls.append((routine, status, day, project_id, detail))

    def run_probe_raises_first(checkout_dir: str) -> tuple[str, str]:
        if "p-raise" in checkout_dir:
            raise RuntimeError("probe subprocess crashed")
        return "clean", ""

    summary = dispatch(
        list_projects=lambda: [
            {"id": "p-raise", "audits_enabled": True},
            {"id": "p-ok", "audits_enabled": True},
        ],
        get_repo_url=lambda pid: f"https://github.com/org/{pid}",
        run_probe=run_probe_raises_first,
        clone_repo=_ok_clone,
        post_heartbeat=post_heartbeat,
        day="2026-07-09",
    )

    by_pid = {e["project_id"]: e for e in summary}
    assert by_pid["p-raise"]["status"] == "failed"
    assert "probe subprocess crashed" in (by_pid["p-raise"]["detail"] or "")
    assert by_pid["p-ok"]["status"] == "clean"
    assert len(calls) == 2
