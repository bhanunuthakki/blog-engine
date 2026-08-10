# blog-engine

Turns things already written elsewhere into WordPress **drafts** for
[bhanunuthakki.com](https://www.bhanunuthakki.com), and writes new book reviews
natively.

Two source docs in, drafts out:

| Source | Becomes | Category |
|---|---|---|
| `Book & Podcast Notes (Master)` | one post per book/podcast entry | `books` |
| `[Public] Investing Memos` | one post per co-investment thesis | `investing` |

Nothing here ever publishes. Every write lands as a draft; publishing is a human
action in WP Admin. See [AGENTS.md](AGENTS.md) for why, for the positioning filter
that decides whether a source entry deserves a post at all, and for the plain-
language voice rules every draft has to follow.

**What to write next lives in [ROADMAP.md](ROADMAP.md).**

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

**WordPress.** Credentials live at `C:\Users\bhanu\.gemini\.secrets\wordpress.env`
(site URL, username, application password). Generate the application password at
WP Admin → Users → Profile → Application Passwords. Never commit this file.

**Google Docs.** Reuses the `angel-memos` OAuth client — that project already
holds the `documents` scope this one needs, so there's nothing new to authorize.
If you ever need a separate client, drop `credentials.json` in
`%USERPROFILE%\.config\blog-engine\` and authorize once from an interactive
terminal.

Verify both:

```bash
blog-engine check-auth
```

## Usage

Always dry-run first. It fetches, parses, renders, and prints one decision per
source entry without writing anything:

```bash
blog-engine sync --source all --dry-run
```

Then apply. The **first** real sync will see every historical entry in both docs,
so go incrementally:

```bash
blog-engine sync --source all --apply --limit 2
```

Other commands:

| Command | Does |
|---|---|
| `blog-engine list-new` | Pending decisions only, no writes |
| `blog-engine show <slug>` | Print one entry's rendered Markdown — no WordPress call |
| `blog-engine suppress --source <s>` | Retire a backlog: mark current entries never-to-post (local ledger only) |
| `blog-engine unsuppress <key>` | Reverse a suppression |
| `blog-engine check-auth` | Verify WordPress and Google credentials |

### Retired backlogs

The 15 memo entries that existed on 2026-07-24 are **suppressed** — the historical
deal memos aren't wanted on the blog, so they're recorded as never-to-be-posted and
show up as `skip_suppressed`. Memos added *after* that date are picked up normally.
Suppression is hash-free, so editing a retired memo doesn't resurrect it;
`unsuppress` is the only way back.

The book/podcast backlog is **not** suppressed — 30 entries remain available to work
through.

## Skills

`plain-writing` and `book-review` are repo-local Codex skills. Invoke them with
`$plain-writing` or `$book-review`, or ask in plain language. Claude Code uses the compatibility
entry under `.claude/skills`; Gemini reads the canonical `SKILL.md` through the
project routing in [GEMINI.md](GEMINI.md).

| Skill | Use |
|---|---|
| `$plain-writing` | Compress public copy into Bhanu's plain voice without losing facts or uncertainty |
| `$book-review` | Turn reactions plus attribution-checked research into terse notes → approval → master doc + WP draft |
| `blog-sync` | Draft posts for source entries that don't have one yet |
| `wp-post` | One-off post/page read and write |
| `post-idea` | Sharpen an idea into an angle; standing backlog included |

## How it works

Markdown is the single interchange format. Gutenberg blocks appear only at the
WordPress boundary — the site runs the block editor, so posting raw HTML yields a
post that renders but can't be edited.

```
Google Doc → DocParagraph[] → BookNotesEntry / PublicMemoEntry
                                        ↓  render.py
                                   PostDraft (markdown)
                                        ↓  sync.decide  (pure, no network)
                                   SyncDecision[]
                                        ↓  sync.execute
                            markdown_to_blocks → WordPress draft
                                        ↓
                                 state/posted.json
```

`state/posted.json` is the ledger: which source entry became which post, plus a
content hash. A changed hash on a still-draft post refreshes it; a changed hash on
a **published** post is reported and never written — a live post is only edited by
a human who decided to.

Slugs deliberately exclude mutable metadata (no rating, no date) so an entry keeps
its identity across edits.

## Development

```bash
.venv/Scripts/ruff format . && .venv/Scripts/ruff check .
.venv/Scripts/basedpyright
.venv/Scripts/pytest
```

Tests are pure-core and hit no network. Integration tests touch the real site and
real docs and are skipped by default — opt in with `pytest -m integration`.

## Out of scope

The **private** memo doc is never read; anonymization is guaranteed upstream by
`angel-memos`. Linking anonymized `earnings-summary` micro-theses is deferred until
it gets its own anonymization pass. See [DEFINITIONS.md](DEFINITIONS.md) for the
canonical vocabulary.
