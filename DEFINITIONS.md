# Definitions

Canonical terminology for this repo. Use these terms verbatim in code
(variables, types, functions, file names), comments, commit messages, and
conversation. Propose additions before introducing a new domain term.

## Sources

- **Source doc** — one of the two Google Docs this project reads. Never plural
  beyond those two, and never the private memo doc.
- **Book notes doc** — `Book & Podcast Notes (Master)`. H3 per entry, H4 per theme.
- **Public memos doc** — `[Public] Investing Memos`. H3 container `Memos`, H4 per entry.
- **Source entry** — one parsed unit from a source doc: a `BookNotesEntry` or a
  `PublicMemoEntry`. Identified forever by its **raw heading**.
- **Raw heading** — the verbatim heading text of a source entry, unmodified. The
  stable upstream identity; stored on the ledger as `source_key`.
- **Doc paragraph** — `DocParagraph`, the normalized read model (text +
  `heading_level` + `bullet_depth`) that parsers consume. Insulates parsing from
  the Google Docs API shape.

## Entry anatomy

- **Theme** — one `Theme N: <label>` section of a book notes entry (`ThemeBlock`).
  Its `label` has the `Theme N:` prefix stripped.
- **Summary** — the single non-bullet line directly under a theme heading.
- **Takeaway** — a top-level bullet inside a theme: a bolded label plus a claim.
- **Example** — a child bullet under a takeaway carrying the concrete anecdote
  (dates, names, numbers). A takeaway without an example is incomplete.
- **Memo section** — one labelled section of a public memo entry (`MemoSection`),
  e.g. `Market & Opportunity`. Has a `body`, `bullets`, or both.
- **Category descriptor** — the anonymized stand-in for a company name in the
  public memos doc, e.g. `Inference Procurement & Orchestration Platform`.
  Never a real company name.

## Pipeline

- **Post draft** — `PostDraft`: rendered Markdown plus title, slug, excerpt, and
  taxonomy. The unit handed to the WordPress client. Distinct from a *WordPress
  draft*.
- **WordPress draft** — a real post on the site with `status=draft`. The only
  thing this project ever creates.
- **Render** — source entry → `PostDraft`. Markdown out; never blocks.
- **Blocks** — Gutenberg block markup (`<!-- wp:paragraph -->` …). Produced only
  at the WordPress boundary by `markdown_to_blocks`.
- **Ledger** — `state/posted.json`: which source entry became which post, and its
  content hash at last sync. Machine-local, not committed.
- **Ledger key** — `<source>:<slug>`, namespaced so two sources cannot collide.
- **Content hash** — `sha256:<hex>` over whitespace-normalized source content.
  Whitespace-only upstream edits must not read as a change.
- **Decision** — `SyncDecision`, the pure verdict for one source entry this run.
- **Drift** — a source entry whose content changed after its post was published.
  Reported, never auto-applied.
- **Suppression** — recording a source entry as deliberately never-to-be-posted
  (`SuppressedEntry`). Retires a pre-existing backlog without creating posts.
  Keyed by ledger key and **hash-free**: editing a suppressed entry upstream does
  not resurrect it. Reversible via `blog-engine unsuppress`.

## Actions (`SyncAction`)

- **create** — no ledger record; make a new WordPress draft.
- **update_draft** — content changed and the post is still a draft; rewrite it.
- **skip_unchanged** — hash matches; do nothing.
- **skip_suppressed** — explicitly suppressed; never draft. Reported, not silently
  omitted.
- **report_published_drift** — content changed but the post is live; report only.

## Out of scope

- The **private memo doc** — never read. See `AGENTS.md` § Sources.
- **Earnings Summary live state** — its database, account-linked inputs, private research state, and
  unreviewed artifacts are never a source. A separately produced public DCF, brief, or portfolio-weight
  derivative is eligible only after `scripts/check_public_boundary.py` passes.
- **Publishing** — a human action in WP Admin, never taken by this project.
- **Autonomous ideation** — considered and rejected.
