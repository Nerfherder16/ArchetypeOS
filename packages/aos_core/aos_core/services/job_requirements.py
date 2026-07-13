"""Server-owned job execution requirements (AOS-NODE-EXECUTION-001).

A job's ``required_capability`` / ``sensitivity`` / ``requires_write`` are DERIVED
here at origination — never trusted from the client — so routing decides which node
may run a job from a server-authoritative source. This mirrors the worker's
per-handler ``HandlerSpec`` (capability/sensitivity), kept in agreement by
``test_job_requirements_match_handlers``. AOS-AUTHORITY-HARDEN-001 (WP4) extends
this registry with the action class.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobRequirement:
    capability: str
    sensitivity: str = "public"
    requires_write: bool = False
    # AOS-AUTHORITY-HARDEN-001: the action class is SERVER-OWNED — derived here, never
    # supplied by the client. The authority chokepoint classifies a job from this, so
    # a client can no longer submit a write/egress handler as ``read_only``.
    action_class: str = "read_only"


# job_type → execution requirements. Adding a job type adds a row here (and its
# worker handler module). Values agree with the worker HandlerSpecs. All current
# handlers are read-only, in-process analysis (no external egress / repo write) →
# ``read_only``; a future write/deploy/egress job declares its real class here and
# the origination chokepoint will then demand an authorized envelope for it.
JOB_REQUIREMENTS: dict[str, JobRequirement] = {
    "repository_scan": JobRequirement(capability="scan"),
    "project_digest": JobRequirement(capability="digest"),
    "council_review": JobRequirement(capability="council"),
    "foundation_council_review": JobRequirement(capability="council"),
    "research": JobRequirement(capability="research"),
    "research_run": JobRequirement(capability="research"),
    "test": JobRequirement(capability="noop"),
}


def get_requirement(job_type: str) -> JobRequirement | None:
    """The requirement for a known job type, or ``None`` if the type is unknown."""
    return JOB_REQUIREMENTS.get(job_type)


__all__ = ["JobRequirement", "JOB_REQUIREMENTS", "get_requirement"]
