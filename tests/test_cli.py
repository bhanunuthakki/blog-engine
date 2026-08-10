"""cli: exit codes and the `show` slug lookup, with network calls stubbed
out via monkeypatch so these stay fast and offline."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from blog_engine import cli
from blog_engine.config import Settings
from blog_engine.ledger import ledger_key, load_ledger, save_ledger
from blog_engine.models import Ledger, LedgerEntry, PostDraft, PostStatus, SourceKind
from blog_engine.sync import DraftBatch

_RANGE_DRAFT = PostDraft(title="Range", slug="range", markdown="Body text for Range.")
_RANGE_BATCH: DraftBatch = [(_RANGE_DRAFT, SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
_WHALE_DRAFT = PostDraft(title="Billion Dollar Whale", slug="whale", markdown="Body text.")
_TWO_ENTRY_BATCH: DraftBatch = [
    *_RANGE_BATCH,
    (_WHALE_DRAFT, SourceKind.BOOK_NOTES, "Billion Dollar Whale (April 2026 - 8/10)"),
]


def _returning(batch: DraftBatch) -> object:
    def rendered_drafts(
        source: cli.SourceChoice, settings: Settings, limit: int | None
    ) -> DraftBatch:
        return batch

    return rendered_drafts


def test_check_auth_exits_nonzero_when_credentials_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli, "load_settings", lambda: Settings(wordpress_env_path=tmp_path / "missing.env")
    )
    runner = CliRunner()
    result = runner.invoke(cli.main, ["check-auth"])
    assert result.exit_code != 0


def test_show_prints_markdown_for_matching_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    monkeypatch.setattr(cli, "load_settings", Settings)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["show", "range"])
    assert result.exit_code == 0
    assert "Body text for Range." in result.output


def test_show_exits_nonzero_when_slug_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning([]))
    monkeypatch.setattr(cli, "load_settings", Settings)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["show", "missing-slug"])
    assert result.exit_code != 0


def test_list_new_prints_decisions_without_writing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(state_dir=Path("nonexistent-state")))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["list-new"])
    assert result.exit_code == 0
    assert "create" in result.output.lower()


def test_sync_dry_run_default_does_not_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(state_dir=tmp_path / "state"))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["sync"])
    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert not (tmp_path / "state" / "posted.json").exists()


# ---------------------------------------------------------------------------
# Console-encoding safety: printing the doc's curly quotes/em dashes must
# never crash, even on a legacy-codepage Windows console.
# ---------------------------------------------------------------------------

_UNICODE_SAMPLE = "Franklin\N{RIGHT SINGLE QUOTATION MARK}s Life \N{EM DASH} An American Story"


def test_ascii_stream_would_raise_without_the_fix() -> None:
    """Sanity check that the scenario below is a real risk: an 'ascii'
    stream's default (strict) error handling does raise on these chars."""
    buffer = io.BytesIO()
    narrow_stdout = io.TextIOWrapper(buffer, encoding="ascii")
    with pytest.raises(UnicodeEncodeError):
        narrow_stdout.write(_UNICODE_SAMPLE)
        narrow_stdout.flush()


def test_make_stdio_encode_safe_prevents_unicode_encode_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = io.BytesIO()
    narrow_stdout = io.TextIOWrapper(buffer, encoding="ascii")
    monkeypatch.setattr(cli.sys, "stdout", narrow_stdout)

    cli._make_stdio_encode_safe()

    narrow_stdout.write(_UNICODE_SAMPLE)  # must not raise
    narrow_stdout.flush()
    buffer.seek(0)
    assert b"?" in buffer.read()


def test_show_prints_unicode_content_without_crashing(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = PostDraft(
        title="Franklin's Life", slug="franklins-life", markdown=f"Body with {_UNICODE_SAMPLE}."
    )
    monkeypatch.setattr(
        cli, "_rendered_drafts", _returning([(draft, SourceKind.BOOK_NOTES, "raw heading")])
    )
    monkeypatch.setattr(cli, "load_settings", Settings)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["show", "franklins-life"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# suppress / unsuppress commands.
# ---------------------------------------------------------------------------


def test_suppress_command_writes_ledger_and_prints_titles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_TWO_ENTRY_BATCH))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(state_dir=tmp_path / "state"))
    runner = CliRunner()

    result = runner.invoke(cli.main, ["suppress", "--source", "book"])

    assert result.exit_code == 0
    assert "Range" in result.output
    assert "Billion Dollar Whale" in result.output
    ledger = load_ledger(tmp_path / "state" / "posted.json")
    assert ledger_key(SourceKind.BOOK_NOTES, "range") in ledger.suppressed
    assert ledger_key(SourceKind.BOOK_NOTES, "whale") in ledger.suppressed


def test_suppress_command_uses_default_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(state_dir=tmp_path / "state"))
    runner = CliRunner()

    runner.invoke(cli.main, ["suppress"])

    ledger = load_ledger(tmp_path / "state" / "posted.json")
    entry = ledger.suppressed[ledger_key(SourceKind.BOOK_NOTES, "range")]
    assert entry.reason == "Pre-existing backlog; retired without posting."


def test_suppress_command_reports_already_posted_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(state_dir=tmp_path / "state")
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    posted_key = ledger_key(SourceKind.BOOK_NOTES, "range")
    posted_entry = LedgerEntry(
        key=posted_key,
        source=SourceKind.BOOK_NOTES,
        source_key="Range (May 2026 - 7/10)",
        content_hash="sha256:x",
        wp_post_id=7,
        wp_status=PostStatus.DRAFT,
        slug="range",
        first_synced=date(2026, 1, 1),
        last_synced=date(2026, 1, 1),
    )
    ledger_path = settings.state_dir / "posted.json"
    save_ledger(ledger_path, Ledger(entries={posted_key: posted_entry}))

    runner = CliRunner()
    result = runner.invoke(cli.main, ["suppress"])

    assert result.exit_code == 0
    assert "already-posted" in result.output.lower()
    ledger = load_ledger(ledger_path)
    assert posted_key not in ledger.suppressed


def test_unsuppress_command_removes_suppression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(state_dir=tmp_path / "state")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))
    ledger_path = settings.state_dir / "posted.json"

    runner = CliRunner()
    runner.invoke(cli.main, ["suppress"])
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert key in load_ledger(ledger_path).suppressed

    result = runner.invoke(cli.main, ["unsuppress", key])

    assert result.exit_code == 0
    assert key not in load_ledger(ledger_path).suppressed


def test_unsuppress_command_unknown_key_exits_nonzero_with_clear_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(state_dir=tmp_path / "state"))
    runner = CliRunner()

    result = runner.invoke(cli.main, ["unsuppress", "book_notes:nonexistent"])

    assert result.exit_code != 0
    assert "book_notes:nonexistent" in result.output


# ---------------------------------------------------------------------------
# --show-suppressed: summary line by default, full list on request.
# ---------------------------------------------------------------------------


def test_list_new_collapses_suppressed_entries_into_a_summary_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(state_dir=tmp_path / "state")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_TWO_ENTRY_BATCH))
    ledger_path = settings.state_dir / "posted.json"

    runner = CliRunner()
    runner.invoke(cli.main, ["suppress"])  # suppresses both entries

    result = runner.invoke(cli.main, ["list-new"])

    assert result.exit_code == 0
    assert "2 entries suppressed" in result.output
    assert "Range" not in result.output
    assert "Billion Dollar Whale" not in result.output
    assert load_ledger(ledger_path).suppressed  # sanity: they really are suppressed


def test_list_new_show_suppressed_flag_expands_the_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(state_dir=tmp_path / "state")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_rendered_drafts", _returning(_RANGE_BATCH))

    runner = CliRunner()
    runner.invoke(cli.main, ["suppress"])

    result = runner.invoke(cli.main, ["list-new", "--show-suppressed"])

    assert result.exit_code == 0
    assert "Range" in result.output
    assert "skip_suppressed" in result.output
