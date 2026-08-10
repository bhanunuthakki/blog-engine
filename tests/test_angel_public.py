"""angel_public: container scoping as a privacy boundary, heading split
(em dash / en dash / hyphen / no-dash fallback), tolerant fallback, and
section grouping."""

from __future__ import annotations

import pytest

from blog_engine.config import Settings
from blog_engine.google_docs import DocParagraph
from blog_engine.sources.angel_public import (
    PublicMemosStructureError,
    _split_label,
    _split_memo_heading,
    parse_public_memos,
)

_SETTINGS = Settings()


def _h1(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=1, bullet_depth=None)


def _h3(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=3, bullet_depth=None)


def _h4(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=4, bullet_depth=None)


def _p(text: str) -> DocParagraph:
    return DocParagraph(text=text, heading_level=None, bullet_depth=None)


def _bullet(text: str, depth: int = 0) -> DocParagraph:
    return DocParagraph(text=text, heading_level=None, bullet_depth=depth)


# ---------------------------------------------------------------------------
# _split_memo_heading — the real corpus, verbatim.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("heading", "descriptor", "stage"),
    [
        (
            "Emerging Market EV & Energy Infrastructure — Series A Deal Memo",
            "Emerging Market EV & Energy Infrastructure",
            "Series A",
        ),
        (
            "Full Stack Mineral Discovery - Series B Deal Memo",
            "Full Stack Mineral Discovery",
            "Series B",
        ),
        (
            "Advanced Battery Management Edge Software — Series A+ Deal Memo",
            "Advanced Battery Management Edge Software",
            "Series A+",
        ),
        (
            "Plug-and-Play Residential Battery Network — Pre-Seed Deal Memo",
            "Plug-and-Play Residential Battery Network",
            "Pre-Seed",
        ),
        (
            "Next-Gen Geothermal Surface Hardware — Seed Deal Memo",
            "Next-Gen Geothermal Surface Hardware",
            "Seed",
        ),
        (
            "Synthetic Livestock Feed Additives — Seed+ Deal Memo",
            "Synthetic Livestock Feed Additives",
            "Seed+",
        ),
        (
            "WhatsApp CRM & Customer Acquisition Tool for Brands in India — Seed Deal Memo",
            "WhatsApp CRM & Customer Acquisition Tool for Brands in India",
            "Seed",
        ),
        (
            "Social Nerdcore Collectibles Marketplace — Seed+ Deal Memo",
            "Social Nerdcore Collectibles Marketplace",
            "Seed+",
        ),
    ],
)
def test_memo_heading_split_real_corpus(heading: str, descriptor: str, stage: str) -> None:
    assert _split_memo_heading(heading) == (descriptor, stage)


@pytest.mark.parametrize(
    "heading",
    [
        "Sustainable Cookstove Provider in Emerging Markets",
        "Next Gen ACs",
        "AI Driven Deal Diligence Automation for Private Market Investors",
    ],
)
def test_memo_heading_with_no_dash_falls_back_to_whole_heading(heading: str) -> None:
    assert _split_memo_heading(heading) == (heading, "")


def test_internal_hyphens_never_treated_as_the_delimiter() -> None:
    """'Plug-and-Play' and 'Pre-Seed' have hyphens with no surrounding
    whitespace — only a space-delimited dash is the descriptor/stage split."""
    descriptor, stage = _split_memo_heading(
        "Plug-and-Play Residential Battery Network — Pre-Seed Deal Memo"
    )
    assert descriptor == "Plug-and-Play Residential Battery Network"
    assert stage == "Pre-Seed"


# ---------------------------------------------------------------------------
# _split_label
# ---------------------------------------------------------------------------


def test_split_label_inline_body() -> None:
    label, body = _split_label("What does it do? Replaces meat-based feed.")
    assert label == "What does it do?"
    assert body == "Replaces meat-based feed."


def test_split_label_banner_only() -> None:
    label, body = _split_label("Market & Opportunity")
    assert label == "Market & Opportunity"
    assert body == ""


def test_split_label_unrecognized_text_has_no_label() -> None:
    label, body = _split_label("Just some prose.")
    assert label is None
    assert body == "Just some prose."


def test_split_label_bold_wrapped_inline_body() -> None:
    """angel-memos bolds every label; `DocParagraph.text` now surfaces that
    as `**Label**` markdown, which must still match."""
    label, body = _split_label("**What does it do?** Replaces meat-based feed.")
    assert label == "What does it do?"
    assert body == "Replaces meat-based feed."


def test_split_label_bold_wrapped_banner_only() -> None:
    label, body = _split_label("**Market & Opportunity**")
    assert label == "Market & Opportunity"
    assert body == ""


# ---------------------------------------------------------------------------
# parse_public_memos — container scoping is a privacy boundary.
# ---------------------------------------------------------------------------


def test_missing_container_heading_raises() -> None:
    paragraphs = [_h1("Private Investing"), _h3("Investment Strategy"), _p("Some strategy text.")]
    with pytest.raises(PublicMemosStructureError):
        parse_public_memos(paragraphs, _SETTINGS)


def test_content_before_memos_container_never_leaks_into_output() -> None:
    """The doc's H1 is 'Private Investing' with three sibling H3 sections —
    Investment Strategy, Portfolio Observations, Diligence Process — before
    Memos. None of that is cleared for publication."""
    paragraphs = [
        _h1("Private Investing"),
        _h3("Investment Strategy"),
        _p("What does it do? Confidential strategy notes."),
        _bullet("A secret bullet."),
        _h3("Portfolio Observations"),
        _p("More private prose."),
        _h3("Diligence Process"),
        _p("Internal process notes."),
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("Date: May 2026"),
        _p("What does it do? Makes widgets."),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    assert len(entries) == 1
    assert entries[0].category_descriptor == "Widget Co"
    rendered_text = repr(entries)
    assert "Confidential" not in rendered_text
    assert "secret bullet" not in rendered_text
    assert "private prose" not in rendered_text
    assert "Internal process notes" not in rendered_text


def test_stops_at_next_h3_after_memos() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("Date: May 2026"),
        _h3("Archive"),
        _h4("Should Not Appear — Seed Deal Memo"),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    assert len(entries) == 1
    assert entries[0].category_descriptor == "Widget Co"


def test_entry_fields_and_date_label() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("Date: May 2026"),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    entry = entries[0]
    assert entry.category_descriptor == "Widget Co"
    assert entry.stage_label == "Seed"
    assert entry.date_label == "May 2026"
    assert entry.raw_heading == "Widget Co — Seed Deal Memo"


def test_section_with_inline_body_and_no_bullets() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("What does it do? Makes widgets."),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    section = entries[0].sections[0]
    assert section.label == "What does it do?"
    assert section.body == "Makes widgets."
    assert section.bullets == ()


def test_section_banner_followed_by_bullets() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("Market & Opportunity"),
        _bullet("Job(s) to be done: Reduce toil."),
        _bullet("Market Size: $1B."),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    section = entries[0].sections[0]
    assert section.label == "Market & Opportunity"
    assert section.body == ""
    assert [b.text for b in section.bullets] == [
        "Job(s) to be done: Reduce toil.",
        "Market Size: $1B.",
    ]


def test_multiple_sections_grouped_correctly() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("What does it do? Makes widgets."),
        _p("Why is it important? Widgets matter."),
        _p("Anti-Thesis"),
        _bullet("Risk one."),
        _bullet("Risk two."),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    sections = entries[0].sections
    assert [s.label for s in sections] == [
        "What does it do?",
        "Why is it important?",
        "Anti-Thesis",
    ]
    assert [b.text for b in sections[2].bullets] == ["Risk one.", "Risk two."]


def test_multiple_entries_under_container() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Widget Co — Seed Deal Memo"),
        _p("Date: May 2026"),
        _h4("Gizmo Inc — Series A Deal Memo"),
        _p("Date: June 2026"),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    assert [e.category_descriptor for e in entries] == ["Widget Co", "Gizmo Inc"]
    assert [e.stage_label for e in entries] == ["Seed", "Series A"]


def test_entry_with_fallback_heading_has_empty_stage() -> None:
    paragraphs = [
        _h3("Memos"),
        _h4("Next Gen ACs"),
        _p("Date: May 2026"),
    ]
    entries = parse_public_memos(paragraphs, _SETTINGS)
    assert entries[0].category_descriptor == "Next Gen ACs"
    assert entries[0].stage_label == ""
