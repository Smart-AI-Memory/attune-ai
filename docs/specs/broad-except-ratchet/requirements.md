# Broad-Except Ratchet — Requirements

**Status:** draft (2026-08-02) — AWAITING CHAIR REVIEW. No
implementation authority until the chair approves; this draft
exists so the review has a concrete object.
**Slug:** `broad-except-ratchet`
**Provenance:** chair directive 2026-08-02 ("spec 3 and 4 for chair
review") from the post-dry-run feedback exchange. Evidence base:
bug-predict run `925f08cc1d32` and code-review run `603bd3c065c3`
(2026-08-02) — both flagged the swallow-pattern cluster; bug-predict
counted ~581 `except Exception` sites with the corresponding lint
globally disabled.

## Problem

Broad `except Exception` handlers are the soil silent failures grow
in. Both halves of the run-meta pipe bug (fixed in #1904) were
masked at the consumer by a blanket except that stamped a succeeded
run failed; the memory subsystem shows the same silent-degradation
pattern. The Critical Rules already forbid *bare* `except:`, but
`except Exception` with a swallow is functionally equivalent and
unpoliced at ~581 sites.

## Proposed mechanism (for review, not ratified)

A shrink-only per-file baseline ratchet, modeled on
`tests/unit/ci/test_no_new_sys_modules_patch.py`:

- R1. A guard test scans `src/` for `except Exception` (and
  `except BaseException`) occurrences per file and compares against
  a frozen baseline dict. A NEW or RAISED count anywhere fails CI.
- R2. The baseline is seeded from the current tree at approval time
  and only ever ratchets DOWN — converting a file removes or lowers
  its entry.
- R3. Legitimate sites (evidence collectors, must-not-crash hook
  paths — e.g. `pull_briefing`'s "appendix must not kill the
  routine") stay in the baseline indefinitely; the ratchet freezes
  debt, it does not force conversion.
- R4. A site that logs AND re-raises, or logs and returns an
  explicit degraded sentinel per a documented contract, is still
  counted (keeping the scan mechanical); the baseline is the escape
  hatch, not pattern-matching cleverness.

## Open questions for the chair

- Q1. Count `# noqa: BLE001`-annotated sites too, or treat the
  annotation as the documented-contract marker and exclude them?
  (Excluding makes the ratchet weaker but aligns with the existing
  lint vocabulary.)
- Q2. Scope: `src/attune` only, or also `attune_redis/` and
  `backend/`?
- Q3. Is a fires-on-violation test (per the principles-impact
  candidate) required at approval, or part of implementation?

## Acceptance criteria (when approved)

- Guard test exists, seeded, green on the seeding commit.
- Adding one new `except Exception` to any src file fails the guard
  in CI (fires-on-violation receipt recorded in decisions.md).
- Baseline documented as shrink-only in the test's docstring.

## Out of scope

- Converting any existing site (separate, opportunistic work).
- Style enforcement beyond the two broad-exception forms.
