"""sync: decide's four actions, execute's write behavior, and the central
safety property — REPORT_PUBLISHED_DRIFT never writes, and a published
post is never updated."""

from __future__ import annotations

from datetime import date

import pytest

from blog_engine.ledger import content_hash, ledger_key
from blog_engine.models import (
    Ledger,
    LedgerEntry,
    PostDraft,
    PostStatus,
    SourceKind,
    SuppressedEntry,
    SyncAction,
)
from blog_engine.sync import (
    DuplicateSlugError,
    UnknownSuppressionKeyError,
    decide,
    execute,
    suppress,
    unsuppress,
)
from blog_engine.wordpress import WPPost


def _draft(slug: str = "range", markdown: str = "Some content.") -> PostDraft:
    return PostDraft(title="Range", slug=slug, markdown=markdown, category_slugs=("books",))


def _ledger_entry(
    slug: str = "range",
    *,
    content: str = "Some content.",
    status: PostStatus = PostStatus.DRAFT,
    post_id: int = 1,
) -> LedgerEntry:
    key = ledger_key(SourceKind.BOOK_NOTES, slug)
    return LedgerEntry(
        key=key,
        source=SourceKind.BOOK_NOTES,
        source_key="Range (May 2026 - 7/10)",
        content_hash=content_hash(content),
        wp_post_id=post_id,
        wp_status=status,
        slug=slug,
        first_synced=date(2026, 5, 1),
        last_synced=date(2026, 5, 1),
    )


def _suppressed_entry(
    slug: str = "range", *, reason: str = "Pre-existing backlog; retired without posting."
) -> SuppressedEntry:
    return SuppressedEntry(
        key=ledger_key(SourceKind.BOOK_NOTES, slug),
        source=SourceKind.BOOK_NOTES,
        source_key="Range (May 2026 - 7/10)",
        suppressed_on=date(2026, 5, 1),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# decide — all four actions.
# ---------------------------------------------------------------------------


def test_decide_create_when_key_absent() -> None:
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    assert decisions[0].action == SyncAction.CREATE


def test_decide_skip_unchanged_when_hash_matches() -> None:
    entry = _ledger_entry(content="Some content.")
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="Some content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.SKIP_UNCHANGED
    assert decisions[0].existing_post_id == entry.wp_post_id


def test_decide_update_draft_when_hash_differs_and_status_is_draft() -> None:
    entry = _ledger_entry(content="Old content.", status=PostStatus.DRAFT)
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="New content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.UPDATE_DRAFT


def test_decide_report_published_drift_when_hash_differs_and_status_is_publish() -> None:
    entry = _ledger_entry(content="Old content.", status=PostStatus.PUBLISH)
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="New content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.REPORT_PUBLISHED_DRIFT


def test_decide_report_published_drift_for_private_status_too() -> None:
    entry = _ledger_entry(content="Old content.", status=PostStatus.PRIVATE)
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="New content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.REPORT_PUBLISHED_DRIFT


def test_every_decision_has_a_reason() -> None:
    entry = _ledger_entry()
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].reason


def test_decide_raises_on_duplicate_slug_within_one_run() -> None:
    drafts = [
        (_draft(slug="range"), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)"),
        (_draft(slug="range"), SourceKind.BOOK_NOTES, "Range, Second Reading (June 2026 - 8/10)"),
    ]
    with pytest.raises(DuplicateSlugError) as exc_info:
        decide(drafts, Ledger())
    message = str(exc_info.value)
    assert "Range (May 2026 - 7/10)" in message
    assert "Range, Second Reading (June 2026 - 8/10)" in message


def test_decide_same_slug_different_source_does_not_collide() -> None:
    """Ledger keys are namespaced by source, so the same slug from two
    different docs is not a collision."""
    drafts = [
        (_draft(slug="widget-co"), SourceKind.BOOK_NOTES, "Widget Co (May 2026 - 7/10)"),
        (_draft(slug="widget-co"), SourceKind.ANGEL_PUBLIC, "Widget Co — Seed Deal Memo"),
    ]
    decisions = decide(drafts, Ledger())
    assert len(decisions) == 2


# ---------------------------------------------------------------------------
# decide — suppression beats every other rule.
# ---------------------------------------------------------------------------


def test_decide_skip_suppressed_for_a_suppressed_key() -> None:
    entry = _suppressed_entry()
    ledger = Ledger(suppressed={entry.key: entry})
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.SKIP_SUPPRESSED


def test_decide_suppression_reason_names_date_and_reason_text() -> None:
    entry = _suppressed_entry(reason="Not a fit for the blog.")
    ledger = Ledger(suppressed={entry.key: entry})
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, ledger)
    assert "2026-05-01" in decisions[0].reason
    assert "Not a fit for the blog." in decisions[0].reason


def test_decide_suppression_beats_a_changed_content_hash() -> None:
    """The central safety property of suppression: editing a suppressed
    entry upstream must not resurrect it. Even though the ledger also has a
    stale LedgerEntry whose hash would normally trigger UPDATE_DRAFT/
    REPORT_PUBLISHED_DRIFT, suppression is checked first and wins."""
    suppressed = _suppressed_entry()
    stale_entry = _ledger_entry(content="Completely different old content.")
    ledger = Ledger(entries={stale_entry.key: stale_entry}, suppressed={suppressed.key: suppressed})
    drafts = [(_draft(markdown="Brand new edited content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.SKIP_SUPPRESSED


def test_decide_suppression_beats_report_published_drift_too() -> None:
    suppressed = _suppressed_entry()
    published_entry = _ledger_entry(content="Old.", status=PostStatus.PUBLISH)
    ledger = Ledger(
        entries={published_entry.key: published_entry}, suppressed={suppressed.key: suppressed}
    )
    drafts = [(_draft(markdown="New."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    assert decisions[0].action == SyncAction.SKIP_SUPPRESSED


# ---------------------------------------------------------------------------
# execute — the central safety property.
# ---------------------------------------------------------------------------


class _FakeClient:
    """Records every call; never touches the network.

    `existing_posts` seeds `get_post_by_slug` — the lost-ledger adoption
    path `execute` uses before ever calling `create_post`."""

    def __init__(self, existing_posts: dict[str, WPPost] | None = None) -> None:
        self.created: list[PostDraft] = []
        self.updated: list[tuple[int, PostDraft]] = []
        self.slug_lookups: list[str] = []
        self._existing_posts = existing_posts or {}

    def get_post_by_slug(self, slug: str) -> WPPost | None:
        self.slug_lookups.append(slug)
        return self._existing_posts.get(slug)

    def create_post(self, draft: PostDraft, status: PostStatus) -> WPPost:
        self.created.append(draft)
        return WPPost(id=99, slug=draft.slug, status=status, link="https://example.com/99")

    def update_post(self, post_id: int, draft: PostDraft) -> WPPost:
        self.updated.append((post_id, draft))
        return WPPost(
            id=post_id, slug=draft.slug, status=PostStatus.DRAFT, link="https://example.com/x"
        )


def test_execute_create_calls_client_and_updates_ledger() -> None:
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    client = _FakeClient()
    ledger, report = execute(decisions, drafts, client, Ledger(), today=date(2026, 5, 1))
    assert len(client.created) == 1
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert key in ledger.entries
    assert ledger.entries[key].wp_post_id == 99
    assert any("CREATE" in line for line in report)


# ---------------------------------------------------------------------------
# execute — CREATE adopts an already-existing WordPress post instead of
# blindly duplicating when the ledger is absent/lost (see sync.py docstring).
# ---------------------------------------------------------------------------


def test_execute_create_looks_up_the_slug_before_creating() -> None:
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    client = _FakeClient()
    execute(decisions, drafts, client, Ledger(), today=date(2026, 5, 1))
    assert client.slug_lookups == ["range"]


def test_execute_create_with_no_existing_post_creates_normally() -> None:
    """The absent branch, made explicit against the new slug-lookup path."""
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    client = _FakeClient(existing_posts={})

    ledger, report = execute(decisions, drafts, client, Ledger(), today=date(2026, 5, 1))

    assert len(client.created) == 1
    assert client.updated == []
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert ledger.entries[key].wp_post_id == 99
    assert any("CREATE" in line for line in report)


def test_execute_create_adopts_existing_draft_instead_of_duplicating() -> None:
    """A lost/wiped ledger must not create a second post: if WordPress
    already has a draft at this slug, adopt it and refresh its content."""
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    existing = WPPost(id=42, slug="range", status=PostStatus.DRAFT, link="https://example.com/42")
    client = _FakeClient(existing_posts={"range": existing})

    ledger, report = execute(decisions, drafts, client, Ledger(), today=date(2026, 5, 1))

    assert client.created == []
    assert client.updated == [(42, drafts[0][0])]
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert ledger.entries[key].wp_post_id == 42
    assert ledger.entries[key].wp_status == PostStatus.DRAFT
    assert any("ADOPT" in line for line in report)


def test_execute_create_adopts_existing_published_post_with_no_write() -> None:
    """A lost ledger discovering an already-published post at this slug
    must record it in the ledger (so it isn't rediscovered every run) but
    never write to it — the same reasoning as REPORT_PUBLISHED_DRIFT."""
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, Ledger())
    existing = WPPost(id=42, slug="range", status=PostStatus.PUBLISH, link="https://example.com/42")
    client = _FakeClient(existing_posts={"range": existing})

    ledger, report = execute(decisions, drafts, client, Ledger(), today=date(2026, 5, 1))

    assert client.created == []
    assert client.updated == []
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert ledger.entries[key].wp_post_id == 42
    assert ledger.entries[key].wp_status == PostStatus.PUBLISH
    assert any("DRIFT" in line for line in report)


def test_execute_update_draft_calls_client() -> None:
    entry = _ledger_entry(content="Old content.", status=PostStatus.DRAFT)
    ledger_before = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="New content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger_before)
    client = _FakeClient()
    ledger_after, report = execute(decisions, drafts, client, ledger_before, today=date(2026, 6, 1))
    assert client.updated == [(entry.wp_post_id, drafts[0][0])]
    assert ledger_after.entries[entry.key].content_hash == content_hash("New content.")
    assert any("UPDATE" in line for line in report)


def test_execute_skip_unchanged_makes_no_client_calls() -> None:
    entry = _ledger_entry(content="Same content.")
    ledger = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="Same content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger)
    client = _FakeClient()
    execute(decisions, drafts, client, ledger)
    assert client.created == []
    assert client.updated == []


def test_execute_published_drift_performs_no_write() -> None:
    """The central safety property: a post whose content changed after
    going live is reported, never silently overwritten."""
    entry = _ledger_entry(content="Old content.", status=PostStatus.PUBLISH)
    ledger_before = Ledger(entries={entry.key: entry})
    drafts = [(_draft(markdown="New content."), SourceKind.BOOK_NOTES, "Range")]
    decisions = decide(drafts, ledger_before)
    client = _FakeClient()

    ledger_after, report = execute(decisions, drafts, client, ledger_before)

    assert client.created == []
    assert client.updated == []
    assert ledger_after == ledger_before  # untouched
    assert any("DRIFT" in line for line in report)


def test_execute_never_calls_update_for_a_published_post() -> None:
    """Even if a caller somehow constructed an UPDATE_DRAFT-shaped decision
    for a published ledger entry, execute's client interaction for drift is
    exercised via decide()'s own routing — this asserts the routing holds
    end to end for a batch mixing both outcomes."""
    draft_ledger_entry = _ledger_entry(
        slug="range", content="Old.", status=PostStatus.DRAFT, post_id=1
    )
    published_entry = _ledger_entry(
        slug="whale", content="Old whale.", status=PostStatus.PUBLISH, post_id=2
    )
    ledger_before = Ledger(
        entries={draft_ledger_entry.key: draft_ledger_entry, published_entry.key: published_entry}
    )
    drafts = [
        (_draft(slug="range", markdown="New."), SourceKind.BOOK_NOTES, "Range"),
        (
            _draft(slug="whale", markdown="New whale."),
            SourceKind.BOOK_NOTES,
            "Billion Dollar Whale",
        ),
    ]
    decisions = decide(drafts, ledger_before)
    client = _FakeClient()

    execute(decisions, drafts, client, ledger_before)

    assert client.updated == [(draft_ledger_entry.wp_post_id, drafts[0][0])]
    assert all(post_id != published_entry.wp_post_id for post_id, _ in client.updated)


def test_execute_skip_suppressed_makes_no_client_calls() -> None:
    entry = _suppressed_entry()
    ledger = Ledger(suppressed={entry.key: entry})
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    decisions = decide(drafts, ledger)
    client = _FakeClient()

    ledger_after, report = execute(decisions, drafts, client, ledger)

    assert client.created == []
    assert client.updated == []
    assert client.slug_lookups == []
    assert ledger_after == ledger  # untouched
    assert any("SUPPRESS" in line for line in report)


# ---------------------------------------------------------------------------
# suppress / unsuppress — the local-only backlog-retirement mechanism.
# ---------------------------------------------------------------------------


def test_suppress_records_every_entry_in_the_batch() -> None:
    drafts = [
        (_draft(slug="range"), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)"),
        (_draft(slug="whale"), SourceKind.BOOK_NOTES, "Billion Dollar Whale (April 2026 - 8/10)"),
    ]
    result = suppress(drafts, Ledger(), reason="Backlog.", today=date(2026, 7, 24))

    assert set(result.newly_suppressed) == {
        ledger_key(SourceKind.BOOK_NOTES, "range"),
        ledger_key(SourceKind.BOOK_NOTES, "whale"),
    }
    assert result.already_suppressed == ()
    assert result.already_posted == ()
    for key in result.newly_suppressed:
        entry = result.ledger.suppressed[key]
        assert entry.reason == "Backlog."
        assert entry.suppressed_on == date(2026, 7, 24)


def test_suppress_is_idempotent_on_already_suppressed_keys() -> None:
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    first = suppress(drafts, Ledger(), reason="Backlog.", today=date(2026, 7, 24))
    second = suppress(drafts, first.ledger, reason="Backlog, take two.", today=date(2026, 7, 25))

    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert second.newly_suppressed == ()
    assert second.already_suppressed == (key,)
    # The original suppression record is untouched by the idempotent call.
    assert second.ledger.suppressed[key].reason == "Backlog."
    assert second.ledger.suppressed[key].suppressed_on == date(2026, 7, 24)


def test_suppress_refuses_to_suppress_an_already_posted_key() -> None:
    """Suppressing a key that already has a real post would be a lie."""
    posted = _ledger_entry(slug="range")
    ledger = Ledger(entries={posted.key: posted})
    drafts = [(_draft(slug="range"), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]

    result = suppress(drafts, ledger, reason="Backlog.", today=date(2026, 7, 24))

    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert result.already_posted == (key,)
    assert result.newly_suppressed == ()
    assert key not in result.ledger.suppressed


def test_unsuppress_round_trips() -> None:
    drafts = [(_draft(), SourceKind.BOOK_NOTES, "Range (May 2026 - 7/10)")]
    suppressed_result = suppress(drafts, Ledger(), reason="Backlog.", today=date(2026, 7, 24))
    key = ledger_key(SourceKind.BOOK_NOTES, "range")
    assert key in suppressed_result.ledger.suppressed

    restored = unsuppress([key], suppressed_result.ledger)

    assert key not in restored.suppressed
    # Nothing else about the ledger changed.
    assert restored.entries == suppressed_result.ledger.entries


def test_unsuppress_unknown_key_raises_and_names_it() -> None:
    with pytest.raises(UnknownSuppressionKeyError, match="book_notes:nonexistent"):
        unsuppress(["book_notes:nonexistent"], Ledger())
