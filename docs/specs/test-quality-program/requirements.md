# Spec: Test Quality Program

**Status**: living (ongoing program — never "complete"; the playbook and
rubric are in continuous use). Relabelled from "approved" 2026-06-09 so the
in-flight list stops treating an ongoing program as unexecuted work.
**Created**: 2026-05-12
**Origin**: Long-running umbrella for module-by-module test
quality improvement. Codifies a playbook the
`docs/COVERAGE_BUG_LOG.md` history already shows works (80
modules pushed to 100% across prior sessions, ~22% bug-find
rate, 4 named bug classes). This spec makes that playbook
official, re-orients it from "push to 100%" to "meaningful
coverage on customer-facing paths first, with test-reliability
hardening as a sibling concern," and provides the
prioritization rubric so future sessions don't re-derive it.

---

## Phase 1: Requirements

### Why

Three forces converge:

1. **The previous workstream was framed as a percentage chase.**
   COVERAGE_BUG_LOG records 80 modules pushed to 100% but the
   framing optimized line coverage rather than judgment about
   what `meaningful` looks like for a given module. The bug
   findings (Class 1/2/3 + load-bearing-comment) are the
   real product — coverage numbers are a side effect.

2. **Test reliability is a separate quality concern that
   shares investigative posture.** CLAUDE.md "Lessons Learned"
   surfaces a steady drumbeat of test-reliability bugs:
   structlog stdout pollution, `sys.modules` pollution,
   `datetime.utcnow()` migration cascades, Windows
   `time.time()` resolution, `Path.rename` vs `Path.replace`
   cross-platform, the `/sbin` symlink Ubuntu artifact,
   `MetaPathFinder` deprecated in Python 3.12+, dispatch-table
   patching needing `patch.dict` not `patch.attribute`. These
   are not captured in COVERAGE_BUG_LOG — it tracks production
   bugs surfaced by coverage work, not bugs *in* tests. Adding a
   fifth bug class for test-reliability gives the lessons a
   stable home.

3. **There is no prioritization rubric.** Past sessions picked
   modules opportunistically. With ~645 source files,
   opportunistic selection drifts toward easy wins and away
   from customer-facing risk. A documented rubric weighted on
   customer-facing exposure × coverage gap × risk class is the
   right anchor.

The pre-existing specs cover the surrounding terrain but leave
the core "improve test quality, one module at a time" loop
unspecified:

| Spec | What it covers | What it doesn't |
|------|---------------|------------------|
| `test-infrastructure/` (complete) | Re-enabled xdist; chunked runner retired | What to do next, module by module |
| `ignored-tests/` (approved, 4/4 resolved) | Four specific `--ignore`-d files | Wider `xfail/skip/mock-driven` patterns |
| `coverage-exclusion-policy/` (approved) | Denominator: what's excluded and why | Numerator: what's included and how to push it |
| `coverage-canonical-pattern/` (draft) | CI coverage collection machinery | Module-level test quality |
| `redis-decoupling/` (approved) | Replace fake Redis with real Redis in tests | Other faked-but-broken integrations |

### Goals

- **G1.** A documented per-module loop ("the playbook") that
  any future session can pick up and execute without re-deriving
  the steps. Lives in `design.md`.
- **G2.** A prioritization rubric (customer_weight ×
  coverage_gap × risk_multiplier) that surfaces the next 3-5
  candidate modules at any given time. Rubric output cached as a
  project memory after the first scoring pass so future sessions
  don't recompute from scratch.
- **G3.** A bug-class taxonomy that extends
  `docs/COVERAGE_BUG_LOG.md`'s existing 4 classes with a 5th
  for test-reliability bugs (timing, pollution, cross-platform
  artifacts). Every entry in the log lands in exactly one class.
- **G4.** At least one module taken through the full loop
  end-to-end in this spec's first execution cycle, including
  the CHANGELOG note + COVERAGE_BUG_LOG entry. Proves the
  playbook is operational, not theoretical.
- **G5.** A standing definition of "meaningful coverage" in
  terms of judgment-based signals (public-API behaviors, error
  paths, edge cases that would surprise a caller) rather than a
  line-coverage percentage. Resolves the ongoing tension between
  the 85% CI gate and the per-module judgment work.

### Non-goals

- **Not a percentage target.** Modules judged "meaningfully
  covered" may sit at any % above the CI floor. The 85% CI gate
  is independently maintained by
  `docs/specs/coverage-canonical-pattern/` and the exclusion
  policy.
- **Not a single PR.** Expect a long sequence of small focused
  PRs (one module per session) over many sessions. This spec is
  the framework, not the work.
- **Not test-suite reduction for its own sake.** Deletion of
  low-value tests is in scope when justified, but the program's
  output is *better* tests, not *fewer* tests.
- **Not CI re-architecture.** Belongs to
  `coverage-canonical-pattern/` and is out of scope here.
- **Not coverage exclusion auditing.** Belongs to
  `coverage-exclusion-policy/`. When the per-module loop finds
  a module that *should* be excluded, log the question and hand
  off to that spec.

### Definition: "meaningful coverage"

The judgment-based criteria (apply per module, not as a global
checklist):

1. **Public-API behaviors.** Every exported function/class has
   at least one test asserting a non-trivial return value or
   side effect on a real (not mocked) input shape.
2. **Error paths.** Each `raise` statement in the module has a
   test that drives the raise condition. If the raise is
   unreachable, that's a Class 2 bug — fix the code, don't add a
   skip.
3. **Dispatch branches.** For switch/dispatch tables (enum
   dispatch, command routers, plugin registries), each entry has
   at least one test. Missing entries are a Class 2A signal.
4. **Edge cases that would surprise a caller.** Empty inputs,
   boundary values, unicode/null bytes for any string-handling
   path, timezone-aware vs naive datetimes for any timestamp
   logic, cross-platform path semantics for any filesystem path
   logic.
5. **Real objects over mocks where cheap.** If using a real
   object costs <100ms per test and doesn't require network
   reach, prefer it. Reserve mocks for network, subprocess,
   slow filesystem.

A module that meets criteria 1-4 with appropriate use of
criterion 5 is "meaningfully covered" — even if line coverage
sits at 87% because an `ImportError` fallback or a defensive
`pragma: no cover` exists.

### Public-API impact

None. This is internal process and tooling. No PyPI consumer
sees a behavior change.
