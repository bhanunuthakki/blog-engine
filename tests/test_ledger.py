"""ledger: round-trip, missing file, whitespace-insensitive hashing."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from blog_engine.ledger import content_hash, ledger_key, load_ledger, save_ledger
from blog_engine.models import Ledger, LedgerEntry, PostStatus, SourceKind, SuppressedEntry


def _entry(key: str = "book_notes:range") -> LedgerEntry:
    return LedgerEntry(
        key=key,
        source=SourceKind.BOOK_NOTES,
        source_key="Range (May 2026 - 7/10)",
        content_hash=content_hash("some content"),
        wp_post_id=42,
        wp_status=PostStatus.DRAFT,
        slug="range",
        first_synced=date(2026, 5, 1),
        last_synced=date(2026, 5, 1),
    )


def _suppressed(key: str = "angel_public:widget-co") -> SuppressedEntry:
    return SuppressedEntry(
        key=key,
        source=SourceKind.ANGEL_PUBLIC,
        source_key="Widget Co — Seed Deal Memo",
        suppressed_on=date(2026, 7, 24),
        reason="Pre-existing backlog; retired without posting.",
    )


def test_missing_file_returns_empty_ledger(tmp_path: Path) -> None:
    ledger = load_ledger(tmp_path / "does-not-exist.json")
    assert ledger == Ledger()
    assert ledger.entries == {}


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state" / "posted.json"
    original = Ledger(entries={"book_notes:range": _entry()})
    save_ledger(path, original)
    loaded = load_ledger(path)
    assert loaded == original


def test_round_trip_with_suppressed_entries(tmp_path: Path) -> None:
    path = tmp_path / "state" / "posted.json"
    original = Ledger(
        entries={"book_notes:range": _entry()},
        suppressed={"angel_public:widget-co": _suppressed()},
    )
    save_ledger(path, original)
    loaded = load_ledger(path)
    assert loaded == original
    assert loaded.suppressed["angel_public:widget-co"].reason == (
        "Pre-existing backlog; retired without posting."
    )


def test_ledger_written_before_suppressed_field_existed_still_loads(tmp_path: Path) -> None:
    """Backward compatibility: a `posted.json` on disk from before the
    `suppressed` field was added has no such key at all — it must still
    load, defaulting `suppressed` to empty rather than failing validation."""
    path = tmp_path / "posted.json"
    legacy_payload = {
        "version": 1,
        "entries": {
            "book_notes:range": json.loads(_entry().model_dump_json()),
        },
        # no "suppressed" key at all — simulates a pre-suppression ledger.
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    loaded = load_ledger(path)

    assert loaded.suppressed == {}
    assert "book_notes:range" in loaded.entries


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "posted.json"
    save_ledger(path, Ledger())
    assert path.is_file()


def test_save_is_atomic_no_leftover_tmp_file(tmp_path: Path) -> None:
    path = tmp_path / "posted.json"
    save_ledger(path, Ledger())
    assert not (tmp_path / "posted.json.tmp").exists()


def test_content_hash_is_stable_for_identical_text() -> None:
    assert content_hash("hello world") == content_hash("hello world")


def test_content_hash_ignores_whitespace_only_differences() -> None:
    a = content_hash("hello   world\n\nagain")
    b = content_hash("hello world again")
    assert a == b


def test_content_hash_differs_for_different_content() -> None:
    assert content_hash("hello world") != content_hash("goodbye world")


def test_content_hash_has_sha256_prefix() -> None:
    assert content_hash("x").startswith("sha256:")


def test_ledger_key_format() -> None:
    assert ledger_key(SourceKind.BOOK_NOTES, "range") == "book_notes:range"
    assert ledger_key(SourceKind.ANGEL_PUBLIC, "widget-co") == "angel_public:widget-co"
