## Layer 8: Self Learning and Evolution

Owns continuous improvement.

Capabilities:

- Nightly Self Learning Loop
- Learning Feedback Loop (lessons registry; RFC-0004)
- Evolution Intelligence
- Meta Agent
- Prompt and Workflow Evolution
- Engineering Simulation Lab
- Doc-staleness self-heal (AOS-20 detects doc-vs-reality drift; AOS-SELFHEAL-001 closes the loop to *correct* it — `tools/doc_staleness.py --fix` generates a deterministic reconciliation DRAFT from `git log` without editing prose or gaming the alarm (Article XII), a `post-merge` git hook regenerates it when `main` advances, and the `/reconcile-state` skill applies the narrative half for human approval. **AOS-SELFHEAL-002 adds the CI-on-main trigger** — `.github/workflows/doc-staleness-reconcile.yml` runs `--fix` on every merge and idempotently opens/updates (or auto-closes) a single `doc-staleness` tracking issue with the draft, catching drift the PR-Guardian WARN misses when no PR is open; the LLM narrative reconciliation is intended to run from a nightly Claude routine via `/reconcile-state`. **AOS-SELFHEAL-002b runs that narrative half** — a nightly routine (`scripts/nightly/reconcile_state.{sh,prompt.md}`, registered via `/schedule`; runbook `docs/runbooks/nightly-routines.md`) that gates deterministically on the detector, then wakes a headless `claude` to apply the reconciliation and **open a PR for review** (never merges); merging it is the merge that auto-closes the tracking issue. Remaining follow-ups: a Stop hook + in-container nightly-loop/digest wiring (needs a runner→DB path). **AOS-STATE-SEMANTIC-001 + AOS-STATE-RECON-002 add semantic-label drift** — beyond the numeric watermark/PR-lag checks, the detector now flags the P1-4 rot where the machine watermark is current but the human narrative still calls a *shipped* subsystem advisory/pending/proposed. Each subsystem is keyed on an ENFORCEMENT SYMBOL (`jobs.py::claim_job_for_node`, `connectors.py::connector_views`, `authority_envelope.py::consume_action`) not a file path — file existence is too weak because the module predates the enforcement — so a match means the behaviour is on the execution path and an Open-Decisions row calling it by a contradiction token is HARD drift; and `semantic-label-stale` is a PR-Guardian **BLOCK** (a shipped-but-mislabelled row is a lie, not the expected one-PR reconciliation lag), while every other doc-staleness signal stays an advisory WARN and the detector still fails open))
- Conflict self-heal (AOS-SELFHEAL-003: the repo learns from its own merge friction. `tools/conflict_digest.py` deterministically harvests the day's conflicts from two git-native substrates — `git rerere`'s rr-cache (marker conflicts + resolution state) and `git reflog` (rebase/merge/reset friction, which catches the union-auto-resolved coordination-doc conflicts rerere misses) — into `.archetype/conflicts/<date>.md`. A nightly routine (`scripts/nightly/conflict_learn.{sh,prompt.md}`, `/schedule`-registered) gates on that signal, then wakes a headless `claude` to distill **recurring** patterns into `LES-L##` draft lessons and **open a PR for review** — one-off noise produces nothing (Article XII). `scripts/install-hooks.sh` enables `rerere` so conflicts are recorded. Realizes the NIGHTLY_SELF_LEARNING_LOOP "detect repeated pain points" mandate for merge friction.)
- Audit heartbeat observability + per-project audits (AOS-SELFHEAL: each nightly self-learn probe (conflict / toil / coherence / session-pain) posts an `AuditHeartbeat` on every run — `clean` / `findings` / `failed` — via `POST /audits/heartbeat`, so a *missed* run is visible instead of silent; `GET /audits/heartbeats` backs the Control Tower **Nightly Audits** board. **Per-project audit toggle (AOS-SELFHEAL-PROJ-AUDITS):** a project opts any repo it manages into the loop, not just ArchetypeOS auditing itself — `Project.audits_enabled` (default off) toggled via `PATCH /projects/{id}`; `AuditHeartbeat.project_id` (soft reference, no FK) with composite uniqueness `(routine, project_id)` so a global routine (`project_id` NULL, the self-audit) and a per-project audit scope the same routine independently and never collide; `record_heartbeat` upserts per `(routine, project)`. The coherence probe already parameterizes by `--repo-root`, so a dispatcher can run the repo-state audit against each opted-in project's repo and post a per-project heartbeat — deferred follow-up.)

Primary artifacts:

- docs/rfc/RFC-0004-Learning-Feedback-Loop.md
- knowledge/wiki/lessons/index.md
- tools/doc_staleness.py (AOS-20 detector + AOS-SELFHEAL-001 `--fix` draft generator) with apps/api/tests/test_doc_staleness.py; scripts/hooks/post-merge + scripts/install-hooks.sh; skills/ci_devops/reconcile_state.md
- docs/NIGHTLY_SELF_LEARNING_LOOP.md
- docs/EVOLUTION_INTELLIGENCE.md
- docs/META_AGENT.md
- docs/PROMPT_WORKFLOW_EVOLUTION.md
- docs/ENGINEERING_SIMULATION_LAB.md
- packages/aos_core/aos_core/models.py (AuditHeartbeat + Project.audits_enabled), packages/aos_core/aos_core/services/audit_heartbeat.py, apps/api/app/routes/audits.py + routes/projects.py (PATCH toggle), apps/api/alembic/versions/0015_per_project_audits.py; scripts/nightly/heartbeat.sh

