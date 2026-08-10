# Standing post backlog

Carried over from the *Blog Next Steps* strategy session (2026-05-17). Each idea
already went through one round of critique — the **sharpened** line is the version
worth writing, not the original framing. Don't re-litigate these from scratch.

Priorities are his, from the original backlog screenshot.

---

## P0 — AI in corporate finance

**Sharpened:** *"AI in corp finance — the only thing it's actually replacing is
the spreadsheet."* Three parts: (1) a task taxonomy decomposing strat finance into
~30 atomic tasks, marked LLM-tractable today / LLM-augmented / not tractable;
(2) why spreadsheets are the wrong substrate for AI (cell-level state, no types,
no tests, no versioning); (3) the harness — `earnings-summary` as the worked
counter-example.

**Why it's the strongest idea he has:** hard credentials (Plaid, Meta, Houlihan)
*and* a real AI-in-finance codebase. Stands on all three positioning legs.
Don't write it as a survey — the task taxonomy is the asset, and it's downloadable.

## P0 — Monthly build log

**Sharpened:** three sections — three things read that changed a number in his
head; one thing shipped or broken; one question he's chewing on. Monthly, not
weekly (weekly dies in 90 days). Doubles as a forcing function: can't publish
without having built, read, and thought.

**Caveat:** this is the idea most at risk of becoming the burden the whole
1–2 hr/week constraint exists to prevent. Quarterly is an acceptable retreat.

## P1 — Methane

**Sharpened:** *"Methane is the highest-ROI ton of carbon — here's why no one's
funding it."* Frame as a capital allocator: $/ton avoided × time-to-deployment ×
scalability ceiling. Walk Mill, Kairos, IRA §45V, the landfill data. End with a
concrete "what would you fund" section, forwardable to climate VCs.
Primary source: Nat's deck.

## P1 — Thermal batteries

**Sharpened:** *"Industrial heat is a bigger TAM than electricity — and thermal
batteries are the only thing pricing it."* Build the Sankey of industrial energy
use, stratified by temperature *and* delivery form (steam / electric / direct
heat), then map each band to incumbent vs. challenger tech.
**Upgraded from P2** — the Sankey alone is shareable, and most people don't grok
why the temperature stratification is what matters.

## P1 — Unit economics of policy

**Sharpened:** three separate posts, never one "manifesto" — the word is a
brand-killer and three unrelated policy areas in one post means none land.
*"The unit economics of US healthcare — why the math forces a cartel"*;
*"…of higher ed — what tuition actually buys"*; *"…of urban transit — why farebox
recovery is a trap."* Each is model-able and plays to the finance brand.

## P2 — Plastics

**Sharpened:** *"I was wrong about plastics — the relative impact is smaller than
I thought, but the substitution story is harder."* Lead with the recalibration
(Nat's slides 146 & 192), then a substitution-feasibility ladder by use case
(packaging → fiber → durable goods → medical).
**Lowest-effort idea in the queue** — the hook already exists.

---

## Added during the session

- **"What portfolio-tracker taught me about benchmarking"** — Modified Dietz vs.
  TWR vs. IRR, and when each is wrong. Pulls triple duty: the build, the investing
  process, the strat-finance corpus.
- **"Building earnings-summary as a forcing function for thesis discipline"** —
  why the three-layer architecture exists, with Ousterhout's deep-modules framing.
  Cross-posts well to Hacker News.

## Recurring formats considered

`Wrong About` (quarterly) · annual letter (Dec 31) · `From the desk` (monthly
snapshot) · per-holding micro-thesis updates. The last one is the largest unforced
error available: those summaries are **already generated** by `earnings-summary`,
so publishing them is near-zero marginal effort — but it needs the anonymization
pass that's currently out of scope. See `AGENTS.md` § Sources.

## Explicitly rejected

Hubs, a reading-capture tool, the audio pilot, and an autonomous scout/ideator
agent fleet. All were explored in depth and cut as content marketing dressed up as
building. The conclusion that survived: **the builds are the work; the blog is a
label on the box.** What flips the "not just a finance guy" perception is a repo
someone clones, a screencast of the thing working, or a specific technical
decision explained in three lines — not more essays.

Don't resurrect these without him raising them first.
