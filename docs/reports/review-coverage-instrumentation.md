# Review Coverage Is Unmeasured — and It Catches What Tests Cannot

**Date:** 2026-07-31
**Author:** Claude (lead), for chair review
**Status:** report — not a spec, no implementation authority
**Provenance:** the outcome-first-fix arc (#1805–#1816), six
cross-review lanes, one scoped re-review

---

## The claim

We measure test coverage to two decimal places, ratchet it, and
gate merges on it. We measure **review coverage** not at all —
despite evidence that a second model finds a class of defect our
test machinery structurally cannot.

## The evidence, from one arc

Six codex lanes ran across the outcome-first-fix work. They
produced **21 findings, 20 of which I judged real** after checking
each against the code. Nearly every one was a *truthfulness*
defect: a claim the artifact didn't support.

The decisive data point came at close-out. The final lane's brief
hit the 60k-char cap and went **7 files sent / 14 omitted** —
silently dropping `fix_workflow.py`, the primary module it was
reviewing. Re-running it scoped to production source only (**9
sent / 0 omitted**) found **four more real defects, three of them
HIGH**:

- `exit_code()` returned SUCCESS when git was unavailable — but
  without git, out-of-scope edits are *undetectable*, so the empty
  violation list meant "we couldn't look," not "nothing was
  wrong."
- Scope violations used exact-path matching while the workflow's
  own guard allowed a scope directory's descendants — legitimate
  edits would have been flagged as violations.
- A workflow crash exited 2 with no receipt, leaving partial edits
  unattributed.

**At the moment those three HIGH defects existed, the modules
containing them were at 100% test coverage**, with 2,146 tests
green including all five Windows lanes.

That is the whole argument. Coverage said complete. The code was
lying about its own success condition.

## Why tests can't catch this class

Test coverage answers *"did a test execute this line?"* It cannot
answer *"does this line claim more than it verified?"* Every defect
above is semantic: a success verdict emitted without the check that
would justify it. A test asserting `exit_code() == 0` under those
conditions would have *passed* — and would itself have been wrong.

This is the same family as the vacuous-verifier bug caught earlier
in the arc: a dry-trace assertion carrying an unconditional escape,
so two pins could never fail. Fully covered. Entirely useless.

## What review coverage would measure

Per file, per risk class, over a time window:

1. **Reviewed at all** — has any lane's `manifest.sent` included it?
2. **Reviewed at current content** — or only at an older revision?
3. **Never-reviewed set** — `omitted ∪ everything committed since
   the last lane`. Tonight this was materially larger than any
   `omitted` list, because an entire follow-up PR and a seven-guard
   registration commit landed *after* the last lane ran and
   appeared in no manifest at all.

Point 3 is the one nothing currently tracks, and the one I got
wrong by hand before correcting it.

## Cheapest viable instrument

The data already exists — `run_review` returns `manifest.sent` and
`manifest.omitted` on every lane, and the R5 ledger already records
rows. Today those are prose. Three steps, roughly in cost order:

1. **Persist manifests as data**, not ledger prose — `(file, sha,
   lane, timestamp)` per reviewed file.
2. **A `review-coverage` report** answering "which changed files in
   this diff have never been seen by a lane, at any revision?"
3. **Optional gate**, mirroring the D11 risk classes: a lead-authored
   diff touching contract/security/persistence surfaces cannot reach
   the chair with never-reviewed files in it.

Step 1 alone would have prevented tonight's blind spot.

## Counter-case

Review coverage is a *proxy*, and proxies get gamed once measured.
A 100%-reviewed diff whose lanes were shallow is worse than an
honest 60%, because the number licenses confidence. Test coverage
has this disease already — it's why the complexity ratchet and the
vacuous-verifier catch both exist. If we instrument this, the
number must stay diagnostic (a "what did nobody look at?" query),
not become a merge-gate percentage.

## What I'd want ruled

- Is this a spec, or a ledger-format change plus a query script?
- Does it bind only D11 risk classes, or all lead-authored diffs?
- Diagnostic-only, or eventually gating — and if gating, what
  prevents the proxy-gaming failure above?
