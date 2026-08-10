"""Sync decision (pure) and execution (effectful), kept deliberately separate.

`decide` is the entire interesting policy and has no network dependency —
every rule it implements is testable without a WordPress client. `execute`
carries out the decisions; its central safety property is that
`REPORT_PUBLISHED_DRIFT` performs no write at all, so a live post can never
be silently overwritten just because the upstream doc changed.

`suppress`/`unsuppress` are a second, independent pure pair: they manage
`Ledger.suppressed` — the mechanism for retiring a pre-existing backlog
(entries that must never become posts) without touching WordPress at all,
while leaving anything added upstream *later* to flow through `decide`
normally. `decide` checks suppression first, ahead of the `entries` lookup,
so a suppressed entry stays suppressed even if its upstream content changes
— suppression is deliberately hash-free (see `models.SuppressedEntry`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from blog_engine.ledger import content_hash, ledger_key
from blog_engine.models import (
    Ledger,
    LedgerEntry,
    PostDraft,
    PostStatus,
    SourceKind,
    SuppressedEntry,
    SyncAction,
    SyncDecision,
)

DraftBatch = list[tuple[PostDraft, SourceKind, str]]
"""Rendered draft, which doc it came from, and the upstream `raw_heading`."""


class DuplicateSlugError(RuntimeError):
    """Raised when two source entries in the same run would render to the
    same ledger key. Left unchecked, the second draft would look like an
    edit of the first and silently overwrite it in the ledger — the same
    hazard `SyncAction.REPORT_PUBLISHED_DRIFT` exists to prevent, just one
    step earlier."""


class UnknownSuppressionKeyError(RuntimeError):
    """Raised by `unsuppress` when asked to lift a suppression that isn't
    currently recorded — almost certainly a typo'd key, not something to
    silently no-op on."""


class WordPressPost(Protocol):
    """The subset of `wordpress.WPPost` that `execute` reads."""

    id: int
    slug: str
    status: PostStatus
    link: str


class SyncClient(Protocol):
    """The subset of `wordpress.WordPressClient` that `execute` calls."""

    def get_post_by_slug(self, slug: str) -> WordPressPost | None: ...

    def create_post(self, draft: PostDraft, status: PostStatus) -> WordPressPost: ...

    def update_post(self, post_id: int, draft: PostDraft) -> WordPressPost: ...


def decide(drafts: DraftBatch, ledger: Ledger) -> list[SyncDecision]:
    """The pure verdict for every entry in `drafts`. No network."""
    _check_unique_keys(drafts)

    decisions: list[SyncDecision] = []
    for draft, source, _raw_heading in drafts:
        key = ledger_key(source, draft.slug)

        suppression = ledger.suppressed.get(key)
        if suppression is not None:
            decisions.append(
                SyncDecision(
                    key=key,
                    action=SyncAction.SKIP_SUPPRESSED,
                    title=draft.title,
                    reason=(
                        f"Suppressed on {suppression.suppressed_on.isoformat()}: "
                        f"{suppression.reason}"
                    ),
                )
            )
            continue

        existing = ledger.entries.get(key)

        if existing is None:
            decisions.append(
                SyncDecision(
                    key=key,
                    action=SyncAction.CREATE,
                    title=draft.title,
                    reason=f"No ledger entry for '{key}'; will create a new draft.",
                )
            )
            continue

        if existing.content_hash == content_hash(draft.markdown):
            decisions.append(
                SyncDecision(
                    key=key,
                    action=SyncAction.SKIP_UNCHANGED,
                    title=draft.title,
                    reason=f"Content hash unchanged since post #{existing.wp_post_id} was last synced.",
                    existing_post_id=existing.wp_post_id,
                )
            )
            continue

        if existing.wp_status == PostStatus.DRAFT:
            decisions.append(
                SyncDecision(
                    key=key,
                    action=SyncAction.UPDATE_DRAFT,
                    title=draft.title,
                    reason=f"Content changed and post #{existing.wp_post_id} is still a draft; will update it.",
                    existing_post_id=existing.wp_post_id,
                )
            )
            continue

        decisions.append(
            SyncDecision(
                key=key,
                action=SyncAction.REPORT_PUBLISHED_DRIFT,
                title=draft.title,
                reason=(
                    f"Content changed but post #{existing.wp_post_id} is "
                    f"'{existing.wp_status.value}', not draft; refusing to overwrite live content."
                ),
                existing_post_id=existing.wp_post_id,
            )
        )

    return decisions


def execute(
    decisions: list[SyncDecision],
    drafts: DraftBatch,
    client: SyncClient,
    ledger: Ledger,
    *,
    status: PostStatus = PostStatus.DRAFT,
    today: date | None = None,
) -> tuple[Ledger, list[str]]:
    """Carry out `decisions` against `client`. Returns the updated ledger and
    human-readable report lines, one per decision.

    `REPORT_PUBLISHED_DRIFT` performs no write — this is the property that
    keeps a live post from ever being silently overwritten.

    A `CREATE` decision means only "absent from *this* ledger" — `decide` is
    pure and never asked WordPress. Since the ledger is a local, gitignored
    cache (not durable — losing it, or checking out clean on a new machine,
    wipes it), `execute` double-checks with WordPress before creating:
    finding an existing post at the slug means adopting it (draft: refresh
    its content; non-draft: record it, no write, same reasoning as
    `REPORT_PUBLISHED_DRIFT`) instead of stamping out a duplicate."""
    run_date = today if today is not None else date.today()
    draft_by_key = {
        ledger_key(source, draft.slug): (draft, source, raw_heading)
        for draft, source, raw_heading in drafts
    }
    entries = dict(ledger.entries)
    report: list[str] = []

    for decision in decisions:
        if decision.action == SyncAction.SKIP_UNCHANGED:
            report.append(f"SKIP    {decision.title}: {decision.reason}")
            continue

        if decision.action == SyncAction.SKIP_SUPPRESSED:
            report.append(f"SUPPRESS {decision.title}: {decision.reason}")
            continue

        if decision.action == SyncAction.REPORT_PUBLISHED_DRIFT:
            report.append(f"DRIFT   {decision.title}: {decision.reason}")
            continue

        draft, source, raw_heading = draft_by_key[decision.key]
        new_hash = content_hash(draft.markdown)

        if decision.action == SyncAction.CREATE:
            existing_post = client.get_post_by_slug(draft.slug)

            if existing_post is None:
                post = client.create_post(draft, status)
                entries[decision.key] = LedgerEntry(
                    key=decision.key,
                    source=source,
                    source_key=raw_heading,
                    content_hash=new_hash,
                    wp_post_id=post.id,
                    wp_status=post.status,
                    slug=post.slug,
                    first_synced=run_date,
                    last_synced=run_date,
                )
                report.append(f"CREATE  {decision.title}: created post #{post.id} ({post.link}).")
                continue

            if existing_post.status == PostStatus.DRAFT:
                # The ledger lost track of this entry (a wiped/lost state
                # file, a fresh checkout on a new machine) but WordPress
                # already has a draft at this slug. Adopt it instead of
                # creating a duplicate.
                post = client.update_post(existing_post.id, draft)
                entries[decision.key] = LedgerEntry(
                    key=decision.key,
                    source=source,
                    source_key=raw_heading,
                    content_hash=new_hash,
                    wp_post_id=post.id,
                    wp_status=post.status,
                    slug=post.slug,
                    first_synced=run_date,
                    last_synced=run_date,
                )
                report.append(
                    f"ADOPT   {decision.title}: post #{post.id} already existed "
                    f"for this slug; recorded it and refreshed the draft."
                )
                continue

            # Exists and is not a draft (e.g. published) — same reasoning as
            # REPORT_PUBLISHED_DRIFT: it may have been published and hand-
            # edited on the site since. Record it in the ledger, from the
            # real post's own id/status/slug, so the next run recognizes it
            # instead of re-discovering the same drift every time — but
            # never write to a live post.
            entries[decision.key] = LedgerEntry(
                key=decision.key,
                source=source,
                source_key=raw_heading,
                content_hash=new_hash,
                wp_post_id=existing_post.id,
                wp_status=existing_post.status,
                slug=existing_post.slug,
                first_synced=run_date,
                last_synced=run_date,
            )
            report.append(
                f"DRIFT   {decision.title}: post #{existing_post.id} already "
                f"existed for this slug with status '{existing_post.status.value}'; "
                f"recorded it without writing — it may have been published and "
                f"edited by hand."
            )
            continue

        # UPDATE_DRAFT
        existing = ledger.entries[decision.key]
        post = client.update_post(existing.wp_post_id, draft)
        entries[decision.key] = existing.model_copy(
            update={
                "content_hash": new_hash,
                "wp_status": post.status,
                "slug": post.slug,
                "last_synced": run_date,
            }
        )
        report.append(f"UPDATE  {decision.title}: updated post #{post.id}.")

    return ledger.model_copy(update={"entries": entries}), report


@dataclass(frozen=True)
class SuppressionResult:
    """What `suppress()` did, for the CLI to report back to the user."""

    ledger: Ledger
    newly_suppressed: tuple[str, ...]
    """Keys suppressed by this call."""

    already_suppressed: tuple[str, ...]
    """Keys that were already suppressed — an idempotent no-op, not an error."""

    already_posted: tuple[str, ...]
    """Keys skipped because they're already in `ledger.entries` — suppressing
    a post that already exists would be a lie."""


def suppress(
    drafts: DraftBatch, ledger: Ledger, *, reason: str, today: date | None = None
) -> SuppressionResult:
    """Record every entry in `drafts` as suppressed. A purely local ledger
    operation — never touches WordPress.

    Skips (and reports back) any key already in `ledger.entries`, and is
    idempotent on keys already suppressed."""
    run_date = today if today is not None else date.today()
    suppressed = dict(ledger.suppressed)
    newly_suppressed: list[str] = []
    already_suppressed: list[str] = []
    already_posted: list[str] = []

    for draft, source, raw_heading in drafts:
        key = ledger_key(source, draft.slug)

        if key in ledger.entries:
            already_posted.append(key)
            continue

        if key in suppressed:
            already_suppressed.append(key)
            continue

        suppressed[key] = SuppressedEntry(
            key=key,
            source=source,
            source_key=raw_heading,
            suppressed_on=run_date,
            reason=reason,
        )
        newly_suppressed.append(key)

    return SuppressionResult(
        ledger=ledger.model_copy(update={"suppressed": suppressed}),
        newly_suppressed=tuple(newly_suppressed),
        already_suppressed=tuple(already_suppressed),
        already_posted=tuple(already_posted),
    )


def unsuppress(keys: list[str], ledger: Ledger) -> Ledger:
    """Remove `keys` from `ledger.suppressed` — the reverse of `suppress`.

    Raises `UnknownSuppressionKeyError` naming every key that isn't
    currently suppressed, rather than silently ignoring a typo."""
    missing = [key for key in keys if key not in ledger.suppressed]
    if missing:
        raise UnknownSuppressionKeyError(
            f"Not currently suppressed, so nothing to remove: {', '.join(missing)}."
        )
    remaining = {key: entry for key, entry in ledger.suppressed.items() if key not in keys}
    return ledger.model_copy(update={"suppressed": remaining})


def _check_unique_keys(drafts: DraftBatch) -> None:
    """Guard against two entries in one run rendering to the same ledger key
    — see `DuplicateSlugError`."""
    seen: dict[str, str] = {}
    for draft, source, raw_heading in drafts:
        key = ledger_key(source, draft.slug)
        if key in seen:
            raise DuplicateSlugError(
                f"Two source entries render to the same slug '{draft.slug}' "
                f"(key '{key}'): '{seen[key]}' and '{raw_heading}'. Rename one "
                f"upstream so they don't collide."
            )
        seen[key] = raw_heading
