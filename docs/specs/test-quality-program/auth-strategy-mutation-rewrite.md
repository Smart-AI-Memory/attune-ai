# auth_strategy behavioral-test rewrite (mutation-driven)

**Status:** slices 1–6 complete — closing (pending a final
clean-cache mutmut refresh)
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

- **Slice 1 — Serialization fidelity** (enum values, dataclass field
  defaults, `to_dict`, `from_dict`): hardened in **QA #2 phase 5**.
  Six behavioral tests in `TestAuthStrategySerializationDefaults` pin
  the contract the happy-path suite left open — every `SubscriptionTier`
  / `AuthMode` on-disk string, the no-arg dataclass defaults, the
  `metadata` default_factory independence, the `from_dict({})` `.get()`
  fallbacks, and `to_dict` emitting raw `.value` strings (a `.value`
  removal is caught by `type(...) is str`, since the enums subclass
  `str`). Six load-bearing mutants proven killed by apply/revert
  (defaults `500`→`501`, `True`→`False`; enum value mutate;
  `from_dict` `.get` fallback `500`→`501` and `"pro"`→`None`; `.value`
  drop). No production bug surfaced — test-only.

- **Slices 2–5** (QA #2 phase 6, one test-only PR): the remaining
  behaviorally-killable survivors, each proven by apply/revert. No
  production bug surfaced.
  - **Slice 2 — Cost estimation** (`TestAuthStrategyCostEstimationExactness`,
    5 tests): exact API `monetary_cost` (the four tier constants), both
    `fits_in_context` boundaries (`200_000` / `1_000_000` + `<` vs `<=`),
    `int()` truncation in `estimate_tokens`, the default `mode=None`
    param. 6 mutants killed. Equivalent: `round(,4)`→`round(,5)` (both
    render `0.0002`).
  - **Slice 3 — Pros/cons rendering** (`TestAuthStrategyProsConsRendering`,
    5 tests): `auto`-section key parity, `auto.estimate` `mode` /
    `.value`-typed `current_recommendation`, plus data-bearing
    interpolation guards (tier value, thresholds, monetary cost). 4
    mutants killed; a cosmetic copy mutant proven to survive (the
    function is mostly display text — equivalent by design).
  - **Slice 4 — Persistence I/O** (`TestAuthStrategyPersistenceDefaultPath`,
    4 tests): `load()`'s default-path branch + `.exists()` guard against
    a known file, `save(None)` serialized content, full save→load
    round-trip of every field. 3 mutants killed; `json.dump` `indent`
    proven equivalent. All `AUTH_STRATEGY_FILE`-patched (real user state
    untouched).
  - **Slice 5 — Interactive setup**
    (`TestConfigureAuthInteractiveContract`, 3 tests): the net-new
    non-display survivors — `setup_completed=True`, input `.strip()`
    before lookup, persistence via `save()`. 2 mutants killed; the
    `default_mode == AUTO` print branch proven equivalent. (`tier_map` /
    `mode_map` routing was already covered by `TestConfigureAuthInteractive`.)

- **Slice 6 — Utilities** (`count_lines_of_code`,
  `get_module_size_category`): **no new tests needed.** The existing
  `TestGetModuleSizeCategory`, `TestCountLinesOfCode`, and
  `TestCountNonBlankLines` already kill every slice-6 mutant. Verified
  2026-06-12 by apply/revert of 12 mutants against the existing suite —
  both category boundaries (`< 500` / `< 2000`, the `<`→`<=` flips and
  threshold offsets), the comment/blank-skip logic (`.strip()` drop,
  `not startswith("#")` removal, `and`→`or`), `lines += 1`, the
  exists-guard return value, the first-read encoding, and the
  dual-read-failure fallback — all already `KILLED`. The plan's
  slice-6 survivor row reflected the stale 2026-06-12 snapshot, not
  current killability (scope-drift; the code is the contract).

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

Slices 1–6 are complete: slice 1 shipped in [PR #797]; slices 2–5
shipped as one test-only PR (QA #2 phase 6); slice 6 was verified
already-covered by the existing suite (no new tests). Every
behaviorally-killable survivor is proven dead by apply/revert, and the
documented-equivalent survivors (print/format strings, `round`
precision, `json.dump` indent) are recorded inline above.

One step remains before formally closing: a final clean-cache
`mutmut==2.4.4` refresh over the whole module to confirm only the
documented-equivalent survivors remain. Until that refresh runs, this
stays a (near-complete) sub-plan under the living
`test-quality-program`.

[PR #797]: https://github.com/Smart-AI-Memory/attune-ai/pull/797
