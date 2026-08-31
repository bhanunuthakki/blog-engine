---
name: book-review
description: Turn a finished book, nonfiction audiobook, or podcast episode into Bhanu's ultra-terse Book & Podcast Notes entry, using his reactions plus model recall and web research to surface missed themes and verify that each concrete example is actually attributed to the work. Use when the user says "book review", "podcast notes", "I finished/read/listened to X", "log this book", "add X to my notes", provides reading highlights or dictated reactions, or explicitly invokes `$book-review`. Draft for approval before appending to the master Google Doc or creating a WordPress draft.
---

# Generate a book or podcast review

Turn Bhanu's reactions into high-impact notes to self. Act as a thought partner:
surface themes he may have missed, but never let model recall masquerade as
evidence.

Read the root `AGENTS.md` Voice and book/podcast-review rules before drafting.
Then read `../plain-writing/SKILL.md` and apply its compression workflow.
Plainness, honest ratings, and the drafts-only boundary are binding.

## Output contract

Use this exact shape:

```markdown
### <Title> (<Month Year> - <N>/10>)

#### Theme 1: <Punchy claim>
<One or two ultra-terse sentences explaining the fundamental learning.>
  - **<Argument title>**: <One sentence maximum summarizing the concept.>
      - *Example*: <Concrete evidence with exact names, dates, numbers, or a strict anecdote.>
  - **<Argument title>**: <One sentence maximum.>
      - *Example*: <Concrete evidence.>

#### Theme 2: <Punchy claim>
...
```

- Use **2-4 themes**. Three or four is normal; use two when the work truly centers
  on two ideas. Never pad the count.
- Give each theme **2-4 argument/example pairs**.
- Make themes claims, not topics. "Action Beats Belief" works; "Leadership"
  does not.
- Treat themes Bhanu suggests as anchors, then validate, refine, merge, or reject
  them based on his reactions and the evidence. Do not preserve a weak theme just
  because it arrived in the prompt.
- Put the point first. Use short sentences and everyday words. Delete filler.
- Spell out acronyms and explain terms of art on first use.
- Keep the rating honest: 8+ recommend, 7 conditional, 6 or below skip. Use
  `WIP` or `DNF` instead of a rating when appropriate.

## Evidence standard

Measure **attribution fidelity**: whether the book or episode actually uses the
example. Do not independently fact-check whether the author's underlying anecdote
or claim is true unless Bhanu asks.

Attempt web verification for **every example**, including examples Bhanu supplies.
Use model recall for discovery only. It may propose missing themes, arguments, and
examples, but treat every recalled detail as unverified until it clears one of
these gates:

1. **Source-verified:** a source shows that the book or episode contains or
   discusses the example. Prefer an accessible book excerpt or preview, an
   official transcript, publisher or author material, or an author interview
   explicitly attributing the example to the work.
2. **User-confirmed after search:** no qualifying public source was found, that
   limitation was disclosed, and Bhanu explicitly confirms the example from the
   work or his highlights. Merely appearing in his initial notes does not skip the
   web-verification attempt.

A page proving that an event happened does not prove that the book cited it. A
generic summary may help discover a theme, but it cannot verify a specific
example unless it clearly attributes that example to the book or episode. Never
use a search-result snippet as evidence.

For each candidate example:

- Search distinctive names, dates, numbers, or phrases together with the title
  and author or episode name.
- Prefer an excerpt, preview, transcript, publisher page, or author material that
  exposes the attribution directly. Broaden to secondary sources only when they
  explicitly say the work uses the example.
- Link the page that supports the attribution.
- Record a page, chapter, or timestamp only when the source exposes it. Never
  guess one.
- Check that the source supports the exact claim, not merely a nearby fact.
- Prefer one direct or near-primary source over several pages repeating the same
  unsupported claim.
- Use the narrowest wording the source supports. Do not join partial details from
  different pages or add names, dates, or numbers that the attribution source
  does not support.

If no qualifying source is available, show the item as an **unverified
candidate** during review and disclose that the search failed. Ask Bhanu to
confirm it from the work or a highlight. Exclude it from the approved notes if he
does not explicitly confirm it. Apply this rule especially strictly to examples
surfaced by model recall. If web search is unavailable, say so; do not quietly
fall back to recall.

Keep citations out of the terse entry unless Bhanu asks for them there. Put them
in a separate evidence appendix during review, with one row per example:
`Example | origin | status | source or search result | what it verifies`. Use
only `source-verified`, `user-confirmed-after-search`, or `excluded` as statuses.

## Workflow

### 1. Gather once

Accept a title alone, highlights, scattered bullets, dictated reactions, or a
voice transcript. Ask only what cannot be inferred, in one batched round:

- Rating out of 10, `WIP`, or `DNF`?
- Book, audiobook, or podcast? Which author or episode?
- Which ideas stuck, and what changed his mind?
- Which examples does he remember well enough to confirm?

Offer an initial read of the likely themes instead of asking him to generate them
from scratch.

### 2. Discover and verify

Build a candidate set from three lanes:

- Bhanu's reactions and highlights.
- Model recall, clearly marked as candidate material.
- Web research for missed themes and direct attribution of examples.

Search broadly enough to catch themes he may have missed. Then run every candidate
example, including Bhanu's, through the attribution gate above. Distinguish
disagreement with his reading from uncertainty about attribution; surface either
rather than smoothing it away.

### 3. Draft and self-correct

Order themes by how much they mattered to Bhanu, not by chapter order. Before
showing the draft:

- Delete generic claims and throat-clearing.
- Delete vague attribution such as "studies show" or "the author believes"
  unless the sentence names the specific study, person, event, or evidence.
- Replace vague examples with exact ones or remove the argument.
- Confirm every argument has an immediate example.
- Confirm every example received a web-attribution attempt.
- Confirm every example is `source-verified` or
  `user-confirmed-after-search`; exclude everything else.
- Remove repeated themes and any point that does not earn its space.
- Read it aloud mentally; rewrite anything that sounds corporate or machine-made.

Check the positioning filter in `AGENTS.md`. A review may belong in the notes doc
without becoming a blog post; say so plainly.

### 4. Review before writing

Show, in this order:

1. The terse draft.
2. A short list of themes or examples added through recall/web research.
3. The evidence appendix.
4. The positioning recommendation.

Use an editable drafting surface when the runtime provides one; otherwise show
clean Markdown in chat. Iterate until Bhanu approves. Do not append to Google Docs
or create a WordPress draft before explicit approval.

### 5. Place after approval

Append the approved entry to the top of `Book & Podcast Notes (Master)`, document
  the document ID from `BLOG_ENGINE_BOOK_NOTES_DOC_ID`, using
`blog_engine.google_docs.append_under_heading`. It is revision-guarded and refuses
duplicate headings.

Then create a WordPress **draft** through `blog_engine.render` and
`blog_engine.wordpress`, and record it in the ledger so `blog-sync` cannot draft
the same entry again. Prefer the shared path:

```bash
blog-engine sync --source book --apply --limit 1
```

Report the WordPress edit link, rating, theme count, and whether the review clears
the positioning bar.

## Never

- Publish or rewrite a live post.
- Invent or silently repair an anecdote, quotation, date, number, page, or
  timestamp.
- Treat model recall, a search snippet, the initial notes alone, or repeated
  unsourced web claims as proof that the work contains an example.
- Inflate a rating or make a lukewarm review sound enthusiastic.
- Proceed to an external write before Bhanu approves the exact draft.
