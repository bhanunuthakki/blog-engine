"""Checks for material that must not be committed to the public repository."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FORBIDDEN_TEXT = (
    "/Users/",
    "/home/",
    "C:\\Users\\",
)
FORBIDDEN_PATH_PARTS = (
    "/private/",
    "/corpus/",
    "/sources-private/",
    "/BLOG_NEXT_STEPS.txt/",
)
GOOGLE_DOC_URL = re.compile(r"https?://docs\.google\.com/document/d/[A-Za-z0-9_-]{20,}")
DOC_ID_LITERAL = re.compile(
    r"(?:BOOK_NOTES_DOC_ID|PUBLIC_MEMOS_DOC_ID)\s*=\s*[\"']([A-Za-z0-9_-]{20,})[\"']"
)


def violations(repo: Path) -> list[str]:
    raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, check=True, capture_output=True
    ).stdout
    found: list[str] = []
    for name in raw.decode().split("\0"):
        if not name:
            continue
        path = repo / name
        if not path.exists():
            continue
        relative = "/" + path.relative_to(repo).as_posix() + "/"
        if any(part in relative for part in FORBIDDEN_PATH_PARTS):
            found.append(name)
            continue
        if name == "src/blog_engine/public_boundary.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        has_document_id = False
        if not name.startswith("tests/"):
            has_document_id = GOOGLE_DOC_URL.search(text) is not None or any(
                not match.group(1).startswith("configure-")
                for match in DOC_ID_LITERAL.finditer(text)
            )
        if any(marker in text for marker in FORBIDDEN_TEXT) or has_document_id:
            found.append(name)
    return found
