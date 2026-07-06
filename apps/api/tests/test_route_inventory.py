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
        # digests
        ("POST", "/projects/{project_id}/digests"),
        ("GET", "/projects/{project_id}/digests"),
        ("GET", "/digests/{digest_id}"),
        # council
        ("POST", "/projects/{project_id}/council-reviews"),
        ("GET", "/projects/{project_id}/council-reviews"),
        ("GET", "/council-reviews/{review_id}"),
        # knowledge (AOS-KNOW-002 — global, not project-scoped)
        ("POST", "/knowledge/sync"),
        ("GET", "/knowledge/pages"),
        ("GET", "/knowledge/pages/{page_id}"),
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
    # /decisions/{decision_id}/approve, POST /decisions/{decision_id}/reject) = 45.
    assert len(EXPECTED_ROUTES) == 45
    assert len(_actual_routes()) == 45
