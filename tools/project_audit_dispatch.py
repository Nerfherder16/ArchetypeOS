"""Per-project coherence dispatcher (AOS-ARCH-EDGES-001, task #44).

Runs the repo-state (coherence) audit against every project that has opted into
nightly audits (``audits_enabled=True``) and posts a per-project heartbeat
(routine="coherence", project_id=<the project's id>) so results show on the
Nightly Audits board's per-project section.

MVP scope: DETECT + heartbeat per project.

Out of scope (do NOT do this here): opening remediation PRs on external repos.
That would require authenticated push access to arbitrary third-party repos and
is a separate workflow that must be approved by the project owner. This
dispatcher only reads the repo (shallow clone) and reports findings.

Design for hermetic testability: the core ``dispatch()`` function accepts
injectable seam functions for every side effect. ``main()`` wires the real
implementations. No side effects in importable code paths.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Generator

TOOLS_DIR = Path(__file__).resolve().parent
PROBE_SCRIPT = TOOLS_DIR / "coherence_probe.py"


# ---------------------------------------------------------------------------
# Core dispatcher — all side effects are injected
# ---------------------------------------------------------------------------


def dispatch(
    *,
    list_projects: Callable[[], list[dict]],
    get_repo_url: Callable[[str], str | None],
    run_probe: Callable[[str], tuple[str, str]],
    clone_repo: Callable[[str], "contextlib.AbstractContextManager[str]"],
    post_heartbeat: Callable[[str, str, str, str, str | None], None],
    day: str,
) -> list[dict]:
    """Run the coherence probe against each audits-enabled project.

    For each project with ``audits_enabled=True``:
      1. Resolve its repo URL via ``get_repo_url``.
      2. Clone it (shallow) via ``clone_repo``.
      3. Run the coherence probe via ``run_probe``.
      4. Post a per-project heartbeat via ``post_heartbeat``.

    A project with no repo URL, a clone failure, or a probe failure posts
    status="failed" — it never crashes the whole run.

    Returns a summary list of ``{project_id, status, detail}`` dicts.

    Out of scope: opening remediation PRs on external repos (see module docstring).
    """
    projects = list_projects()
    summary: list[dict] = []

    for project in projects:
        project_id: str = project["id"]
        if not project.get("audits_enabled"):
            continue

        status = "failed"
        detail: str | None = None

        try:
            repo_url = get_repo_url(project_id)
            if not repo_url:
                detail = f"No remote_url configured for project {project_id}"
                post_heartbeat("coherence", status, day, project_id, detail)
                summary.append({"project_id": project_id, "status": status, "detail": detail})
                continue

            with clone_repo(repo_url) as checkout_dir:
                status, detail = run_probe(checkout_dir)

        except Exception as exc:  # noqa: BLE001
            detail = str(exc)

        post_heartbeat("coherence", status, day, project_id, detail)
        summary.append({"project_id": project_id, "status": status, "detail": detail})

    return summary


# ---------------------------------------------------------------------------
# Real seam implementations wired by main()
# ---------------------------------------------------------------------------


def _make_list_projects(base_url: str, token: str | None) -> Callable[[], list[dict]]:
    def list_projects() -> list[dict]:
        req = urllib.request.Request(f"{base_url}/projects")
        if token:
            req.add_header("x-telemetry-token", token)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    return list_projects


def _make_get_repo_url(base_url: str, token: str | None) -> Callable[[str], str | None]:
    def get_repo_url(project_id: str) -> str | None:
        req = urllib.request.Request(f"{base_url}/projects/{project_id}/repositories")
        if token:
            req.add_header("x-telemetry-token", token)
        with urllib.request.urlopen(req) as resp:
            repos: list[dict] = json.loads(resp.read())
        # Use the first repo that has a remote_url.
        for repo in repos:
            url = repo.get("remote_url")
            if url:
                return url
        return None

    return get_repo_url


def _make_post_heartbeat(base_url: str, token: str | None) -> Callable[[str, str, str, str, str | None], None]:
    def post_heartbeat(
        routine: str, status: str, day: str, project_id: str, detail: str | None = None
    ) -> None:
        payload: dict = {
            "routine": routine,
            "status": status,
            "day": day,
            "project_id": project_id,
        }
        if detail is not None:
            payload["detail"] = detail
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{base_url}/audits/heartbeat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if token:
            req.add_header("x-telemetry-token", token)
        with urllib.request.urlopen(req):
            pass

    return post_heartbeat


@contextmanager
def _clone_repo(remote_url: str) -> Generator[str, None, None]:
    """Shallow-clone ``remote_url`` into a temp dir; clean up after."""
    with tempfile.TemporaryDirectory(prefix="aos-audit-clone-") as tmpdir:
        subprocess.run(
            ["git", "clone", "--depth", "1", remote_url, tmpdir],
            check=True,
            capture_output=True,
            text=True,
        )
        yield tmpdir


def _run_probe(checkout_dir: str) -> tuple[str, str]:
    """Run ``coherence_probe.py`` against ``checkout_dir``.

    Parses the ``signal=true|false`` line from stdout.
    Returns ``("findings", "")`` on signal=true, ``("clean", "")`` on signal=false.
    On non-zero exit or any exception, returns ``("failed", <error detail>)``.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        json_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, str(PROBE_SCRIPT), "--repo-root", checkout_dir, "--json", json_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "failed", result.stderr.strip() or result.stdout.strip() or "probe exited non-zero"

        for line in result.stdout.splitlines():
            if line.startswith("signal="):
                signal_val = line.split("=", 1)[1].strip().lower()
                return ("findings" if signal_val == "true" else "clean"), ""

        return "failed", "probe produced no signal= line"
    except Exception as exc:  # noqa: BLE001
        return "failed", str(exc)
    finally:
        try:
            Path(json_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Per-project coherence dispatcher (AOS-ARCH-EDGES-001). "
            "Runs the coherence probe against each opted-in project and posts "
            "a heartbeat to the AOS API."
        )
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("AOS_API_URL", "http://localhost:8000"),
        help="Base URL of the AOS API (default: $AOS_API_URL or http://localhost:8000).",
    )
    parser.add_argument(
        "--day",
        default=None,
        help=(
            "Audit day in YYYY-MM-DD format. "
            "Defaults to today's UTC date if not supplied."
        ),
    )
    args = parser.parse_args(argv)

    # Derive day outside importable code so datetime.now() is never called at
    # import time. Pass --day explicitly in tests for full hermeticity.
    day = args.day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    token: str | None = os.environ.get("AOS_TELEMETRY_TOKEN") or None
    base_url = args.api_url.rstrip("/")

    summary = dispatch(
        list_projects=_make_list_projects(base_url, token),
        get_repo_url=_make_get_repo_url(base_url, token),
        run_probe=_run_probe,
        clone_repo=_clone_repo,
        post_heartbeat=_make_post_heartbeat(base_url, token),
        day=day,
    )

    for entry in summary:
        parts = [f"project={entry['project_id']}", f"status={entry['status']}"]
        if entry.get("detail"):
            parts.append(f"detail={entry['detail']!r}")
        print(" ".join(parts))

    enabled = len(summary)
    findings = sum(1 for e in summary if e["status"] == "findings")
    failed = sum(1 for e in summary if e["status"] == "failed")
    print(f"\nSummary: {enabled} project(s) audited, {findings} findings, {failed} failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
