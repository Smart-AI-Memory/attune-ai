# Coverage Bug Log

Append-only log of bugs surfaced while pushing module coverage toward 100%.
The thesis: branches that resist coverage are signal — almost always one of
three patterns.

**Bug classes**

1. **Crash paths nobody triggered** — production code that throws on real
   input but had no test exercising the path.
2. **Dead code wearing defensive-coding clothes** — code that looks defensive
   but is unreachable, which means it's also untested and couldn't actually
   defend.
3. **Tests that mocked around the bug** — tests pass because they mock the
   broken caller; coverage at 100% looks fine, production code is wrong.

Format: most recent session at top. Per bug: `module — class — one-liner`.

---

## 2026-05-12 — first PoC under test-quality-program spec (Opus 4.7)

First module pair taken through the formalized playbook
(`docs/specs/test-quality-program/`, spec PR #257).
Paired PR: `memory/security/query.py` + `memory/security/reports.py`.
Selected via rubric (top two scores in the working set: 3.99 and
3.80, both data-handling 1.5× risk). **1 production bug surfaced.**

- `memory/security/query.py` — **class 1** — a single audit log
  line with a malformed `timestamp` aborted iteration. Inner
  try-except caught only `JSONDecodeError`, so `ValueError` from
  `datetime.fromisoformat()` propagated to the outer broad except
  clause — the function logged once and returned whatever results
  had accumulated so far. Symptom: a query with date filters
  silently truncated its result set with no caller-visible
  indication. Fix: per-line try/except for `(ValueError,
  AttributeError)` inside the iteration loop, mirroring the
  JSONDecodeError handler. Continues iteration on bad lines,
  logs a warning per skip.

**Coverage delta:**

| Module | Before | After |
|---|---|---|
| `memory/security/query.py` | 11.2% | 100.00% |
| `memory/security/reports.py` | 11.2% | 100.00% |

**Tests:** 62 total (37 query, 25 reports). Real `AuditLogger`
host instances against `tmp_path` — criterion-5 "real objects
over mocks" of the meaningful-coverage definition. Determinism
verified across 3 back-to-back runs and under `-n auto`
alongside the full memory test subtree (1367 passed, no
cross-test interference).

**Notes on the second module:** `reports.py` surfaced no
production bugs. Every defensive `.get(..., default)` path is
real and reachable (the audit-log JSON shape isn't strictly
enforced upstream so missing keys do happen in production). No
Class 2 candidates. Demonstrates the spec's "absence of bugs is
also data" observation from prior sessions.

---

## 2026-05-09 — session 49e (Opus 4.7)

Test-infrastructure spec executed (docs/specs/test-infrastructure/).
**3 production bugs surfaced**, none in the spec's target area — all
side effects of investigating it.

### Spec outcome (Phase 2A diagnosis)

The "biggest infrastructure debt" identified in the project-health
audit turned out to be a stale comment, not a real bug. `pytest.ini`
forced `-n 0` (sequential execution) for years based on a one-line
comment about "import timing issues with workflows package." Test #1
of the spec (flip `-n 0` → `-n auto`, run full suite) just worked:
14,073 tests pass under xdist in 101 seconds. The issue evidently
got fixed incidentally as the codebase evolved; nobody re-checked
the constraint.

This is a **fourth diagnostic pattern worth naming**: "load-bearing
comment that nobody re-validated." Different shape from Class 1/2/3,
because the bug is in the documented constraint, not the code.

### Bugs surfaced as side effects

- `plugin/.claude-plugin/marketplace.json` + `plugin/core/__init__.py`
  — version mismatch (6.3.0 vs plugin.json 6.6.0) from PR #204's
  release bump that didn't propagate. Surfaced by `test_all_versions_match`
  under the re-enabled parallel run, NOT introduced by it. Bumped both
  to 6.6.0.
- `tests/unit/plugins/test_plugin_config_validation.py` — test asserted
  `plugin/commands/` directory shouldn't exist (skills migration), but
  PR #204 intentionally added `plugin/commands/handoff.md`. Test wasn't
  updated. Replaced with `test_commands_directory_only_has_allowlisted_commands`
  with explicit allowlist.
- 463 stale help templates in `plugin/help/generated/`. The
  `Check Help Template Freshness` pre-commit hook is warn-only locally
  but in CI auto-regenerates and reports "files modified by hook" as
  a failure. This had been blocking dependabot PRs (#191, #192) for
  5+ days. Regenerated via `ATTUNE_DOCS_AUTOREGEN=1`; both PRs unblocked
  on rebase.

### Audit findings (task #4)

The four `--ignore`-d test files in `pytest.ini` were audited. All
four have real test debt totaling 88 failures. Resolution deferred
to a follow-up spec because each needs design work, not 5-minute
fixes. Findings documented inline in `pytest.ini`.

---

## 2026-05-09 — session 49d (Opus 4.7)

Targeted sweep using a new AST-based scanner
(`scripts/find_dead_defensive_code.py`) for the four Class 2 sub-patterns.
**2 production bugs surfaced**, both Class 2A (the most common shape).

### Tooling added

- `scripts/find_dead_defensive_code.py` — heuristic finder for 2A
  (exhaustive enum dispatch + dead default), 2B (post-loop fallback),
  2C (divisor guard hints). Walks the AST and emits candidates worth
  reading. Self-bootstraps the enum-member map by walking the source
  tree first.

### Bugs — Class 2A (default after exhaustive enum dispatch)

- `models/tasks.py:get_tasks_for_tier` — `if tier == ModelTier.X` for
  all three members of `ModelTier`, followed by `return []`. The
  trailing default was unreachable for known tiers and silently swallowed
  unknown ones. Replaced with `raise ValueError(f"Unknown ModelTier: ...")`
  and added a test for the raise path.
- `trust/circuit_breaker.py:should_require_confirmation` — same shape on
  `TrustState`. Trailing `return True  # Default to safe` was unreachable
  AND would have masked an incomplete dispatch if a new state were added.
  Replaced with `raise ValueError(f"Unknown TrustState: ...")` and a
  matching test.

This brings sub-pattern 2A's known instances to **6 across 6 unrelated
modules** (`meta_orch_estimation`, `meta_orch_analysis`, `explainer`,
`ab_testing/allocator`, `models/tasks`, `trust/circuit_breaker`). The
shape repeats reliably enough to argue it's a stable category.

The 2C scanner emitted 4 candidates that all need manual review (it
flags any `if x > 0:` guarding `/x`, regardless of whether the divisor
is structurally non-zero). Triaging those is left as future work.

---

## 2026-05-09 — session 49c (Opus 4.7)

13 modules pushed to 100% (or accepted ~98% for partial for-loop branches).
**2 production bugs surfaced** — both Class 2 (dead defensive code).

### Modules — 0 bugs

- `socratic/feedback_models.py` — 91.53% → 100% (4 zero-use guard branches in
  `get_score_for_context`)
- `socratic/collaboration_models.py` — 93.55% → 100% (roundtrip serialization
  for Comment/Vote/Change/CollaborativeSession + VotingResult.approval_rate
  zero-active branch)
- `socratic/success_models.py` — 93.92% → 100% (BOOLEAN-with-non-bool
  fall-through, LOWER_IS_BETTER no-max, RANGE infinite size, unknown
  direction default)
- `socratic/ascii_visualizer.py` — 90.00% → 100% (>3 tools, long agent string
  truncation, parallel marker, _center text-wider-than-width, empty-stage
  agent listing skip)
- `socratic/generator.py` — 95.45% → 100% (unknown-template skip,
  reporter-only/generator-only stages, real `_create_xml_agent`)
- `socratic/html_renderer.py` — 96.30% → 100% (show_when data attribute,
  option description span)
- `socratic/ab_testing/models.py` — 97.85% → 100% (avg_success_score
  zero-impressions short-circuit)
- `socratic/session.py` — 93.50% → 100% (can_generate at max_rounds,
  from_dict goal_analysis reconstruction)
- `workflows/progress.py` — 69.01% → 100% (full ProgressTracker lifecycle:
  callback errors, stage start/complete/fail/skip/fallback/retry, async
  callback path, factory)

### Bugs — Class 2 (dead defensive code)

- `socratic/explainer.py` — Defensive default `return explanation.to_markdown()`
  after the `OutputFormat` enum chain (TEXT/MARKDOWN/HTML/JSON all explicitly
  handled). The enum has exactly four values, all covered above. Removed and
  collapsed JSON branch into the natural-fall-through path.
- `socratic/ab_testing/allocator.py` — Defensive default
  `return self._fixed_allocation(user_id)` after the `AllocationStrategy`
  enum chain (FIXED/EPSILON_GREEDY/THOMPSON_SAMPLING/UCB all explicitly
  handled). Same pattern: 4 enum values, all covered. Replaced final
  `if`-check with direct `return self._ucb_allocation()`.

Both bugs are sub-pattern A of Class 2 — **"defensive default after
exhaustive enum dispatch."** Same shape, same fix. This is at least the
fourth instance of this exact pattern (also seen in
`meta_orch_estimation.py`, `meta_orch_analysis.py`, and `retry.py` post-loop
fallback variants).

---

## 2026-05-09 — session 49b (Opus 4.7)

6 additional modules pushed to 100% (or accepted ~96% for module-import
unreachable code). **0 production bugs surfaced.** Absence of bugs is also
data — these modules were already well-tested at edges; the coverage gaps
were genuine missing tests, not hidden defects.

- `resilience/circuit_breaker.py` — 87.93% → 100%
- `workflows/escalation/convenience.py` — 88.89% → 100%
- `workflows/progress_models.py` — 98.18% → 100%
- `workflows/state_mixin.py` — 97.67% → 100%
- `workflows/progress.py` — 69.01% → 100% (new test_progress_tracker.py)
- `workflows/telemetry_mixin.py` — 87.34% → 96.20% (module-import
  ImportError fallback at lines 29-31 is unreachable post-import; accepted)

---

## 2026-05-09 — session 49 (Opus 4.7)

11 modules pushed to 100%. 4 production bugs surfaced.

- `socratic/cli_console.py` — **class 1** — `Console.table()` raised
  `IndexError` when a row had more cells than headers (guard existed in the
  width-calculation loop, missing in the print loop). Fixed by mirroring the
  guard.
- `orchestration/meta_orchestrator.py` — **class 1** — `compose_team()` read
  `plan.phases`, but `ExecutionPlan` has no `phases` attribute. Every call
  raised `AttributeError`. Replaced with `[]` (matches what
  `DynamicTeamBuilder.build_from_plan` defaults to).
- `orchestration/meta_orch_analysis.py` — **class 2** — `_classify_domain`
  had an unreachable for-loop-fell-through branch (the inner `return`
  always fires when `max_score > 0`). Refactored to `max(scores, key=...)`.
- `resilience/retry.py` — **class 2** — three identical post-loop blocks
  (`if last_exception: raise last_exception`) were unreachable: the loop
  always raises or returns. Removed across `async_wrapper`, `sync_wrapper`,
  and `retry_with_backoff`. Kept the `RuntimeError` fallback, which IS
  reachable when `max_attempts < 1`.

---

## Prior cumulative sessions (retroactive — recovered from session notes)

Bugs found and fixed across earlier coverage pushes. Less granular because
they predate this log.

- `socratic/feedback_collector.py` — **class 3** — infinite recursion
  between `get_insights()` and `_generate_recommendations()`. Existing tests
  passed by mocking the recursive caller. Fixed by extracting a
  `_compute_domain_insights()` helper and breaking the cycle.
- `socratic/engine.py` — **class 1** — `_generate_success_criteria`
  constructed `SuccessMetric()` without the required `description` argument.
- `meta_workflows/pattern_memory.py` — **class 2** — unreachable
  `if form_response:` block (line 233) removed.
- `meta_workflows/llm_execution.py` — **class 2** — dead
  `raise RuntimeError("No tiers attempted")` removed.
- `meta_workflows/pattern_learner.py` — **class 2** — dead
  `if failure_count > 0:` removed (creating an entry always increments past
  zero).
- `models/provider_config.py` — **class 2** — dead `if model:` filter
  removed.
- `models/telemetry/analytics.py` — **class 2** — three dead defensive
  `if x > 0:` divisor guards removed.

---

## Tally

| Class | Description | Count |
|-------|-------------|-------|
| 1 | Crash paths nobody triggered | 3 |
| 2 | Dead defensive code | 13 |
| 3 | Tests mocking around bugs | 1 |
| 4 | Load-bearing comments nobody re-validated | 1 |

**Class 2 sub-patterns observed:**

- **2A — Defensive default after exhaustive enum dispatch.** A function
  switches on an enum, handles every value explicitly, then has a
  trailing default. Dead. (6 instances: `meta_orch_estimation`,
  `meta_orch_analysis`, `explainer`, `ab_testing/allocator`,
  `models/tasks`, `trust/circuit_breaker` — last two found by
  `scripts/find_dead_defensive_code.py`.)
- **2B — Post-loop fallback after a loop that always returns/raises.**
  `for ... try: return except: raise` patterns where the loop body
  guarantees exit, but a `if last_exception: raise` block sits beneath it
  anyway. Dead. (3 instances in `retry.py`.)
- **2C — Defensive divisor guard where divisor is structurally non-zero.**
  `if x > 0:` before division, where every code path that creates the
  entry also increments past 0. Dead. (3 instances in
  `telemetry/analytics.py`, 1 in `pattern_learner.py`.)
- **2D — Filter on already-filtered data.** `if model:` filter applied to
  a list whose construction already excluded falsy entries. Dead.
  (1 instance: `provider_config.py`.)

**Sessions where 0 bugs surfaced:** 1 (session 49b).

**Bug-find rate:** 18 bugs across 80 modules pushed to 100% = ~22% of
modules contain at least one production bug surfaced by the coverage push.
Plus 3 merge-artifact bugs surfaced by the test-infrastructure spec
(version mismatch, commands-directory test, stale templates) that aren't
strictly coverage-push finds but came from the same investigative posture.

Modules at 100%: 80 (cumulative across all sessions).
