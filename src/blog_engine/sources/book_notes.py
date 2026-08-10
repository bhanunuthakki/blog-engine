"""Parse the Book & Podcast Notes (Master) doc into `BookNotesEntry` values.

Doc shape (H3 = entry, H4 = theme):

    Benjamin Franklin: An American Life (June 2026 - 8/10)
      Theme 1: Action Beats Belief
        <summary paragraph>
        - bullet
        - bullet
      Key Luminaries Cited in the Book        <- H4, no "Theme N:" prefix
        - bullet

    [DNF] How Infrastructure Really Works (January 2026 - 7/10)
    Acquired Podcast, Trader Joe's (January 2026 - 8/10)

Everything before the first entry-level (H3) heading is preamble — the doc's
H1 title and its H4 "How I Generate Notes & Themes" process notes — and is
dropped rather than pattern-matched, since that's simpler and can't miss a
new preamble shape. `book_notes_skip_headings` still applies at entry level
for any doc-structure heading that *does* land at H3.

A hyperlinked podcast episode name reaches this module as plain text plus
`DocParagraph.links` — Google Docs never puts markdown link syntax in
`.text`. The heading's first link (if any) becomes `source_url`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from blog_engine.config import Settings
from blog_engine.google_docs import DocParagraph
from blog_engine.models import BookNotesEntry, Bullet, MediaKind, ThemeBlock

_STATUS_PREFIX_RE = re.compile(r"^\s*\[(WIP|DNF)\]\s*", re.IGNORECASE)
_TRAILING_META_RE = re.compile(r"^(?P<title>.*?)\s*\((?P<meta>[^()]*)\)\s*$")
_MONTH_RATING_RE = re.compile(r"^(?P<month>[A-Za-z]+ \d{4})\s*-\s*(?P<rating>\d{1,2}/10|NA)$")
_THEME_PREFIX_RE = re.compile(r"^Theme\s+\d+\s*:\s*(.+)$", re.IGNORECASE)
# The `Introduction:` label is often bold in the doc, which DocParagraph.text
# now surfaces as `**Introduction:**` markdown — strip either form.
_INTRODUCTION_PREFIX_RE = re.compile(r"^\*{0,2}Introduction:\*{0,2}\s*")


def parse_book_notes(paragraphs: list[DocParagraph], settings: Settings) -> list[BookNotesEntry]:
    """Extract every entry from the paragraph stream, in document order."""
    entries: list[BookNotesEntry] = []
    entry: _EntryBuilder | None = None
    theme: _ThemeBuilder | None = None
    seen_first_entry = False

    def flush_theme() -> None:
        nonlocal theme
        if entry is not None and theme is not None:
            entry.themes.append(theme.build())
        theme = None

    def flush_entry() -> None:
        nonlocal entry
        flush_theme()
        if entry is not None:
            entries.append(entry.build())
        entry = None

    for para in paragraphs:
        level = para.heading_level
        text = para.text.strip()

        if level == settings.book_notes_entry_level:
            seen_first_entry = True
            flush_entry()
            if text in settings.book_notes_skip_headings:
                continue
            parsed = _parse_entry_heading(text)
            entry = _EntryBuilder(
                raw_heading=text,
                title=parsed.title,
                media=parsed.media,
                month_label=parsed.month_label,
                rating=parsed.rating,
                status_flags=parsed.status_flags,
                source_url=para.links[0] if para.links else None,
            )
            continue

        if not seen_first_entry:
            continue  # doc preamble: H1 title, process notes, their bullets

        if level == settings.book_notes_theme_level:
            if entry is None:
                continue
            flush_theme()
            theme = _ThemeBuilder(raw_heading=text, label=_theme_label(text))
            continue

        if level is not None:
            continue  # a heading level that isn't entry or theme: structural noise

        if para.bullet_depth is not None:
            if theme is not None:
                theme.bullets.append(Bullet(text=text, depth=min(para.bullet_depth, 3)))
            continue

        if theme is not None and not theme.summary:
            theme.summary = _INTRODUCTION_PREFIX_RE.sub("", text).strip()

    flush_entry()
    return entries


# ---------------------------------------------------------------------------
# Heading parsing — pure, unit-tested against the real heading corpus.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ParsedHeading:
    title: str
    media: MediaKind
    month_label: str | None
    rating: int | None
    status_flags: tuple[str, ...]


def _parse_entry_heading(raw_heading: str) -> _ParsedHeading:
    """Split an entry heading into title/media/month/rating/status.

    Handles all documented shapes: plain books, books written as
    `Title, Author (Month - N/10)`, `[WIP]`/`[DNF]` bracketed prefixes,
    podcast headings (any heading containing "Podcast", case-insensitive),
    a `NA` rating, and headings with no trailing metadata group at all.
    """
    text = raw_heading.strip()

    status_flags: tuple[str, ...] = ()
    prefix_match = _STATUS_PREFIX_RE.match(text)
    if prefix_match is not None:
        status_flags = (prefix_match.group(1).upper(),)
        text = text[prefix_match.end() :]

    media = MediaKind.PODCAST if "podcast" in text.lower() else MediaKind.BOOK

    meta_match = _TRAILING_META_RE.match(text)
    if meta_match is None:
        return _ParsedHeading(
            title=text.strip(),
            media=media,
            month_label=None,
            rating=None,
            status_flags=status_flags,
        )

    title = meta_match.group("title").strip()
    meta = meta_match.group("meta").strip()

    month_rating_match = _MONTH_RATING_RE.match(meta)
    if month_rating_match is None:
        # Trailing parens we don't recognize (not a "<Month Year> - <rating>"
        # shape) — keep the title, drop the metadata rather than guess.
        return _ParsedHeading(
            title=title, media=media, month_label=None, rating=None, status_flags=status_flags
        )

    month_label = month_rating_match.group("month")
    rating_text = month_rating_match.group("rating")
    rating = None if rating_text == "NA" else int(rating_text.split("/")[0])
    return _ParsedHeading(
        title=title,
        media=media,
        month_label=month_label,
        rating=rating,
        status_flags=status_flags,
    )


def _theme_label(raw_heading: str) -> str:
    """Strip a `Theme N:` prefix; a heading without one keeps its full text
    (e.g. `Key Luminaries Cited in the Book`)."""
    match = _THEME_PREFIX_RE.match(raw_heading.strip())
    return match.group(1).strip() if match is not None else raw_heading.strip()


# ---------------------------------------------------------------------------
# Mutable builders — converted to frozen models only at flush time.
# ---------------------------------------------------------------------------


@dataclass
class _ThemeBuilder:
    raw_heading: str
    label: str
    summary: str = ""
    bullets: list[Bullet] = field(default_factory=list[Bullet])

    def build(self) -> ThemeBlock:
        return ThemeBlock(label=self.label, summary=self.summary, bullets=tuple(self.bullets))


@dataclass
class _EntryBuilder:
    raw_heading: str
    title: str
    media: MediaKind
    month_label: str | None
    rating: int | None
    status_flags: tuple[str, ...]
    source_url: str | None
    themes: list[ThemeBlock] = field(default_factory=list[ThemeBlock])

    def build(self) -> BookNotesEntry:
        return BookNotesEntry(
            raw_heading=self.raw_heading,
            title=self.title,
            media=self.media,
            month_label=self.month_label,
            rating=self.rating,
            status_flags=self.status_flags,
            source_url=self.source_url,
            themes=tuple(self.themes),
        )
