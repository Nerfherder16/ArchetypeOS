## Layer 0: Constitution and Governance

Owns the rules of the system.

Capabilities:

- Engineering Constitution
- RFC process
- Arbiter and Final Judge rules
- decision lifecycle
- human approval model
- authority action policy (AOS-AUTHORITY-001: enforced action-class policy — no write/destructive path bypasses `requires_approval`)
- safety model
- agent contract
- agent hierarchy
- external review triage

Primary artifacts:

- docs/ENGINEERING_CONSTITUTION.md
- docs/CONSTITUTION_AMENDMENTS.md
- docs/RFC_PROCESS.md
- docs/ARBITER_FINAL_JUDGE.md
- docs/DECISION_LIFECYCLE.md
- docs/AUTHORITY_POLICY.md (AOS-AUTHORITY-001: action classes + central requires_approval evaluator; GET /authority/action-classes, POST /authority/evaluate, GET /authority/pending)
- docs/AGENT_HIERARCHY_AND_COMMUNICATION.md
- docs/EXTERNAL_REVIEW_TRIAGE_2026_07_04.md
- agents/UNIVERSAL_AGENT_CONTRACT.md
- knowledge/wiki/reviews/2026-07-08-archetypeos-system-evaluation.md (AOS-REVIEW-001 system evaluation)
- docs/reviews/2026-07-10-recall-shakedown.md (first foreign-project shakedown: scan/DNA/reasoned-distill proven on System-Recall; found the read-only-vault deployed-distill constraint + the unbounded-prompt free-tier silent-floor bug (#50); §4 decides distillation stays local-first build-time)
- docs/reviews/2026-07-10-rfc0013-slice1-reality-test.md (RFC-0013 Slice-1 capability-extraction reality gate: 5-repo portfolio run showed select_source_files is the ceiling (3 heuristic attempts failed) + free-pool provider variance; pivots to a whole-repo symbol digest + deterministic cite-must-exist hallucination filter + retry-on-empty)
- docs/CONSOLIDATION_PLAN.md (AOS-REVIEW-001 phased execution plan / consolidation roadmap)

