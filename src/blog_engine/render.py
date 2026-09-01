"""Render a parsed source entry into a `PostDraft`.

Markdown out, not blocks — block conversion happens once, at the WordPress
boundary (`markdown_blocks.markdown_to_blocks`), so every renderer here
stays in one text format.

The slug is identity: it drives the ledger key (`ledger.ledger_key`), so it
must be a pure function of content that doesn't change on a routine edit —
title/category only, never rating, date, or status.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from blog_engine.config import Settings
from blog_engine.models import (
    BookNotesEntry,
    Bullet,
    MediaKind,
    MemoSection,
    PostDraft,
    PublicMemoEntry,
)

_SLUG_APOSTROPHE_RE = re.compile("['\N{RIGHT SINGLE QUOTATION MARK}]")
_SLUG_COLLAPSE_RE = re.compile(r"[^a-z0-9]+")
_SENTENCE_END_RE = re.compile(r"[.!?](\s|$)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_EXCERPT_MAX_CHARS = 200

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_EMPHASIS_RE = re.compile(r"\*\*|\*|__|_")
_MD_ESCAPE_RE = re.compile(r"\\([*_\\])")

_WHAT_DOES_IT_DO_LABEL = "What does it do?"
_WHY_IMPORTANT_LABEL = "Why is it important?"


def render_book_notes(entry: BookNotesEntry, settings: Settings) -> PostDraft:
    """Render a Book & Podcast Notes entry: intro line, then one `##` per
    theme with its summary and bullets."""
    media_word = "podcast episode" if entry.media == MediaKind.PODCAST else "book"
    intro = f"A note on the {media_word} **{entry.title}**."
    if entry.rating is not None:
        intro += f" Rating: {entry.rating}/10."
    if entry.month_label is not None:
        intro += f" {entry.month_label}."
    if entry.status_flags:
        intro += f" ({', '.join(entry.status_flags)})."
    if entry.source_url is not None:
        intro += f" [Source]({entry.source_url})."

    blocks: list[str] = [intro]
    for theme in entry.themes:
        blocks.append(f"## {theme.label}")
        if theme.summary:
            blocks.append(theme.summary)
        if theme.bullets:
            blocks.append(_bullet_lines(theme.bullets))

    blocks.append("*This note originated from the Book & Podcast Notes doc.*")

    return PostDraft(
        title=entry.title,
        slug=slugify(entry.title),
        markdown="\n\n".join(blocks),
        excerpt=_excerpt_from(((t.summary, t.bullets) for t in entry.themes), intro),
        category_slugs=(settings.book_category_slug,),
    )


def render_public_memo(entry: PublicMemoEntry, settings: Settings) -> PostDraft:
    """Render a public deal-memo entry as a short pointer post, not a
    reproduction: a 1-2 sentence plain trim of what the company does (see
    `_build_tldr` — a trim, never a rewrite) plus a link to the full memo.
    The doc is already the shareable artifact; this post just signposts it.

    No per-section `##` headings or bullets — that detail lives in the doc.
    """
    tldr = _build_tldr(entry.sections)

    lead_parts: list[str] = []
    if entry.stage_label:
        lead_parts.append(f"Stage: {entry.stage_label}.")
    if entry.date_label:
        lead_parts.append(f"Dated {entry.date_label}.")
    lead = " ".join(lead_parts)

    blocks: list[str] = []
    if tldr:
        blocks.append(tldr)
    if lead:
        blocks.append(lead)
    blocks.append(f"[Read the full memo]({settings.public_memos_doc_url})")

    return PostDraft(
        title=entry.category_descriptor,
        slug=slugify(entry.category_descriptor),
        markdown="\n\n".join(blocks),
        excerpt=" ".join(_strip_markdown(tldr).split()) if tldr else "",
        category_slugs=(settings.investing_category_slug,),
        upstream_approval_sha256=entry.upstream_approval_sha256,
    )


def _build_tldr(sections: tuple[MemoSection, ...]) -> str:
    """A 1-2 sentence plain trim of the memo — never a rewrite, never a new
    claim. Prefers the first sentence of `What does it do?` plus the first
    sentence of `Why is it important?` (when that section exists); falls
    back to up to two sentences of `What does it do?` alone; falls back
    again to the first section that has any body at all."""
    what_it_does = _find_section(sections, _WHAT_DOES_IT_DO_LABEL)
    why_important = _find_section(sections, _WHY_IMPORTANT_LABEL)

    if what_it_does is not None and what_it_does.body:
        if why_important is not None and why_important.body:
            sentences = _first_sentences(what_it_does.body, 1) + _first_sentences(
                why_important.body, 1
            )
        else:
            sentences = _first_sentences(what_it_does.body, 2)
        return " ".join(sentences)

    fallback = next((section for section in sections if section.body), None)
    if fallback is None:
        return ""
    return " ".join(_first_sentences(fallback.body, 2))


def _find_section(sections: tuple[MemoSection, ...], label: str) -> MemoSection | None:
    return next((section for section in sections if section.label == label), None)


def _first_sentences(text: str, count: int) -> list[str]:
    """The first `count` sentences of `text`, whitespace-normalized."""
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(normalized)[:count] if s.strip()]


def slugify(text: str) -> str:
    """Drop apostrophes (ASCII `'` and the curly `'` the doc actually uses),
    lowercase, collapse every remaining run of non-alphanumerics to one
    `-`, trim the edges. Deterministic and stable across re-renders of the
    same title. Apostrophes are dropped rather than turned into a `-`
    separator so `Freedom's Forge` reads `freedoms-forge`, not
    `freedom-s-forge` — these slugs are permanent public URLs."""
    without_apostrophes = _SLUG_APOSTROPHE_RE.sub("", text)
    return _SLUG_COLLAPSE_RE.sub("-", without_apostrophes.lower()).strip("-")


def _bullet_lines(bullets: Iterable[Bullet]) -> str:
    """One markdown list item per bullet, indented 2 spaces per depth level,
    joined as a single multi-line block (no blank lines between items — that
    would split them into separate lists once run through `markdown_to_blocks`)."""
    return "\n".join(f"{'  ' * bullet.depth}- {bullet.text}" for bullet in bullets)


def _excerpt_from(
    sections: Iterable[tuple[str, tuple[Bullet, ...]]],
    fallback: str,
) -> str:
    """Excerpt drawn from the entry's first real content — a theme summary or
    section body, else its first bullet — falling back to the lead line only
    when the entry has neither.

    The lead line makes a poor excerpt on its own: it's near-identical
    boilerplate on every post ("A note on the book X."), and WordPress shows
    the excerpt on category and archive pages where that reads as filler.
    """
    for body, bullets in sections:
        if body:
            return _make_excerpt(body)
        if bullets:
            return _make_excerpt(bullets[0].text)
    return _make_excerpt(fallback)


def _make_excerpt(paragraph: str) -> str:
    """First sentence, or the first ~200 chars, of `paragraph`, whitespace-
    normalized and stripped of Markdown.

    WordPress renders an excerpt as plain text, so leaving `**` or a
    `[label](url)` in it would show the raw markers to a reader.
    """
    normalized = " ".join(_strip_markdown(paragraph).split())
    if not normalized:
        return ""
    match = _SENTENCE_END_RE.search(normalized)
    if match is not None and match.start() < _EXCERPT_MAX_CHARS:
        return normalized[: match.start() + 1].strip()
    return normalized[:_EXCERPT_MAX_CHARS].strip()


def _strip_markdown(text: str) -> str:
    """Drop Markdown markup, keeping the visible text: `[label](url)` becomes
    `label`, emphasis markers are removed, and `\\*` unescapes to `*`."""
    without_links = _MD_LINK_RE.sub(r"\1", text)
    without_emphasis = _MD_EMPHASIS_RE.sub("", without_links)
    return _MD_ESCAPE_RE.sub(r"\1", without_emphasis)
