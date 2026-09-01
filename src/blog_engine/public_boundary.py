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
PERSONAL_EMAIL = re.compile(
    r"\b(?:bhanu|nuthakki)[^@\s]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE
)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
HIGH_CONFIDENCE_SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,})"
)
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)"
    r"\s*[=:]\s*[\"'](?P<value>[^\"'\s]{12,})[\"']",
    re.IGNORECASE,
)
SYNTHETIC_SECRET = re.compile(
    r"(?:dummy|example|fake|fixture|placeholder|redacted|changeme|not-a-real|test-token)",
    re.IGNORECASE,
)
PERSONAL_ACCOUNT_FACT = re.compile(
    r"\b(?:my|owner|personal|brokerage|portfolio|holding|account)\b.{0,80}"
    r"\b(?:cost[ _-]*basis|account[ _-]*balance|position[ _-]*(?:value|size)"
    r"|share[ _-]*quantity|shares|account[ _-]*(?:id|number))\b.{0,40}[$€£]?\d",
    re.IGNORECASE,
)
ACCOUNT_FACT_SUFFIXES = {".csv", ".json", ".md", ".tsv", ".txt", ".yaml", ".yml"}
UNSCANNABLE_PRIVATE_SUFFIXES = {".db", ".docx", ".pdf", ".sqlite", ".xlsx", ".zip"}


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
        if path.suffix.lower() in UNSCANNABLE_PRIVATE_SUFFIXES:
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
        has_secret = (
            PRIVATE_KEY.search(text) is not None
            or HIGH_CONFIDENCE_SECRET.search(text) is not None
        )
        if not has_secret:
            has_secret = any(
                not SYNTHETIC_SECRET.search(match.group("value"))
                for match in CREDENTIAL_ASSIGNMENT.finditer(text)
            )
        has_account_fact = (
            path.suffix.lower() in ACCOUNT_FACT_SUFFIXES
            and PERSONAL_ACCOUNT_FACT.search(text) is not None
        )
        if (
            any(marker in text for marker in FORBIDDEN_TEXT)
            or has_document_id
            or PERSONAL_EMAIL.search(text) is not None
            or has_secret
            or has_account_fact
        ):
            found.append(name)
    return found
