---
description: Run the deterministic PR Guardian against the current branch diff (add "full" for the complete local gate)
---

Run ArchetypeOS's deterministic PR Guardian and report its verdict. Never bypass a BLOCK finding; overrides (`PR_GUARDIAN_OVERRIDE_*`) require recorded rationale in the PR body.

Arguments: `$ARGUMENTS` — optional. `full` runs the complete local gate; any other value is treated as a path to a PR-body file.

1. Freshness: `git fetch origin main`.
2. Resolve the PR body file:
   - If a body-file path was passed in the arguments, use it.
   - Else, if a PR is open for the current branch, save its body to a temp file and use that (the guardian validates the real Verification Metadata).
   - Else, run without `--body-file` overrides: `scripts/pre_pr_guardian.sh` provides a compliant placeholder body automatically.
3. Run the check:
   - Default: `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>`
   - `full`: `bash scripts/pre_pr_guardian.sh` (guardian + compileall + pytest for api and worker + web build + compose config).
4. Report back verbatim: the verdict line (`PASS` / `PASS_WITH_WARNINGS` / `BLOCK`), every finding, the scanner-informed checks line, and the exit code.
5. If the verdict is BLOCK: identify the offending files/lines, propose the fix, and do not push until a re-run passes. If a finding is a false positive, use the matching override token in the PR body with a one-line rationale — never edit the guardian to silence it.

The guardian is read-only and deterministic (`docs/PR_GUARDIAN.md`). Merges additionally require the Manual Merge Gate: a head-SHA-pinned verification comment with CI evidence.
