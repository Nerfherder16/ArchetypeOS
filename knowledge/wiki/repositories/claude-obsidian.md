# claude-obsidian

## Aliases

- AgriciDaniel/claude-obsidian
- AI second brain for Obsidian
- Karpathy LLM Wiki (Obsidian implementation)

## Status

evaluated

## Verdict

partial-borrow — do not vendor whole. AOS already implements the Karpathy LLM-Wiki pattern natively (`knowledge/wiki/`, reviewed in `docs/KARPATHY_OBSIDIAN_REVIEW.md`). ~80% overlaps existing subsystems; take two additive artifacts.

## Repo facts

- URL: https://github.com/AgriciDaniel/claude-obsidian
- Language: Python · License: MIT · Stars: ~9,048 · Last push: 2026-05-28
- Shape: a Claude Code plugin — 15 `SKILL.md` prompt docs, 3 sub-agent specs, `hooks/hooks.json`, ~12 shell/Python helper scripts. Core filing/linking is LLM reasoning, not deterministic code.

## AOS engines touched

- Knowledge Graph (overlap: high)
- Research Engine (overlap: high)
- Decision Intelligence (overlap: medium)
- knowledge/wiki/lessons (overlap: high)

## Overlap vs additive

- Overlap (reject): self-organizing filing, entity extraction, cross-linking, the wiki structure itself — AOS's `knowledge/wiki/` is already more structured.
- Additive (borrow):
  1. **BM25 + cosine retrieval scripts** (`scripts/bm25-index.py`, `retrieve.py`, `rerank.py`, `contextual-prefix.py`) — self-contained pure-Python, no Obsidian dependency, no LLM control flow. Satisfies **RFC-0010**. Effort ~2-4 days.
  2. **`skills/think/SKILL.md` frontmatter + 10-principle framework** — maps onto Decision Intelligence / ADR authoring. Docs-only. Effort ~1-2 days.

## Risks

- Bus factor of 1 (sole maintainer; marketing-mirror fork can diverge).
- Core skill logic is non-deterministic LLM reasoning — conflicts with "verification over inference" for authoritative knowledge.
- Prompt-injection surface: `autoresearch` writes arbitrary fetched web content into the vault; sanitization enforced by the same Claude, not deterministic code.
- MIT license — compatible; attribution required if code is vendored.

## Evidence

- [[../../../docs/repo-research/claude-obsidian|Full teardown]] — file inventory, dependency audit, 4 integration options, per-option risk
- `docs/KARPATHY_OBSIDIAN_REVIEW.md` — prior AOS review confirming the pattern was already adopted natively
- `docs/rfc/RFC-0010-Embedding-Relevance-Tier-Transfer-Engine.md` — the RFC the retrieval-script borrow serves

## Linked Decisions / Projects

- Plane AOS-59 — "Evaluate: claude-obsidian" (Done) — this evaluation, in the External Repo Evaluation & Adoption Pipeline module
- Plane AOS-60 — "Borrow BM25 retrieval scripts → RFC-0010" (Backlog / open) — the committed borrow
- Pending: RFC-0010 borrow — not yet graduated to a decision card
