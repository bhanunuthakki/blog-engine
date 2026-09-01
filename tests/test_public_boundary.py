import subprocess
from pathlib import Path

from blog_engine.public_boundary import violations


def test_public_boundary_is_clean() -> None:
    assert violations(Path(__file__).resolve().parents[1]) == []


def tracked_repo(tmp_path: Path, relative: str, content: str) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-f", relative], cwd=tmp_path, check=True)
    return tmp_path


def test_rejects_credential_content(tmp_path: Path) -> None:
    repo = tracked_repo(tmp_path, "notes.txt", "api_key='ghp_" + "A" * 30 + "'\n")
    assert violations(repo) == ["notes.txt"]


def test_rejects_personal_account_fact(tmp_path: Path) -> None:
    repo = tracked_repo(tmp_path, "notes.md", "my portfolio cost basis: $1234\n")
    assert violations(repo) == ["notes.md"]


def test_allows_synthetic_credential_assignment(tmp_path: Path) -> None:
    repo = tracked_repo(tmp_path, "notes.txt", "api_key='placeholder-value-123'\n")
    assert violations(repo) == []


def test_rejects_unscannable_private_document(tmp_path: Path) -> None:
    repo = tracked_repo(tmp_path, "exports/research.xlsx", "not really a workbook\n")
    assert violations(repo) == ["exports/research.xlsx"]
