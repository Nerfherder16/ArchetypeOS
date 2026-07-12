"""Refactor guard for AOS-APIROUTES-001.

Freezes the exact (method, path) set the API exposes. If the per-domain
router split ever drops, adds, or renames a route, this test fails. Filters to
FastAPI ``APIRoute`` instances so framework-internal routes (``/openapi.json``,
``/docs``, ``/redoc`` ...) are excluded.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app

EXPECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # health (app-level, stays in main.py)
        ("GET", "/health"),
        # projects
        ("POST", "/projects"),
        ("GET", "/projects"),
        ("GET", "/projects/{project_id}"),
        ("PATCH", "/projects/{project_id}"),
        # repositories
        ("POST", "/projects/{project_id}/repositories"),
        ("GET", "/projects/{project_id}/repositories"),
        ("GET", "/repositories/{repository_id}/dna"),
        # repository distillation (AOS-DISTILL-001 — RFC-0008 content extraction)
        ("POST", "/repositories/{repository_id}/distill"),
        # scans
        ("POST", "/repositories/{repository_id}/scan"),
        ("GET", "/repositories/{repository_id}/scans"),
        ("GET", "/repositories/{repository_id}/scans/{artifact_id}"),
        # architecture
        ("GET", "/projects/{project_id}/architecture"),
        ("PATCH", "/architecture/nodes/{node_id}"),
        ("PATCH", "/architecture/edges/{edge_id}"),
        # jobs
        ("POST", "/jobs"),
        ("GET", "/jobs/{job_id}"),
        ("GET", "/projects/{project_id}/jobs"),
        # schedules
        ("POST", "/projects/{project_id}/schedules"),
        ("GET", "/projects/{project_id}/schedules"),
        ("GET", "/schedules/{schedule_id}"),
        ("PATCH", "/schedules/{schedule_id}"),
        ("DELETE", "/schedules/{schedule_id}"),
        ("POST", "/schedules/{schedule_id}/run"),
        # artifacts
        ("POST", "/artifacts"),
        ("GET", "/projects/{project_id}/artifacts"),
        # decisions (decisions + research-notes + recommendations)
        ("POST", "/projects/{project_id}/decisions"),
        ("GET", "/projects/{project_id}/decisions"),
        ("GET", "/decisions/{decision_id}"),
        ("POST", "/projects/{project_id}/research-notes"),
        ("GET", "/projects/{project_id}/research-notes"),
        ("GET", "/research-notes/{note_id}"),
        ("POST", "/projects/{project_id}/recommendations"),
        ("GET", "/projects/{project_id}/recommendations"),
        ("GET", "/recommendations/{recommendation_id}"),
        # recommendation generator (AOS-RECO-ENGINE-001 — deterministic Technology
        # Fitness pass over RepositoryDNA + research; compare -> recommend seam)
        ("POST", "/projects/{project_id}/recommendations/generate"),
        # decision loop (AOS-COUNCIL-PHASEC — Council review → draft → approve/reject)
        ("POST", "/council-reviews/{review_id}/draft-decision"),
        ("POST", "/decisions/{decision_id}/approve"),
        ("POST", "/decisions/{decision_id}/reject"),
        # evolution engine (AOS-EVOLVE-001 — decision staleness + advisory re-evaluation)
        ("GET", "/projects/{project_id}/decisions/stale"),
        ("POST", "/decisions/{decision_id}/reevaluate"),
        # decision → knowledge (AOS-COUNCIL-PHASEC2A — approved decision → repo-vault ADR)
        ("POST", "/decisions/{decision_id}/adr"),
        # digests
        ("POST", "/projects/{project_id}/digests"),
        ("GET", "/projects/{project_id}/digests"),
        ("GET", "/digests/{digest_id}"),
        # council
        ("POST", "/projects/{project_id}/council-reviews"),
        ("GET", "/projects/{project_id}/council-reviews"),
        ("GET", "/council-reviews/{review_id}"),
        # research engine (AOS-RESEARCH-001 — RFC-0011 ranked evidence dossiers)
        ("POST", "/projects/{project_id}/research"),
        # multi-phase research plans (AOS-RESEARCH-003 — Finding 15)
        ("POST", "/projects/{project_id}/research-plans"),
        ("GET", "/projects/{project_id}/research-plans"),
        ("GET", "/research-plans/{plan_id}"),
        # research runs (AOS-RESEARCH-003 executor — criteria 2-5)
        ("POST", "/research-plans/{plan_id}/run"),
        ("GET", "/research-plans/{plan_id}/runs"),
        ("GET", "/research-runs/{run_id}"),
        ("POST", "/research-runs/{run_id}/sources/{source_ref:path}/decision"),
        # nightly-probe heartbeats (AOS-SELFHEAL observability)
        ("POST", "/audits/heartbeat"),
        ("GET", "/audits/heartbeats"),
        # knowledge (AOS-KNOW-002 — global, not project-scoped)
        ("POST", "/knowledge/sync"),
        ("GET", "/knowledge/pages"),
        ("GET", "/knowledge/pages/{page_id}"),
        # knowledge transfer (AOS-TRANSFER-001 — RFC-0009 portfolio reuse)
        ("POST", "/projects/{project_id}/transfer"),
        # usage ledger (AOS-USAGE-001 — LLM token/cost summary per tier)
        ("GET", "/usage/summary"),
        # voice command center (AOS-VOICE-001 — review-first voice turns + inbox)
        ("POST", "/voice/turns"),
        ("GET", "/voice/inbox"),
        # voice inbox review (AOS-VOICE-003 — approve/dismiss a draft)
        ("PATCH", "/voice/inbox/{item_id}"),
        # voice TTS (AOS-VOICE-004 — Groq Orpheus spoken replies)
        ("POST", "/voice/speak"),
        # node registry (AOS-NODE-001 — distributed runtime)
        ("POST", "/nodes/enroll"),
        ("POST", "/nodes/register"),
        ("POST", "/nodes/{node_id}/heartbeat"),
        # AOS-AUTH-BOUNDARY-001: operator-owned credential lifecycle
        ("POST", "/nodes/{node_id}/rotate-credential"),
        ("POST", "/nodes/{node_id}/revoke-credential"),
        ("GET", "/nodes"),
        ("GET", "/nodes/route"),
        ("GET", "/nodes/{node_id}"),
        ("GET", "/connectors"),
        ("POST", "/connectors/reconcile"),
        ("GET", "/connectors/{name}"),
        ("POST", "/connectors/{name}/probe"),
        ("POST", "/connectors/{name}/health"),
        ("GET", "/authority/action-classes"),
        ("POST", "/authority/evaluate"),
        ("GET", "/authority/pending"),
        ("POST", "/authority/actions"),
        ("POST", "/authority/actions/{action_id}/authorize"),
        ("POST", "/authority/actions/{action_id}/reject"),
        ("GET", "/authority/actions/{action_id}"),
        # implementation plans (AOS-BUILD-PLAN-001 — RFC-0015 Design §1, Decision → Plan)
        ("POST", "/decisions/{decision_id}/plan"),
        ("GET", "/plans/{plan_id}"),
        ("GET", "/projects/{project_id}/plans"),
        ("POST", "/plans/{plan_id}/approve"),
        # evidence spine API (AOS-EVIDENCE-API-001 — RFC-0018 HTTP surface over
        # services/evidence.py)
        ("POST", "/projects/{project_id}/sources"),
        ("GET", "/projects/{project_id}/sources"),
        ("POST", "/sources/{source_id}/versions"),
        ("GET", "/sources/{source_id}/versions"),
        ("POST", "/source-versions/{version_id}/fragments"),
        ("POST", "/projects/{project_id}/claims"),
        ("GET", "/projects/{project_id}/claims"),
        ("GET", "/claims/{claim_id}"),
        ("POST", "/claims/{claim_id}/evidence"),
        ("POST", "/claims/{claim_id}/relationships"),
        ("POST", "/projects/{project_id}/conflicts"),
        ("GET", "/projects/{project_id}/conflicts"),
        ("PATCH", "/conflicts/{conflict_id}"),
        ("POST", "/projects/{project_id}/corpus-snapshots"),
        ("GET", "/projects/{project_id}/corpus-snapshots"),
        ("POST", "/decisions/{decision_id}/project-claim"),
        # evidence backfill (AOS-EVIDENCE-BACKFILL-001 — RFC-0018 C5: project
        # EXISTING RepositoryDNA/Decision/Recommendation/Evaluation/Risk/
        # ResearchRun rows into the claim model)
        ("POST", "/projects/{project_id}/evidence-backfill"),
        # genome API (AOS-GENOME-API-001 — RFC-0019 §16 HTTP surface over
        # services/genome.py)
        ("POST", "/projects/{project_id}/genomes/generate"),
        ("GET", "/projects/{project_id}/genomes"),
        ("GET", "/genomes/{genome_id}"),
        ("POST", "/genomes/{genome_id}/review"),
        ("POST", "/genomes/{genome_id}/approve"),
        ("GET", "/genomes/{genome_id}/questions"),
        ("POST", "/genomes/{from_id}/compare/{to_id}"),
        # foundation API (AOS-FOUNDATION-API-001 — RFC-0020 design §16 HTTP
        # surface over services/foundation.py)
        ("POST", "/projects/{project_id}/foundation-runs"),
        ("GET", "/projects/{project_id}/foundation-runs"),
        ("GET", "/foundation-runs/{run_id}"),
        ("POST", "/foundation-runs/{run_id}/compile-requirements"),
        ("POST", "/foundation-runs/{run_id}/generate-candidates"),
        ("POST", "/foundation-runs/{run_id}/evaluate-eligibility"),
        ("POST", "/foundation-runs/{run_id}/candidates"),
        ("GET", "/candidates/{candidate_id}"),
        ("POST", "/candidates/{candidate_id}/score"),
        ("POST", "/candidates/{candidate_id}/elements"),
    }
)


def _actual_routes() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }


def test_route_inventory_matches_frozen_set() -> None:
    actual = _actual_routes()
    assert actual == EXPECTED_ROUTES, {
        "missing": EXPECTED_ROUTES - actual,
        "unexpected": actual - EXPECTED_ROUTES,
    }


def test_route_inventory_count() -> None:
    # 38 domain routes + GET /health = 39 (method, path) pairs, plus the 3
    # AOS-KNOW-002 knowledge routes (POST /knowledge/sync, GET /knowledge/pages,
    # GET /knowledge/pages/{page_id}) = 42, plus the 3 AOS-COUNCIL-PHASEC decision
    # -loop routes (POST /council-reviews/{review_id}/draft-decision, POST
    # /decisions/{decision_id}/approve, POST /decisions/{decision_id}/reject) = 45,
    # plus the AOS-COUNCIL-PHASEC2A ADR export route (POST
    # /decisions/{decision_id}/adr) = 46, plus the AOS-DISTILL-001 repository
    # distillation route (POST /repositories/{repository_id}/distill) = 47,
    # plus the AOS-TRANSFER-001 knowledge-transfer route (POST
    # /projects/{project_id}/transfer) = 48, plus the AOS-USAGE-001 usage-ledger
    # route (GET /usage/summary) = 49, plus the AOS-VOICE-001 Voice Command Center
    # routes (POST /voice/turns, GET /voice/inbox) = 51, plus the AOS-RESEARCH-001
    # research-engine route (POST /projects/{project_id}/research) = 52, plus the
    # AOS-VOICE-004 TTS route (POST /voice/speak) = 53, plus the AOS-VOICE-003
    # inbox-review route (PATCH /voice/inbox/{item_id}) = 54, plus the AOS-NODE-001
    # node-registry routes (POST /nodes/register, POST /nodes/{node_id}/heartbeat,
    # GET /nodes, GET /nodes/{node_id}) = 58, plus the AOS-CONNECTOR-001 connector
    # -registry routes (GET /connectors, GET /connectors/{name}, POST
    # /connectors/{name}/health) = 61, plus the AOS-AUTHORITY-001 authority-policy
    # routes (GET /authority/action-classes, POST /authority/evaluate, GET
    # /authority/pending) = 64, plus the AOS-RESEARCH-003 research-plan routes
    # (POST /projects/{project_id}/research-plans, GET /projects/{project_id}/
    # research-plans, GET /research-plans/{plan_id}) = 67, plus the AOS-RESEARCH-003
    # research-run routes (POST /research-plans/{plan_id}/run, GET /research-plans/
    # {plan_id}/runs, GET /research-runs/{run_id}, POST /research-runs/{run_id}/
    # sources/{source_ref}/decision) = 71, plus the AOS-SELFHEAL heartbeat routes
    # (POST /audits/heartbeat, GET /audits/heartbeats) = 73, plus the per-project
    # audit toggle (PATCH /projects/{project_id}) = 74, plus the
    # AOS-NODE-IDENTITY-001 enrollment route (POST /nodes/enroll) = 75, the
    # AOS-AUTHORITY-ENVELOPE-001 action-request routes (POST /authority/actions,
    # POST /authority/actions/{id}/authorize, POST /authority/actions/{id}/reject,
    # GET /authority/actions/{id}) = 79, the AOS-NODE-AGENT-001 routing route
    # (GET /nodes/route) = 80, and the AOS-CONNECTOR-RUNTIME-001 routes
    # (POST /connectors/reconcile, POST /connectors/{name}/probe) = 82.
    # AOS-AUTH-BOUNDARY-001 added the operator credential rotate/revoke routes = 84.
    # AOS-BUILD-PLAN-001 added the implementation-plan routes (POST
    # /decisions/{decision_id}/plan, GET /plans/{plan_id}, GET
    # /projects/{project_id}/plans, POST /plans/{plan_id}/approve) = 88.
    # AOS-RECO-ENGINE-001 added the recommendation-generator route (POST
    # /projects/{project_id}/recommendations/generate) = 89.
    # AOS-EVOLVE-001 added the evolution-engine routes (GET
    # /projects/{project_id}/decisions/stale, POST
    # /decisions/{decision_id}/reevaluate) = 91.
    # AOS-EVIDENCE-API-001 added the Evidence Spine HTTP API routes (POST/GET
    # /projects/{project_id}/sources, POST/GET /sources/{source_id}/versions,
    # POST /source-versions/{version_id}/fragments, POST/GET
    # /projects/{project_id}/claims, GET /claims/{claim_id}, POST
    # /claims/{claim_id}/evidence, POST /claims/{claim_id}/relationships,
    # POST/GET /projects/{project_id}/conflicts, PATCH /conflicts/{conflict_id},
    # POST/GET /projects/{project_id}/corpus-snapshots, POST
    # /decisions/{decision_id}/project-claim) = 107.
    # AOS-EVIDENCE-BACKFILL-001 added the evidence-backfill route (POST
    # /projects/{project_id}/evidence-backfill) = 108.
    # AOS-GENOME-API-001 added the genome HTTP API routes (POST
    # /projects/{project_id}/genomes/generate, GET /projects/{project_id}/genomes,
    # GET /genomes/{genome_id}, POST /genomes/{genome_id}/review, POST
    # /genomes/{genome_id}/approve, GET /genomes/{genome_id}/questions, POST
    # /genomes/{from_id}/compare/{to_id}) = 115.
    # AOS-FOUNDATION-API-001 added the foundation HTTP API routes (POST/GET
    # /projects/{project_id}/foundation-runs, GET /foundation-runs/{run_id}, POST
    # /foundation-runs/{run_id}/compile-requirements, POST
    # /foundation-runs/{run_id}/generate-candidates, POST
    # /foundation-runs/{run_id}/evaluate-eligibility, POST
    # /foundation-runs/{run_id}/candidates, GET /candidates/{candidate_id}, POST
    # /candidates/{candidate_id}/score, POST /candidates/{candidate_id}/elements) = 125.
    assert len(EXPECTED_ROUTES) == 125
    assert len(_actual_routes()) == 125
