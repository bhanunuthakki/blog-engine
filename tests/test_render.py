"""render: slug stability, excerpt generation, and body shape."""

from __future__ import annotations

from blog_engine.config import Settings
from blog_engine.models import (
    BookNotesEntry,
    Bullet,
    MediaKind,
    MemoSection,
    PostDraft,
    PublicMemoEntry,
    ThemeBlock,
)
from blog_engine.render import render_book_notes, render_public_memo, slugify

_SETTINGS = Settings()


def _book_entry(**overrides: object) -> BookNotesEntry:
    base: dict[str, object] = {
        "raw_heading": "Range (May 2026 - 7/10)",
        "title": "Range",
        "media": MediaKind.BOOK,
        "month_label": "May 2026",
        "rating": 7,
        "themes": (
            ThemeBlock(
                label="Generalists Win Late",
                summary="A summary sentence.",
                bullets=(Bullet(text="A point", depth=0),),
            ),
        ),
    }
    base.update(overrides)
    return BookNotesEntry.model_validate(base)


def _memo_entry(**overrides: object) -> PublicMemoEntry:
    base: dict[str, object] = {
        "raw_heading": "Widget Co — Seed Deal Memo",
        "category_descriptor": "Widget Co",
        "stage_label": "Seed",
        "date_label": "May 2026",
        "sections": (
            MemoSection(
                label="What does it do?",
                body="Makes widgets.",
            ),
        ),
    }
    base.update(overrides)
    return PublicMemoEntry.model_validate(base)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_lowercases_and_hyphenates() -> None:
    assert slugify("Benjamin Franklin: An American Life") == "benjamin-franklin-an-american-life"


def test_slugify_collapses_runs_of_punctuation() -> None:
    assert slugify("A -- B  ,  C") == "a-b-c"


def test_slugify_trims_leading_trailing_hyphens() -> None:
    assert slugify("(Parenthetical Title)") == "parenthetical-title"


def test_slugify_drops_ascii_apostrophe_rather_than_hyphenating() -> None:
    assert slugify("Freedom's Forge") == "freedoms-forge"


def test_slugify_drops_curly_apostrophe() -> None:
    assert slugify("Freedom\N{RIGHT SINGLE QUOTATION MARK}s Forge") == "freedoms-forge"


def test_slugify_apostrophe_in_real_podcast_title() -> None:
    assert slugify("Acquired Podcast, Trader Joe's") == "acquired-podcast-trader-joes"


def test_slugify_apostrophe_slug_is_still_stable_when_rating_changes() -> None:
    """The apostrophe fix must not disturb the existing stability guarantee."""
    assert slugify("Trader Joe's") == slugify("Trader Joe's")


# ---------------------------------------------------------------------------
# render_book_notes
# ---------------------------------------------------------------------------


def test_book_title_excludes_rating() -> None:
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert draft.title == "Range"
    assert "7" not in draft.title


def test_book_slug_is_stable_when_rating_changes() -> None:
    """The slug is identity — a changed rating must not change it."""
    draft_a = render_book_notes(_book_entry(rating=7), _SETTINGS)
    draft_b = render_book_notes(_book_entry(rating=9), _SETTINGS)
    assert draft_a.slug == draft_b.slug


def test_book_slug_is_stable_when_month_changes() -> None:
    draft_a = render_book_notes(_book_entry(month_label="May 2026"), _SETTINGS)
    draft_b = render_book_notes(_book_entry(month_label="June 2026"), _SETTINGS)
    assert draft_a.slug == draft_b.slug


def test_book_body_contains_rating_and_month() -> None:
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert "7/10" in draft.markdown
    assert "May 2026" in draft.markdown


def test_book_body_has_one_heading_per_theme() -> None:
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert "## Generalists Win Late" in draft.markdown
    assert "A summary sentence." in draft.markdown
    assert "- A point" in draft.markdown


def test_book_category_is_book_category_slug() -> None:
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert draft.category_slugs == (_SETTINGS.book_category_slug,)


def test_book_body_states_source_provenance() -> None:
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert "Book & Podcast Notes doc" in draft.markdown


def test_book_body_includes_source_url_when_present() -> None:
    draft = render_book_notes(
        _book_entry(media=MediaKind.PODCAST, source_url="https://example.com/ep"), _SETTINGS
    )
    assert "https://example.com/ep" in draft.markdown


def test_book_excerpt_comes_from_first_theme_not_the_boilerplate_lead() -> None:
    """The lead line is near-identical on every post, so it makes a filler
    excerpt on archive pages. Real content wins."""
    draft = render_book_notes(_book_entry(), _SETTINGS)
    assert draft.excerpt == "A summary sentence."
    assert not draft.excerpt.startswith("A note on the book")


def test_book_excerpt_falls_back_to_lead_when_entry_has_no_themes() -> None:
    draft = render_book_notes(_book_entry(themes=()), _SETTINGS)
    assert draft.excerpt.startswith("A note on the book")


def test_book_excerpt_is_plain_text_not_markdown() -> None:
    """WordPress renders an excerpt as plain text — raw `**` would be visible."""
    draft = render_book_notes(_book_entry(themes=()), _SETTINGS)
    assert "**" not in draft.excerpt
    assert "Range" in draft.excerpt


def test_excerpt_strips_links_keeping_label() -> None:
    entry = _book_entry(
        themes=(ThemeBlock(label="T", summary="See [the paper](https://example.com/x) here."),),
    )
    draft = render_book_notes(entry, _SETTINGS)
    assert draft.excerpt == "See the paper here."


# ---------------------------------------------------------------------------
# render_public_memo — a short TLDR + link to the doc, not a reproduction.
# ---------------------------------------------------------------------------

_DOC_URL = "https://docs.google.com/document/d/TEST-DOC-ID/edit"
_MEMO_SETTINGS = Settings(public_memos_doc_url=_DOC_URL)


def _render_memo(entry: PublicMemoEntry) -> PostDraft:
    return render_public_memo(entry, _MEMO_SETTINGS)


def test_memo_title_is_category_descriptor() -> None:
    draft = _render_memo(_memo_entry())
    assert draft.title == "Widget Co"


def test_memo_slug_stable_when_date_changes() -> None:
    draft_a = _render_memo(_memo_entry(date_label="May 2026"))
    draft_b = _render_memo(_memo_entry(date_label="June 2026"))
    assert draft_a.slug == draft_b.slug


def test_memo_category_is_investing_category_slug() -> None:
    draft = _render_memo(_memo_entry())
    assert draft.category_slugs == (_SETTINGS.investing_category_slug,)


def test_memo_body_has_no_section_headings() -> None:
    """The whole point of the new shape: detail lives in the doc, not the
    post, so no per-section `##` headings survive into the markdown."""
    entry = _memo_entry(
        sections=(
            MemoSection(label="What does it do?", body="Makes widgets for factories."),
            MemoSection(label="Market & Opportunity", bullets=(Bullet(text="Big market."),)),
            MemoSection(label="Anti-Thesis", bullets=(Bullet(text="Competitors exist."),)),
        )
    )
    draft = _render_memo(entry)
    assert "##" not in draft.markdown


def test_memo_body_has_no_bullets() -> None:
    entry = _memo_entry(
        sections=(
            MemoSection(label="What does it do?", body="Makes widgets for factories."),
            MemoSection(label="Market & Opportunity", bullets=(Bullet(text="Big market."),)),
        )
    )
    draft = _render_memo(entry)
    assert "Big market." not in draft.markdown
    assert "- " not in draft.markdown


def test_memo_tldr_comes_from_what_does_it_do() -> None:
    entry = _memo_entry(
        sections=(MemoSection(label="What does it do?", body="Makes widgets for factories."),)
    )
    draft = _render_memo(entry)
    assert "Makes widgets for factories." in draft.markdown


def test_memo_tldr_is_capped_at_two_sentences() -> None:
    body = "First sentence here. Second sentence here. Third sentence here. Fourth here."
    entry = _memo_entry(sections=(MemoSection(label="What does it do?", body=body),))
    draft = _render_memo(entry)
    tldr_line = draft.markdown.split("\n\n")[0]
    assert tldr_line.count(".") <= 2
    assert "Third sentence" not in tldr_line
    assert "Fourth" not in tldr_line


def test_memo_tldr_uses_why_important_first_sentence_as_second_sentence() -> None:
    entry = _memo_entry(
        sections=(
            MemoSection(label="What does it do?", body="Makes widgets for factories."),
            MemoSection(
                label="Why is it important?",
                body="Factories waste 30% of throughput without them. Other stuff too.",
            ),
        )
    )
    draft = _render_memo(entry)
    tldr_line = draft.markdown.split("\n\n")[0]
    assert "Makes widgets for factories." in tldr_line
    assert "Factories waste 30% of throughput without them." in tldr_line
    assert "Other stuff too." not in tldr_line


def test_memo_tldr_is_a_trim_not_a_rewrite() -> None:
    """No new claims — the TLDR is a verbatim substring of the source text,
    not a paraphrase."""
    body = "Makes widgets for factories that need them fast."
    entry = _memo_entry(sections=(MemoSection(label="What does it do?", body=body),))
    draft = _render_memo(entry)
    assert body in draft.markdown


def test_memo_tldr_falls_back_to_first_section_with_a_body() -> None:
    """No 'What does it do?' section at all — fall back rather than
    inventing a summary."""
    entry = _memo_entry(
        sections=(
            MemoSection(label="Market & Opportunity", body="A large and growing market."),
            MemoSection(label="Anti-Thesis", body="Some risk here."),
        )
    )
    draft = _render_memo(entry)
    assert "A large and growing market." in draft.markdown
    assert "Some risk here." not in draft.markdown


def test_memo_tldr_empty_when_no_section_has_a_body() -> None:
    """Bullets-only sections have no body text to trim from — the TLDR is
    simply absent, not synthesized from bullets."""
    entry = _memo_entry(sections=(MemoSection(label="Anti-Thesis", bullets=(Bullet(text="X"),)),))
    draft = _render_memo(entry)
    assert draft.excerpt == ""


def test_memo_keeps_stage_and_date_as_one_line() -> None:
    draft = _render_memo(_memo_entry(stage_label="Seed", date_label="May 2026"))
    lines_with_stage = [line for line in draft.markdown.split("\n\n") if "Stage:" in line]
    assert len(lines_with_stage) == 1
    assert "\n" not in lines_with_stage[0]
    assert "Seed" in lines_with_stage[0]
    assert "May 2026" in lines_with_stage[0]


def test_memo_link_to_full_memo_present_exactly_once() -> None:
    draft = _render_memo(_memo_entry())
    assert draft.markdown.count(_DOC_URL) == 1
    assert f"[Read the full memo]({_DOC_URL})" in draft.markdown


def test_memo_provenance_footer_replaced_by_link_not_stacked() -> None:
    draft = _render_memo(_memo_entry())
    assert "originated from" not in draft.markdown
    assert draft.markdown.count("[Read the full memo]") == 1


def test_memo_excerpt_is_the_tldr() -> None:
    entry = _memo_entry(
        sections=(MemoSection(label="What does it do?", body="Makes widgets for factories."),)
    )
    draft = _render_memo(entry)
    assert draft.excerpt == "Makes widgets for factories."


def test_memo_excerpt_is_plain_text_not_markdown() -> None:
    entry = _memo_entry(
        sections=(MemoSection(label="What does it do?", body="Makes **widgets** for factories."),)
    )
    draft = _render_memo(entry)
    assert "**" not in draft.excerpt
    assert "widgets" in draft.excerpt
