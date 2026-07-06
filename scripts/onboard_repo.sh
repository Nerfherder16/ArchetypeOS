#!/usr/bin/env bash
set -euo pipefail

# onboard_repo.sh — acquire a repo into the dev repositories dir, then print
# the two API calls that finish onboarding (register + scan). AOS-21.
#
# Usage: onboard_repo.sh <git-url> <name> [ref]
#   <git-url>  git URL to clone (https / git@ / file://)
#   <name>     single path segment; the clone lands at $REPOSITORY_ROOT/<name>
#   [ref]      optional branch/tag to clone
#
# Requires: python3 with `aos_core` importable (installed, or via PYTHONPATH).
# This script adds packages/aos_core to PYTHONPATH so a bare checkout works.

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: onboard_repo.sh <git-url> <name> [ref]" >&2
  exit 2
fi

url="$1"
name="$2"
ref="${3:-}"

# Dev repositories dir (gitignored); matches Settings.repository_root default.
REPOSITORY_ROOT="${REPOSITORY_ROOT:-./repositories}"
export REPOSITORY_ROOT

# Resolve repo root from this script's location so aos_core is importable.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/packages/aos_core${PYTHONPATH:+:$PYTHONPATH}"

# 1) Acquire: shallow-clone into $REPOSITORY_ROOT/<name> (idempotent).
dest="$(python3 -m aos_core.services.onboarding "$url" "$name" ${ref:+"$ref"})"
echo "Acquired repository at: $dest" >&2

# 2) Finish onboarding against a running API. `local_path` is the segment name;
#    safe_repo_path resolves it under repository_root server-side.
cat <<EOF

# Repo acquired. Run these against the live API to finish onboarding:
#
# Register the repository under a project (returns the new REPO_ID):
curl -X POST "\${API_URL:-http://localhost:8000}/projects/\${PROJECT_ID}/repositories" \\
  -H 'Content-Type: application/json' \\
  -d '{"name": "$name", "local_path": "$name"}'

# Scan it (uses REPO_ID from the register response):
curl -X POST "\${API_URL:-http://localhost:8000}/repositories/\${REPO_ID}/scan"
EOF
