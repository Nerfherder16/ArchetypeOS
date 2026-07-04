from pathlib import Path
from app.repository_scanner import scan_repository


def test_scan_repository_detects_manifest_and_languages(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result["package_managers"] == ["npm"]
    assert result["language_mix"]["TypeScript"] == 1
    assert "Dockerfile" in result["deployment_files"]
    assert result["architecture_nodes"]
