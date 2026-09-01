"""The typed contract every other module speaks.

Three families of types, in pipeline order:

  1. **Source entries** — what a parser extracts from an upstream Google Doc.
     `BookNotesEntry` (Book & Podcast Notes Master) and `PublicMemoEntry`
     ([Public] Investing Memos). Both are frozen and carry `raw_heading`, the
     verbatim upstream heading that identifies the entry forever after.

  2. **Post draft** — `PostDraft`, a rendered post plus its taxonomy, ready to
     hand to the WordPress client. Markdown in, blocks out at the boundary.

  3. **Ledger + sync plan** — `LedgerEntry` records what has already been
     pushed; `SyncDecision` is the *pure* verdict about what to do with one
     source entry on this run. Computing decisions is separate from executing
     them so the interesting logic is testable without network.

The safety rule that shapes the whole design lives in `SyncAction`: a source
entry whose content changed after its post went live yields
`REPORT_PUBLISHED_DRIFT`, never a silent overwrite of public content.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class SourceKind(StrEnum):
    """Where an entry originated. Also the ledger key's namespace prefix."""

    BOOK_NOTES = "book_notes"
    ANGEL_PUBLIC = "angel_public"
    NATIVE = "native"
    """Written directly via the `book-review` skill; no upstream doc to diff."""


class MediaKind(StrEnum):
    """Whether a Book & Podcast Notes entry is a book or a podcast episode."""

    BOOK = "book"
    PODCAST = "podcast"


class PostStatus(StrEnum):
    """WordPress post statuses this project uses."""

    DRAFT = "draft"
    PUBLISH = "publish"
    PENDING = "pending"
    PRIVATE = "private"
    FUTURE = "future"


# ---------------------------------------------------------------------------
# Source entries
# ---------------------------------------------------------------------------


class Bullet(BaseModel):
    """One bullet, flattened with an explicit nesting depth.

    Google Docs reports list nesting as `bullet.nestingLevel`, and the block
    renderer re-nests from `depth`. A flat list with depth beats a recursive
    tree here: it maps 1:1 onto the API's own representation, and both the
    parsers and the renderer stay loop-shaped instead of recursive.
    """

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    depth: int = Field(default=0, ge=0, le=3)


class ThemeBlock(BaseModel):
    """One `Theme N: <label>` section of a Book & Podcast Notes entry."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    """The theme name with its `Theme N:` prefix stripped."""

    summary: str = ""
    """The one-line gloss that follows the theme heading, when present."""

    bullets: tuple[Bullet, ...] = ()


class BookNotesEntry(BaseModel):
    """A parsed entry from the Book & Podcast Notes (Master) doc.

    Heading shapes in the wild — the parser must handle all three:
      `Benjamin Franklin: An American Life (June 2026 - 8/10)`
      `Acquired Podcast, <Episode> (March 2026 - 8/10)`
      `Some Title (WIP)` / `Some Title (DNF)`
    """

    model_config = ConfigDict(frozen=True)

    raw_heading: str = Field(min_length=1)
    """Verbatim heading text. The stable identity used for ledger lookup and
    for dedupe against the upstream doc — never a derived or cleaned form."""

    title: str = Field(min_length=1)
    media: MediaKind
    month_label: str | None = None
    """e.g. `June 2026`, as written. Absent on entries with no date."""

    rating: int | None = Field(default=None, ge=1, le=10)
    """Absent only when the heading carries no score — the doc writes that as
    `(December 2025 - NA)`. A `[DNF]` entry usually still has a rating."""

    status_flags: tuple[str, ...] = ()
    """`("WIP",)` / `("DNF",)` when the heading carries one."""

    source_url: str | None = None
    """The episode/book link when the heading itself is hyperlinked — podcast
    entries in the doc are written as `Acquired Podcast, [Trader Joe's](url)`.
    Rendered as a source link on the post."""

    themes: tuple[ThemeBlock, ...] = ()


class MemoSection(BaseModel):
    """One labelled section of a public deal memo.

    Sections come in two shapes and a section may use both: a paragraph body
    (`What does it do?`) or a bullet list (`Market & Opportunity`).
    """

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    body: str = ""
    bullets: tuple[Bullet, ...] = ()


class PublicMemoEntry(BaseModel):
    """A parsed entry from the [Public] Investing Memos doc.

    Only ever sourced from the *public* doc. The private memo doc is not
    referenced anywhere in this project — anonymization is guaranteed
    upstream by `angel-memos`, which writes the public doc only for
    buy/strong_buy decisions and with identifiers already stripped.
    """

    model_config = ConfigDict(frozen=True)

    raw_heading: str = Field(min_length=1)
    """e.g. `Inference Procurement & Orchestration Platform — Seed Deal Memo`."""

    category_descriptor: str = Field(min_length=1)
    """The anonymized category, e.g. `Inference Procurement & Orchestration Platform`."""

    stage_label: str = ""
    """e.g. `Seed`. Empty when the heading omits a stage."""

    date_label: str | None = None
    """The `Date: <Month Year>` line's value."""

    sections: tuple[MemoSection, ...] = ()
    upstream_approval_sha256: str | None = Field(default=None, min_length=64, max_length=64)


# ---------------------------------------------------------------------------
# Post draft
# ---------------------------------------------------------------------------


class PostDraft(BaseModel):
    """A rendered post plus taxonomy, ready for the WordPress client.

    `markdown` is the body in Markdown; conversion to Gutenberg blocks happens
    at the WordPress boundary so everything upstream stays in one text format.
    """

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    markdown: str = Field(min_length=1)
    excerpt: str = ""
    category_slugs: tuple[str, ...] = ()
    tag_slugs: tuple[str, ...] = ()
    upstream_approval_sha256: str | None = Field(default=None, min_length=64, max_length=64)


# ---------------------------------------------------------------------------
# Ledger + sync plan
# ---------------------------------------------------------------------------


class LedgerEntry(BaseModel):
    """What was pushed for one source entry, and what it looked like then."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    """`<source>:<slug>` — namespaced so two sources can't collide."""

    source: SourceKind
    source_key: str = Field(min_length=1)
    """The upstream `raw_heading` this entry was parsed from."""

    content_hash: str = Field(min_length=1)
    """Hash of the normalized source content at last sync. Drives change
    detection — a differing hash means the upstream entry was edited."""

    wp_post_id: int = Field(gt=0)
    wp_status: PostStatus
    slug: str = Field(min_length=1)
    first_synced: date
    last_synced: date


class SuppressedEntry(BaseModel):
    """A source entry deliberately excluded from ever becoming a post.

    Suppression is how a pre-existing backlog gets retired without creating 45
    posts nobody asked for: the entries are recorded as seen-and-skipped, so
    they never surface again, while anything added upstream *later* still gets
    picked up as new.

    Keyed by ledger key and deliberately hash-free — unlike `LedgerEntry`,
    suppression does not track content. Editing a suppressed entry upstream
    must not resurrect it; only an explicit un-suppress does that.
    """

    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    source: SourceKind
    source_key: str = Field(min_length=1)
    suppressed_on: date
    reason: str = Field(min_length=1)


class Ledger(BaseModel):
    """The full `state/posted.json` document."""

    model_config = ConfigDict(frozen=True)

    version: int = 1
    entries: dict[str, LedgerEntry] = Field(default_factory=dict)
    suppressed: dict[str, SuppressedEntry] = Field(default_factory=dict)
    """Keys that must never be drafted. Checked before `entries`."""


class SyncAction(StrEnum):
    """What to do with one source entry on this run."""

    CREATE = "create"
    """Not in the ledger — create a new WordPress draft."""

    UPDATE_DRAFT = "update_draft"
    """Content changed and the existing post is still a draft — safe to rewrite."""

    SKIP_UNCHANGED = "skip_unchanged"
    """Hash matches the ledger — nothing to do."""

    SKIP_SUPPRESSED = "skip_suppressed"
    """Explicitly suppressed — never draft it. Reported rather than silently
    omitted, so a suppressed backlog stays visible in the decision table."""

    REPORT_PUBLISHED_DRIFT = "report_published_drift"
    """Content changed but the post is already public. Report it and stop; a
    live post is never rewritten without a human deciding to."""


class SyncDecision(BaseModel):
    """The pure verdict for one source entry. Executing it is a separate step."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    action: SyncAction
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    """One human-readable sentence — this is what the sync report prints."""

    existing_post_id: int | None = Field(default=None, gt=0)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


class WordPressCredentials(BaseModel):
    """WordPress REST credentials, loaded from the secrets env file.

    `app_password` is a `SecretStr` so it cannot reach a log line, an
    exception message, or a `repr` by accident (AGENTS.md safety rule 4).
    Call `.get_secret_value()` only at the point of building the auth header.
    """

    model_config = ConfigDict(frozen=True)

    site_url: str = Field(min_length=1)
    """Normalized: scheme present, no trailing slash."""

    username: str = Field(min_length=1)
    app_password: SecretStr
