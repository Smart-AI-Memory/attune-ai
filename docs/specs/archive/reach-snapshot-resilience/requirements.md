# Reach Snapshot Resilience

**Status:** implemented (2026-06-24) — Option A shipped in
`scripts/reach_snapshot.py`; tests in
`tests/unit/scripts/test_reach_snapshot.py`.
**Owner:** Patrick + agent
**Created:** 2026-06-22

---

## Decisions

- **D1 → A (resumable partial write).** Each package is persisted to
  the day file as it succeeds (atomic temp+rename); a rerun loads the
  day file, skips already-captured packages, and fetches only the
  remainder. The rate-limit discipline is unchanged (still spaces
  requests, still aborts on the first 429). C (scheduled cadence) is
  left as an optional fast-follow, not done here.
- **Retention → merge/skip within a day.** A rerun the same day merges
  into the existing `<date>.json` and skips packages already present —
  it does not overwrite. The GitHub line is filled in by whichever run
  completes the full package set.

---

## Problem

`scripts/reach_snapshot.py` (usage-signals R4) is kicked off at tag
time by the release ritual to capture a PyPI-downloads + GitHub-traffic
baseline. It reliably fails there:

- pypistats 429-penalizes bursts, and (per the script's own Phase 0
  docstring) the penalty *outlasts* short retries.
- The script's defense is correct-but-blunt: it **aborts the entire
  run on the first 429**, discarding any packages already fetched. So
  a run that gets 3 of 5 packages then 429s writes **nothing** — the
  next run starts from zero and is likely to 429 again.
- Hit twice in one day (2026-06-22, the 8.7.0 and 8.7.1 ships). The
  net effect: the "before/after pair" R4 promises is frequently never
  captured, so the data the release ritual exists to collect is
  silently missing.

This is a resilience gap, not a correctness bug — the rate-limit
discipline (don't hammer) is right; the all-or-nothing failure mode is
what wastes the partial progress.

---

## Goals

1. A snapshot run **preserves partial progress** — packages already
   fetched in a run/day are not lost to a later 429.
2. A 429 degrades to "**rerun later to finish the remainder**," not
   "start over."
3. No change to the rate-limit discipline: still space requests, still
   never hammer on a 429.
4. The release ritual stays unblocked — the snapshot remains
   best-effort and never gates a release.

## Non-goals

- Authenticated/private pypistats access or a different data source.
- In-run aggressive retry/backoff against pypistats (the penalty
  outlasts it — explicitly rejected, see D-Options B).

---

## Options (D1 — approach)

**A — Resumable partial write (recommended).** Persist per-package
results to the day's `<date>.json` *as each succeeds*. On rerun, load
the existing day file and **skip packages already captured today**;
only fetch the remainder. A 429 still aborts the current run, but the
captured packages are durable and a rerun completes the set. Lowest
risk; respects the existing discipline; smallest change.

**B — In-run exponential backoff.** Retry the 429'd package with
growing waits inside the same run. **Rejected** — the module docstring
documents that the penalty outlasts minutes of retrying, so this fights
reality and lengthens a run that's already best-effort.

**C — Move off the release critical path to a scheduled cadence.**
Run the snapshot from a cron/scheduled job (e.g. daily) decoupled from
tag time, so release-time 429s never matter. Complementary to A, not a
substitute (A still needed for the scheduled run to be robust). Could
be a follow-up.

**D — Skip on docs-only releases.** Don't even attempt at tag time for
a `src`-identical release. Narrow; doesn't fix the underlying
fragility. Could pair with C.

**Recommendation:** **A** now (durable partial progress — directly
fixes the wasted-work failure), with **C** as a fast follow if Patrick
wants the snapshot off the release path entirely.

---

## Design sketch (Option A)

- `main()` loads `<out>/<YYYY-MM-DD>.json` if it exists and seeds the
  results dict from it.
- Iterate `PACKAGES`; for each not already present, fetch + **write
  the day file after each success** (atomic write: temp + rename).
- On `RateLimitedError`: log "captured N/total today; rerun after the
  cooldown to finish the rest," write what we have, exit non-zero
  *only* in standalone use — but the release ritual already runs it in
  the background and ignores exit code, so no ritual change needed.
- GitHub signals (already best-effort/degrading) unchanged.

## Validation

- Unit: seed a day file with 2 packages, stub `fetch_pypistats_recent`
  to raise `RateLimitedError` on the 3rd → assert the 2 seeded + any
  newly-fetched persist and the run doesn't lose them.
- Unit: full success path writes all packages and is idempotent on
  rerun (no duplicate fetches — already-present packages skipped).

## Open questions

- **D1**: approve A (and is C a wanted follow-up, or leave tag-time
  best-effort)?
- Retention: is one file per day (current) fine, or should a rerun the
  same day overwrite vs merge? (Design assumes **merge/skip** within a
  day.)
