---
name: plain-writing
description: Rewrite or draft Bhanu's public writing in a plain, succinct, human voice without changing its facts or confidence. Use for blog posts and pages, investing notes, project descriptions, book or podcast notes, build logs, LinkedIn copy, or whenever the user asks to make writing sound like Bhanu, less AI-written, shorter, clearer, punchier, or easier to follow.
---

# Plain Writing

Make the point fast. Keep the proof. Cut everything that exists to sound polished.

Read [references/voice-corpus.md](references/voice-corpus.md) before drafting or
rewriting public copy. Use it to calibrate judgment, not to imitate phrases.

## Non-negotiables

- Preserve every material fact, number, date, name, link, caveat, and level of
  confidence. If a claim is unclear, ask instead of filling the gap.
- Put the conclusion first. Explain it only after the reader knows the point.
- Use short sentences with one idea each. Prefer two clean sentences to one
  sentence joined by commas, dashes, or a semicolon.
- Use everyday words, contractions, active voice, and first person when the format
  allows it.
- Explain a term of art in the same sentence it first appears. Spell out an
  acronym on first use.
- Prefer a number, name, date, product action, or observed result to an adjective.
- Keep uncertainty specific. Say what could go wrong and what evidence would
  change the view.
- Never invent an anecdote, result, quote, motive, or personal reaction.
- Do not make the writing corporate, inspirational, or more certain than the
  source.

Avoid `delve`, `utilize`, `thus`, `robust`, `seamless`, `tapestry`, `ecosystem`
when it only means the product, and `landscape` when it only means the market.
Delete stock openings such as "Let's dive in," "It's worth noting that," and "In
today's world." Do not use "it's not just X, it's Y" or end a paragraph by
restating its first sentence.

## Workflow

### 1. Set the format and ceiling

Choose the closest ceiling before writing:

| Format | Default ceiling |
|---|---:|
| Homepage or bio section | 100 words |
| Project card | 180 words |
| Multi-project page | 350 words |
| Book or podcast theme | 120 words |
| LinkedIn section or post | 220 words |
| Public investing note | 450 words |
| Build log | 800 words |

A ceiling is not a target. Stop when the point is complete.

### 2. Extract the fact spine

Write down, without polishing:

1. The conclusion or reason this exists.
2. The two or three facts that earn the conclusion.
3. The specific risk, limitation, or unfinished part.
4. Any exact wording or link that must survive.

If the source does not contain enough evidence, flag the gap. Do not hide it with
adjectives.

### 3. Draft in Bhanu's order

Use this order unless the format clearly needs another:

1. Point.
2. Concrete proof.
3. Why it matters.
4. Risk, open question, or next step.

Project copy should answer: what problem annoyed me, what the tool does now, one
real design choice, and what is still private or unfinished. A company investing
note should state the bet, outcome math, evidence, and disconfirming risk. An
evergreen investing page should state the principles, link to time-stamped reports,
and name portfolio-level risks. Do not put allocations on an evergreen page if
they need manual updates.

### 4. Compress without flattening the voice

Cut in this order:

1. Throat-clearing and repeated conclusions.
2. Adjectives that do not change the claim.
3. Background the reader does not need for the next sentence.
4. Forced three-item lists and section summaries.
5. Technical detail that does not explain a decision.

Keep the aside, joke, or blunt sentence when it reveals a real opinion. Succinct
does not mean sterile.

### 5. Run the mechanical check

Run:

```powershell
python .agents/skills/plain-writing/scripts/check_plain_writing.py --format project-card path/to/draft.md
```

Use `--format` with `homepage`, `project-card`, `project-page`, `book-theme`,
`linkedin`, `investing-note`, or `build-log`. The checker catches obvious drift;
it does not certify voice. Review each warning in context, then read the result
aloud.

### 6. Report what changed

Return the revised copy and a terse note covering any fact removed, unresolved
ambiguity, or claim that still needs evidence. Do not add a style essay unless the
user asks for one.

## Final read-aloud gate

Before calling it done, ask:

- Would Bhanu say this to a smart friend over a beer?
- Can the reader find the point in the first two sentences?
- Does every paragraph earn its space with a fact, judgment, or useful question?
- Did the edit preserve the source's uncertainty and personality?
- Is there a shorter version that loses nothing important?

If any answer is no, revise once more.
