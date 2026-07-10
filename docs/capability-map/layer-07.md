## Layer 7: Validation and Release Gates

Owns correctness, readiness, and verification.

Capabilities:

- Verification Protocol
- Verification Engine
- Verification Provider abstraction
- Local CLI verification provider
- GitHub Actions verification provider
- Docker verification provider
- Runtime Health verification provider
- Connector Inspection verification provider
- Human Approval verification provider
- PR Guardian
- CI enforcement
- branch protection setup
- branch freshness validation
- Auto-rebase open PRs (AOS-CI-AUTOREBASE-001, LES-L03: when `main` advances, `.github/workflows/auto-rebase-prs.yml` merges it into every open non-draft same-repo PR branch in a real runner — where the `.gitattributes merge=union` driver applies, unlike GitHub's server merge — so union-merged coordination logs self-heal and genuine conflicts get a manual-resolution comment. **AOS-CI-AUTOREBASE-002:** the rebased branch is pushed with a **GitHub App installation token** (`actions/create-github-app-token`, secrets `AUTOREBASE_APP_ID` / `AUTOREBASE_APP_PRIVATE_KEY`) instead of the default `GITHUB_TOKEN` — GitHub does not run workflows on `GITHUB_TOKEN`-pushed commits, so before this fix every auto-rebased head parked its CI run as `action_required` (0 jobs) and PR Guardian silently never ran on the current commit. The token step is gated on the App secret being present (surfaced via a job-level `env` — the `secrets` context is not allowed in `if:`, LES-L18) and both checkout + `GH_TOKEN` fall back to `GITHUB_TOKEN` when absent, so the workflow is safe before the secrets exist and auto-upgrades once they are added.)
- WSL local Level 2 verification
- post-merge validation
- doc-staleness detection (deterministic doc-vs-reality drift check; advisory PR Guardian WARN)
- Engineering Evaluation Standard
- Engineering Evolution Score
- benchmarks
- experiments
- risk register
- release readiness
- alpha self-evaluation review (system evaluates its own repository)
- Level 4 dashboard browser-drive verification

Primary artifacts:

- docs/ALPHA_REVIEW_V0_1.md
- .archetype/alpha/ (captured self-evaluation evidence)
- scripts/web_drive/ (headless-Chromium dashboard drives — seed corpus)
- apps/web/e2e/ (enforced Playwright e2e suite; CI web-e2e job)
- .archetype/guardian/accepted_warnings.json
- docs/VERIFICATION_PROTOCOL.md
- docs/PR_GUARDIAN.md
- docs/BRANCH_PROTECTION.md
- docs/POST_MERGE_VALIDATION.md
- docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md
- docs/WSL_WIN11_RUNTIME_TARGET.md
- scripts/pre_pr_guardian.sh
- scripts/post_merge_validation.sh
- tools/doc_staleness.py (deterministic doc-staleness detector — AOS-20, closes LES-007)
- .github/workflows/ci.yml
- .github/workflows/auto-rebase-prs.yml (AOS-CI-AUTOREBASE-001/002: union-aware auto-rebase of open PRs; App-token push so rebases re-trigger CI)
- docs/ENGINEERING_EVOLUTION_SCORE.md
- templates/benchmark_record.md
- templates/experiment_record.md
- templates/risk_register.csv

