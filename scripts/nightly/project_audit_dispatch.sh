#!/usr/bin/env bash
#
# AOS-PROJECT-AUDIT-DISPATCH — per-project coherence dispatcher (local-cron path).
#
# Runs tools/project_audit_dispatch.py: for every project with audits_enabled it
# clones the project's repo, runs the coherence probe against it, and posts a
# per-project heartbeat (routine=coherence, project_id=<id>) to the AOS API.
#
# This is a LOCAL cron, not a cloud routine: the dispatcher needs the full API
# (GET /projects, GET /projects/{id}/repositories) which is NOT on the public
# /audits funnel — only reachable on the tailnet. Run it on a tailnet host with
# git + python, pointing AOS_API_URL at the API.
#
# Env:
#   AOS_API_URL          base URL of the AOS API (default the tailnet API below)
#   AOS_TELEMETRY_TOKEN  x-telemetry-token, only if the endpoint requires one
#
# Crontab (this WSL host reaches teevee over tailscale):
#   30 4 * * * AOS_API_URL=http://teevee.tail612d5.ts.net:8000 \
#     /home/nerfherder/Dev/ArchetypeOS/scripts/nightly/project_audit_dispatch.sh \
#     >> /home/nerfherder/Dev/ArchetypeOS/.archetype/project-audits/nightly.log 2>&1
#
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO_ROOT"

LOG_DIR=".archetype/project-audits"
mkdir -p "$LOG_DIR"
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

export AOS_API_URL="${AOS_API_URL:-http://teevee.tail612d5.ts.net:8000}"
DAY="$(date -u +%Y-%m-%d)"

log "Dispatching per-project coherence audits (api=$AOS_API_URL, day=$DAY)."
python3 tools/project_audit_dispatch.py --api-url "$AOS_API_URL" --day "$DAY"
log "Done — per-project heartbeats posted for any audits_enabled projects."
