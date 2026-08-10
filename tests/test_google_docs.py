"""Pure functions in `google_docs`: paragraph extraction, block composition,
and the headless-auth guard. The OAuth-touching entry points are exercised
by `check-auth` against the real APIs, not here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from blog_engine.google_docs import (
    Block,
    GoogleDocsStructureError,
    _compose_blocks,
    _credentials_path,
    _extract_paragraphs,
    _find_container_heading_end,
    _heading_exists,
    _is_noninteractive,
    _merge_adjacent_ranges,
)


def _fake_paragraph_elem(
    text: str,
    named_style: str = "NORMAL_TEXT",
    *,
    bullet_nesting: int | None = None,
    links: list[str | None] | None = None,
    bold: list[bool] | None = None,
    italic: list[bool] | None = None,
) -> dict[str, Any]:
    """One `body.content[]` element. `links[i]`/`bold[i]`/`italic[i]` (or
    None/False) tag the i-th textRun; when shorter than the run count the
    rest default to linkless/plain. Splits `text` into one run per character
    run isn't needed — tests only need a handful of runs, so pass `text`
    pre-split via `|`."""
    runs = text.split("|") if "|" in text else [text]
    elements: list[dict[str, Any]] = []
    for i, run_text in enumerate(runs):
        text_run: dict[str, Any] = {"content": run_text}
        url = links[i] if links is not None and i < len(links) else None
        is_bold = bold[i] if bold is not None and i < len(bold) else False
        is_italic = italic[i] if italic is not None and i < len(italic) else False
        text_style: dict[str, Any] = {}
        if url is not None:
            text_style["link"] = {"url": url}
        if is_bold:
            text_style["bold"] = True
        if is_italic:
            text_style["italic"] = True
        if text_style:
            text_run["textStyle"] = text_style
        elements.append({"textRun": text_run})
    para: dict[str, Any] = {
        "paragraphStyle": {"namedStyleType": named_style},
        "elements": elements,
    }
    if bullet_nesting is not None:
        para["bullet"] = {"nestingLevel": bullet_nesting}
    return {"paragraph": para, "endIndex": 0}


def _fake_doc(*elems: dict[str, Any]) -> dict[str, Any]:
    return {"body": {"content": list(elems)}}


# ---------------------------------------------------------------------------
# _extract_paragraphs
# ---------------------------------------------------------------------------


def test_extract_plain_paragraph() -> None:
    doc = _fake_doc(_fake_paragraph_elem("Hello world\n"))
    paras = _extract_paragraphs(doc)
    assert len(paras) == 1
    assert paras[0].text == "Hello world"
    assert paras[0].heading_level is None
    assert paras[0].bullet_depth is None
    assert paras[0].links == ()


def test_extract_heading_level() -> None:
    doc = _fake_doc(_fake_paragraph_elem("A Title\n", "HEADING_3"))
    paras = _extract_paragraphs(doc)
    assert paras[0].heading_level == 3


def test_extract_bullet_depth() -> None:
    doc = _fake_doc(_fake_paragraph_elem("item\n", bullet_nesting=2))
    paras = _extract_paragraphs(doc)
    assert paras[0].bullet_depth == 2


def test_extract_skips_empty_paragraphs() -> None:
    doc = _fake_doc(_fake_paragraph_elem("\n"), _fake_paragraph_elem("real text\n"))
    paras = _extract_paragraphs(doc)
    assert len(paras) == 1
    assert paras[0].text == "real text"


def test_extract_skips_whitespace_only_paragraphs() -> None:
    doc = _fake_doc(_fake_paragraph_elem("   \n"))
    assert _extract_paragraphs(doc) == []


def test_extract_collects_link_url() -> None:
    doc = _fake_doc(
        _fake_paragraph_elem(
            "Acquired Podcast, |Trader Joe's| (Jan 2026 - 8/10)\n",
            links=[None, "https://example.com/ep"],
        )
    )
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "Acquired Podcast, Trader Joe's (Jan 2026 - 8/10)"
    assert paras[0].links == ("https://example.com/ep",)


def test_extract_dedupes_consecutive_identical_links() -> None:
    """A single visual hyperlink is often split across several textRuns by
    Docs formatting boundaries (e.g. a bold sub-span) — those consecutive
    same-URL runs must collapse to one URL in `links`."""
    doc = _fake_doc(
        _fake_paragraph_elem(
            "Trader|Joe's\n",
            links=["https://example.com/ep", "https://example.com/ep"],
        )
    )
    paras = _extract_paragraphs(doc)
    assert paras[0].links == ("https://example.com/ep",)


def test_extract_keeps_two_distinct_links() -> None:
    doc = _fake_doc(
        _fake_paragraph_elem(
            "one |two\n",
            links=["https://a.test", "https://b.test"],
        )
    )
    paras = _extract_paragraphs(doc)
    assert paras[0].links == ("https://a.test", "https://b.test")


# ---------------------------------------------------------------------------
# _extract_paragraphs — bold/italic re-emitted as markdown.
# ---------------------------------------------------------------------------


def test_bold_run_re_emitted_as_markdown() -> None:
    doc = _fake_doc(
        _fake_paragraph_elem("Track Your Habits|: You can't improve.\n", bold=[True, False])
    )
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "**Track Your Habits**: You can't improve."


def test_italic_run_re_emitted_as_markdown() -> None:
    doc = _fake_doc(_fake_paragraph_elem("Example|: Franklin used a grid.\n", italic=[True, False]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "*Example*: Franklin used a grid."


def test_bold_and_italic_run_nests_markers() -> None:
    doc = _fake_doc(_fake_paragraph_elem("both\n", bold=[True], italic=[True]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "**_both_**"


def test_adjacent_runs_with_same_style_are_merged_not_double_wrapped() -> None:
    """Docs often splits one visually-continuous bold phrase across several
    textRuns; re-wrapping each fragment separately would produce
    '**Track** **Your** **Habits**' instead of one span."""
    doc = _fake_doc(_fake_paragraph_elem("Track |Your |Habits\n", bold=[True, True, True]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "**Track Your Habits**"


def test_trailing_whitespace_inside_bold_run_moves_outside_markers() -> None:
    """A bold run's trailing space must not end up inside '**...**', which
    would render literally instead of collapsing like normal whitespace."""
    doc = _fake_doc(_fake_paragraph_elem("Bold phrase |plain\n", bold=[True, False]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "**Bold phrase** plain"
    assert "** " not in paras[0].text.replace("** plain", "")


def test_whitespace_only_styled_run_is_not_wrapped() -> None:
    """A trailing newline/space run inheriting bold styling must not become
    an empty '****' span."""
    doc = _fake_doc(_fake_paragraph_elem("Some text|\n", bold=[False, True]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "Some text"
    assert "****" not in paras[0].text


def test_literal_asterisk_in_doc_text_is_escaped() -> None:
    doc = _fake_doc(_fake_paragraph_elem("A 5*3 grid\n"))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "A 5\\*3 grid"


def test_literal_underscore_in_doc_text_is_escaped() -> None:
    doc = _fake_doc(_fake_paragraph_elem("file_name.py\n"))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "file\\_name.py"


def test_literal_asterisk_inside_bold_run_is_escaped_and_still_bold() -> None:
    doc = _fake_doc(_fake_paragraph_elem("5*3 grid\n", bold=[True]))
    paras = _extract_paragraphs(doc)
    assert paras[0].text == "**5\\*3 grid**"


def test_extract_non_heading_named_style_is_none() -> None:
    doc = _fake_doc(_fake_paragraph_elem("Title\n", "TITLE"))
    assert _extract_paragraphs(doc)[0].heading_level is None


# ---------------------------------------------------------------------------
# _compose_blocks / _merge_adjacent_ranges
# ---------------------------------------------------------------------------


def test_merge_collapses_adjacent_ranges() -> None:
    assert _merge_adjacent_ranges([(0, 5), (5, 10)]) == [(0, 10)]


def test_merge_keeps_disjoint_ranges_separate() -> None:
    assert _merge_adjacent_ranges([(0, 5), (10, 15)]) == [(0, 5), (10, 15)]


def test_compose_concatenates_text_with_newlines() -> None:
    text, _meta = _compose_blocks([Block(text="Hello", style="normal")])
    assert text == "Hello\n"


def test_compose_bold_prefix_capped_to_visible_text() -> None:
    _text, meta = _compose_blocks([Block(text="ABC", style="normal", bold_prefix_chars=99)])
    assert meta["bold_ranges"] == [(0, 3)]


def test_compose_groups_consecutive_bullets() -> None:
    blocks = [
        Block(text="H", style="heading_3"),
        Block(text="A", style="bullet"),
        Block(text="B", style="bullet"),
    ]
    _text, meta = _compose_blocks(blocks)
    assert len(meta["bullet_ranges"]) == 1


# ---------------------------------------------------------------------------
# _find_container_heading_end / _heading_exists
# ---------------------------------------------------------------------------


def _heading_doc(text: str, style: str, end_index: int) -> dict[str, Any]:
    elem = _fake_paragraph_elem(text + "\n", style)
    elem["endIndex"] = end_index
    return _fake_doc(elem)


def test_find_container_returns_end_index() -> None:
    doc = _heading_doc("Memos", "HEADING_3", 42)
    assert _find_container_heading_end(doc, "Memos", level=3) == 42


def test_find_container_raises_when_missing() -> None:
    doc = _heading_doc("Other", "HEADING_3", 42)
    with pytest.raises(GoogleDocsStructureError):
        _find_container_heading_end(doc, "Memos", level=3)


def test_heading_exists_true() -> None:
    doc = _heading_doc("Zeno Moto", "HEADING_3", 40)
    assert _heading_exists(doc, "Zeno Moto", 3) is True


def test_heading_exists_false_at_wrong_level() -> None:
    doc = _heading_doc("Zeno Moto", "HEADING_2", 40)
    assert _heading_exists(doc, "Zeno Moto", 3) is False


# ---------------------------------------------------------------------------
# _is_noninteractive
# ---------------------------------------------------------------------------


def test_noninteractive_when_headless_env_set() -> None:
    assert _is_noninteractive({"BLOG_ENGINE_HEADLESS": "1"}, stdin_isatty=True) is True


def test_noninteractive_when_stdin_not_a_tty() -> None:
    assert _is_noninteractive({}, stdin_isatty=False) is True


def test_interactive_when_tty_and_no_headless_flag() -> None:
    assert _is_noninteractive({}, stdin_isatty=True) is False


# ---------------------------------------------------------------------------
# _credentials_path
# ---------------------------------------------------------------------------


def test_credentials_path_prefers_own_config_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own_dir = tmp_path / "own"
    own_dir.mkdir()
    (own_dir / "credentials.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("BLOG_ENGINE_CONFIG_DIR", str(own_dir))
    assert _credentials_path() == own_dir / "credentials.json"


def test_credentials_path_falls_back_to_angel_memos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own_dir = tmp_path / "own"
    own_dir.mkdir()
    monkeypatch.setenv("BLOG_ENGINE_CONFIG_DIR", str(own_dir))
    result = _credentials_path()
    assert result == Path.home() / ".config" / "angel-memos" / "credentials.json"
