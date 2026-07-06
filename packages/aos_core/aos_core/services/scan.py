from datetime import datetime, timezone
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from aos_core.config import get_settings
from aos_core.models import ArchitectureEdge, ArchitectureNode, Artifact, Repository, RepositoryDNA, new_id
from aos_core.repository_scanner import safe_repo_path, scan_repository


def run_scan(repository_id: str, db: Session) -> dict:
    settings = get_settings()
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        repo_path = safe_repo_path(settings.repository_root, repository.local_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scan = scan_repository(repo_path)
    repository.last_scanned_at = datetime.now(timezone.utc)

    dna = repository.dna or RepositoryDNA(repository_id=repository.id)
    dna.language_mix = scan["language_mix"]
    dna.package_managers = scan["package_managers"]
    dna.frameworks = scan.get("frameworks", [])
    dna.deployment_files = scan["deployment_files"]
    dna.runtime_services = scan["summary"].get("runtime_services", [])
    dna.risk_flags = scan["risk_flags"]
    dna.scan_summary = scan
    dna.confidence = 0.65
    dna.evidence = ["read-only repository scanner"]
    dna.status = "draft"
    db.add(dna)

    root_node = (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.repository_id == repository.id, ArchitectureNode.type == "repository")
        .first()
    )
    if root_node:
        root_node.label = repository.name
        root_node.confidence = 0.9
        root_node.evidence = ["registered repository"]
    else:
        root_node = ArchitectureNode(
            project_id=repository.project_id,
            repository_id=repository.id,
            label=repository.name,
            type="repository",
            confidence=0.9,
            evidence=["registered repository"],
            status="draft",
        )
    db.add(root_node)
    db.flush()
    # The scan report labels its root by the directory name (scan["root_name"]);
    # register the DB root node under both so contains edges (from=root_name)
    # and any repository-scoped edge resolve to it.
    node_by_label = {repository.name: root_node, scan["root_name"]: root_node}
    nodes_out = [{"id": root_node.id, "label": root_node.label, "type": root_node.type, "confidence": root_node.confidence}]

    for item in scan["architecture_nodes"][1:]:
        node = (
            db.query(ArchitectureNode)
            .filter(
                ArchitectureNode.repository_id == repository.id,
                ArchitectureNode.type == item["type"],
                ArchitectureNode.label == item["label"],
                ArchitectureNode.parent_id == root_node.id,
            )
            .first()
        )
        if node:
            node.confidence = item["confidence"]
            node.evidence = item["evidence"]
        else:
            node = ArchitectureNode(
                project_id=repository.project_id,
                repository_id=repository.id,
                label=item["label"],
                type=item["type"],
                parent_id=root_node.id,
                confidence=item["confidence"],
                evidence=item["evidence"],
                status="draft",
            )
        db.add(node)
        db.flush()
        node_by_label[item["label"]] = node
        nodes_out.append({"id": node.id, "label": node.label, "type": node.type, "confidence": node.confidence})

    edges_out = []
    for item in scan["architecture_edges"]:
        from_node = node_by_label.get(item["from"])
        to_node = node_by_label.get(item["to"])
        if not from_node or not to_node:
            continue
        edge = (
            db.query(ArchitectureEdge)
            .filter(
                ArchitectureEdge.repository_id == repository.id,
                ArchitectureEdge.from_node_id == from_node.id,
                ArchitectureEdge.to_node_id == to_node.id,
                ArchitectureEdge.type == item["type"],
            )
            .first()
        )
        if edge:
            edge.confidence = item["confidence"]
            edge.evidence = item["evidence"]
        else:
            edge = ArchitectureEdge(
                project_id=repository.project_id,
                repository_id=repository.id,
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                type=item["type"],
                confidence=item["confidence"],
                evidence=item["evidence"],
                status="draft",
            )
        db.add(edge)
        db.flush()
        edges_out.append({"id": edge.id, "from_node_id": edge.from_node_id, "to_node_id": edge.to_node_id, "type": edge.type, "confidence": edge.confidence})

    artifact_body = json.dumps(scan, indent=2, sort_keys=True)
    checksum = hashlib.sha256(artifact_body.encode("utf-8")).hexdigest()
    artifact_id = new_id()
    artifact_name = f"repository-scan-{artifact_id}.json"
    artifact_dir = settings.artifact_root / repository.project_id / repository.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / artifact_name
    artifact_path.write_text(artifact_body, encoding="utf-8")
    artifact = Artifact(
        id=artifact_id,
        project_id=repository.project_id,
        repository_id=repository.id,
        artifact_type="repository_scan",
        name=artifact_name,
        path=str(artifact_path),
        content_type="application/json",
        checksum=checksum,
        size_bytes=len(artifact_body.encode("utf-8")),
        summary="Read-only repository scan report",
    )
    db.add(artifact)
    db.commit()

    return {
        "repository_id": repository.id,
        "summary": scan,
        "dna": {
            "language_mix": dna.language_mix,
            "package_managers": dna.package_managers,
            "frameworks": dna.frameworks,
            "deployment_files": dna.deployment_files,
            "risk_flags": dna.risk_flags,
            "confidence": dna.confidence,
        },
        "architecture_nodes": nodes_out,
        "architecture_edges": edges_out,
        "artifacts": [{"id": artifact.id, "name": artifact.name, "path": artifact.path, "checksum": artifact.checksum}],
    }
