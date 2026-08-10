"""Runtime configuration: the secrets file, the two source docs, taxonomy.

Reads `%USERPROFILE%\\.config\\blog-engine\\config.toml` when present and falls
back to baked-in defaults matching the current setup. Google OAuth reuses the
`angel-memos` client secret by default — that project already holds the full
`documents` scope this one needs, so there is no second authorization to do.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from blog_engine.models import PostStatus

_DEFAULT_WORDPRESS_ENV = Path(r"C:\Users\Bhanu\.gemini\.secrets\wordpress.env")

# Doc IDs confirmed against Drive on 2026-07-24.
_DEFAULT_BOOK_NOTES_DOC_ID = "1Ec-rllS_JbpuunvgSpjfXDhpREHi1iuHyYyGb6CRAR4"
_DEFAULT_PUBLIC_MEMOS_DOC_ID = "1nyFj17M4kktlHD028AVF9D-8zeyGRGKC-MXzHNfXA80"

# Headings in the Book & Podcast Notes doc that are structure, not entries.
_DEFAULT_BOOK_NOTES_SKIP_HEADINGS = ("How I Generate Notes & Themes",)

_CONFIG_DIR_ENV_VAR = "BLOG_ENGINE_CONFIG_DIR"
_DEFAULT_CONFIG_FILENAME = "config.toml"


class Settings(BaseModel):
    """Static configuration. Nothing here varies per post."""

    model_config = ConfigDict(frozen=True)

    wordpress_env_path: Path = Field(default=_DEFAULT_WORDPRESS_ENV)

    book_notes_doc_id: str = Field(default=_DEFAULT_BOOK_NOTES_DOC_ID, min_length=1)
    public_memos_doc_id: str = Field(default=_DEFAULT_PUBLIC_MEMOS_DOC_ID, min_length=1)

    book_notes_entry_level: int = Field(default=3, ge=1, le=6)
    """Heading level at which one book/podcast entry starts (H3 today)."""

    book_notes_theme_level: int = Field(default=4, ge=1, le=6)
    """Heading level of the `Theme N:` blocks inside an entry (H4 today)."""

    book_notes_skip_headings: tuple[str, ...] = Field(default=_DEFAULT_BOOK_NOTES_SKIP_HEADINGS)

    public_memos_container_heading: str = Field(default="Memos", min_length=1)
    """The H3 container the memo entries live under, per angel-memos' writer."""

    public_memos_entry_level: int = Field(default=4, ge=1, le=6)

    public_memos_doc_url: str = Field(
        default="https://docs.google.com/document/d/1nyFj17M4kktlHD028AVF9D-8zeyGRGKC-MXzHNfXA80/edit",
        min_length=1,
    )
    """Where an investment post sends the reader for the full memo.

    An investment post is a 1-2 sentence summary plus this link — the doc is the
    artifact, the post is the pointer. Before publishing one, confirm this doc is
    actually shareable: it opens with a `Private Investing` heading and carries
    Investment Strategy / Portfolio Observations / Diligence Process sections that
    the anonymizing pipeline does not write. Parsing stays below `Memos`; a reader
    following this link does not.
    """

    book_category_slug: str = Field(default="books", min_length=1)
    investing_category_slug: str = Field(default="investing", min_length=1)

    state_dir: Path = Field(default=Path("state"))
    """Ledger location, relative to the repo root unless absolute."""

    default_status: PostStatus = PostStatus.DRAFT
    """Never anything but DRAFT without an explicit human decision."""


def config_dir() -> Path:
    """Where `config.toml` lives."""
    override = os.environ.get(_CONFIG_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".config" / "blog-engine"


def load_settings() -> Settings:
    """Read `config.toml` if present, else return defaults."""
    path = config_dir() / _DEFAULT_CONFIG_FILENAME
    if not path.is_file():
        return Settings()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return Settings.model_validate(raw)
