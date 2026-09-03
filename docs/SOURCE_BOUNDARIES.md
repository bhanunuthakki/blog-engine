# Source and backlog boundaries

## Public investing memo document

Scoping to the `Memos` container is a privacy boundary, not a parsing convenience. The public memos document has an H1 of `Private Investing` and carries three sibling H3 sections before `Memos`—`Investment Strategy`, `Portfolio Observations`, and `Diligence Process`—that are not written by the anonymizing pipeline and are not cleared for publication. Parse only content under the `Memos` H3 and stop at the next H3.

The private memo document is out of scope and must never be read by this project. `angel-memos` writes the public derivative only for `buy` and `strong_buy` decisions, replacing company and founder identity, customer identity, and exact dollar figures according to its public-output contract. Blog Engine consumes that derivative and must not add identifiers.

If a public entry still includes a real company or founder name, an unbucketed dollar figure, or other identifying detail, flag it and refuse to draft. Do not repair anonymity locally; the fix belongs in `angel-memos`, where it protects future derivatives.

## Backlog decisions

The memo backlog present on 2026-07-24 is suppressed by owner decision and recorded as never-to-be-posted. Only later public-memo entries are normally eligible. Do not offer suppressed entries as drafts; `blog-engine unsuppress <key>` is the explicit reversal path.

The book and podcast backlog is not suppressed. Its entries remain candidates subject to the rating and positioning gates in the `blog-sync` workflow.
