# Phase 0 — supporting copy and history

The Artifacts page was rewritten on 2026-08-09. Its current source is
[`artifacts-page.md`](artifacts-page.md). What remains is the screencasts, the
GitHub profile copy, and the contact/footer links below.

**The videos are the actual work here.** Copy takes ten minutes to paste. A 3–5
minute screencast of each tool running is what makes the builder claim land. Format
and hosting guidance, plus the redaction checklist, is in
[ROADMAP.md](../ROADMAP.md) under *Making the videos* — read the checklist before
recording, because YouTube can't edit a video after it's published.

---

## Two notes before you paste

**`portfolio-tracker` is private.** Only `earnings-summary` and a fork are public.
That no longer blocks anything now the evidence is video — you don't need a public
repo to show a tool working — so I've left it unlinked below. If you do make it
public, wrap the name in
`[portfolio-tracker](https://github.com/bhanunuthakki/portfolio-tracker)`.

**`earnings-summary` publishes your coverage universe.** `micro_thesis/holdings/`
has 100 committed JSON files, one per ticker, readable by anyone today. Credentials
are clean — only `.env.example` is committed, the portfolio database is gitignored,
and `transcripts/`, `ir_documents/`, `data/bear_case/` and `output/` aren't in the
repo at all. So it isn't a leak, but it is a disclosure worth making on purpose.
Since GitHub is no longer the centerpiece, nothing here amplifies it. The same
decision comes back the moment you point a camera at that tool.

---

## 1. GitHub profile README

Still worth having — it's corroboration for the minority who go looking. Create a
repo named exactly **`bhanunuthakki`** (matching the username, which is what makes
GitHub show its README on your profile), add `README.md`:

```markdown
Hi, I'm Bhanu.

I work in strategic finance — currently at Meta, previously Plaid and Houlihan
Lokey. Mostly I build tools for the investing and analysis work I'd otherwise be
doing in a spreadsheet.

Two I use every day:

**[earnings-summary](https://github.com/bhanunuthakki/earnings-summary)** — pulls
filings, earnings call transcripts and investor-relations documents for the ~28
companies I follow, and turns them into a brief each morning. Every AI call in it
gets routed to a chosen model, checked against a schema, and logged with what it
cost and how long it took.

**portfolio-tracker** — pulls my actual brokerage data and works out returns
properly, matched to when money actually went in and out, benchmarked against the
S&P 500.

I write at [bhanunuthakki.com](https://www.bhanunuthakki.com) about capital
allocation, climate, and what it takes to build things.
```

The earnings-summary URL is verified. Then **pin `earnings-summary`** — a pinned
private repo is visible only to you, so portfolio-tracker only becomes worth pinning
if you open it.

## 2. Repo description

`portfolio-tracker` already has one. Add to **earnings-summary**:

> Morning research briefs for the companies I track — filings, transcripts and IR
> documents run through a governed multi-model AI pipeline.

## 3. Artifacts page — superseded

The Gems table and grades were removed on 2026-08-09. Do not paste the old copy
below back into WordPress. It is retained only as a record of the earlier plan.

### portfolio-tracker

*[embed the screencast here]*

> **What it does:** Connects to my brokerage accounts and calculates what my
> portfolio has actually returned, then compares it to just having bought the index.
>
> **Why I built it:** Every tool I tried either showed a return number without
> saying how it was calculated, or quietly got it wrong when I added money mid-year.
> If you put cash in right before a rally, a naive calculation flatters you. Mine
> matches returns to when money actually moved, so the number means something.
>
> **Stack:** FastAPI, React, SQLite, Plaid, SnapTrade
>
> **Grade:** A

### earnings-summary

*[embed the screencast here]*

> **What it does:** Every morning it pulls new filings, earnings call transcripts
> and investor documents for the ~28 companies I follow, and writes me a brief on
> what changed.
>
> **Why I built it:** I kept finding out about things weeks late, and re-reading the
> same 80-page filings to answer the same handful of questions. The interesting part
> isn't the summarizing — it's that every AI call is governed. Each one goes through
> a single entry point, picks a model based on the job, gets its output checked
> against a fixed schema, and logs what it cost.
>
> **Stack:** Python, SQLite, multi-model AI routing, FMP
>
> **Grade:** A

Keep the Grade column — it's the most distinctive thing on that page and it reads as
senior. Grade honestly; an A on everything means nothing.

To embed, paste the YouTube URL on its own line in the block editor and it becomes a
player automatically. `blog-engine`'s Markdown converter now does the same thing, so
a bare video URL on its own line in any generated post becomes a proper embed.

## 4. Contact page and footer

Add GitHub. Right now someone can read the whole site with no way to check that any
of the building is real:

> **GitHub:** [github.com/bhanunuthakki](https://github.com/bhanunuthakki)

Worth adding an RSS link at the same time — it's free and lets people follow before
a newsletter exists. Once there's a video or two, a link to the YouTube channel
belongs here too.
