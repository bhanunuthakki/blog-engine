"""`blog-engine` command-line entry point (`click` group `main`)."""

from __future__ import annotations

import sys
from typing import Literal, cast

import click

from blog_engine.config import Settings, load_settings
from blog_engine.credentials import load_wordpress_credentials
from blog_engine.google_docs import GoogleDocsAuthError, ensure_credentials, fetch_paragraphs
from blog_engine.ledger import ledger_key, load_ledger, save_ledger
from blog_engine.models import SourceKind, SyncAction, SyncDecision
from blog_engine.render import render_book_notes, render_public_memo
from blog_engine.sources.angel_public import parse_public_memos
from blog_engine.sources.book_notes import parse_book_notes
from blog_engine.sync import (
    DraftBatch,
    UnknownSuppressionKeyError,
    decide,
    execute,
    suppress,
    unsuppress,
)
from blog_engine.wordpress import WordPressClient, WordPressError

SourceChoice = Literal["book", "memos", "all"]
_SOURCE_CHOICES = ("book", "memos", "all")
_DEFAULT_SUPPRESS_REASON = "Pre-existing backlog; retired without posting."


@click.group()
def main() -> None:
    """Sync the Book & Podcast Notes and [Public] Investing Memos docs to
    WordPress draft posts on bhanunuthakki.com."""
    _make_stdio_encode_safe()


@main.command()
@click.option("--source", type=click.Choice(_SOURCE_CHOICES), default="all", show_default=True)
@click.option(
    "--dry-run/--apply",
    default=True,
    help="--dry-run (default) only prints decisions; --apply writes to WordPress.",
)
@click.option("--limit", type=int, default=None, help="Cap the number of entries per source.")
@click.option(
    "--show-suppressed",
    is_flag=True,
    default=False,
    help="List every suppressed entry individually instead of a one-line summary.",
)
def sync(source: str, dry_run: bool, limit: int | None, show_suppressed: bool) -> None:
    """Fetch, parse, render, and decide what to sync — writing only with --apply."""
    settings = load_settings()
    ledger_path = settings.state_dir / "posted.json"
    ledger = load_ledger(ledger_path)
    drafts = _rendered_drafts(cast(SourceChoice, source), settings, limit)
    decisions = decide(drafts, ledger)
    _print_decisions(decisions, show_suppressed=show_suppressed)

    if dry_run:
        click.echo("\nDry run — no changes written. Re-run with --apply to sync.")
        return

    credentials = load_wordpress_credentials(settings.wordpress_env_path)
    client = WordPressClient(credentials)
    updated_ledger, report = execute(
        decisions, drafts, client, ledger, status=settings.default_status
    )
    save_ledger(ledger_path, updated_ledger)

    click.echo("")
    for line in report:
        click.echo(line)


@main.command("list-new")
@click.option("--source", type=click.Choice(_SOURCE_CHOICES), default="all", show_default=True)
@click.option("--limit", type=int, default=None, help="Cap the number of entries per source.")
@click.option(
    "--show-suppressed",
    is_flag=True,
    default=False,
    help="List every suppressed entry individually instead of a one-line summary.",
)
def list_new(source: str, limit: int | None, show_suppressed: bool) -> None:
    """Print sync decisions without writing anything — a dry-run summary."""
    settings = load_settings()
    ledger = load_ledger(settings.state_dir / "posted.json")
    drafts = _rendered_drafts(cast(SourceChoice, source), settings, limit)
    _print_decisions(decide(drafts, ledger), show_suppressed=show_suppressed)


@main.command()
@click.argument("slug")
def show(slug: str) -> None:
    """Print the rendered markdown for the source entry whose slug is SLUG."""
    settings = load_settings()
    drafts = _rendered_drafts(cast(SourceChoice, "all"), settings, None)
    for draft, _source, _raw_heading in drafts:
        if draft.slug == slug:
            click.echo(draft.markdown)
            return
    raise click.ClickException(f"No source entry found with slug '{slug}'.")


@main.command("check-auth")
def check_auth() -> None:
    """Verify WordPress credentials and Google Docs auth. Prints nothing secret."""
    settings = load_settings()
    credentials = load_wordpress_credentials(settings.wordpress_env_path)
    client = WordPressClient(credentials)
    try:
        name = client.verify_auth()
    except WordPressError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(f"WordPress OK — authenticated as '{name}' at {credentials.site_url}.")

    try:
        ensure_credentials()
    except GoogleDocsAuthError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo("Google Docs OAuth credentials OK.")


@main.command("suppress")
@click.option("--source", type=click.Choice(_SOURCE_CHOICES), default="all", show_default=True)
@click.option(
    "--reason",
    default=_DEFAULT_SUPPRESS_REASON,
    show_default=True,
    help="Recorded on every suppression; shown in `sync`'s decision reasons.",
)
@click.option("--limit", type=int, default=None, help="Cap the number of entries per source.")
def suppress_cmd(source: str, reason: str, limit: int | None) -> None:
    """Retire every current entry for SOURCE without ever posting it.

    A purely local ledger write — never touches WordPress, and needs no
    --apply. Anything added upstream *after* this runs is unaffected and
    will still sync normally."""
    settings = load_settings()
    ledger_path = settings.state_dir / "posted.json"
    ledger = load_ledger(ledger_path)
    drafts = _rendered_drafts(cast(SourceChoice, source), settings, limit)

    result = suppress(drafts, ledger, reason=reason)
    save_ledger(ledger_path, result.ledger)

    click.echo(
        f"Wrote {len(result.newly_suppressed)} suppression(s) to {ledger_path} "
        f"(reason: {reason!r})."
    )
    if result.newly_suppressed:
        titles_by_key = {ledger_key(source_kind, d.slug): d.title for d, source_kind, _ in drafts}
        click.echo("Suppressed:")
        for key in result.newly_suppressed:
            click.echo(f"  {titles_by_key.get(key, key)} ({key})")
    if result.already_posted:
        click.echo(
            f"Skipped {len(result.already_posted)} already-posted entr"
            f"{'y' if len(result.already_posted) == 1 else 'ies'} (suppressing would be a lie):"
        )
        for key in result.already_posted:
            click.echo(f"  {key}")
    if result.already_suppressed:
        click.echo(f"{len(result.already_suppressed)} were already suppressed (no-op).")


@main.command("unsuppress")
@click.argument("keys", nargs=-1, required=True)
def unsuppress_cmd(keys: tuple[str, ...]) -> None:
    """Remove one or more ledger KEYS from suppression, so they sync normally again."""
    settings = load_settings()
    ledger_path = settings.state_dir / "posted.json"
    ledger = load_ledger(ledger_path)
    try:
        updated = unsuppress(list(keys), ledger)
    except UnknownSuppressionKeyError as exc:
        raise click.ClickException(str(exc)) from None
    save_ledger(ledger_path, updated)
    click.echo(f"Removed {len(keys)} suppression(s): {', '.join(keys)}.")


def _rendered_drafts(source: SourceChoice, settings: Settings, limit: int | None) -> DraftBatch:
    """Fetch, parse, and render every entry for `source` (or both, for
    `"all"`), each paired with its `SourceKind` and upstream `raw_heading`."""
    drafts: DraftBatch = []

    if source in ("book", "all"):
        paragraphs = fetch_paragraphs(settings.book_notes_doc_id)
        entries = parse_book_notes(paragraphs, settings)
        if limit is not None:
            entries = entries[:limit]
        drafts.extend(
            (render_book_notes(entry, settings), SourceKind.BOOK_NOTES, entry.raw_heading)
            for entry in entries
        )

    if source in ("memos", "all"):
        paragraphs = fetch_paragraphs(settings.public_memos_doc_id)
        memo_entries = parse_public_memos(paragraphs, settings)
        if limit is not None:
            memo_entries = memo_entries[:limit]
        drafts.extend(
            (
                render_public_memo(entry, settings),
                SourceKind.ANGEL_PUBLIC,
                entry.raw_heading,
            )
            for entry in memo_entries
        )

    return drafts


def _make_stdio_encode_safe() -> None:
    """The source docs are full of curly quotes and em dashes. A Windows
    console on a legacy codepage (e.g. cp437) can't encode them — printed
    output degrading to `?` is acceptable, but a `UnicodeEncodeError`
    crashing the command mid-run is not. `TextIOWrapper.reconfigure` isn't
    on every stream (e.g. under pytest's capture), so this is a no-op there."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")


def _print_decisions(decisions: list[SyncDecision], *, show_suppressed: bool = False) -> None:
    """Print the decision table. A suppressed backlog can be large (that's
    the point of suppressing it), so by default `SKIP_SUPPRESSED` rows
    collapse into one summary line instead of drowning everything else;
    `--show-suppressed` expands them."""
    if not decisions:
        click.echo("No source entries found.")
        return

    suppressed = [d for d in decisions if d.action == SyncAction.SKIP_SUPPRESSED]
    visible = (
        decisions
        if show_suppressed
        else [d for d in decisions if d.action != SyncAction.SKIP_SUPPRESSED]
    )

    if visible:
        width = max(len(d.action.value) for d in visible)
        for d in visible:
            click.echo(f"{d.action.value.ljust(width)}  {d.title} — {d.reason}")

    if suppressed and not show_suppressed:
        noun = "entry" if len(suppressed) == 1 else "entries"
        click.echo(
            f"{SyncAction.SKIP_SUPPRESSED.value}  {len(suppressed)} {noun} suppressed "
            f"(use --show-suppressed to list)."
        )
