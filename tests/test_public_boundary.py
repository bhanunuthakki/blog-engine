from pathlib import Path

from blog_engine.public_boundary import violations


def test_public_boundary_is_clean() -> None:
    assert violations(Path(__file__).resolve().parents[1]) == []
