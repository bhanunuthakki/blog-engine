"""markdown_blocks: every block type, nesting, inline combos, escaping."""

from blog_engine.markdown_blocks import markdown_to_blocks


def test_h2_heading_has_no_level_attribute() -> None:
    """Matches the site's own verified markup: H2 carries no level attr."""
    out = markdown_to_blocks("## The Promise of Sodium-Ion")
    assert out == (
        "<!-- wp:heading -->\n"
        '<h2 class="wp-block-heading">The Promise of Sodium-Ion</h2>\n'
        "<!-- /wp:heading -->"
    )


def test_h3_heading_carries_level_attribute() -> None:
    out = markdown_to_blocks("### A Subheading")
    assert out == (
        '<!-- wp:heading {"level":3} -->\n'
        '<h3 class="wp-block-heading">A Subheading</h3>\n'
        "<!-- /wp:heading -->"
    )


def test_h4_heading_carries_level_attribute() -> None:
    out = markdown_to_blocks("#### Deep Heading")
    assert '<!-- wp:heading {"level":4} -->' in out
    assert '<h4 class="wp-block-heading">Deep Heading</h4>' in out


def test_paragraph_block() -> None:
    out = markdown_to_blocks("Just a paragraph.")
    assert out == "<!-- wp:paragraph -->\n<p>Just a paragraph.</p>\n<!-- /wp:paragraph -->"


def test_paragraph_soft_wraps_join_with_space() -> None:
    out = markdown_to_blocks("Line one\nLine two")
    assert "<p>Line one Line two</p>" in out


def test_blank_line_separates_two_paragraphs_into_two_blocks() -> None:
    out = markdown_to_blocks("First.\n\nSecond.")
    assert out == (
        "<!-- wp:paragraph -->\n<p>First.</p>\n<!-- /wp:paragraph -->"
        "\n\n"
        "<!-- wp:paragraph -->\n<p>Second.</p>\n<!-- /wp:paragraph -->"
    )


def test_unordered_list_basic() -> None:
    out = markdown_to_blocks("- one\n- two")
    assert out == (
        "<!-- wp:list -->\n"
        '<ul class="wp-block-list">\n'
        "<!-- wp:list-item -->\n"
        "<li>one</li>\n"
        "<!-- /wp:list-item -->\n"
        "<!-- wp:list-item -->\n"
        "<li>two</li>\n"
        "<!-- /wp:list-item -->\n"
        "</ul>\n"
        "<!-- /wp:list -->"
    )


def test_ordered_list_has_ordered_attribute_and_ol_tag() -> None:
    out = markdown_to_blocks("1. first\n2. second")
    assert '<!-- wp:list {"ordered":true} -->' in out
    assert '<ol class="wp-block-list">' in out
    assert "</ol>" in out


def test_nested_unordered_list_two_space_indent() -> None:
    out = markdown_to_blocks("- parent\n  - child")
    assert "<li>parent\n<!-- wp:list -->" in out
    assert "<li>child</li>" in out
    # The nested list closes, then the parent <li> closes.
    assert "<!-- /wp:list --></li>" in out


def test_nested_unordered_list_four_space_indent() -> None:
    out = markdown_to_blocks("- parent\n    - child")
    assert "<li>parent\n<!-- wp:list -->" in out
    assert "<li>child</li>" in out


def test_nested_list_is_inside_parent_li_after_parent_text() -> None:
    out = markdown_to_blocks("- parent text\n  - child text")
    parent_li_start = out.index("<li>parent text")
    child_index = out.index("child text")
    nested_open = out.index("<!-- wp:list -->", parent_li_start + 1)
    assert parent_li_start < nested_open < child_index


def test_three_level_nesting() -> None:
    out = markdown_to_blocks("- a\n  - b\n    - c")
    assert out.count("<!-- wp:list -->") == 3
    assert out.count("<!-- /wp:list -->") == 3
    assert "<li>c</li>" in out


def test_sibling_items_after_nested_child_stay_at_parent_level() -> None:
    out = markdown_to_blocks("- a\n  - nested\n- b")
    # 'b' is a top-level sibling of 'a': it comes after the nested list's
    # own closing tag, and there are exactly two </ul> in the whole output
    # (one nested, one outer) rather than three.
    inner_list_close = out.index("</ul>")
    b_index = out.index("<li>b</li>")
    assert b_index > inner_list_close
    assert out.count("</ul>") == 2


def test_blockquote_wraps_paragraph_blocks() -> None:
    out = markdown_to_blocks("> A quoted line.")
    assert out == (
        "<!-- wp:quote -->\n"
        '<blockquote class="wp-block-quote">\n'
        "<!-- wp:paragraph -->\n<p>A quoted line.</p>\n<!-- /wp:paragraph -->"
        "\n</blockquote>\n"
        "<!-- /wp:quote -->"
    )


def test_blockquote_multiple_paragraphs() -> None:
    out = markdown_to_blocks("> First quoted paragraph.\n>\n> Second quoted paragraph.")
    assert out.count("<!-- wp:paragraph -->") == 2
    assert "First quoted paragraph." in out
    assert "Second quoted paragraph." in out


def test_bold_inline() -> None:
    out = markdown_to_blocks("This is **bold** text.")
    assert "<p>This is <strong>bold</strong> text.</p>" in out


def test_italic_star_inline() -> None:
    out = markdown_to_blocks("This is *italic* text.")
    assert "<p>This is <em>italic</em> text.</p>" in out


def test_italic_underscore_inline() -> None:
    out = markdown_to_blocks("This is _italic_ text.")
    assert "<p>This is <em>italic</em> text.</p>" in out


def test_inline_code() -> None:
    out = markdown_to_blocks("Run `pytest` now.")
    assert "<p>Run <code>pytest</code> now.</p>" in out


def test_link_inline() -> None:
    out = markdown_to_blocks("An [inline link](https://example.com).")
    assert (
        '<a href="https://example.com" target="_blank" rel="noreferrer noopener">inline link</a>'
        in out
    )


def test_link_inside_bold_span_works() -> None:
    out = markdown_to_blocks("A **[bold link](https://example.com)** here.")
    assert (
        '<strong><a href="https://example.com" target="_blank" '
        'rel="noreferrer noopener">bold link</a></strong>' in out
    )


def test_mixed_inline_formatting_in_one_paragraph() -> None:
    out = markdown_to_blocks("**Bold**, *italic*, `code`, and [a link](https://x.test).")
    assert "<strong>Bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out
    assert '<a href="https://x.test"' in out


def test_backslash_escaped_star_is_not_read_as_emphasis() -> None:
    out = markdown_to_blocks("A literal \\*star\\* here.")
    assert "<p>A literal *star* here.</p>" in out
    assert "<em>" not in out


def test_backslash_escaped_underscore_is_not_read_as_emphasis() -> None:
    out = markdown_to_blocks("A literal \\_underscore\\_ here.")
    assert "<p>A literal _underscore_ here.</p>" in out
    assert "<em>" not in out


def test_escaped_star_survives_alongside_real_bold() -> None:
    out = markdown_to_blocks("**Real bold** and a literal \\*star\\*.")
    assert "<strong>Real bold</strong>" in out
    assert "literal *star*." in out


def test_html_escaping_ampersand_lt_gt() -> None:
    out = markdown_to_blocks("Ben & Jerry's <ice cream> is > great")
    assert "Ben &amp; Jerry's &lt;ice cream&gt; is &gt; great" in out
    assert "<ice cream>" not in out


def test_escaping_does_not_touch_generated_tags() -> None:
    out = markdown_to_blocks("**bold & italic** and *more*")
    assert "<strong>bold &amp; italic</strong>" in out
    assert "&lt;strong&gt;" not in out


def test_heading_inline_formatting_is_rendered() -> None:
    out = markdown_to_blocks("## The **Promise** of Sodium-Ion")
    assert '<h2 class="wp-block-heading">The <strong>Promise</strong> of Sodium-Ion</h2>' in out


def test_blocks_separated_by_blank_line() -> None:
    out = markdown_to_blocks("## Heading\n\nA paragraph.\n\n- item")
    parts = out.split("\n\n")
    assert len(parts) == 3


def test_full_document_matches_verified_site_sample() -> None:
    markdown = (
        "## The Promise of Sodium-Ion\n\nText with an [inline link](https://example.com) here."
    )
    out = markdown_to_blocks(markdown)
    assert out == (
        "<!-- wp:heading -->\n"
        '<h2 class="wp-block-heading">The Promise of Sodium-Ion</h2>\n'
        "<!-- /wp:heading -->"
        "\n\n"
        "<!-- wp:paragraph -->\n"
        "<p>Text with an "
        '<a href="https://example.com" target="_blank" rel="noreferrer noopener">'
        "inline link</a> here.</p>\n"
        "<!-- /wp:paragraph -->"
    )


# ---------------------------------------------------------------------------
# Video embeds — a bare recognized-host URL alone in its own paragraph.
# ---------------------------------------------------------------------------


def _assert_valid_embed(out: str, *, url: str, provider: str) -> None:
    """Structural checks shared by every embed test — not one long exact-
    string match, which would be brittle against the verified real markup."""
    assert out.startswith("<!-- wp:embed ")
    assert out.endswith("<!-- /wp:embed -->")
    assert f'"providerNameSlug":"{provider}"' in out
    assert f'"url":"{url}"' in out
    assert f"is-provider-{provider}" in out
    assert f"wp-block-embed-{provider}" in out
    assert "is-type-video" in out
    assert '"type":"video"' in out
    assert '"responsive":true' in out
    assert "wp-has-aspect-ratio" in out
    assert '<div class="wp-block-embed__wrapper">' in out
    # The URL appears exactly once as bare text inside the wrapper, and
    # exactly once more inside the attributes JSON — never as a link.
    assert out.count(url) == 2
    assert f'<a href="{url}"' not in out


def test_youtube_watch_url_alone_becomes_embed() -> None:
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    out = markdown_to_blocks(url)
    _assert_valid_embed(out, url=url, provider="youtube")


def test_youtu_be_short_url_alone_becomes_embed() -> None:
    url = "https://youtu.be/dQw4w9WgXcQ"
    out = markdown_to_blocks(url)
    _assert_valid_embed(out, url=url, provider="youtube")


def test_youtube_shorts_url_alone_becomes_embed() -> None:
    url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    out = markdown_to_blocks(url)
    _assert_valid_embed(out, url=url, provider="youtube")


def test_vimeo_url_alone_becomes_embed() -> None:
    url = "https://vimeo.com/76979871"
    out = markdown_to_blocks(url)
    _assert_valid_embed(out, url=url, provider="vimeo")


def test_loom_url_stays_a_link_because_the_site_cannot_resolve_it() -> None:
    """Loom isn't a WordPress core oEmbed provider, and a proxy check against
    the live site confirmed it doesn't resolve there. An embed block would be
    structurally valid but render as a bare link, so we emit the link outright
    rather than implying a player that never appears."""
    out = markdown_to_blocks("https://www.loom.com/share/abc123def456")
    assert "<!-- wp:embed" not in out
    assert "<!-- wp:paragraph -->" in out


def test_non_video_url_alone_on_a_line_stays_a_paragraph() -> None:
    out = markdown_to_blocks("https://example.com/some-page")
    assert "<!-- wp:paragraph -->" in out
    assert "<!-- wp:embed" not in out


def test_video_url_with_surrounding_text_stays_inline_link() -> None:
    out = markdown_to_blocks("Check out this build: https://youtu.be/dQw4w9WgXcQ")
    assert "<!-- wp:embed" not in out
    assert "<!-- wp:paragraph -->" in out
    assert '<a href="https://youtu.be/dQw4w9WgXcQ"' not in out  # bare, not [text](url)
    assert "https://youtu.be/dQw4w9WgXcQ" in out


def test_video_url_inside_a_list_item_is_not_converted() -> None:
    out = markdown_to_blocks("- Watch it here: https://youtu.be/dQw4w9WgXcQ")
    assert "<!-- wp:embed" not in out
    assert "<!-- wp:list -->" in out
    assert "https://youtu.be/dQw4w9WgXcQ" in out


def test_video_url_joined_to_adjacent_paragraph_line_is_not_converted() -> None:
    """A URL alone on its own *line* still needs to be alone in its own
    *paragraph* — no blank line above means it merges with the prior line
    into one paragraph, which disqualifies it."""
    out = markdown_to_blocks("Some intro text.\nhttps://youtu.be/dQw4w9WgXcQ")
    assert "<!-- wp:embed" not in out
    assert "<!-- wp:paragraph -->" in out


def test_embed_blocks_are_separated_by_blank_lines_from_siblings() -> None:
    markdown = "Intro paragraph.\n\nhttps://youtu.be/dQw4w9WgXcQ\n\nOutro paragraph."
    out = markdown_to_blocks(markdown)
    parts = out.split("\n\n")
    assert len(parts) == 3
    assert parts[1].startswith("<!-- wp:embed ")
