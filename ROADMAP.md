# Blog roadmap

Sequenced plan, drawn up 2026-07-24. The raw idea list with prior critique lives in
[.claude/skills/post-idea/backlog.md](.claude/skills/post-idea/backlog.md) — this
file is the order to do things in and why.

Budget assumption: **1–2 hours a week, most weeks zero.** Every estimate below is
honest, not optimistic. If a phase slips a month, nothing breaks.

## Current next steps — 2026-08-09

1. **Record the first two demos.** Start with Portfolio Tracker and Earnings
   Summary. Use the redaction checklist below, upload to YouTube, then add each URL
   to `drafts/artifacts-page.md` and the live Artifacts page.
2. **Build the public portfolio report in Earnings Summary.** The monthly output
   should show holdings, performance, and thesis changes. The quarterly output
   should add a deeper review of what worked, what did not, and which risks remain.
   It needs a stable public URL before the Investing page can link to it.
3. **Condense future public investing memos upstream.** The public derivative
   remains the right source, but each new entry should carry the decision, two or
   three facts, outcome math, and the main risk. Historical entries stay
   suppressed.
4. **Use `$plain-writing` on the remaining public copy.** Work page by page when a
   post is already being touched; do not create a rewrite project for its own sake.
5. **Fix the site-wide mobile overflow.** The updated page bodies fit at 390 px,
   but the theme's full-width header still creates a small horizontal scrollbar.

## The two goals, and which work serves which

| Goal | What actually moves it |
|---|---|
| **Don't read as a finance-only guy** | Working code someone can go look at, and write-ups of systems actually built |
| **Learning in public / meet interesting people** | Consistent honest writing, and somewhere for it to travel |

Book reviews serve the second goal well and the first one barely. Build logs serve
both. That's why the build logs are ahead of the individual reviews here, even
though the reviews are the easier writing.

---

## Phase 0 — Make the builder evidence visible (~2–3h, do first)

Nothing else lands properly until this exists. Someone who reads a good build log
with nowhere to go next is a wasted post.

**The evidence is video, not repo links** (decided 2026-07-24). A 3–5 minute
screencast — half demo, half him talking about why the tool exists — proves the
thing works in a way a repository link never does. A reader has to be a programmer,
and curious, to get anything from a repo. Anyone can watch a tool run.

It also resolves two problems at once: `portfolio-tracker` is private, and
`earnings-summary` publicly exposes its coverage universe. On video he controls the
frame, so neither constrains what he can show.

- Start with one screencast each for Portfolio Tracker and Earnings Summary,
  embedded on the Artifacts page. Add demos for Angel Memos and Blog Engine when
  they show a useful decision. See *Making the videos* below — the redaction
  checklist there is not optional.
- Add a one-line description to `earnings-summary` (portfolio-tracker has one).
- **Done 2026-08-09:** the Artifacts page now leads with Portfolio Tracker,
  Earnings Summary, Angel Memos, and Blog Engine. Gems and grades are gone. Source
  copy lives in `drafts/artifacts-page.md`; videos remain.
- Add GitHub to the Contact page and the footer. Still worth doing — it's
  corroboration for the minority who go looking, just no longer the main exhibit.

Current page copy lives in [drafts/artifacts-page.md](drafts/artifacts-page.md).
The older supporting notes remain in
[drafts/phase-0-copy.md](drafts/phase-0-copy.md), but their Artifacts copy is
superseded.

---

## Phase 1 — "My favorite reads of 2026 so far" (~1–1.5h)

The easiest real post, and there's precedent: *2021: What I've Enjoyed & Learned*
(Jan 2022) is the same format under the `recommendations` category.

Fourteen entries were logged January–June 2026. The eight rated 8 or higher:

| Read | Rating |
|---|---|
| Greenlights | 9/10 |
| Benjamin Franklin: An American Life | 8/10 |
| Billion Dollar Whale | 8/10 |
| The Changing World Order | 8/10 |
| The New Map | 8/10 |
| My Life in Full | 8/10 |
| Acquired — Trader Joe's | 8/10 |
| Acquired — Indian Premier League | 8/10 |

The other six from the same window, worth a passing mention for honesty: *Range*,
*Path Between The Seas*, *God Save Texas*, *Runnin' Down a Dream* and *Born
Standing Up* all at 7/10, plus *How Infrastructure Really Works* — picked up, rated
7, and not finished.

Shape: a short intro on how and why the notes get taken at all (the dictate-then-
structure process is genuinely interesting to people), then one short paragraph per
read — the single thing that stuck, not a summary. Include the 7s and the DNF at
the end; being honest about what got put down is the most distinctive part of the
whole system and costs nothing.

**One post covering eight reads is the right call**, not eight posts. It paces
naturally (twice a year), it shows range in a single page, and it doesn't flood a
blog that's published eleven posts in six years.

> **Interaction with the tool:** after this goes live, suppress the entries it
> covers so `blog-sync` doesn't later offer the same eight as individual posts:
> `blog-engine suppress --source book --reason "Covered in the H1 2026 roundup."`
> Careful — that suppresses *all* current book entries, which is probably what you
> want here, since it also retires the 2025 backlog. Going forward, only standouts
> get their own post.

---

## Phase 2 — angel-memos build log (~2–3h + video)

The strongest builder story available, because the system does something people
haven't seen.

Working angle: **"I built a tool that argues against my own investments."**

Lead with the screencast, then the writing. Recording this one needs care — the
demo runs on real deals, so use a company already written up in the public doc, or
scrub the identifiers on screen. See *Making the videos*.

That's the hook and it's true. The substance underneath:

- Why bother — it's easy to talk yourself into a deal you already like, so the
  tool writes the bear case whether or not you want it.
- The bit worth explaining to a technical reader: **the two-document split.** A
  private memo keeps every name and number; a public one is generated from it with
  company names replaced by category descriptions, founders reduced to job titles,
  and dollar figures bucketed into ranges. Same analysis, safe to share. Only deals
  actually invested in ever reach the public version.
- One thing that didn't work, or that would be done differently.

Serves capital allocation *and* operational execution. Keep it plain — no reader
should need to know what a SAFE or a post-money cap is to follow it.

---

## Phase 3 — earnings-summary build log (~2–3h + video)

Working angle: **"I look at 28 companies every morning without opening a
spreadsheet."** Lead with the outcome, then explain how.

The easiest video of the three: the morning brief already exists as a rendered
report, so the demo is just walking through one. Decide first whether the coverage
list is on screen.

Two candidate directions — pick one, don't do both in one post:

1. **The anti-spreadsheet argument.** Why a spreadsheet is the wrong tool for
   something you re-run every day: no types, no tests, no version history, and one
   fat-fingered cell silently corrupts a number you then act on.
2. **How every AI call is governed.** Each call goes through one entry point, picks
   a model based on the job, gets its output checked against a schema, and logs
   what it cost and how long it took. Almost nobody does this, and it's the
   strongest "I actually build production systems" signal in the whole portfolio.

Direction 2 is rarer and better builder signal. Direction 1 is more relatable and
sets up Phase 4. Either works — 2 if picking on signal, 1 if picking on reach.

---

## Phase 4 — AI in corporate finance (~8–12h, the big one)

The single most valuable post available, and the only one that can't be shortcut.
It needs real expertise, not tooling.

Angle: **"the only thing AI is actually replacing in corporate finance is the
spreadsheet."** The asset is a task taxonomy — break strategic finance into ~30
concrete tasks and mark each one as automatable today, AI-assisted, or still
firmly human. Ship the table as something downloadable.

Rare combination backing it: Plaid, Meta, Houlihan, *and* a working codebase. Very
few people can write this. Budget several sessions; don't start it in a week
without time.

---

## After that

Nothing is committed beyond Phase 4. Options, in rough order of appeal:

- **Individual book reviews**, sparingly — a 9/10 that genuinely changed something.
  One a month at most.
- **The H2 2026 roundup** in January, making it a twice-yearly habit.
- **Methane** or **thermal batteries** from the backlog — both well developed.
- **A build log for blog-engine itself** — the system that publishes the blog is a
  reasonably funny thing to publish on the blog.

## Making the videos

### Where to host: YouTube, public, embedded

Not the WordPress media library. Bluehost is shared hosting with an upload cap
(usually somewhere between 2 MB and 64 MB) and no transcoding, so a self-hosted
video buffers badly and dies on mobile.

YouTube is free, transcodes to every resolution, adapts to the viewer's connection,
embeds natively in Gutenberg, and — unlike every other option — is itself a
distribution channel. Distribution is the gap this whole roadmap otherwise ignores,
so getting it for free matters. Public, not unlisted: unlisted reaches only people
already on the blog, which defeats the point.

Alternatives, if YouTube association is unwanted: **Vimeo** (~$12–20/mo) has a
cleaner player, no end-screen recommendations, and can restrict embedding to your
own domain. **Cloudflare Stream** (~$5 per 1,000 minutes stored) gives full control
and zero branding but needs setup.

**Capture and hosting are separate decisions.** Record with whatever is easiest —
Loom is purpose-built for screen-plus-webcam-bubble and is the fastest path to a
first video, Windows Game Bar (`Win`+`Alt`+`R`) is free and already installed but
has no webcam overlay, OBS if more control is wanted. Then download and upload to
YouTube. Don't let Loom's free tier (25 videos, 5 minutes each) be the host — it
caps length and reads as a work tool.

### Format

Three to five minutes. Not fifteen — blog visitors won't watch fifteen.

- **On camera, ~20 seconds:** what this is and why it exists.
- **Screen, the bulk of it:** the thing running on real data. Zoom in. Text has to
  be readable on a phone, so a full 1080p desktop with a normal terminal font is
  already too small.
- **One design decision**, explained plainly — the same thing the written build log
  would cover.
- **Say what's still broken.** This is the most credible thing in the video and it
  costs nothing.
- **On camera, ~15 seconds** to close.

Don't script it tightly. The appeal is that it's real, and over-rehearsing removes
the only advantage this format has over a polished demo.

**Still write 2–3 paragraphs around the embed.** A page that's only a video doesn't
get indexed, and plenty of people won't watch but will read.

### Redaction checklist — do this before every upload

A screen recording leaks far more than a screenshot, and **YouTube cannot edit a
published video's content.** A mistake means deleting and re-uploading, which breaks
the URL and every embed pointing at it. So this happens before, not after.

- **Dollar amounts and position sizes.** Use a percentage-only view, or scale the
  underlying numbers. Real balances are the single most sensitive thing on screen.
- **The holdings list.** Decide deliberately whether the coverage universe is being
  shown — that's the same decision as the public `micro_thesis/holdings/` directory.
- **Terminal output.** API keys, tokens, `.env` contents, and full paths containing
  the username. Scroll back before recording, not just during.
- **Browser chrome.** Other tabs, the bookmarks bar, and the account email in the
  corner. Use a clean profile.
- **Notifications.** Turn on Focus Assist / Do Not Disturb. A Slack preview
  appearing mid-demo is the classic way this goes wrong.
- **Watch the whole thing full-screen before uploading.** Every frame.

## Two things this roadmap does not solve

**Distribution.** Every post above lands on a site with no newsletter, no RSS
promotion, and no cross-posting. Publishing is now easy; being read is not. Worth
deciding — even just consistently cross-posting to LinkedIn would be a start.

**Feedback.** There's no analytics, so there's no way to know which of these
actually worked. Something light (Plausible, Fathom) would answer that; Google
Analytics would be a brand cost on a site like this.
