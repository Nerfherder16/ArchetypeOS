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
        # decision loop (AOS-COUNCIL-PHASEC — Council review → draft → approve/reject)
        ("POST", "/council-reviews/{review_id}/draft-decision"),
        ("POST", "/decisions/{decision_id}/approve"),
        ("POST", "/decisions/{decision_id}/reject"),
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
        ("POST", "/nodes/register"),
        ("POST", "/nodes/{node_id}/heartbeat"),
        ("GET", "/nodes"),
        ("GET", "/nodes/{node_id}"),
        ("GET", "/connectors"),
        ("GET", "/connectors/{name}"),
        ("POST", "/connectors/{name}/health"),
        ("GET", "/authority/action-classes"),
        ("POST", "/authority/evaluate"),
        ("GET", "/authority/pending"),
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
    # sources/{source_ref}/decision) = 71.
    assert len(EXPECTED_ROUTES) == 71
    assert len(_actual_routes()) == 71
