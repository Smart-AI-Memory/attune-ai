# Broad-Except Ratchet — Requirements

**Status:** complete (2026-08-07 — guard built, baseline seeded at
613 sites / 253 files, fires-on-violation receipted in three shapes;
D2 in [decisions.md](decisions.md)). Approved 2026-08-06 with Q1–Q3
ruled (D1). Ongoing obligation: the baseline is SHRINK-ONLY — lower
entries as sites are converted.
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

## Ratified clauses (from the Q1–Q3 rulings, D1 2026-08-06)

- R5. **`# noqa: BLE001`-annotated sites are COUNTED.** The
  annotation is not an exemption: 580 of 586 `src/attune` sites
  carry it, so excluding them would police 6 sites. The baseline is
  the only escape hatch (R2/R3).
- R6. **Scope is `src/attune` + `attune_redis` + `backend`.**
  `attune_redis` ships bundled in the wheel; `backend` is 7 sites
  and holds auth/subscription code where a swallow costs most.
- R7. **The fires-on-violation receipt lands with the build**, not
  with approval: the build PR seeds the baseline AND demonstrates
  that one added `except Exception` fails the guard in CI.

## Acceptance criteria (when approved)

- Guard test exists, seeded, green on the seeding commit.
- Adding one new `except Exception` to any src file fails the guard
  in CI (fires-on-violation receipt recorded in decisions.md).
- Baseline documented as shrink-only in the test's docstring.

## Out of scope

- Converting any existing site (separate, opportunistic work).
- Style enforcement beyond the two broad-exception forms.
