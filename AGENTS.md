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
- **Never rewrite a live post.** If a source entry changes after its post went
  public, report the drift and stop. `SyncAction.REPORT_PUBLISHED_DRIFT` encodes
  this; don't route around it.
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

## Voice

**Write the way Bhanu talks: plain, casual, easy to follow.** A smart friend who
doesn't work in finance or software should understand every paragraph on the first
read. That's the bar, and it applies to every post — reviews, theses, build logs,
all of it. Nerdy and specific is good. Formal is not.

These are requirements, not preferences:

- **Short sentences, one idea each.** If a sentence needs two commas and a
  semicolon, split it into two.
- **Everyday words.** Use "use" not "utilize", "buy" not "acquire", "start" not
  "commence", "about" not "regarding", "so" not "thus".
- **Explain any term of art in the same sentence you first use it** — "NRR (whether
  existing customers spend more each year)". If it can't be explained in a clause,
  cut it or rewrite around it.
- **Spell out acronyms on first use.** Every post. Assume no prior post was read.
- **Contractions.** "It's", "doesn't", "I'd". Always.
- **Active voice, first person.** "I built this because…" not "This was built to…"
- **Concrete beats abstract.** A number, a name, or a date beats an adjective every
  time. "50,000 SKUs vs 4,000" lands; "a much smaller selection" doesn't.
- **Say the point first, then explain it.** Never build up to the conclusion.
- **Cut throat-clearing.** Delete "It's worth noting that", "In today's world",
  "At the end of the day", "Let's dive in".

**Tics that read as machine-written — avoid entirely:** delve, leverage (as a
verb), robust, seamless, landscape, ecosystem, tapestry, "it's not just X, it's Y",
"in an era of", "a testament to", three-item lists where two would do, and
paragraphs that end by restating their own opening sentence.

A good test: read it aloud. If it sounds like something he'd actually say to a
friend over a beer, it's right. If it sounds like a LinkedIn post or a consulting
deck, rewrite it.

**Do:** ask clarifying questions about fuzzy ideas; offer concrete specific
suggestions; find the intersection of "interesting to me" and "valuable signal to
others"; connect ideas back to the positioning; challenge assumptions productively.

**Don't:** make it polished or corporate; push conventional portfolio-site
structure; suggest generic thought-leadership moves; lose his personality in the
professionalism; write listicles or engagement bait.

### Stance differs by post type; plainness never does

The register below changes *how he stands* relative to the subject. It does **not**
license denser vocabulary — a thesis post still has to pass the friend-at-a-bar
test.

| | Book/podcast review | Build log | Co-investment thesis |
|---|---|---|---|
| Stance | First person. What changed in his head. | First person. What he built and why. | Mostly about the company, not him. |
| Shape | Themes as claims, each with a concrete anecdote carrying dates, names, numbers. | One real design decision, the problem behind it, what he'd do differently. | Sections anchored to comparables and unit economics. |
| Uncertainty | Welcome and interesting — DNFs and honest ratings are the point. | Say what's broken or unfinished. | Name the specific risk, don't hedge vaguely. |
| Anchor | 8+ recommend, 7 conditional, ≤6 skip. Never inflate. | Working code someone could go read. | Entry price tied to outcome math. |

The `angel-memos` public style guide at
`..\angel-memos\src\angel_memos\prompts\public_doc_style.md` governs thesis
*structure* and lists phrasings to avoid. Follow its structure — but it was written
for a co-investor audience, so **translate its finance vocabulary into plain
English for the blog.** LCOE becomes "the all-in cost per unit of energy over the
project's life", and so on.

## Sources, and the privacy line

| Source | Doc | Becomes |
|---|---|---|
| Book & Podcast Notes (Master) | `1Ec-rllS_JbpuunvgSpjfXDhpREHi1iuHyYyGb6CRAR4` | one post per entry, category `books` |
| [Public] Investing Memos | `1nyFj17M4kktlHD028AVF9D-8zeyGRGKC-MXzHNfXA80` | one post per entry, category `investing` |

**Scoping to the `Memos` container is a privacy boundary, not a parsing
convenience.** The public memos doc has an H1 of `Private Investing` and carries
three sibling H3 sections before `Memos` — `Investment Strategy`, `Portfolio
Observations`, `Diligence Process` — which are *not* written by the anonymizing
pipeline and are not cleared for publication. Parse only what sits under the
`Memos` H3, and stop at the next H3.

**The private memo doc is out of scope and must never be read by this project.**
Anonymization is guaranteed upstream: `angel-memos` writes the public doc only
for `buy`/`strong_buy` decisions, with company names replaced by category
descriptors, founders reduced to titles, customers to tier descriptors, and
dollar figures to bucketed ranges. This repo reads the already-anonymized
derivative and adds no identifiers of its own.

If a public-doc entry still contains something identifying — a real company name,
a founder's name, an unbucketed dollar figure — that is an upstream bug. Flag it
and refuse to draft. Do not silently anonymize it here; the fix belongs in
`angel-memos` where it protects every future entry.

**The memo backlog is retired by decision (2026-07-24).** The 15 memo entries that
existed in the public doc as of that date are *suppressed* — recorded as
never-to-be-posted — because Bhanu doesn't want the historical deal memos on the
blog. Only memos added **after** that date become posts. Don't offer to draft the
retired ones; if he ever wants one, `blog-engine unsuppress <key>` reverses it.

The book/podcast backlog is **not** suppressed — those remain available to work
through, filtered by rating and positioning per the `blog-sync` procedure.

Earnings-summary briefs are **deliberately out of scope for now.** Linking
anonymized public-market micro-theses needs its own anonymization pass (position
sizes, cost basis) and will be spec'd separately.

## Architecture

Markdown is the single interchange format. Sources parse to typed entries →
render to Markdown → convert to Gutenberg blocks only at the WordPress boundary.

```
Google Doc → DocParagraph[] → BookNotesEntry / PublicMemoEntry
                                        ↓  render.py
                                   PostDraft (markdown)
                                        ↓  sync.decide  (pure)
                                   SyncDecision[]
                                        ↓  sync.execute
                            markdown_to_blocks → WordPress draft
                                        ↓
                                 state/posted.json
```

`models.py` is the contract; `sync.decide` is pure so the safety rules are
unit-testable without network. The ledger keys on a **slug that never encodes
mutable metadata** (no rating, no date) — identity must survive an edit.

## Video posts

The primary evidence for "I build things" is a screencast, not a repo link
(decided 2026-07-24) — half demo, half him talking about why the tool exists. Format,
hosting, and the mandatory redaction checklist live in `ROADMAP.md` § Making the
videos.

The rule that matters here: **a screen recording discloses far more than a
screenshot, and a published video can't be edited.** Before any recording is
uploaded, the dollar amounts, holdings list, terminal output, browser chrome, and
notifications all have to be cleared. If asked to help prepare or publish a video
post, walk that checklist explicitly rather than assuming it was done — the failure
is irreversible and public.

Embed by putting the video URL alone on its own line; `markdown_to_blocks` converts
a bare **YouTube or Vimeo** URL into a real embed block. Those are the two providers
this site actually resolves — verified against its oEmbed proxy on 2026-07-24. Loom
is deliberately not supported: it isn't a WordPress core oEmbed provider, so an embed
block would render as a bare link. Loom is fine for *recording*; host the result on
YouTube.

Always pair an embed with a couple of paragraphs of text — a video-only page doesn't
get indexed and excludes everyone who won't watch.

**The Artifacts page is a project index, not a prompt or skill directory.** Feature
tools Bhanu actually uses. Do not restore Gem listings, grades, or other labels that
need manual upkeep. Keep the source copy in `drafts/artifacts-page.md`; add a demo
link only after the video has passed the redaction checklist above.

## Procedures

The work here breaks into four repeatable procedures. Canonical procedures live
at the paths below. Codex discovers repo-local skills under `.agents/skills` and
can invoke them with `$<name>`. Claude Code uses the matching compatibility entry
under `.claude/skills` when one exists. Gemini and other runtimes read the
canonical file completely before acting.

| Procedure | Purpose | Path |
|---|---|---|
| `plain-writing` | Compress public copy without losing facts or Bhanu's voice | `.agents/skills/plain-writing/SKILL.md` |
| `book-review` | Develop attribution-checked book/podcast notes, then place them after approval | `.agents/skills/book-review/SKILL.md` |
| `blog-sync` | Find source-doc entries with no post yet and draft them | `.claude/skills/blog-sync/SKILL.md` |
| `wp-post` | Direct WordPress read/write for one-off post work | `.claude/skills/wp-post/SKILL.md` |
| `post-idea` | Develop a post angle from a topic or the existing backlog | `.claude/skills/post-idea/SKILL.md` |

## Working here

- The site runs Gutenberg block markup, not classic HTML. Never post raw HTML.
- Credentials come from `C:\Users\bhanu\.gemini\.secrets\wordpress.env` and are
  never echoed, logged, or committed. The app password is a `SecretStr`.
- Google Docs auth reuses the `angel-memos` OAuth client (same `documents`
  scope), so there is no second authorization to perform.
- `blog-engine sync` defaults to `--dry-run`. Read the decision table before
  `--apply`.
- Any cron must avoid the protected **03:00–05:00 America/Los_Angeles** window
  reserved for the earnings-summary pipeline.
