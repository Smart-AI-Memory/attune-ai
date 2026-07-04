# Spec: Windows xdist Worker-Crash Flake Investigation

> Multiple test files have surfaced "worker 'gwN' crashed" Windows-only
> failures over the past two weeks. The existing CLAUDE.md lesson named
> the family (repeated socket probes under xdist worker pressure on
> Windows) and prescribed an xfail pattern, but instances have now
> appeared in three distinct test files. Time to identify the shared
> polluter and decide on a structural fix rather than continuing to
> add xfails one test at a time.
**Status:** approved
**Created:** 2026-06-02
**Owner:** —
**Related:**
- CLAUDE.md lesson "xdist worker crashes on Windows can come from
  repeated socket probes in fixture/helper code, not from the test
  itself" — names the family and the established xfail pattern
- PR #421 (2026-05-16) — first xfail for the family
  (`test_redis_fallback.py::test_tracks_retries_in_metrics`)
- PR #481 (2026-05-26) — second xfail in same file
  (`test_redis_fallback.py::TestErrorHandlingEdgeCases::test_handles_max_clients_exceeded`)
- PRs #559, #561 (2026-06-02) — third and fourth distinct test
  files surfacing the same crash signature; both passed on
  flake-rerun rather than xfail

---

## Phase 1: Requirements

**Status:** draft

### Problem statement

The `xdist worker 'gwN' crashed while running '<test>'` failure mode
has now appeared on Windows CI lanes across at least three distinct
test files in two weeks:

| When | PR | File | Test(s) | Resolution |
|------|----|----|---------|------------|
| 2026-05-16 | #421 | `tests/unit/memory/short_term/test_redis_fallback.py` | `TestMetricsTracking::test_tracks_retries_in_metrics` | xfail strict=False |
| 2026-05-26 | #481 | (same file) | `TestErrorHandlingEdgeCases::test_handles_max_clients_exceeded` | xfail (mirrored #421 rationale) |
| 2026-06-02 | #559 | `tests/memory/test_unified_memory.py` | `TestUnifiedMemoryBackendInit::test_init_with_auto_start_file_first_fallback` | passed on rerun |
| 2026-06-02 | #561 | `tests/agents/test_notifications.py` | `TestComplianceAlerts::test_compliance_alert_structure`, `test_sms_only_for_critical_high` | passed on rerun (in flight at spec-draft time) |

The pattern: a Windows xdist worker crashes (no Python traceback in
the gh log — just the xdist "worker crashed" summary), then the same
test passes when rerun under different worker distribution. Same
shape on Ubuntu/macOS would surface a real traceback; the Windows
"worker crash" is opaque.

The existing CLAUDE.md lesson explicitly says:

> Three tests sharing the xfail is the signal to actually invest in
> root-causing the polluter.

We've crossed that threshold. Continuing to xfail or rerun-and-merge
each new instance leaves the polluter live and gradually grows the
list of distrusted tests.

### Scope

**In scope:**

- Inventory all Windows xdist worker crashes in CI history for the
  last 30-60 days. The four above are the ones we've noticed; a
  systematic scan may surface more we worked around silently
  (rerunning a failed CI job without flagging the failure as
  flake-class).
- Identify what the crashing tests share at the *fixture, helper,
  or import* level. The existing lesson points at repeated socket
  probes in `MemoryFeatures.list_all_features()` and
  `BaseOperations.__init__` — verify whether that pattern explains
  every instance, or whether multiple polluters exist.
- Decision: fix the shared polluter(s) at the source vs. add
  systematic xfails to every test in the affected blast radius.
- If "fix": land the production-side change with a regression test
  that reproduces the polluter behavior cross-platform.
- If "xfail": codify a single helper / marker so the pattern is
  discoverable and removable as a unit when a structural fix lands.

**Out of scope:**

- Linux/macOS test failures (different failure mode, different
  diagnosis path).
- Non-xdist Windows failures — those are normally diagnosable from
  the test output.
- Test-quality improvements to the crashing tests themselves —
  the tests appear to be testing real behavior correctly; the
  failure is environmental, not test-logic.
- Replacing xdist on Windows with serial pytest — already studied
  in CLAUDE.md ("Restoring parallelism exposes Windows xdist
  worker crashes that `-n 1` was hiding by being too slow") and
  rejected on cost grounds.

### User stories

1. **As Patrick reviewing CI on a docs-only PR, I want Windows test
   failures to be either (a) genuinely impossible (no flakes) or
   (b) trivially recognized as the known polluter family** — so I
   don't burn cycles each PR rerunning and waiting.
2. **As a contributor opening a PR, I don't want my PR's CI to be
   the unlucky one that finally surfaces a tenth instance of this
   pattern** — the polluter should be confined or removed.
3. **As a future agent triaging a "worker crashed" failure on
   Windows, I want a documented diagnosis path** — "is this the
   known polluter family?" answerable in <2 minutes rather than
   re-reading three CLAUDE.md lessons.
4. **As the lessons system itself, I don't want the family's lesson
   text to grow indefinitely** — the existing entry is already
   ~200 lines across two distinct lessons. Codifying the fix
   collapses both lessons to "this is fixed; see PR #X."

### Current behavior (grounded in code)

The existing CLAUDE.md lesson identifies two specific call sites
that exhibit the repeated-socket-probe pattern:

1. `MemoryFeatures.list_all_features()` iterates 5 Redis features
   and calls `is_redis_running()` per feature. Each call opens a
   real socket to `localhost:6379` with a 1s connect timeout.
2. `BaseOperations.__init__` blocks ~17s on
   `_create_client_with_retry` (3 retries × 5s socket timeout) when
   no Redis is running.

The lesson's prescribed production-side fix is:

> Dedupe repeated probes in feature-listing helpers (one probe per
> call, not N).

That fix has not yet landed. The lesson's test-side workaround
(patch `_create_client_with_retry` to skip retries) has been
applied per-test as instances surface.

But neither the unified-memory test (#559) nor the notifications
test (#561) appear at first glance to exercise the Redis socket-
probe code paths. So either:
- The shared polluter is broader than the Redis probes
  specifically (perhaps any socket-probe-heavy helper imported at
  module load, even transitively).
- Or there are multiple unrelated polluters and the lesson named
  only one family of them.

### Proposed investigation mechanism

The investigation has four cheap probes before any commit:

1. **Probe A — inventory.** `gh run list --status failure --limit
   200` filtered to Windows lanes, grep for "worker.*crashed" in
   each. Categorize by test file + class. Expected output: a
   ranked list of files with crash counts. Cost: 10-15 min of
   API calls.

2. **Probe B — shared-import trace.** For each crashing test file,
   run `python -c "import <module>"` and trace what gets imported
   at module load (without test fixtures). Look for any module
   that opens sockets, threads, subprocesses, or file watchers at
   import time. Cost: 30 min.

3. **Probe C — fixture-graph trace.** For each crashing test, walk
   the pytest fixture graph (`pytest --collect-only -q` +
   manual conftest reading) and identify any autouse or
   session-scoped fixtures that hit network/IPC. Cost: 30-60 min.

4. **Probe D — Windows reproducer.** Attempt local reproduction
   on Windows (VM or runner SSH) with the failing tests in
   isolation under `pytest -n auto`. Cost: 1-2 hours including
   VM spin-up. Defer unless A/B/C don't converge.

After Probe A+B+C, decision tree:

- **A reveals <5 distinct files affected AND B/C identify a
  single shared polluter** → fix the polluter. Single PR, ship
  cross-platform regression test that fails before fix and passes
  after.
- **A reveals 5-10 files AND multiple polluters** → fix each
  polluter incrementally. One PR per polluter; mark each xfailed
  test as removable once its polluter is fixed.
- **A reveals 10+ files OR B/C can't identify a shared cause** →
  add a custom pytest marker (`@pytest.mark.windows_xdist_flaky`)
  with a single-source skip rationale; apply systematically;
  document the marker as the project's xfail-for-this-family
  signal.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Family of Windows-only worker crashes; four documented instances across three test files. |
| **Interfaces** | partial | Probes named but their tooling (run-list query, fixture-graph traversal) needs design phase. |
| **User-facing behavior** | addressed | CI signal becomes meaningful again. No user-runtime impact. |
| **Edge cases** | partial | What if Probe A reveals the family is broader than expected? Decision tree covers it. What if Probe D's reproducer doesn't reproduce? Phase 2 problem. |
| **Compatibility** | addressed | Production-side fix is back-compat by construction (faster code path). Marker-based fallback is additive. |
| **Error handling** | addressed | Probes are read-only; investigation cannot break anything. |
| **Tradeoffs & alternatives** | addressed | See below. |
| **Rollback** | addressed | Investigation PR is pure docs (the findings report) — no rollback needed. Fix PR(s) are independently revertable. |

### Edge cases & open questions

| Case | Expected |
|------|----------|
| Probe A finds zero historical instances beyond the four listed | Promote the existing four to a "narrow family" and ship the xfail-marker approach; production-side fix not justified |
| Probe A finds 20+ instances we silently reran-and-merged over | Promote to "real CI debt"; production-side fix is mandatory |
| Probes B+C identify two distinct polluters | Each gets its own fix PR; don't bundle |
| Probe D reproduces locally but Probes B+C didn't predict it | Polluter is timing-dependent (not import-graph dependent); investigation continues into runtime fixture interaction |
| Probe D can't reproduce locally | Polluter is CI-runner-specific (different socket handling, different scheduler); accept marker-based xfail with explicit "CI-only flake" rationale |
| New instance surfaces during investigation | Add to inventory; don't react; let the systematic approach catch it |

**DECIDE-1** — Investigation depth ceiling.
*Recommend:* **cap at Probe C (no Windows VM reproduction in v1).**
Reproduction is high cost; if Probes A+B+C don't converge on a
single polluter, fall back to the marker-based approach
immediately rather than spending a day on local repro that may
not even reproduce.

**DECIDE-2** — Fix-first vs. marker-first ordering.
*Recommend:* **inventory-first.** Don't pick fix-vs-marker until
Probe A's output is in hand. The right answer depends on whether
this is 3-4 files (fix-worth-it) or 20+ (marker-as-belt-and-
suspenders while we work toward fix).

**DECIDE-3** — Treatment of currently-xfailed tests once polluter
is fixed.
*Recommend:* **remove xfails as the polluter fix lands, one
removal per test in the fix PR's diff.** The xfails are stand-ins
for the underlying issue; removing them is the natural completion
signal.

### Tradeoffs & alternatives

| Option | Pros | Cons | Pick |
|--------|------|------|------|
| **Investigate now, fix the polluter** (this spec) | Permanent fix; lessons section can collapse | Time cost; may discover the polluter is environmental and unfixable | ✅ default |
| **Keep xfailing per-instance** (status quo) | Zero up-front cost | Distrusted-test list grows; lesson text grows; eventually crowds out real bugs | ✗ — already at the codified threshold |
| **Marker-based xfail without investigation** | Cheap; standardizes the pattern | Doesn't reduce the failure rate; just makes it more uniform | △ — acceptable as Probe-A-failure fallback |
| **Replace xdist with serial pytest on Windows** | Eliminates entire class | Triples Windows CI time (matches CLAUDE.md lesson); some tests stop completing within timeout | ✗ — rejected in prior work |

### Rollback strategy

The investigation Phase (Probes A-C) produces a report — `docs/specs/
windows-xdist-flakes/investigation-report-2026-06-XX.md` — and no
production code changes. Rollback is `git revert` of that one file
addition.

Production-side fixes from later phases are each independently
revertable. Restoration of the existing xfails is captured in the
fix PR's commit message so reversal is mechanical.

### Testing strategy

The investigation Phase doesn't need new tests beyond what the
existing test suite already provides (the flakes themselves are
the signal).

Once a polluter is identified, the fix PR ships a regression test
that:

- Reproduces the polluter's pre-fix behavior on POSIX (the
  reproduction must work cross-platform so it's not skipped where
  CI normally runs); fails before the fix, passes after.
- Verifies that the affected pre-fix tests pass under `pytest -n
  auto` (a smoke check that the fix actually eliminates the
  worker crash).

### Gaps

None blocking Phase 1 approval. Three DECIDEs have recommended
defaults. Phase 2 (design) locks the exact Probe-A query format,
the Probe-B/C trace mechanics, and the inventory report shape.

---

## Phase 2: Design — *(not started; awaiting requirements approval)*

## Phase 3: Tasks — *(not started)*
