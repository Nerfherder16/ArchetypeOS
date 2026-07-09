# LES-L15 — adding docs under knowledge/wiki/repositories/ makes sync_knowledge derive them as repository KnowledgePages, breaking count-pinned knowledge tests

## Aliases

- test_knowledge.py assert 35 == 32 after adding repo register files
- keep-pile register shares the Distillation Engine's wiki/repositories/ dir
- a "docs-only" PR broke an API test
- N_LESSONS pin assumed a lessons-only vault

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- PR #153 (external repo eval keep-pile) added `knowledge/wiki/repositories/{index,claude-obsidian,claude-video}.md`. CI "API tests and lint" failed: `test_knowledge.py::test_sync_knowledge` (`assert 35 == 32`) and `test_knowledge_api`.
- Root cause: `sync_knowledge` (packages/aos_core/aos_core/services/knowledge.py) derives a `KnowledgePage(page_type="repository")` for every `wiki/repositories/*.md` with a `# ` heading (RFC-0008 Distillation Engine). `synced = lesson_count + decision_count + repository_count`. The test pinned `result["synced"] == N_LESSONS`, silently assuming the vault holds only lessons — true until this PR added the first real repository-dir pages.
- The keep-pile register and the Distillation Engine **share the same `wiki/repositories/` directory** for different purposes (evaluation judgment vs. onboarded-repo content extraction), so register files are counted as repository pages too — including `index.md`.
- Fix: made the assertions count-agnostic per the file's own LES-012 philosophy — assert self-consistency (`created == synced`, `updated == 0` on first sync; re-sync updates all) and lesson-specific facts filtered to `page_type == "lesson"`, never a pinned total. `docs/CAPABILITY_MAP.md` Layer 1 updated to record the register and the shared directory.

## Linked Decisions / Projects

- [[LES-012]] — the originating "derive counts from the live vault, never pin a magic total" rule; this is a fresh instance (repository pages, not lesson growth)
- [[LES-025]] — sibling "knowledge tests must derive live state, not pin it" (open lessons); same failure class
- [[LES-L14]] — the other session's account of the SAME keep-pile collision from the git-history side (my commit rode along as an ancestor of its PR)
- [[LES-003]] — the Guardian metadata/capability-map BLOCK that also fired on #153 repeats this; cited, not duplicated

## Content

- Event: a "docs/knowledge-only" PR broke an API test because the docs it added land in a directory that a service turns into DB rows.
- Root cause: a count-pinned test encoded a hidden assumption (lessons-only vault) that a new, legitimate page type invalidated. Anything under `wiki/repositories/` with a heading becomes a `repository` KnowledgePage — the keep-pile register shares that dir with the Distillation Engine.
- Rules:
  1. Adding files under `knowledge/wiki/{lessons,decisions,repositories}/` is never "just docs" — `sync_knowledge` projects them into `KnowledgePage` rows. Run `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests/test_knowledge.py` before assuming a vault change is test-neutral.
  2. Tests over the live vault must assert self-consistency + type-filtered facts, never a pinned cross-type total (LES-012 / LES-025). A new page type must not break them.
  3. The keep-pile register (`wiki/repositories/index.md` + per-repo pages) and Distillation Engine output coexist in one directory; keep that in mind when either counts or lists repository pages.
