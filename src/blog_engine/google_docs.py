"""Google Docs reader/writer for the two source docs.

Auth mirrors `angel-memos`' `google_docs.py`: OAuth desktop flow on first
use, refresh token cached at `<config_dir>/google-token.json`. `credentials.json`
is looked up in this project's own `config_dir()` first, falling back to
`angel-memos`' — that project already holds the same `documents` scope, so
there is no second authorization to do unless this project wants its own.

Everything downstream of this module reads a normalized `DocParagraph`
stream (`fetch_paragraphs`) rather than raw Docs API JSON, so the source
parsers never touch the API shape directly.
"""

# The googleapiclient discovery API is dynamically typed; its partial stubs
# leak unknowns through every chained call. Contain that here rather than
# annotating each hop — mirrors angel-memos' `google_docs.py`.
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from blog_engine.config import config_dir

_SCOPES = ["https://www.googleapis.com/auth/documents"]
_CREDENTIALS_FILENAME = "credentials.json"
_TOKEN_FILENAME = "google-token.json"
_ANGEL_MEMOS_CREDENTIALS_PATH = Path.home() / ".config" / "angel-memos" / _CREDENTIALS_FILENAME

_HEADING_STYLE_RE = re.compile(r"^HEADING_([1-6])$")

BlockStyle = Literal[
    "heading_2",
    "heading_3",
    "heading_4",
    "heading_5",
    "normal",
    "bullet",
]


@dataclass(frozen=True)
class DocParagraph:
    """One normalized paragraph read from a Google Doc.

    `text` re-emits bold/italic textRuns as markdown (`**bold**`,
    `*italic*`) rather than flattening them to plain text — the source docs
    use emphasis to carry real structure (bold sub-labels in bullets like
    `**Argument:** ...`, italic asides), and `markdown_to_blocks` downstream
    turns that markdown back into `<strong>`/`<em>`. A literal `*`/`_`
    already present in the doc text is backslash-escaped so it can't be
    misread as emphasis syntax on that trip.

    `heading_level` is `1`-`6` for `HEADING_n` styles, `None` otherwise.
    `bullet_depth` is the 0-based `bullet.nestingLevel` when the paragraph
    is a list item, else `None`. `links` collects every distinct hyperlink
    URL attached to a text run in the paragraph, in document order —
    consecutive runs of the *same* link (a single visual hyperlink is often
    split across several runs by Docs) are deduplicated, but two genuinely
    different links both appear.
    """

    text: str
    heading_level: int | None
    bullet_depth: int | None
    links: tuple[str, ...] = ()


@dataclass(frozen=True)
class Block:
    """One paragraph-level block of content to insert into a doc.

    `text` is the visible paragraph text (no trailing newline — the composer
    appends it). `style` controls the paragraph style. `bold_prefix_chars`
    bolds the first N characters of the visible text.
    """

    text: str
    style: BlockStyle
    bold_prefix_chars: int = 0


class GoogleDocsAuthError(RuntimeError):
    """Raised when OAuth setup is missing or invalid."""


class GoogleDocsStructureError(RuntimeError):
    """Raised when the target document doesn't have the expected heading."""


class GoogleDocsDuplicateError(RuntimeError):
    """Raised when an entry with the same heading already exists in the doc,
    so re-inserting would create a duplicate. Pass `force=True` to override."""


# ---------------------------------------------------------------------------
# Public API: read.
# ---------------------------------------------------------------------------


def fetch_paragraphs(doc_id: str) -> list[DocParagraph]:
    """Read `doc_id` and return its paragraphs as a normalized stream."""
    service = build("docs", "v1", credentials=_load_credentials())
    doc = service.documents().get(documentId=doc_id).execute()
    return _extract_paragraphs(doc)


def _extract_paragraphs(doc: dict[str, Any]) -> list[DocParagraph]:
    """Pure extraction from a `documents.get` response body — split out from
    `fetch_paragraphs` so it's testable against a hand-built fixture."""
    result: list[DocParagraph] = []
    for elem in doc.get("body", {}).get("content", []):
        para = elem.get("paragraph")
        if para is None:
            continue
        text = _paragraph_text(para)
        if not text.strip():
            continue
        named_style = para.get("paragraphStyle", {}).get("namedStyleType", "")
        bullet = para.get("bullet")
        result.append(
            DocParagraph(
                text=text,
                heading_level=_heading_level(named_style),
                bullet_depth=bullet.get("nestingLevel", 0) if bullet is not None else None,
                links=_paragraph_links(para),
            )
        )
    return result


def _paragraph_text(para: dict[str, Any]) -> str:
    """Concatenated textRun content, re-emitting bold/italic runs as
    markdown, with the trailing newline stripped. See `DocParagraph`."""
    runs = _merge_styled_runs(para.get("elements", []))
    rendered = "".join(_render_styled_run(content, bold, italic) for content, bold, italic in runs)
    return rendered.removesuffix("\n")


def _merge_styled_runs(elements: list[dict[str, Any]]) -> list[tuple[str, bool, bool]]:
    """Concatenate each textRun's content, style, and adjacency into
    `(content, bold, italic)` triples, merging consecutive runs that share
    the same `(bold, italic)` pair — Docs frequently splits one visually
    continuous styled phrase into several runs at formatting or link
    boundaries, and re-wrapping each fragment separately would produce
    `**Word1** **Word2**` instead of `**Word1 Word2**`."""
    merged: list[tuple[str, bool, bool]] = []
    for elem in elements:
        text_run = elem.get("textRun")
        if text_run is None:
            continue
        content = text_run.get("content", "")
        style = text_run.get("textStyle", {})
        bold = bool(style.get("bold", False))
        italic = bool(style.get("italic", False))
        if merged and merged[-1][1] == bold and merged[-1][2] == italic:
            prev_content, _, _ = merged[-1]
            merged[-1] = (prev_content + content, bold, italic)
        else:
            merged.append((content, bold, italic))
    return merged


def _render_styled_run(content: str, bold: bool, italic: bool) -> str:
    """Wrap `content` in markdown emphasis markers, keeping any leading or
    trailing whitespace outside the markers (Docs sometimes includes a
    trailing space inside a bold run) and escaping literal `*`/`_` inside
    it. A whitespace-only run (e.g. the paragraph's closing newline
    inheriting the previous run's style) is returned unchanged — there is no
    visible text to emphasize."""
    if not content.strip():
        return content
    leading = content[: len(content) - len(content.lstrip())]
    trailing = content[len(content.rstrip()) :]
    core = _escape_markdown_syntax(content.strip())
    if bold and italic:
        core = f"**_{core}_**"
    elif bold:
        core = f"**{core}**"
    elif italic:
        core = f"*{core}*"
    return f"{leading}{core}{trailing}"


def _escape_markdown_syntax(text: str) -> str:
    """Backslash-escape a literal backslash, `*`, or `_` so doc text that
    happens to contain them survives `markdown_to_blocks` as plain
    characters rather than being read as emphasis syntax."""
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")


def _paragraph_links(para: dict[str, Any]) -> tuple[str, ...]:
    """Distinct hyperlink URLs in document order, collapsing consecutive
    runs that carry the same link (one visual hyperlink split across runs)."""
    links: list[str] = []
    for run in para.get("elements", []):
        text_run = run.get("textRun")
        if text_run is None:
            continue
        link = text_run.get("textStyle", {}).get("link")
        if link is None:
            continue
        url = link.get("url")
        if not isinstance(url, str):
            continue
        if not links or links[-1] != url:
            links.append(url)
    return tuple(links)


def _heading_level(named_style: str) -> int | None:
    match = _HEADING_STYLE_RE.match(named_style)
    return int(match.group(1)) if match is not None else None


# ---------------------------------------------------------------------------
# Public API: write (book-review flow).
# ---------------------------------------------------------------------------


def append_under_heading(
    doc_id: str,
    container_heading: str,
    container_level: int,
    blocks: list[Block],
    *,
    dedupe_heading: str | None = None,
    dedupe_level: int | None = None,
    force: bool = False,
) -> None:
    """Insert `blocks` immediately after the named container heading.

    Ported from angel-memos' `insert_blocks_under`: concurrency-safe via
    `writeControl.requiredRevisionId` with a single retry on a 400/409 (a
    human editing the doc mid-request), and optionally idempotent via a
    dedupe-heading existence check.

    Raises:
      GoogleDocsStructureError: the container heading is missing.
      GoogleDocsDuplicateError: an entry with `dedupe_heading` already exists.
    """
    service = build("docs", "v1", credentials=_load_credentials())

    def _attempt() -> None:
        doc = service.documents().get(documentId=doc_id).execute()
        if (
            not force
            and dedupe_heading is not None
            and dedupe_level is not None
            and _heading_exists(doc, dedupe_heading, dedupe_level)
        ):
            raise GoogleDocsDuplicateError(
                f"An entry titled '{dedupe_heading}' already exists in the doc. "
                f"Re-running would duplicate it; pass force=True to override."
            )
        insert_at = _find_container_heading_end(doc, container_heading, container_level)
        api_requests = _build_insert_requests(insert_at, blocks)
        body: dict[str, Any] = {"requests": api_requests}
        revision_id = doc.get("revisionId")
        if revision_id:
            body["writeControl"] = {"requiredRevisionId": revision_id}
        service.documents().batchUpdate(documentId=doc_id, body=body).execute()

    try:
        _attempt()
    except HttpError as exc:
        if exc.resp.status in (400, 409):
            _attempt()
        else:
            raise


def _build_insert_requests(insert_at: int, blocks: list[Block]) -> list[dict[str, Any]]:
    text, meta = _compose_blocks(blocks)
    api_requests: list[dict[str, Any]] = [
        {"insertText": {"location": {"index": insert_at}, "text": text}},
    ]
    for named_style, rel_start, rel_end in meta["paragraph_styles"]:
        api_requests.append(
            {
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": insert_at + rel_start,
                        "endIndex": insert_at + rel_end,
                    },
                    "paragraphStyle": {"namedStyleType": named_style},
                    "fields": "namedStyleType",
                }
            }
        )
    for rel_start, rel_end in meta["bold_ranges"]:
        api_requests.append(
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": insert_at + rel_start,
                        "endIndex": insert_at + rel_end,
                    },
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
        )
    for rel_start, rel_end in meta["bullet_ranges"]:
        api_requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": insert_at + rel_start,
                        "endIndex": insert_at + rel_end,
                    },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )
    return api_requests


def _compose_blocks(blocks: list[Block]) -> tuple[str, dict[str, list[Any]]]:
    """Flatten `blocks` to insertable text + relative-offset request metadata."""
    pieces: list[str] = []
    paragraph_styles: list[tuple[str, int, int]] = []
    bold_ranges: list[tuple[int, int]] = []
    bullet_block_ranges: list[tuple[int, int]] = []

    cursor = 0
    for block in blocks:
        block_text = block.text + "\n"
        pieces.append(block_text)
        rel_start = cursor
        rel_end = cursor + len(block_text)

        paragraph_styles.append((_block_style_to_named(block.style), rel_start, rel_end))

        if block.bold_prefix_chars > 0:
            n = min(block.bold_prefix_chars, len(block.text))
            bold_ranges.append((rel_start, rel_start + n))

        if block.style == "bullet":
            bullet_block_ranges.append((rel_start, rel_end))

        cursor = rel_end

    bullet_ranges = _merge_adjacent_ranges(bullet_block_ranges)
    return "".join(pieces), {
        "paragraph_styles": paragraph_styles,
        "bold_ranges": bold_ranges,
        "bullet_ranges": bullet_ranges,
    }


def _block_style_to_named(style: BlockStyle) -> str:
    if style == "heading_2":
        return "HEADING_2"
    if style == "heading_3":
        return "HEADING_3"
    if style == "heading_4":
        return "HEADING_4"
    if style == "heading_5":
        return "HEADING_5"
    return "NORMAL_TEXT"


def _merge_adjacent_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    out: list[tuple[int, int]] = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = out[-1]
        if start == prev_end:
            out[-1] = (prev_start, end)
        else:
            out.append((start, end))
    return out


def _find_container_heading_end(doc: dict[str, Any], text: str, level: int) -> int:
    target_style = f"HEADING_{level}"
    for elem in doc.get("body", {}).get("content", []):
        para = elem.get("paragraph")
        if para is None:
            continue
        style = para.get("paragraphStyle", {}).get("namedStyleType", "")
        if style != target_style:
            continue
        if _paragraph_text(para).strip() == text:
            return int(elem["endIndex"])
    raise GoogleDocsStructureError(
        f"Document does not contain a {target_style} paragraph titled '{text}'. "
        f"Add it manually before publishing entries."
    )


def _heading_exists(doc: dict[str, Any], text: str, level: int) -> bool:
    target_style = f"HEADING_{level}"
    for elem in doc.get("body", {}).get("content", []):
        para = elem.get("paragraph")
        if para is None:
            continue
        if para.get("paragraphStyle", {}).get("namedStyleType", "") != target_style:
            continue
        if _paragraph_text(para).strip() == text:
            return True
    return False


# ---------------------------------------------------------------------------
# Auth.
# ---------------------------------------------------------------------------


def _is_noninteractive(env: dict[str, str], stdin_isatty: bool) -> bool:
    """Whether the browser OAuth flow would have no human to complete it."""
    if env.get("BLOG_ENGINE_HEADLESS", "").strip().lower() in {"1", "true", "yes"}:
        return True
    return not stdin_isatty


def ensure_credentials() -> None:
    """Auth preflight: obtain (and cache) credentials, failing fast with a
    clear error rather than hanging on a browser prompt mid-run."""
    _load_credentials()


def _credentials_path() -> Path:
    """`credentials.json` location: this project's own config dir first,
    falling back to angel-memos' (already authorized with the same scope)."""
    own = config_dir() / _CREDENTIALS_FILENAME
    if own.is_file():
        return own
    return _ANGEL_MEMOS_CREDENTIALS_PATH


def _load_credentials() -> Credentials:
    token_path = config_dir() / _TOKEN_FILENAME
    creds_path = _credentials_path()

    creds: Credentials | None = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if creds is not None and creds.valid:
        return creds

    if creds is not None and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise GoogleDocsAuthError(
                f"Cached Google token at {token_path} could not be refreshed "
                f"({exc}). Delete it and re-run interactively to re-authorize."
            ) from exc
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not creds_path.is_file():
        raise GoogleDocsAuthError(
            f"Missing OAuth credentials. Looked at:\n"
            f"  - {config_dir() / _CREDENTIALS_FILENAME}\n"
            f"  - {_ANGEL_MEMOS_CREDENTIALS_PATH}\n"
            "1. Create a Google Cloud project (or reuse angel-memos')\n"
            "2. Enable the Google Docs API\n"
            "3. Create OAuth client credentials (Desktop app type)\n"
            "4. Save the credentials JSON to one of the paths above"
        )

    if _is_noninteractive(dict(os.environ), sys.stdin.isatty()):
        raise GoogleDocsAuthError(
            "Google Docs authorization is required but this is a non-interactive "
            "run (no browser available). Run `blog-engine check-auth` once from "
            "an interactive terminal to authorize, then retry."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), _SCOPES)
    creds = cast(Credentials, flow.run_local_server(port=0))
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
