# blog-engine — project rulebook

Turns things Bhanu already writes elsewhere into WordPress **drafts** for
[bhanunuthakki.com](https://www.bhanunuthakki.com), and writes new book reviews
natively. It layers on the machine-wide safety contract and procedure routing;
everything below is specific to this repo.

## What this project is for

The blog is **supporting infrastructure for the builds, not the main thing.**
That was settled explicitly: the site should cost ~1–2 hr/week and most weeks
zero. This repo exists to remove the friction between "Bhanu wrote a thing" and
"the thing is on the blog" — not to manufacture content.

Consequences that bind every skill here:

- **Drafts only. Never publish.** Every write lands as `status=draft`. Publishing
  is a human action taken in WP Admin. No skill, cron, or CLI flag publishes.
- **Automated source sync never rewrites a live post.** If a source entry changes after its post
  went public, report the drift and stop; `SyncAction.REPORT_PUBLISHED_DRIFT` encodes this. A live
  edit is allowed only when the user explicitly names that post and exact change in the current
  conversation, following the read-before-write `wp-post` workflow.
- **No autonomous ideation.** An agent fleet that scans feeds and generates post
  ideas on a schedule was considered and rejected — it produces work, not value.
  Ideation happens when Bhanu asks.
- **Volume is not the goal.** Nine posts nobody reads is worse than two that get
  forwarded. If a source entry doesn't clear the bar in *Positioning* below, say
  so instead of drafting it.

## Positioning — the filter for every draft

Bhanu's distinctive value sits at the intersection of three things. A post earns
its place by standing on at least two of them:

- **Capital allocation mindset** — think like an investor. Multi-order reasoning
  down to the true value drivers; explicit return and risk profiles.
- **Technology landscape** — opinionated views on where tech is heading and where
  value will accrue.
- **Operational execution** — what it actually takes to build, and how execution
  becomes competitive advantage.

The site's job is authentic self-expression and learning in public: a repository
of real interests that invites conversations with interesting people. It is not a
portfolio site and not a thought-leadership channel.

Before drafting, ask: **does this reflect how Bhanu actually thinks?** Can he
maintain it without it becoming a burden? Does it invite the conversations he
wants? Does it clarify the positioning?

## Writing workflow

Use `.agents/skills/plain-writing/SKILL.md` for voice, selection, post-type stance, compression,
and the read-aloud gate. This rulebook owns why and what the project publishes; the skill owns how
public copy is written. The latest user edit is authoritative, including details they deliberately
removed. Do not expand an acronym when the expansion does not help the reader. Thesis structure may reuse `../angel-memos/src/angel_memos/prompts/public_doc_style.md`,
translated through the plain-writing contract for a general reader.

## Sources, and the privacy line

| Source | Doc | Becomes |
|---|---|---|
| Book & Podcast Notes (Master) | local `BLOG_ENGINE_BOOK_NOTES_DOC_ID` setting | one post per entry, category `books` |
| [Public] Investing Memos | local `BLOG_ENGINE_PUBLIC_MEMOS_DOC_ID` setting | one post per entry, category `investing` |

Before any source read, import, suppression, or sync decision, load
`docs/SOURCE_BOUNDARIES.md`. The private memo doc is never in scope; only the `Memos` subtree of the
already-anonymized public derivative may be parsed. Identifying content is an upstream failure: refuse
the draft rather than anonymizing it here. Historical memo suppression and the unsuppressed book backlog
remain ledger decisions, not fresh editorial judgment.

Public-market DCFs, briefs, and portfolio weights are not categorically private, but they may enter
this public repo only through an explicit public derivative that passes
`scripts/check_public_boundary.py` and its tests. Personal amounts, cost basis, share quantities,
account identifiers, identity-bearing source paths, private research state, and unscannable private
artifacts remain prohibited. Earnings Summary is not a current automated source; never read its live
database or private artifacts merely because public-safe derivatives are permitted.

## Architecture authority

`README.md` owns the pipeline and commands. `src/blog_engine/models.py` owns typed entries;
`sync.decide` is the pure decision boundary; and `state/posted.json` is the post ledger. A source
slug is stable identity and never includes mutable rating or date metadata.

## Video posts

Video is a public, hard-to-reverse disclosure boundary. Follow `ROADMAP.md` § Making the videos
for the recording/redaction checklist and `docs/VIDEO_POSTS.md` for supported embeds and artifact-page
placement. Stop before upload or publication; the owner performs both actions.

## Procedures

The work here breaks into five repeatable workflows. Cross-runtime owners live under
`.agents/skills`; the remaining `.claude/skills` entries are legacy runtime-local workflows pending
migration, not a second source for the cross-runtime skills. Codex can invoke discovered repo-local
skills with `$<name>`. Other runtimes read the applicable listed file completely before acting.

| Procedure | Purpose | Path |
|---|---|---|
| `plain-writing` | Compress public copy without losing facts or Bhanu's voice | `.agents/skills/plain-writing/SKILL.md` |
| `book-review` | Develop attribution-checked book/podcast notes, then place them after approval | `.agents/skills/book-review/SKILL.md` |
| `blog-sync` | Find source-doc entries with no post yet and draft them | `.claude/skills/blog-sync/SKILL.md` |
| `wp-post` | Direct WordPress read/write for one-off post work | `.claude/skills/wp-post/SKILL.md` |
| `post-idea` | Develop a post angle from a topic or the existing backlog | `.claude/skills/post-idea/SKILL.md` |

## Working here

- The site runs Gutenberg block markup, not classic HTML. Never post raw HTML.
- Credentials come from a local configured environment file and are never echoed,
  logged, or committed. The app password is a `SecretStr`.
- Google Docs auth reuses the `angel-memos` OAuth client (same `documents`
  scope), so there is no second authorization to perform.
- `blog-engine sync` defaults to `--dry-run`. Read the decision table before
  `--apply`.
- Any cron must avoid the protected **03:00–05:00 America/Los_Angeles** window
  reserved for the earnings-summary pipeline.

A draft is ready only when its source identity, privacy boundary, positioning filter, plain-writing
gate, and relevant tests pass. "Draft created" never means published or publication-approved.

## Interface

- Profile: none
