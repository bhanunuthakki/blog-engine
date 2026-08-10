"""Load/save the ledger (`state/posted.json`) and its content-hash primitive.

The hash is computed over whitespace-normalized text so a trivial upstream
reformat (extra blank line, retyped spacing) doesn't look like a content
change and trigger a needless `UPDATE_DRAFT`/`REPORT_PUBLISHED_DRIFT`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from blog_engine.models import Ledger, SourceKind

_WHITESPACE_RE = re.compile(r"\s+")


def load_ledger(path: Path) -> Ledger:
    """Read the ledger at `path`; a missing file is an empty ledger, not an
    error — the first sync run has nothing to have recorded yet."""
    if not path.is_file():
        return Ledger()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Ledger.model_validate(raw)


def save_ledger(path: Path, ledger: Ledger) -> None:
    """Write `ledger` atomically: a full write followed by a rename, so a
    crash mid-write can never leave a half-written ledger on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.tmp"
    tmp_path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)


def content_hash(text: str) -> str:
    """`sha256:<hex>` over `text` with all whitespace runs collapsed to a
    single space and the ends trimmed."""
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def ledger_key(source: SourceKind, slug: str) -> str:
    return f"{source.value}:{slug}"
