#!/usr/bin/env bash
# Install the repo's git hooks (AOS-SELFHEAL-001) via core.hooksPath so they are
# versioned with the repo instead of living in each dev's local .git/hooks.
# Run once after cloning: `bash scripts/install-hooks.sh`.
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
git -C "${REPO_ROOT}" config core.hooksPath scripts/hooks
chmod +x "${REPO_ROOT}"/scripts/hooks/* 2>/dev/null || true
echo "Installed git hooks: core.hooksPath -> scripts/hooks"
echo "Hooks: $(ls "${REPO_ROOT}/scripts/hooks" 2>/dev/null | tr '\n' ' ')"

# Enable git rerere so resolved conflicts are recorded into .git/rr-cache — the
# deterministic substrate for the conflict self-learn nightly (AOS-SELFHEAL-003).
# Without this, resolved conflicts leave almost no trace and the nightly cannot
# learn from them.
git -C "${REPO_ROOT}" config rerere.enabled true
git -C "${REPO_ROOT}" config rerere.autoupdate true
echo "Enabled git rerere (conflict recording for AOS-SELFHEAL-003)"
