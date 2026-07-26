# Docs Outbox — Requirements (CANDIDATE)

**Status:** draft (2026-07-22) — spec CANDIDATE captured by chair
ruling; the post-lift `/spec` interview re-derives requirements
from this brainstorm input. Do not implement from this document.
**Slug:** `docs-outbox`
**Provenance:** 2026-07-22 multi-llm session close-out (feedback →
batching discussion → pipeline ideation; chair: "capture as a spec
candidate for post-lift"). Companion memory:
`project_docs_outbox_idea`.

## Problem (motivating evidence)

Small docs artifacts — lessons appends, roundtable reports and
archives, process drafts, plan files — each ship as their own
auto-merge PR. The 2026-07-22 session alone produced ~13 such PRs:
each costs a CI matrix run, a merge commit, and starter-reconcile
noise, and three lessons PRs in one evening could have been one.
Naive batching has two logged failure modes: an open armed
catch-all PR merges its first commit and strands the rest
(#942 class), and an armed label never re-classifies a PR whose
later commits change its nature (#1577 class). Batching also
delays availability: a lesson merged at 9am is recallable by a 1pm
session; a lesson parked on a branch all day is not.

## Candidate design (the four composable parts)

### C1 — Outbox, not branch

Small docs land in `~/.attune/docs-outbox/` as plain files during
the day. The git branch + PR is composed only at sweep time — no
long-lived branch, no armed-PR window, no per-session PR ceremony.

### C2 — Mechanical routing by artifact type

Lessons, roundtable reports/archives, process drafts, plan files →
ALWAYS outbox. `decisions.md` rulings, spec status flips,
starter-adjacent state → ALWAYS merge-now via the existing flow
(parallel sessions act on them same-day). No per-case judgment;
the Stop-hook lessons reminder points at the outbox.

### C3 — Pending recall layer

Hydration reads the outbox as a provenance-tagged `pending` layer
beside the merged corpus: an artifact is recallable the moment it
is written; the nightly merge provides durability and history.
Recall surfaces MUST display the pending tag (content that has not
had merge-time review). Consistent with the ratified
corpus-files → Redis-derived-serving architecture.

### C4 — Curating sweep

End-of-workday launchd job (US-5/clean-run pattern) plus an
on-demand skill: dedupe related lessons, run the memory lint, flag
core-worthy candidates, present a one-screen digest for chair
approval, then open ONE auto-merge PR. The ops Collaboration inbox
gains a "N docs pending, oldest Nd" row so outbox rot gets the
decisions-with-deadlines treatment.

## Known costs (named at ideation)

- The outbox is machine-local until swept (acceptable single-Mac;
  durability arrives at the sweep).
- The `pending` tag adds one provenance concept recall must render
  honestly.
- The sweep PR squashes N unrelated docs into one commit (history
  granularity trade, accepted for this artifact class).

## Interview questions for the `/spec` session

- Sweep cadence default (end-of-workday time? chair-triggered
  only?) and the stale-outbox warning threshold.
- Does the pending layer serve to ALL recall surfaces or only
  jit/lesson recall?
- Multi-session write discipline inside the outbox (per-file
  appends vs per-session subdirs).
- Whether the digest approval is a chip, an inbox row, or a skill
  turn.
