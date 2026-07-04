#!/usr/bin/env python3
"""Deterministic PR Guardian checks for ArchetypeOS.

This script is intentionally conservative. It does not use an LLM and it does not
modify files. It blocks obvious PR hygiene, safety, and v0.1 governance failures
before reviewers spend time on a PR.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----"),
]

REQUIRED_FILES = [
    "docs/ENGINEERING_CONSTITUTION.md",
    "docs/CAPABILITY_MAP.md",
    "docs/V0_1_SCOPE_LOCK.md",
    "docs/RUNTIME_DECISION_RECORD.md",
    "docs/AUTHORITY_APPROVAL_ENGINE.md",
    "docs/KNOWLEDGE_VAULT_STRUCTURE.md",
    "docs/PR_GUARDIAN.md",
    "docker-compose.yml",
    ".env.example",
    "apps/api/requirements.txt",
    "apps/worker/requirements.txt",
    "apps/web/package.json",
]

CODE_PREFIXES = ("apps/api/app/", "apps/worker/app/", "apps/web/src/")
TEST_PREFIXES = ("apps/api/tests/", "apps/worker/tests/")
DOC_PREFIXES = ("docs/", "README.md", "CLAUDE.md", ".archetype/")
GOVERNANCE_DOC_ALLOWLIST = {
    "docs/CAPABILITY_MAP.md",
    "docs/ENGINEERING_CONSTITUTION.md",
    "docs/MASTER_ROADMAP.md",
    "docs/V0_1_SCOPE_LOCK.md",
    "docs/CONCRETE_BUILD_PATH.md",
}

ALLOWED_VERIFICATION_STATUSES = {
    "Verified",
    "Verified with warnings",
    "Verification pending",
    "Verification unavailable",
    "Verification blocked",
}
ALLOWED_VERIFICATION_LEVELS = {f"Level {level}" for level in range(6)}
REQUIRED_VERIFICATION_FIELDS = [
    "Verification Status",
    "Verification Level",
    "Verification Method",
    "Evidence",
    "Limitations",
    "Required Next Verifier",
]
MERGE_BLOCKING_VERIFICATION_STATUSES = {
    "Verification unavailable",
    "Verification blocked",
}


class GuardianError(RuntimeError):
    pass


def run_git(args: list[str]) -> str:
    completed = subprocess.run(["git", *args], check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def changed_files(base: str, head: str) -> list[str]:
    try:
        output = run_git(["diff", "--name-only", f"{base}...{head}"])
    except subprocess.CalledProcessError:
        output = run_git(["diff", "--name-only", f"{base}", f"{head}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def changed_file_statuses(base: str, head: str) -> dict[str, str]:
    try:
        output = run_git(["diff", "--name-status", f"{base}...{head}"])
    except subprocess.CalledProcessError:
        output = run_git(["diff", "--name-status", f"{base}", f"{head}"])
    statuses: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            statuses[parts[-1]] = parts[0]
    return statuses


def diff_text(base: str, head: str) -> str:
    try:
        return run_git(["diff", f"{base}...{head}"])
    except subprocess.CalledProcessError:
        return run_git(["diff", f"{base}", f"{head}"])


def read_body(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def has_override(body: str, key: str) -> bool:
    return f"PR_GUARDIAN_OVERRIDE_{key}" in body


def any_path(paths: Iterable[str], prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefixes) for path in paths)


def field_value(body: str, field: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(field)}\s*:\s*(.+?)\s*$", body)
    if not match:
        return None
    return match.group(1).strip()


def check_required_files() -> list[Finding]:
    findings: list[Finding] = []
    for file_name in REQUIRED_FILES:
        if not Path(file_name).exists():
            findings.append(Finding("block", "missing-required-file", f"Required foundation file is missing: {file_name}"))
    return findings


def check_secret_patterns(diff: str) -> list[Finding]:
    findings: list[Finding] = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(Finding("block", "possible-secret", "Potential secret detected in added diff line."))
                return findings
    return findings


def check_tests_for_code_changes(files: list[str], body: str) -> list[Finding]:
    findings: list[Finding] = []
    api_changed = any(path.startswith("apps/api/app/") for path in files)
    worker_changed = any(path.startswith("apps/worker/app/") for path in files)
    web_changed = any(path.startswith("apps/web/src/") for path in files)
    api_tests_changed = any(path.startswith("apps/api/tests/") for path in files)
    worker_tests_changed = any(path.startswith("apps/worker/tests/") for path in files)

    if api_changed and not api_tests_changed and not has_override(body, "TESTS"):
        findings.append(Finding("block", "missing-api-tests", "API code changed without API test changes. Add tests or include PR_GUARDIAN_OVERRIDE_TESTS with rationale."))
    if worker_changed and not worker_tests_changed and not has_override(body, "TESTS"):
        findings.append(Finding("block", "missing-worker-tests", "Worker code changed without worker test changes. Add tests or include PR_GUARDIAN_OVERRIDE_TESTS with rationale."))
    if web_changed and not has_override(body, "WEB_TESTS"):
        findings.append(Finding("warn", "web-tests-not-enforced", "Web source changed. Build is enforced, but UI tests are not yet available in v0.1."))
    return findings


def check_docs_for_code_changes(files: list[str], body: str) -> list[Finding]:
    findings: list[Finding] = []
    code_changed = any_path(files, CODE_PREFIXES) or "docker-compose.yml" in files or any(path.startswith(".github/workflows/") for path in files)
    docs_changed = any_path(files, DOC_PREFIXES)
    if code_changed and not docs_changed and not has_override(body, "DOCS"):
        findings.append(Finding("block", "missing-docs", "Implementation/runtime files changed without documentation updates. Update docs or include PR_GUARDIAN_OVERRIDE_DOCS with rationale."))
    return findings


def check_capability_map(files: list[str], statuses: dict[str, str], body: str) -> list[Finding]:
    findings: list[Finding] = []
    added_docs = [
        path
        for path in files
        if path.startswith("docs/")
        and path.endswith(".md")
        and statuses.get(path, "").startswith("A")
        and path not in GOVERNANCE_DOC_ALLOWLIST
        and not path.startswith("docs/rfc/")
    ]
    if added_docs and "docs/CAPABILITY_MAP.md" not in files and not has_override(body, "CAPABILITY_MAP"):
        findings.append(
            Finding(
                "block",
                "capability-map-not-updated",
                "New docs were added without updating docs/CAPABILITY_MAP.md. Add map changes or include PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP with rationale.",
            )
        )
    return findings


def check_high_risk_files(files: list[str], body: str) -> list[Finding]:
    findings: list[Finding] = []
    high_risk = [
        path
        for path in files
        if path in {"docker-compose.yml", ".env.example"}
        or path.startswith(".github/workflows/")
        or "auth" in path.lower()
        or "secret" in path.lower()
    ]
    if high_risk and not has_override(body, "HIGH_RISK_ACK"):
        findings.append(
            Finding(
                "warn",
                "high-risk-files",
                "High-risk files changed. PR body should include risk notes or PR_GUARDIAN_OVERRIDE_HIGH_RISK_ACK.",
            )
        )
    return findings


def check_no_runtime_junk(files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    forbidden_parts = ("__pycache__", ".pytest_cache", "node_modules", ".venv", "dist/")
    for path in files:
        if any(part in path for part in forbidden_parts) or path.endswith(".pyc"):
            findings.append(Finding("block", "runtime-junk", f"Runtime/build artifact should not be committed: {path}"))
    return findings


def check_verification_metadata(body: str) -> list[Finding]:
    findings: list[Finding] = []
    missing = [field for field in REQUIRED_VERIFICATION_FIELDS if field_value(body, field) is None]
    if missing:
        findings.append(
            Finding(
                "block",
                "missing-verification-metadata",
                "PR body is missing required verification metadata fields: " + ", ".join(missing),
            )
        )
        return findings

    status = field_value(body, "Verification Status")
    level = field_value(body, "Verification Level")
    if status not in ALLOWED_VERIFICATION_STATUSES:
        findings.append(
            Finding(
                "block",
                "invalid-verification-status",
                "Verification Status must be one of: " + ", ".join(sorted(ALLOWED_VERIFICATION_STATUSES)),
            )
        )
    elif status in MERGE_BLOCKING_VERIFICATION_STATUSES:
        findings.append(
            Finding(
                "block",
                "verification-not-mergeable",
                f"Verification Status '{status}' is not mergeable. Resolve verification before merge.",
            )
        )
    elif status == "Verification pending":
        findings.append(
            Finding(
                "warn",
                "verification-pending",
                "Verification is pending. This PR must not merge until the required next verifier records a stronger status.",
            )
        )

    if level not in ALLOWED_VERIFICATION_LEVELS:
        findings.append(
            Finding(
                "block",
                "invalid-verification-level",
                "Verification Level must be one of: " + ", ".join(sorted(ALLOWED_VERIFICATION_LEVELS)),
            )
        )

    for field in ("Verification Method", "Evidence", "Limitations", "Required Next Verifier"):
        value = field_value(body, field)
        if value is not None and value.strip().lower() in {"", "n/a", "none", "tbd", "todo"}:
            findings.append(
                Finding(
                    "warn",
                    "weak-verification-metadata",
                    f"{field} should contain concrete verification detail, not '{value}'.",
                )
            )

    return findings


def render(findings: list[Finding], files: list[str]) -> int:
    blocks = [finding for finding in findings if finding.severity == "block"]
    warnings = [finding for finding in findings if finding.severity == "warn"]

    print("# PR Guardian Report")
    print()
    print(f"Changed files: {len(files)}")
    for path in files:
        print(f"- {path}")
    print()

    if not findings:
        print("Verdict: PASS")
        print("No deterministic guardian findings.")
        return 0

    if blocks:
        print("Verdict: BLOCK")
    else:
        print("Verdict: PASS_WITH_WARNINGS")
    print()

    for finding in findings:
        print(f"- [{finding.severity.upper()}] {finding.code}: {finding.message}")

    return 1 if blocks else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PR Guardian checks.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--body-file", type=Path)
    args = parser.parse_args()

    body = read_body(args.body_file)
    files = changed_files(args.base, args.head)
    statuses = changed_file_statuses(args.base, args.head)
    diff = diff_text(args.base, args.head)

    findings: list[Finding] = []
    findings.extend(check_required_files())
    findings.extend(check_no_runtime_junk(files))
    findings.extend(check_secret_patterns(diff))
    findings.extend(check_tests_for_code_changes(files, body))
    findings.extend(check_docs_for_code_changes(files, body))
    findings.extend(check_capability_map(files, statuses, body))
    findings.extend(check_high_risk_files(files, body))
    findings.extend(check_verification_metadata(body))

    return render(findings, files)


if __name__ == "__main__":
    sys.exit(main())
