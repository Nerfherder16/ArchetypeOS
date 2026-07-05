from sqlalchemy.orm import Session
from aos_core.models import Artifact, Decision, NightlyDigest, Recommendation, Repository, ResearchNote, now_utc


def build_digest(project_id: str, db: Session) -> NightlyDigest:
    scan_artifacts = (
        db.query(Artifact)
        .filter(Artifact.project_id == project_id, Artifact.artifact_type == "repository_scan")
        .order_by(Artifact.created_at.desc(), Artifact.id)
        .limit(20)
        .all()
    )
    decisions = (
        db.query(Decision)
        .filter(Decision.project_id == project_id)
        .order_by(Decision.created_at.desc(), Decision.id)
        .limit(20)
        .all()
    )
    research_notes = (
        db.query(ResearchNote)
        .filter(ResearchNote.project_id == project_id)
        .order_by(ResearchNote.created_at.desc(), ResearchNote.id)
        .limit(20)
        .all()
    )
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.project_id == project_id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id)
        .limit(20)
        .all()
    )
    repositories = db.query(Repository).filter(Repository.project_id == project_id).order_by(Repository.name, Repository.id).all()

    changes: list[dict] = []
    for artifact in scan_artifacts:
        changes.append(
            {
                "type": "repository_scan",
                "repository_id": artifact.repository_id,
                "artifact": artifact.name,
                "at": artifact.created_at.isoformat(),
            }
        )
    for decision in decisions:
        changes.append({"type": "decision", "title": decision.title, "at": decision.created_at.isoformat()})
    for note in research_notes:
        changes.append({"type": "research_note", "title": note.title, "at": note.created_at.isoformat()})
    for recommendation in recommendations:
        changes.append({"type": "recommendation", "title": recommendation.title, "at": recommendation.created_at.isoformat()})

    # repeated tasks: repositories scanned more than once (all scan artifacts, not just the recent 20)
    scan_counts: dict[str, int] = {}
    for repository_id, in (
        db.query(Artifact.repository_id)
        .filter(Artifact.project_id == project_id, Artifact.artifact_type == "repository_scan")
        .all()
    ):
        if repository_id is None:
            continue
        scan_counts[repository_id] = scan_counts.get(repository_id, 0) + 1
    repeated_tasks = [
        {"task": "repository_scan", "repository_id": repository_id, "count": count}
        for repository_id, count in sorted(scan_counts.items())
        if count > 1
    ]

    draft_recommendations: list[dict] = []
    # rule 1: repository DNA risk_flags mention missing tests
    for repository in repositories:
        dna = repository.dna
        if dna is None:
            continue
        matching = next(
            (flag for flag in dna.risk_flags if isinstance(flag, str) and "test" in flag.lower()),
            None,
        )
        if matching is not None:
            draft_recommendations.append(
                {"title": f"Add tests to {repository.name}", "reason": matching, "status": "draft"}
            )
    # rule 2: repository registered but never scanned
    for repository in repositories:
        if repository.last_scanned_at is None:
            draft_recommendations.append(
                {
                    "title": f"Run a scan for {repository.name}",
                    "reason": "repository registered but never scanned",
                    "status": "draft",
                }
            )
    # rule 3: decision with no typed research_note evidence
    unlinked_decisions = sorted(
        (
            decision
            for decision in decisions
            if not any(
                isinstance(entry, dict) and entry.get("type") == "research_note" for entry in decision.evidence
            )
        ),
        key=lambda decision: decision.title,
    )
    for decision in unlinked_decisions:
        draft_recommendations.append(
            {
                "title": f"Link research to decision: {decision.title}",
                "reason": "decision has no linked research",
                "status": "draft",
            }
        )
    # rule 4: project has scans but no decisions
    if scan_artifacts and not decisions:
        draft_recommendations.append(
            {
                "title": "Record the first decision for this project",
                "reason": "scans exist but no decisions",
                "status": "draft",
            }
        )

    n_repos = len(repositories)
    n_scans = sum(scan_counts.values())
    n_decisions = len(decisions)
    n_notes = len(research_notes)
    n_recs = len(recommendations)
    n_drafts = len(draft_recommendations)
    summary = (
        f"{n_repos} repositories, {n_scans} scan runs, {n_decisions} decisions, "
        f"{n_notes} research notes, {n_recs} recommendations; {n_drafts} draft suggestions"
    )

    return NightlyDigest(
        project_id=project_id,
        digest_date=now_utc(),
        summary=summary,
        changes=changes,
        recommendations=draft_recommendations,
        repeated_tasks=repeated_tasks,
    )
