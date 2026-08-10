"""book_notes: the real heading corpus, theme parsing, preamble dropping,
and the podcast-link source_url wiring."""

from __future__ import annotations

from blog_engine.config import Settings
from blog_engine.google_docs import DocParagraph
from blog_engine.models import MediaKind
from blog_engine.sources.book_notes import _parse_entry_heading, _theme_label, parse_book_notes

_SETTINGS = Settings()


def _h1(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=1, bullet_depth=None)


def _h3(text: str, links: tuple[str, ...] = ()) -> DocParagraph:
    return DocParagraph(text=text, heading_level=3, bullet_depth=None, links=links)


def _h4(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=4, bullet_depth=None)


def _p(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=None, bullet_depth=None)


def _bullet(text: str, depth: int = 0) -> DocParagraph:
    return DocParagraph(text=text, heading_level=None, bullet_depth=depth)


# ---------------------------------------------------------------------------
# _parse_entry_heading — the real corpus, verbatim.
# ---------------------------------------------------------------------------


def test_plain_book_heading() -> None:
    parsed = _parse_entry_heading("Benjamin Franklin: An American Life (June 2026 - 8/10)")
    assert parsed.title == "Benjamin Franklin: An American Life"
    assert parsed.media == MediaKind.BOOK
    assert parsed.month_label == "June 2026"
    assert parsed.rating == 8
    assert parsed.status_flags == ()


def test_book_with_author_after_comma_is_still_book() -> None:
    parsed = _parse_entry_heading("Upside of Stress, Kelly Mcgonigal (October 2025 - 7/10)")
    assert parsed.media == MediaKind.BOOK
    assert parsed.title == "Upside of Stress, Kelly Mcgonigal"
    assert parsed.rating == 7


def test_dnf_prefix_stripped_from_title_and_rating_kept() -> None:
    parsed = _parse_entry_heading("[DNF] How Infrastructure Really Works (January 2026 - 7/10)")
    assert parsed.status_flags == ("DNF",)
    assert parsed.title == "How Infrastructure Really Works"
    assert parsed.rating == 7


def test_dnf_with_na_rating_is_none_not_raise() -> None:
    parsed = _parse_entry_heading("[DNF] Origins of Totalitarianism (December 2025 - NA)")
    assert parsed.status_flags == ("DNF",)
    assert parsed.rating is None
    assert parsed.month_label == "December 2025"


def test_wip_prefix_case_insensitive() -> None:
    parsed = _parse_entry_heading("[wip] Some Title (June 2026 - 5/10)")
    assert parsed.status_flags == ("WIP",)
    assert parsed.title == "Some Title"


def test_podcast_marker_detected() -> None:
    parsed = _parse_entry_heading("Acquired Podcast, Trader Joe's (January 2026 - 8/10)")
    assert parsed.media == MediaKind.PODCAST
    assert parsed.title == "Acquired Podcast, Trader Joe's"
    assert parsed.rating == 8


def test_podcast_with_trailing_junk_before_parens_folds_into_title() -> None:
    parsed = _parse_entry_heading("Acquired Podcast, Google 3-Part Series (October 2025 - 9/10)")
    assert parsed.title == "Acquired Podcast, Google 3-Part Series"
    assert parsed.media == MediaKind.PODCAST
    assert parsed.rating == 9


def test_podcast_marker_anywhere_in_heading() -> None:
    parsed = _parse_entry_heading("Dwarkesh Podcast, Satya Nadella (November 2025 - 7/10)")
    assert parsed.media == MediaKind.PODCAST
    parsed2 = _parse_entry_heading("Cheeky Pint Podcast, Dave Ricks (November 2025 - 9/10)")
    assert parsed2.media == MediaKind.PODCAST


def test_heading_with_no_trailing_metadata_still_parses() -> None:
    parsed = _parse_entry_heading("Some Title With No Metadata")
    assert parsed.title == "Some Title With No Metadata"
    assert parsed.month_label is None
    assert parsed.rating is None
    assert parsed.status_flags == ()


# ---------------------------------------------------------------------------
# _theme_label
# ---------------------------------------------------------------------------


def test_theme_prefix_stripped() -> None:
    assert _theme_label("Theme 1: Action Beats Belief") == "Action Beats Belief"


def test_theme_without_prefix_keeps_full_text() -> None:
    assert _theme_label("Key Luminaries Cited in the Book") == "Key Luminaries Cited in the Book"


def test_theme_prefix_case_insensitive() -> None:
    assert _theme_label("theme 2: Something") == "Something"


# ---------------------------------------------------------------------------
# parse_book_notes — full pipeline.
# ---------------------------------------------------------------------------


def test_preamble_before_first_entry_is_dropped() -> None:
    paragraphs = [
        _h1("Tab 1"),
        _h4("How I Generate Notes & Themes"),
        _bullet("Step one of the process"),
        _bullet("Step two of the process"),
        _h3("Range (May 2026 - 7/10)"),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert len(entries) == 1
    assert entries[0].title == "Range"
    assert entries[0].themes == ()


def test_skip_headings_setting_excludes_a_structural_h3() -> None:
    settings = Settings(book_notes_skip_headings=("Process Notes",))
    paragraphs = [
        _h3("Process Notes"),
        _bullet("not a real entry"),
        _h3("Range (May 2026 - 7/10)"),
    ]
    entries = parse_book_notes(paragraphs, settings)
    assert len(entries) == 1
    assert entries[0].title == "Range"


def test_theme_summary_and_bullets_attached() -> None:
    paragraphs = [
        _h3("Range (May 2026 - 7/10)"),
        _h4("Theme 1: Generalists Win Late"),
        _p("A summary sentence for this theme."),
        _bullet("First point", depth=0),
        _bullet("Nested point", depth=1),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    theme = entries[0].themes[0]
    assert theme.label == "Generalists Win Late"
    assert theme.summary == "A summary sentence for this theme."
    assert [b.text for b in theme.bullets] == ["First point", "Nested point"]
    assert [b.depth for b in theme.bullets] == [0, 1]


def test_theme_with_no_summary_goes_straight_to_bullets() -> None:
    paragraphs = [
        _h3("Range (May 2026 - 7/10)"),
        _h4("Theme 1: No Summary Here"),
        _bullet("Straight to a bullet"),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    theme = entries[0].themes[0]
    assert theme.summary == ""
    assert theme.bullets[0].text == "Straight to a bullet"


def test_introduction_label_stripped_from_summary() -> None:
    paragraphs = [
        _h3("Range (May 2026 - 7/10)"),
        _h4("Theme 1: Something"),
        _p("Introduction: The rest of the sentence."),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert entries[0].themes[0].summary == "The rest of the sentence."


def test_bold_introduction_label_stripped_from_summary() -> None:
    """The label is often bold in the doc; DocParagraph.text now surfaces
    that as `**Introduction:**` markdown — must still strip."""
    paragraphs = [
        _h3("Range (May 2026 - 7/10)"),
        _h4("Theme 1: Something"),
        _p("**Introduction:** The rest of the sentence."),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert entries[0].themes[0].summary == "The rest of the sentence."


def test_non_theme_h4_keeps_full_text_as_theme_label() -> None:
    """`Key Luminaries Cited in the Book` sits at theme level (H4) with no
    `Theme N:` prefix — the existing fallback already covers it."""
    paragraphs = [
        _h3("Benjamin Franklin: An American Life (June 2026 - 8/10)"),
        _h4("Theme 1: Action Beats Belief"),
        _bullet("A point"),
        _h4("Key Luminaries Cited in the Book"),
        _bullet("Franklin"),
        _bullet("Washington"),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    labels = [t.label for t in entries[0].themes]
    assert labels == ["Action Beats Belief", "Key Luminaries Cited in the Book"]
    assert [b.text for b in entries[0].themes[1].bullets] == ["Franklin", "Washington"]


def test_multiple_entries_in_sequence() -> None:
    paragraphs = [
        _h3("Range (May 2026 - 7/10)"),
        _h4("Theme 1: A"),
        _bullet("bullet"),
        _h3("Billion Dollar Whale (April 2026 - 8/10)"),
        _h4("Theme 1: B"),
        _bullet("bullet"),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert [e.title for e in entries] == ["Range", "Billion Dollar Whale"]
    assert [e.rating for e in entries] == [7, 8]


def test_podcast_source_url_from_heading_link() -> None:
    paragraphs = [
        _h3(
            "Acquired Podcast, Trader Joe's (January 2026 - 8/10)",
            links=("https://example.com/acquired-tj",),
        ),
    ]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert entries[0].source_url == "https://example.com/acquired-tj"
    assert entries[0].media == MediaKind.PODCAST


def test_book_entry_with_no_link_has_no_source_url() -> None:
    paragraphs = [_h3("Range (May 2026 - 7/10)")]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert entries[0].source_url is None


def test_raw_heading_is_verbatim() -> None:
    paragraphs = [_h3("[DNF] Mother Tongue (August 2025 - 5/10)")]
    entries = parse_book_notes(paragraphs, _SETTINGS)
    assert entries[0].raw_heading == "[DNF] Mother Tongue (August 2025 - 5/10)"
