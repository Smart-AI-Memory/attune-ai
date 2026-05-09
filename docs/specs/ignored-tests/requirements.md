# Spec: Resolve `--ignore`-d Test Files

**Status**: approved
**Parent**: `docs/specs/test-infrastructure/` (task #10, deferred)
**Created**: 2026-05-09

---

## Phase 1: Requirements

### Problem statement

Four test files are silently skipped via `--ignore` directives in
`pytest.ini`. The test-infrastructure spec (2026-05-09) audited them
and found 88 real failures across the four files — these are not
"ghost" failures from stale state, they are tests written against
production surface that has since drifted.

```
pytest.ini --ignore directives (audited 2026-05-09):

  tests/unit/models/test_execution_and_fallback_architecture.py  41 fail / 11 pass
  tests/unit/orchestration/test_composition_patterns.py          14 fail / 21 pass
  tests/unit/workflows/test_orchestrated_release_prep.py          5 fail / 30 pass
  tests/unit/scaffolding/test_scaffolding_cli.py                 28 fail / 14 pass

  Total: 88 failures, 76 passes hidden behind --ignore.
```

The four files have **different shapes** of test debt and need
different responses. Treating them as one bucket ("fix the failing
tests") will either underspend (rubber-stamping mocks back into
green) or overspend (rewriting tests for surfaces that aren't
actually used).

#### Per-file diagnosis (from test-infrastructure audit)

1. **`test_execution_and_fallback_architecture.py` — 41 fail / 11 pass.**
   Written as "Architectural Tests for LLM Execution and Fallback
   System" with a coverage target of "95%+ (from 21-73%)". Header
   contains live admissions of drift:
   `# NOTE: FallbackPolicy may not exist or have different API - Gap 3.2`.
   Production reality: `FallbackPolicy` lives in
   `src/attune/models/fallback_policy.py`, not `fallback.py`. These
   are **aspirational tests written ahead of the implementation**
   that were never reconciled when the implementation landed in a
   different shape.

2. **`test_composition_patterns.py` — 14 fail / 21 pass.**
   File header claims **"XFAIL TEST REMEDIATION - COMPLETED
   (2026-01-24)"** and lists all 24 xfail tests as refactored to
   use mocks. Reality: 14 tests still fail. Either the remediation
   was incomplete, or composition-pattern code has regressed since
   January. This is **stale "fixed" status** — the most dangerous
   category of test debt because it inspires false confidence.

3. **`test_orchestrated_release_prep.py` — 5 fail / 30 pass.**
   Small failure ratio. Sample diagnosis from prior audit:
   `assert isinstance(result, AgentResult)` fires at
   `core_strategies.py:161` because real workflow execution returns
   a non-`AgentResult` type. This is **return-type drift** — fixable
   with bounded scope (likely a few hours of work).

4. **`test_scaffolding_cli.py` — 28 fail / 14 pass.**
   Uses heavy `sys.modules` injection
   (`sys.modules["test_generator"] = MagicMock()`,
   `sys.modules["patterns"] = MagicMock()`) before importing the
   module under test. High failure ratio suggests the
   `src/attune/scaffolding/cli.py` surface has moved out from
   under the mocks. **Mock-driven test that didn't follow its
   target.**

### Why this matters now

- 88 failing tests live in the repo as `--ignore` flags.
  `git grep --ignore` is not how invariants get enforced.
- 76 *passing* tests are also hidden — those are silent coverage we
  can recover by un-ignoring the files (after deciding which tests
  to keep).
- The test-infrastructure spec deferred this work explicitly. Until
  it's resolved, the "is everything green?" signal from
  `pytest tests/` is incomplete by design.
- The longer this sits, the more the four files drift from
  production reality, the more expensive resolution becomes.

### Goals

- **G1: Zero `--ignore` directives in `pytest.ini` for unit tests.**
  Each ignored file is either un-ignored (passing), deleted with
  documented justification, or replaced with a smaller targeted
  test file.
- **G2: Each resolved file has a stable signal.** After resolution,
  the test file either passes consistently under `-n auto` or is
  gone — no `xfail`, no `skip`, no "expected to fail" decorators
  papering over real failures.
- **G3: The 76 currently-hidden passing tests are recovered as
  active coverage** wherever they're testing real, current
  behavior. Not just kept for show — pruned where they assert
  against drift.
- **G4: A documented decision rule for `--ignore` exists.** The
  next time someone reaches for `--ignore` in `pytest.ini`, there's
  a prior decision on the table: is this debt going to be paid down,
  on what timeline, or is the file getting deleted?

### Non-goals

- **Not raising overall coverage.** The goal is correctness of the
  signal, not coverage numbers. If un-ignoring drops measured
  coverage because aspirational tests get deleted, that's fine —
  the prior coverage was lying.
- **Not rewriting production code to match the tests.** Where
  tests assert against an API shape that production no longer
  has and shouldn't have, the tests lose, not the production code.
- **Not adding new tests.** The smart-test workflow exists for
  that. This spec resolves what's already there.
- **Not auditing other ignore mechanisms** (`@pytest.mark.skip`,
  `@pytest.mark.xfail` scattered across other files). Out of scope —
  this spec is about the four `--ignore` lines.

### Success criteria

- `pytest.ini` `addopts` contains zero `--ignore=tests/unit/...`
  directives. (The `--ignore=tests/integration/` directive may
  remain — that's a category exclusion, not test debt.)
- The full unit suite (`pytest tests/unit/`) runs the contents
  of all four files and exits green.
- A short markdown note (`docs/specs/ignored-tests/decisions.md`,
  written during execution) records, for each file, what was
  done and why: kept-and-fixed, partially deleted, fully
  retired. Future readers can answer "what happened to the
  scaffolding CLI tests?" from the repo.
- No new `--ignore` directives are added to compensate.

### Risks

- **Risk 1 — scope creep into production code.** Fixing
  `test_orchestrated_release_prep.py` requires touching
  `core_strategies.py:161` (return-type contract). Other files
  may surface similar production-code debt. Mitigation: when a
  test fix requires production change, treat that production
  change as the deliverable and stop the test rewrite until the
  contract is settled.

- **Risk 2 — `test_execution_and_fallback_architecture.py` is
  aspirational and may have value as a design document even if
  the tests don't pass.** Mitigation: before deletion, extract
  any architecturally-meaningful invariants into either a
  `docs/architecture/` note or a smaller targeted test file.
  Deleting them silently loses the design intent.

- **Risk 3 — `test_composition_patterns.py`'s "remediation
  complete" header is wrong, suggesting whoever wrote it didn't
  actually run the tests after refactoring.** This is a process
  smell. Mitigation: add a note to the resolution decision about
  what changed between 2026-01-24 (claimed remediation date) and
  2026-05-09 (audit) — if it's a real regression, the
  composition-pattern code itself may need attention.

- **Risk 4 — un-ignoring may surface new flakiness under xdist.**
  The 88 known failures were observed in isolation. Running these
  files alongside the other 14,075 tests under `-n auto` may
  reveal cross-file interference. Mitigation: each file gets
  un-ignored individually, full suite re-run, then commit. Don't
  un-ignore all four at once.

- **Risk 5 — "delete the test" is the easy answer and will be
  over-applied.** Mitigation: the decision rule (see Phase 2)
  requires a reason for deletion that isn't "it failed." Tests
  asserting current behavior get fixed; tests asserting fictional
  behavior get deleted with a note.
