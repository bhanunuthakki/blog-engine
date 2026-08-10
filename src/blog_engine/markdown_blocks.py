"""Markdown -> Gutenberg block markup.

Pure text-in, text-out. This is the module every rendered post body passes
through at the WordPress boundary, so it is deliberately the most
thoroughly tested thing in the project (see `tests/test_markdown_blocks.py`).

Supported constructs: headings (`##`-`####`), paragraphs, unordered and
ordered lists (with indent-based nesting), blockquotes, and the inline set
bold/italic/code/link. Block markup matches the site's own verified
Gutenberg output — notably, an H2 heading carries no `level` attribute
(Gutenberg's default), while H3+ do.

`\\*` and `\\_` are recognized as escaped literals (backslash-then-marker),
so a source document that happens to contain a literal asterisk or
underscore — or one whose emphasis got re-emitted as markdown by
`google_docs._paragraph_text` and needed to protect an incidental one —
survives the round trip instead of being misread as emphasis syntax.

A bare YouTube or Vimeo URL alone on its own line (its own paragraph)
becomes a `core/embed` block instead of a linked paragraph — see
`_render_embed` for the exact markup and the sources it was verified
against. Any other URL, or one with surrounding text, stays a plain
paragraph/link; a video URL inside a list item is never converted (list
items never go through the paragraph path at all).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{2,4})\s+(.*)$")
_LIST_ITEM_RE = re.compile(r"^(?P<indent> *)(?P<marker>[-*+]|\d+\.)\s+(?P<text>.*)$")

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_ITALIC_UNDERSCORE_RE = re.compile(r"_([^_]+)_")

# Placeholders that protect `\*`/`\_` from the emphasis regexes above; never
# appear in real doc text, so they're safe stand-ins during the sub passes.
_ESCAPED_STAR_PLACEHOLDER = "\x00ESC-STAR\x00"
_ESCAPED_UNDERSCORE_PLACEHOLDER = "\x00ESC-USCORE\x00"

# Recognized video hosts, mapped to the Gutenberg `providerNameSlug` a real
# oEmbed resolution would assign them (see `_render_embed`).
_YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:(?:www|m)\.)?youtube\.com/(?:watch\?v=|shorts/)\S+$", re.IGNORECASE
)
_YOUTU_BE_URL_RE = re.compile(r"^https?://youtu\.be/\S+$", re.IGNORECASE)
_VIMEO_URL_RE = re.compile(r"^https?://(?:www\.)?vimeo\.com/\S+$", re.IGNORECASE)

# Loom is deliberately absent. It is not one of WordPress core's built-in
# oEmbed providers, and a proxy check against the live site on 2026-07-24
# confirmed YouTube and Vimeo resolve there while Loom has no provider. An
# embed block for a Loom URL is structurally valid but renders as a plain
# link, so emitting one would be a silent failure — better to leave a Loom
# URL as the plain link it would become anyway. Record with Loom if you
# like; host the result on YouTube.


def markdown_to_blocks(markdown: str) -> str:
    """Render `markdown` as a sequence of Gutenberg blocks separated by a
    blank line, matching the site's live block markup."""
    lines = markdown.splitlines()
    blocks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match is not None:
            level = len(heading_match.group(1))
            blocks.append(_render_heading(level, heading_match.group(2).strip()))
            i += 1
            continue

        if _is_blockquote_line(line):
            paragraphs, i = _consume_blockquote(lines, i)
            blocks.append(_render_blockquote(paragraphs))
            continue

        if _is_list_item(line):
            node, i = _parse_list(lines, i)
            blocks.append(_render_list(node))
            continue

        paragraph_lines, i = _consume_paragraph(lines, i)
        joined = " ".join(paragraph_lines)
        provider = _video_provider(joined)
        if provider is not None:
            blocks.append(_render_embed(joined, provider))
        else:
            blocks.append(_render_paragraph(joined))

    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Block consumers — group raw lines into one logical block each.
# ---------------------------------------------------------------------------


def _is_blockquote_line(line: str) -> bool:
    return line.lstrip().startswith(">")


def _is_list_item(line: str) -> bool:
    return _LIST_ITEM_RE.match(line) is not None


def _consume_paragraph(lines: list[str], start: int) -> tuple[list[str], int]:
    """Consecutive non-blank lines that aren't headings/quotes/list items
    join into one paragraph (markdown soft-wrap)."""
    collected: list[str] = []
    i = start
    while (
        i < len(lines)
        and lines[i].strip()
        and _HEADING_RE.match(lines[i]) is None
        and not _is_blockquote_line(lines[i])
        and not _is_list_item(lines[i])
    ):
        collected.append(lines[i].strip())
        i += 1
    return collected, i


def _consume_blockquote(lines: list[str], start: int) -> tuple[list[str], int]:
    """Consecutive `>` lines, split into paragraphs on a bare `>` line."""
    paragraphs: list[str] = []
    current: list[str] = []
    i = start
    while i < len(lines) and _is_blockquote_line(lines[i]):
        content = lines[i].lstrip()[1:].strip()
        if content:
            current.append(content)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
        i += 1
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs, i


# ---------------------------------------------------------------------------
# List parsing — indent-based nesting (2 or 4 spaces per level, either way).
# ---------------------------------------------------------------------------


@dataclass
class _ListItem:
    text: str
    children: _ListNode | None = None


@dataclass
class _ListNode:
    ordered: bool
    items: list[_ListItem] = field(default_factory=list[_ListItem])


def _parse_list(lines: list[str], start: int) -> tuple[_ListNode, int]:
    first_match = _LIST_ITEM_RE.match(lines[start])
    assert first_match is not None  # caller only enters via _is_list_item
    indent = len(first_match.group("indent"))
    ordered = first_match.group("marker") not in ("-", "*", "+")

    items: list[_ListItem] = []
    i = start
    while i < len(lines):
        match = _LIST_ITEM_RE.match(lines[i])
        if match is None or len(match.group("indent")) != indent:
            break
        text = _render_inline(match.group("text").strip())
        i += 1

        children: _ListNode | None = None
        if i < len(lines):
            next_match = _LIST_ITEM_RE.match(lines[i])
            if next_match is not None and len(next_match.group("indent")) > indent:
                children, i = _parse_list(lines, i)

        items.append(_ListItem(text=text, children=children))

    return _ListNode(ordered=ordered, items=items), i


def _render_list(node: _ListNode) -> str:
    tag = "ol" if node.ordered else "ul"
    open_comment = '<!-- wp:list {"ordered":true} -->' if node.ordered else "<!-- wp:list -->"
    lines = [open_comment, f'<{tag} class="wp-block-list">']
    for item in node.items:
        lines.append("<!-- wp:list-item -->")
        li_content = item.text
        if item.children is not None:
            li_content = f"{item.text}\n{_render_list(item.children)}"
        lines.append(f"<li>{li_content}</li>")
        lines.append("<!-- /wp:list-item -->")
    lines.append(f"</{tag}>")
    lines.append("<!-- /wp:list -->")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Block renderers.
# ---------------------------------------------------------------------------


def _render_heading(level: int, text: str) -> str:
    inline = _render_inline(text)
    if level == 2:
        return (
            f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{inline}</h2>\n<!-- /wp:heading -->'
        )
    return (
        f'<!-- wp:heading {{"level":{level}}} -->\n'
        f'<h{level} class="wp-block-heading">{inline}</h{level}>\n'
        "<!-- /wp:heading -->"
    )


def _render_paragraph(text: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{_render_inline(text)}</p>\n<!-- /wp:paragraph -->"


def _video_provider(text: str) -> str | None:
    """`"youtube"` or `"vimeo"` if `text` is *exactly* one bare URL from a
    provider this site can actually resolve, else `None`. Anchored
    start-to-end, so surrounding words (same line or joined from an adjacent
    line with no blank separator) disqualify it — only a URL alone in its own
    paragraph embeds; everything else stays a normal paragraph/link."""
    if _YOUTUBE_URL_RE.match(text) or _YOUTU_BE_URL_RE.match(text):
        return "youtube"
    if _VIMEO_URL_RE.match(text):
        return "vimeo"
    return None


def _render_embed(url: str, provider: str) -> str:
    """A Gutenberg `core/embed` block for `url`.

    Verified against the real `core/embed` source rather than guessed
    (WordPress/Gutenberg `trunk`, block-library package):
      - block.json (attribute names/types/defaults):
        packages/block-library/src/embed/block.json
      - save() output shape — the `<figure>`/`<div class="wp-block-embed__
        wrapper">` structure, and that the URL is bare text with a leading/
        trailing newline, not a link: packages/block-library/src/embed/save.js
      - `is-type-*`/`is-provider-*`/`wp-block-embed-*` class construction:
        same save.js
      - `providerNameSlug` values and URL-matching patterns for YouTube/
        Vimeo: packages/block-library/src/embed/variations.js
      - aspect-ratio class naming (`wp-embed-aspect-<w>-<h>` +
        `wp-has-aspect-ratio`) and that it's derived from the resolved
        iframe's real width/height: packages/block-library/src/embed/util.js
        (`getClassNames`)

    Only `responsive` needs to appear in the attributes JSON — it's the one
    attribute here whose value (`true`) differs from its block.json default
    (`false`); `allowResponsive`/`previewable` are left at their defaults
    and so stay unserialized, matching how the editor itself would emit them.

    We never do a live oEmbed round-trip (no network call from a pure
    function), so there's no real iframe to measure — `16-9` is assumed
    for the aspect-ratio classes as the overwhelmingly common case for
    YouTube and Vimeo, not a value read off the actual video. A wrong
    guess here is cosmetic (letterboxing), not a validation error: WordPress
    treats an element's `class` list as an order- and set-based match when
    checking a block's saved HTML against its own attributes, so this
    output round-trips as valid `core/embed` content in the editor.

    Only providers the live site actually resolves get here — see the note
    beside `_VIMEO_URL_RE` for why Loom is excluded.
    """
    class_list = (
        f"wp-block-embed is-type-video is-provider-{provider} wp-block-embed-{provider} "
        "wp-embed-aspect-16-9 wp-has-aspect-ratio"
    )
    attrs = (
        f'{{"url":"{url}","type":"video","providerNameSlug":"{provider}",'
        '"responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"}'
    )
    return (
        f"<!-- wp:embed {attrs} -->\n"
        f'<figure class="{class_list}"><div class="wp-block-embed__wrapper">\n'
        f"{_escape_html(url)}\n"
        "</div></figure>\n"
        "<!-- /wp:embed -->"
    )


def _render_blockquote(paragraphs: list[str]) -> str:
    inner = "\n".join(_render_paragraph(p) for p in paragraphs)
    return (
        "<!-- wp:quote -->\n"
        f'<blockquote class="wp-block-quote">\n{inner}\n</blockquote>\n'
        "<!-- /wp:quote -->"
    )


# ---------------------------------------------------------------------------
# Inline formatting.
# ---------------------------------------------------------------------------


def _render_inline(text: str) -> str:
    """Escape HTML-sensitive characters first, then layer inline markup on
    top — escaping first means our own generated tags can't be re-escaped,
    and a link's URL gets the same `&` -> `&amp;` treatment HTML wants.

    Backslash-escaped `\\*`/`\\_` are swapped out for placeholders before the
    emphasis regexes run (so they can't be misread as markers) and restored
    to plain `*`/`_` at the end."""
    escaped = _escape_html(text)
    escaped = escaped.replace("\\*", _ESCAPED_STAR_PLACEHOLDER).replace(
        "\\_", _ESCAPED_UNDERSCORE_PLACEHOLDER
    )
    escaped = _LINK_RE.sub(_render_link, escaped)
    escaped = _CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    escaped = _ITALIC_STAR_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)
    escaped = _ITALIC_UNDERSCORE_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)
    return escaped.replace(_ESCAPED_STAR_PLACEHOLDER, "*").replace(
        _ESCAPED_UNDERSCORE_PLACEHOLDER, "_"
    )


def _render_link(match: re.Match[str]) -> str:
    text, url = match.group(1), match.group(2)
    return f'<a href="{url}" target="_blank" rel="noreferrer noopener">{text}</a>'


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
