#!/usr/bin/env bash
#
# AOS-SELFHEAL observability — shared heartbeat helper for the nightly self-learn
# probes. Source this and call `aos_heartbeat <routine> <status> <day> [pr_url]`.
#
# Every probe posts a heartbeat on every outcome (clean / findings / failed) to the
# ArchetypeOS API so a MISSED run is visible instead of silent. The post is
# best-effort: a failure only logs — it never changes the probe's exit code or
# outcome (Article: telemetry must not gate the work).
#
# Env:
#   AOS_API_URL          base URL of the ArchetypeOS API (default http://localhost:8000)
#   AOS_TELEMETRY_TOKEN  x-telemetry-token, only if the endpoint is configured to require one

aos_heartbeat() {
  local routine="$1" status="$2" day="$3" pr_url="${4:-}"
  local api="${AOS_API_URL:-http://localhost:8000}"
  local body
  if [ -n "$pr_url" ]; then
    body=$(printf '{"routine":"%s","status":"%s","day":"%s","pr_url":"%s"}' "$routine" "$status" "$day" "$pr_url")
  else
    body=$(printf '{"routine":"%s","status":"%s","day":"%s"}' "$routine" "$status" "$day")
  fi
  if curl -s --max-time 15 -X POST "${api}/audits/heartbeat" \
      -H "Content-Type: application/json" \
      ${AOS_TELEMETRY_TOKEN:+-H "x-telemetry-token: ${AOS_TELEMETRY_TOKEN}"} \
      -d "$body" >/dev/null 2>&1; then
    return 0
  fi
  echo "[heartbeat] post failed for routine=${routine} status=${status} (non-fatal)" >&2
  return 0
}
