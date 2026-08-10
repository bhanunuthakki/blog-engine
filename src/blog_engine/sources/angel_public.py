"""Parse the [Public] Investing Memos doc into `PublicMemoEntry` values.

Doc shape, written by `angel-memos` (see that project's `google_docs.py`
docstring): an H3 container `Memos`, then per entry an H4
`<Category Descriptor> — <Stage> Deal Memo`, a `Date: <Month Year>` line,
and bold-labelled paragraphs/bullet groups (`What does it do?`, `Market &
Opportunity`, `Team`, ...).

Scoping to `Memos` is a privacy boundary, not a parsing nicety: the doc's H1
is `Private Investing`, and three sibling H3 sections — `Investment
Strategy`, `Portfolio Observations`, `Diligence Process` — sit before
`Memos` and are NOT cleared for publication (they aren't written by the
anonymizing pipeline the way `Memos` is). Parsing stops at the next H3 or
end of doc. A missing `Memos` heading is a hard error: a doc restructure
that silently returned zero entries would look like "nothing new to sync"
instead of "scope boundary broke."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from blog_engine.config import Settings
from blog_engine.google_docs import DocParagraph
from blog_engine.models import Bullet, MemoSection, PublicMemoEntry

# em dash / en dash / hyphen are all real upstream variants of the delimiter.
_MEMO_HEADING_RE = re.compile(r"^(?P<desc>.+?)\s+[—–-]\s+(?P<stage>.+?)\s+Deal\s+Memo$")  # noqa: RUF001

_KNOWN_LABELS = (
    "What does it do?",
    "Why is it important?",
    "Market & Opportunity",
    "Team",
    "Key Metrics (Anonymized Ranges)",
    "Competitive Moat & Company Superpower",
    "Anti-Thesis",
    "Bull Case",
)


class PublicMemosStructureError(RuntimeError):
    """Raised when the `Memos` container heading is missing.

    Returning an empty list instead would silently widen the parse scope to
    nothing (safe but useless) or, if the check were skipped entirely, risk
    treating pre-`Memos` content as public — a privacy failure. Fail loudly.
    """


def parse_public_memos(paragraphs: list[DocParagraph], settings: Settings) -> list[PublicMemoEntry]:
    """Extract every entry under the `Memos` H3, stopping at the next H3."""
    container_level = settings.public_memos_entry_level - 1
    container_heading = settings.public_memos_container_heading

    if not any(
        p.heading_level == container_level and p.text.strip() == container_heading
        for p in paragraphs
    ):
        raise PublicMemosStructureError(
            f"No H{container_level} heading '{container_heading}' found in the doc. "
            "Refusing to parse: content before this heading is not cleared for "
            "publication, and returning zero entries would hide a doc restructure."
        )

    entries: list[PublicMemoEntry] = []
    in_container = False
    entry: _MemoBuilder | None = None
    section: _SectionBuilder | None = None

    def flush_section() -> None:
        nonlocal section
        if entry is not None and section is not None:
            entry.sections.append(section.build())
        section = None

    def flush_entry() -> None:
        nonlocal entry
        flush_section()
        if entry is not None:
            entries.append(entry.build())
        entry = None

    for para in paragraphs:
        level = para.heading_level
        text = para.text.strip()

        if level is not None and level <= container_level:
            flush_entry()
            in_container = level == container_level and text == container_heading
            continue

        if not in_container:
            continue

        if level == settings.public_memos_entry_level:
            flush_entry()
            entry = _MemoBuilder.from_heading(text)
            continue

        if entry is None:
            continue  # stray content between the container heading and the first entry

        if text.startswith("Date:"):
            entry.date_label = text.removeprefix("Date:").strip()
            continue

        if para.bullet_depth is not None:
            if section is not None:
                section.bullets.append(Bullet(text=text, depth=min(para.bullet_depth, 3)))
            continue

        label, body = _split_label(text)
        if label is not None:
            flush_section()
            section = _SectionBuilder(label=label, body=body)

    flush_entry()
    return entries


def _split_label(text: str) -> tuple[str | None, str]:
    """Match `text` against the known section labels.

    A banner (`Market & Opportunity` alone, followed by bullets) returns
    `(label, "")`; an inline-labelled paragraph (`What does it do? <body>`)
    returns `(label, body)`; anything else returns `(None, text)`.

    angel-memos writes every label bold (`_section_banner`/
    `_paragraph_with_bold_prefix`), which `DocParagraph.text` now surfaces
    as `**Label**` markdown — both the plain and bold-wrapped forms match.
    """
    for label in _KNOWN_LABELS:
        for candidate_label in (label, f"**{label}**"):
            if text == candidate_label:
                return label, ""
            prefix = f"{candidate_label} "
            if text.startswith(prefix):
                return label, text[len(prefix) :].strip()
    return None, text


def _split_memo_heading(raw_heading: str) -> tuple[str, str]:
    """Split `<descriptor> <dash> <stage> Deal Memo` into its two halves.

    The dash may be an em dash, en dash, or plain hyphen, but must be
    space-delimited — internal hyphens (`Plug-and-Play`, `Pre-Seed`) never
    match since they have no surrounding whitespace. Headings that don't fit
    the shape (no dash, or no `Deal Memo` suffix) keep the whole heading as
    `category_descriptor` with an empty `stage_label` — tolerated, not raised.
    """
    text = raw_heading.strip()
    match = _MEMO_HEADING_RE.match(text)
    if match is None:
        return text, ""
    return match.group("desc").strip(), match.group("stage").strip()


@dataclass
class _SectionBuilder:
    label: str
    body: str = ""
    bullets: list[Bullet] = field(default_factory=list[Bullet])

    def build(self) -> MemoSection:
        return MemoSection(label=self.label, body=self.body, bullets=tuple(self.bullets))


@dataclass
class _MemoBuilder:
    raw_heading: str
    category_descriptor: str
    stage_label: str
    date_label: str | None = None
    sections: list[MemoSection] = field(default_factory=list[MemoSection])

    def build(self) -> PublicMemoEntry:
        return PublicMemoEntry(
            raw_heading=self.raw_heading,
            category_descriptor=self.category_descriptor,
            stage_label=self.stage_label,
            date_label=self.date_label,
            sections=tuple(self.sections),
        )

    @classmethod
    def from_heading(cls, raw_heading: str) -> _MemoBuilder:
        category, stage = _split_memo_heading(raw_heading)
        return cls(raw_heading=raw_heading, category_descriptor=category, stage_label=stage)
