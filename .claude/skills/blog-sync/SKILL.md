---
name: blog-sync
description: Find entries in the Book & Podcast Notes doc or the [Public] Investing Memos doc that have no blog post yet, and create WordPress drafts for them. Use when the user says "sync the blog", "any new posts to draft", "check for new book notes", "I added a memo", "new co-investment thesis", "post my latest notes", or asks what's pending between the source docs and the site.
---

# Sync source docs to WordPress drafts

Diffs both source docs against the ledger and drafts whatever is new. Read
`AGENTS.md` first — especially § Sources, and the rule that a live post is never
rewritten. Before drafting public copy, read `../plain-writing/SKILL.md`.

## Procedure

### 1. Dry run first, always

```bash
blog-engine sync --source all --dry-run
```

This fetches, parses, renders, and prints a decision per source entry. It writes
nothing. Never skip it — the decision table is what you and he reason about.

### 2. Read the decision table

Four actions, three of which need judgment from you:

| Action | What it means | What you do |
|---|---|---|
| `create` | New entry, no post yet | Candidate to draft — apply the positioning filter below |
| `update_draft` | Entry edited, post still a draft | Safe to refresh; mention what changed |
| `skip_unchanged` | Nothing happened | Say nothing about these beyond a count |
| `skip_suppressed` | Deliberately retired | Say nothing beyond a count; don't offer to draft |
| `report_published_drift` | Entry edited *after* the post went live | **Stop.** Surface it and let him decide |

For `report_published_drift`, show the entry title and what changed, and offer the
options plainly: edit the live post by hand in WP Admin, or accept the doc as the
newer version and leave the post alone. Do not write. Do not offer to "just
update it" — the post is public and he may have edited it there deliberately.

### 3. Filter `create` candidates

Not every source entry should become a post. Check each against `AGENTS.md`
§ Positioning: does it stand on at least two of capital allocation, technology
landscape, operational execution?

Cheap prefilters that do most of the work on book entries, before you even look at
themes:

- **`[DNF]` entries: default to skipping.** He didn't finish the book. A post
  about it is a post about something he bailed on — occasionally interesting as a
  "why I put this down" note, usually not.
- **Rating ≤6: skip.** His own legend says 6-and-below means skip. Publishing a
  review of a book he tells people not to read needs a reason.
- **Rating 7: ask.** The legend is "read if the topic is particularly compelling"
  — so the question is whether the *topic* serves the positioning, not the book.
- **Rating 8+: the real candidates.**

Then apply the positioning filter to what survives. A 6/10 book with no themes
touching any of the three legs is a fine notes-doc entry and a bad post. Say so and
leave it out. Present your recommendation as a short list — "draft these three,
skip these two because…" — rather than drafting everything and letting him prune
afterward.

**The memo backlog is retired.** The 15 memo entries that existed as of 2026-07-24
are suppressed and will show as `skip_suppressed` — Bhanu decided the historical
deal memos don't belong on the blog. Don't offer to draft them. Only memos added
after that date appear as `create`. `blog-engine unsuppress <key>` reverses it if he
ever changes his mind about a specific one.

**The book backlog is live and large.** 30 book/podcast entries going back to
mid-2025 have no posts. That's a backlog to work through deliberately, not a batch
to apply — use the rating and positioning filters above and recommend a handful,
not thirty.

For a public memo entry, also verify the anonymization held: no real company
name, no founder name, no unbucketed dollar figure. If something leaked, **refuse
to draft it** and flag it as an upstream `angel-memos` bug — fixing it there
protects every future entry. Do not scrub it here.

### 4. Apply

Once he's picked:

```bash
blog-engine sync --source all --apply
```

Use `--limit N` to go incrementally on a large first run — the very first sync
will see every historical entry in both docs, which is far more than he wants to
review at once. Start with `--limit 2`, look at the output on the site, then
continue.

### 5. Report

Per created draft: the title, the WP edit link, and the category. Then a one-line
total. Flag anything you skipped and why, so the omission is visible rather than
silent.

## Scheduling

A weekly run is reasonable; it must avoid the protected **03:00–05:00
America/Los_Angeles** window (earnings-summary's pipeline). Any scheduled run is
dry-run-and-report only — it tells him what's pending, it does not create drafts
unattended.

## Never

- `--apply` before showing him the dry-run table.
- Rewrite a published post, or work around `report_published_drift`.
- Draft a public memo entry that still contains identifiers.
- Publish anything.
