# auth_strategy behavioral-test rewrite (mutation-driven)

**Status:** planned — sequenced across sessions
**Parent program:** [test-quality-program](./tasks.md)
**Module:** `src/attune/models/auth_strategy.py`
**Opened:** 2026-06-12 (QA #2 phase 2)

---

## Why this is its own plan, not a single per-module cycle

The standard per-module loop (`design.md` §Per-module loop) assumes
one module → one PR. `auth_strategy.py` does not fit: a clean-cache
`mutmut==2.4.4` pass over the module, using the existing
`tests/unit/models/test_auth_strategy_coverage_boost.py` as the
runner, leaves **128 / 270 mutants surviving (~53%)**.

That is the signature of a coverage-padded suite — the tests hit
lines for the coverage number but assert little. Killing 128 mutants
is a behavioral-test **rewrite** spanning many functions, not a
one-sitting hardening. It is therefore sequenced into per-function
sub-slices, each shippable as its own focused PR under this program.

This confirms the handoff hypothesis (the `*_coverage_boost.py`
suites are coverage-padded) with a hard number.

---

## Already done — do not redo

- **`get_recommended_mode`** (the subscription-vs-API spend routing):
  hardened in **QA #2 phase 2**, [PR #793]. Clean-cache mutmut
  confirms mutants 38–43 (the function's full range) are all killed,
  including the `small_module_threshold` `<`→`<=` boundary (mutant 42,
  verified by apply/revert). The gap was an un-varied input dimension
  (`prefer_subscription=False`), not a weak assertion. Covered by
  `TestAuthStrategyPreferSubscriptionRouting`.

[PR #793]: https://github.com/Smart-AI-Memory/attune-ai/pull/793

---

## Sub-slices (each = one PR)

Ordered by leverage. The live per-slice survivor list is regenerated
at execution time (mutants drift as code/tests change) — see
*Mechanics* below. Counts here are the function groupings of the
2026-06-12 survivor set, not a frozen contract.

| # | Slice | Functions | Survivor shape |
|---|-------|-----------|----------------|
| 1 | Serialization fidelity | enum `.value` defs, dataclass field defaults, `to_dict`, `from_dict` | enum value → `None`/`"XX..XX"`; `500`→`501`, `True`→`False`/`None`; dropped/renamed dict keys |
| 2 | Cost estimation | `estimate_tokens`, `estimate_cost` | arithmetic operator swaps (`*`→`/`), per-tier cost constants, the `fits_in_context` thresholds (`200_000` / `1_000_000`), the `mode is None` default branch |
| 3 | Pros/cons rendering | `get_pros_cons` | dict-key drops, f-string content, threshold-interpolation strings |
| 4 | Persistence I/O | `save`, `load` | default-path branch, the corrupt-file fallback, the `validated_path.exists()` guard |
| 5 | Interactive setup | `configure_auth_interactive` | the `tier_map`/`mode_map` defaults, the `default_mode == AUTO` branch, print strings (many will be **equivalent** — see below) |
| 6 | Utilities | `count_lines_of_code`, `get_module_size_category` | the comment/blank-line skip logic, the `< 500` / `< 2000` category boundaries |

---

## Acceptance per slice

1. Regenerate the live survivor list for the slice's functions
   (full-suite runner — see *Mechanics*).
2. For each **killable** survivor, add a behavioral test that fails
   on the mutant and passes on the original. Prove at least the
   load-bearing ones by apply/revert, not by the aggregate count.
3. **Document equivalent / no-value mutants** in the PR body rather
   than chasing 100%. Expected here: print-string `"XX..XX"` wraps
   (output text not asserted by design), and any blocklist-style
   substring-subsumed entries. Equivalent mutants are expected — do
   not weaken production code to kill them.
4. Tests are **behavioral** (assert observable outputs), not coverage
   padding. The slice's kill-rate, not its line coverage, is the
   quality bar.
5. One PR per slice; test-only unless a real production bug surfaces
   (then a sibling PR per `design.md` risk #5). Log any bug in
   `docs/COVERAGE_BUG_LOG.md`.

---

## Mechanics

Pinned recipe lives in `.claude/lessons.md` (the mutmut 2.4.4
entries). Summary:

- `uv run --with 'mutmut==2.4.4' mutmut run` from a scratch dir with a
  temp `setup.cfg`: `paths_to_mutate=<this file>`, `tests_dir=<the
  models test dir>`, and a `runner` that runs the **full**
  `test_auth_strategy_coverage_boost.py` (not a subset — a scoped
  runner makes everything else falsely "survive").
- Isolate real user state: redirect `HOME` to a temp dir for the run
  (`auth_strategy` tests touch `~/.attune/auth_strategy.json`; a
  mutant can break a test's isolation and clobber the real file).
  Snapshot before, restore after.
- Drive via `nohup` + poll the log for `270/270`; `pgrep` misses the
  uv subprocess and a wait-loop exits early. macOS has no `timeout`.
- Use the MAIN venv python + absolute `PYTHONPATH=<worktree>/src`
  (the worktree editable-install MAPPING points at main's src).

---

## Done-state

Closes when slices 1–6 ship and a clean-cache mutmut refresh shows
only documented-equivalent survivors remaining. Until then this is an
open, sequenced sub-plan under the living `test-quality-program`.
