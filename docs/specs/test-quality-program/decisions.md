# Per-module decisions — Test Quality Program

**Status:** approved


Append-only log. One section per module as it's worked. See
`requirements.md`, `design.md`, `tasks.md` for the framework.

Format per entry:

```text
## <module path>

**Date:** YYYY-MM-DD
**Rubric score at pick time:** <score> (weight × gap × risk)
**Picked because:** <one-line reasoning>
**Outcome:** <one-line summary — modules touched, bug classes, tests added/removed>
**PR:** <link>
**Bug log entry:** <link to COVERAGE_BUG_LOG.md section>

[Body: what stays, what got rewritten, what got deleted, and
why. Any surfaced production change deferred to a sibling PR.]
```

---

<!-- First entry lands here when task #8 ships. -->

## workflows/dependency_check.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.685 (weight=5 × gap=0.537 × risk=1.0)
**Picked because:** First entry with measured `covered_pct`
after `ops/cli.py` shipped. The 11 rows above it
(scores 4.0 / 3.0, `workflows/test_*.py` files) are
coverage-omit artifacts of the `*/test_*.py` pattern in
`pyproject.toml` — coverage never measures them, so the
rubric's `?` marker is informational, not a real gap.
**Outcome:** 1 test file added (`test_dependency_check_execute.py`,
21 tests). Coverage 41.67% → 100% line+branch. Zero
production bugs surfaced. Pattern is reusable for
sibling SDK-native workflows (`bug_predict`,
`perf_audit`, `refactor_plan`).
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — fourth module under test-quality-program"

The module is a thin async shell around
`claude_agent_sdk.query()`. The uncovered slice was
the entire `execute()` body (lines 127–166) and the
`_run_agent_check()` async loop (lines 180–229). The
only thing mocked in the new tests is `query()` itself;
the messages it yields are real
`claude_agent_sdk.AssistantMessage` and
`ResultMessage` dataclasses so the `isinstance()`
checks in `agent_sdk_adapter.collect_agent_output`
fire correctly (this avoids the trap documented in
CLAUDE.md: "Duck-typed test fakes fail
isinstance-based collectors silently"). Depth
mapping (quick=10 / standard=20 / deep=40), each
specific exception path (`ImportError`,
`ConnectionError`, `TimeoutError`, generic
`Exception`), and the empty-stream "No results
returned" fallback are all individually covered.

**Rubric refinement flagged (not done here):** the
`*/test_*.py` omit pattern hides four `workflows/test_*.py`
production modules from coverage entirely. Either the
pattern should tighten to `tests/test_*.py`, or the
rubric script should drop `?` covered_pct rows from
the working-set top. Surfaced as a follow-up; not in
scope for this PR.

## workflows/bug_predict.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.636 (weight=5 × gap=0.527 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `dependency_check.py` shipped. Structurally
identical SDK-native shell — the test scaffold from
PR #265 transferred with a one-pass rename. The prior
decision entry explicitly flagged it as the next pick.
**Outcome:** 1 test file added (`test_bug_predict_execute.py`,
21 tests). Coverage 47.3% → 97% line+branch (only the
`if __name__ == "__main__"` guard at line 271 remains
uncovered, standard untestable boilerplate). Zero
production bugs surfaced. Two SDK-native shells now
through the program; `perf_audit` and `refactor_plan`
remain.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — fifth module under test-quality-program"

Same body shape as `dependency_check`: thin async shell
around `claude_agent_sdk.query()`, three subagents
(`pattern-scanner`, `risk-correlator`,
`prevention-advisor`), depth → max_turns mapping
(quick=10/standard=20/deep=40), specific exception
paths each producing a structured `_error_result`. Only
`claude_agent_sdk.query` is mocked; the messages it
yields are real `claude_agent_sdk.AssistantMessage` and
`ResultMessage` dataclasses so the `isinstance()`
checks in `agent_sdk_adapter.collect_agent_output` fire
correctly. No production changes; no sibling PR
needed.

**Reuse signal:** Two consecutive SDK-native cycles
shipped from the same test scaffold with single-pass
renames. The pattern is mature enough to script as a
per-workflow template (e.g. `scripts/scaffold_sdk_workflow_tests.py`
taking module path + subagent list as inputs). Flagged
for the next cycle to consider; not committed.

## workflows/perf_audit.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.606 (weight=4 × gap=0.651 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `bug_predict.py` shipped. Third instance of the
SDK-native shell pattern — same scaffold transferred
verbatim with subagent + method-name renames.
**Outcome:** 1 test file added (`test_perf_audit_execute.py`,
23 tests including 2 for the inline `main()` CLI entry
point). Coverage 34.8% → 96% line+branch. Only line 281
(`if __name__ == "__main__"`) and one falsy-branch in
`main()` remain uncovered. Zero production bugs
surfaced. Three SDK-native shells now through the
program; `refactor_plan` remains.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — sixth module under test-quality-program"

Same body shape as the two prior SDK-native cycles
with one twist: `perf_audit.py` ships an inline
`main()` CLI entry point (lines 259-277) rather than
delegating to a sibling `*_report.py` module. Two
extra tests handle it — one happy path with a patched
`query()` yielding a `ResultMessage`, one error path
with `query()` raising `RuntimeError`. Both go through
`capsys` to assert the printed banner.

**Reuse signal (third consecutive cycle):** the test
scaffold is now demonstrably reusable across all
SDK-native shells. The remaining sibling
(`refactor_plan.py`) should be a one-pass rename. If
the inline-`main()` shape recurs there too, scripting
a generator becomes more clearly justified than
hand-renaming.

## memory/short_term/caching.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.287 (weight=3 × gap=0.508 × risk=1.5)
**Picked because:** Top entry with measured `covered_pct`
after the SDK-native trio shipped today
(`dependency_check`, `bug_predict`, `perf_audit`).
`refactor_plan` was skipped — a parallel session had
two open PRs on it (#267, #270); PR #270 merged
during this cycle and took the "seventh module" slot
in the log, so this entry is the eighth. First non-SDK
pick in today's sequence; tests a pure-Python LRU cache.
**Outcome:** 1 test file added (`test_caching.py`,
28 tests). Coverage 49.2% → 100% line+branch. Zero
production bugs surfaced.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — eighth module under test-quality-program"

Test design diverges from the SDK-native scaffold:
explicit branch coverage for the disabled-mode early
returns in `get` / `add` / `contains`, the LRU
eviction path triggered with a deliberately small
3-entry cache, the `get_stats()` division-by-zero
guard, and counter resets on `clear()`. `time.sleep(0.001)`
between adds ensures `last_access` ordering for the
LRU tests (single-process clock resolution is
sufficient given the dict-stored float timestamps).

**Picking pattern observation (informational):**
SDK-native shells in `workflows/*` cluster around the
same scaffold and ship in cycles ~5 minutes each. Pure
data-structure modules in `memory/short_term/*` need
distinct branch-coverage tests but ship just as fast
because they're 100-300 lines of testable surface
each. The rubric's current ordering surfaces these
two clusters intermixed, which is fine — but a
future refinement could tag rows by archetype
(`sdk-shell`, `data-structure`, `cli-entry`,
`async-pipeline`) so picks can be batched by scaffold.
Flagged; not committed.

## workflows/doc_audit/workflow.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.274 (weight=4 × gap=0.569 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `memory/short_term/caching.py` shipped. Fifth
SDK-native shell — the scaffold from PR #265 continues
to transfer verbatim.
**Outcome:** 1 test file added (`test_workflow_execute.py`,
21 tests). Coverage 43.1% → 100% line+branch. Zero
production bugs surfaced. Five SDK-native shells now
through the program.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — ninth module under test-quality-program"

Same body shape as the four prior SDK-native cycles.
Three subagents (`staleness-checker`, `accuracy-reviewer`,
`gap-finder`). The only adaptations needed were the
import path (workflow lives under `doc_audit/`
subdirectory, so test import is
`from attune.workflows.doc_audit.workflow import DocAuditWorkflow`),
patch paths (`attune.workflows.doc_audit.workflow.claude_agent_sdk.query`),
subagent name strings, and the system-prompt
substring check.

**Generator-script ROI threshold:** Five consecutive
cycles from the same scaffold. Per-cycle cost is now
~5 min (test file generation + verification +
docs/CHANGELOG/decisions updates), so a generator
script's payoff is one cycle of work for ~5 modules
of automation. `document_gen/workflow.py` is the next
obvious SDK-native sibling on the rubric — if it
ships under the same scaffold, the generator becomes
a clear win. Still not committed; the cost of writing
the generator (~30 min) is higher than the marginal
savings until there are at least three more
candidates queued.

## workflows/document_gen/workflow.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.143 (weight=4 × gap=0.536 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `doc_audit/workflow.py` shipped. Sixth SDK-native
shell — the test scaffold continues to transfer
verbatim with subagent + method-name renames. Also
the threshold case for the generator-script decision
flagged in the doc_audit cycle.
**Outcome:** 1 test file added (`test_workflow_execute.py`,
24 tests including 3 for `default_context()`). Empty
`__init__.py` added to mirror the `doc_audit/` test
sub-package layout. Coverage 46.4% → 100% line+branch.
Zero production bugs surfaced. Six SDK-native shells
now through the program.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — tenth module under test-quality-program"

Same body shape as the five prior SDK-native cycles
with one twist: `DocumentGenerationWorkflow` exposes
a `default_context()` classmethod that wires up
`PromptService` and `ParsingService` into a
`WorkflowContext` for composition use. Three extra
tests cover it: (a) returns a `WorkflowContext`
instance with both services set, (b) `xml_config`
kwarg is forwarded without raising, (c) `xml_config`
defaults to `None`. Did not introspect the services'
internal state — that's the consumers' contract, not
this workflow's.

**Generator-script decision (deferred):** Six
consecutive SDK-shell cycles makes the case for
codifying the scaffold quite strong. But the next
likely rubric pick (`memory/control_panel.py`,
weight=3, score 2.073, 53.9% covered) is a memory
subsystem, not an SDK shell. Writing the generator
now would optimize for a pattern that's about to
recede from the working set. Re-evaluate if a rubric
refresh surfaces two more SDK shells. Until then, the
~5-min-per-cycle cost of hand-transferring stays
cheaper than the ~30-min generator investment.

## memory/control_panel.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.073 (weight=3 × gap=0.461 × risk=1.5)
**Picked because:** Top non-SDK entry in the rubric
working set after the six SDK-shell cycles drained
the `workflows/*` cluster. Score reflected `covered_pct=53.9`
in the morning csv snapshot.
**Outcome:** 1 test file added (`test_control_panel_error_paths.py`,
7 tests) targeting the remaining 4 error-handling
fallback branches. Coverage **93% → 99%** line+branch.
Rubric staleness surfaced: csv snapshot pre-dated work
landed earlier today that brought existing coverage to
93%, not 53.9%. Zero production bugs surfaced.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — eleventh module under test-quality-program"

**Rubric staleness flagged:** the rubric data is from
this morning, but ~12 cycles have shipped since,
plus a parallel session. Scores >12 hours old should
be re-measured before picking. Cheap operational
fix: re-run `scripts/score_test_quality.py` against
fresh `coverage.xml` between cycles (or at least
once per session). Not committed; next cycle should
either refresh the rubric or pick from a known-fresh
slice.

**Pattern observation:** When existing tests already
cover the happy path well (as here: 4 existing test
files totaling 2,723 lines for a 497-line module),
the right scaffold is NOT a wholesale rewrite — it's
a small targeted file naming the remaining branches
in its docstring and exercising each with focused
patching. This kept the diff to 168 lines and
avoided touching 2.7k lines of correct existing
tests. Worth adding as an explicit branch in the
playbook (design.md §Per-module loop): if existing
coverage ≥85%, write a "fallback-paths" file rather
than starting over.

## cli_commands/help_commands.py

**Date:** 2026-05-12
**Rubric score at pick time:** 4.497 (weight=5 × gap=0.899 × risk=1.0)
**Picked because:** Top measured-coverage entry in a
**fresh** rubric refresh (the morning csv was 12+
cycles stale; refreshed before pick). Weight=5
user-typed entry point at only 10.1% covered — the
biggest gap on the working set.
**Outcome:** 1 production-side fix (added
`python-frontmatter` to `[dev]` extra in
`pyproject.toml`) + 1 test file added
(`test_help_commands_gaps.py`, 15 tests). Coverage
5% (effective 0%) → 100% line+branch.
**Bug Class 3 — silently-skipped tests masquerading
as test coverage.** First real bug surface in 12
cycles.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — twelfth module under test-quality-program"

The 10.1% coverage from the rubric was misleading:
16 tests existed in
`tests/unit/cli_commands/test_help_commands.py` but
all were skipped via `pytest.importorskip("frontmatter")`
in CI environments without `[author]` installed.
`python-frontmatter` is only a transitive dep of
`attune-help` / `attune-author`, which live in
`[author]` (an optional extra not installed in
default CI runs). The fix is one line in pyproject
+ a 2-line lockfile update; afterwards the existing
16 tests run and lift coverage to 73%. The new
15 tests cover the remaining 27% (mostly
`_record_feedback()` which had zero coverage, plus
`cmd_help()` routing branches).

**Lesson added to CLAUDE.md:** when rubric points at
a user-typed entry point with suspiciously low
coverage AND nominal test files exist, grep for
`pytest.importorskip` first. The dep is likely
misclassified (should be in `[dev]`, not just
`[author]`). Fix the gate before adding new tests
or the new tests also silently skip.

**Rubric staleness note (closes the open question
from cycle #11):** the previous cycle flagged a stale
csv; this cycle confirmed the fix is to re-run
`scripts/score_test_quality.py` before each picking
decision. Pre-cycle refresh added ~1 min of overhead
and revealed `cli_commands/help_commands.py` as the
new top pick — a module that didn't appear at all
in the morning csv's top 10. Worth automating in a
session-start hook for future cycles.

## workflows/test_runner.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.649 (weight=3 × gap=0.883 × risk=1.0)
**Picked because:** Top entry in the fresh rubric after
`cli_commands/help_commands.py` shipped (post-#287
merge). The two zero-coverage rows above it
(`workflows/test_lifecycle.py`,
`workflows/test_maintenance_cli.py`, both score 3.0)
were deferred — measured at 0.0% in the csv but the
coverage-omit pattern is ambiguous on whether they
should be measured at all; investigation flagged but
not blocking.
**Outcome:** 1 test file added (`test_test_runner.py`,
24 tests). Coverage 11.7% → 92% line+branch.
Zero production bugs surfaced. Stopped at 92%
because the remaining branches (defusedxml
ImportError fallback + three pytest-output
classifier branches) have marginal-cost > marginal-
value.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — thirteenth module under test-quality-program"

This module presents a different test design than
the prior cycles. Not an SDK shell (no
`claude_agent_sdk.query()`) and not a pure
data-structure (it shells out via `subprocess.run`).
The right scaffold is "external-process tracker":
mock the external boundary (`subprocess.run`,
`get_telemetry_store`) and let the rest run real
— pytest-output parsing, coverage.xml parsing,
dataclass construction, staleness detection from
mtimes.

Three exception paths per public function:
TimeoutExpired, generic Exception, and telemetry
log failure — all caught with best-effort
recovery. The pattern is consistent across the
module's three primary functions; one fixture
shape covers all of them.

**Coverage-omit ambiguity (flagged for follow-up):**
the `*/test_*.py` pattern in pyproject.toml's omit
list should match `workflows/test_runner.py` per
the CLAUDE.md lesson at line ~63, but fresh
coverage.xml does record measurements (11.69%
line-rate observed pre-cycle). Either the lesson
is outdated, the pattern only matches direct
children, or coverage.py instruments but excludes
from certain report paths. Worth a one-cycle dive
to clean up — the rubric's `?` entries from the
morning csv may have been the omit firing, and
the fresh measurements may be a recent
configuration change. Not blocking this cycle.

## workflows/test_runner_helpers.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.125 (weight=3 × gap=0.708 × risk=1.0)
**Picked because:** Top entry in the fresh rubric after
`workflows/test_runner.py` shipped (post-#288 merge).
The two 0%-covered rows above it
(`workflows/test_lifecycle.py`,
`workflows/test_maintenance_cli.py`) are dead code —
flagged for retirement, not coverage.
**Outcome:** 1 test file added
(`test_test_runner_helpers.py`, 26 tests). Coverage
29.2% → 98% line+branch. **Two Bug Class 2 findings
surfaced — neither fixed inline.**
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — fourteenth module under test-quality-program"

**Findings (not fixed in this PR — separate PRs):**

1. `_find_test_file` lines 165-172: dead defensive
   try/except (`ValueError, IndexError`) around code
   that can't raise either. The 2% coverage gap on
   this module IS this dead branch. Will close to
   100% when removed.

2. `workflows/test_lifecycle.py` (535 lines, 0%) and
   `workflows/test_maintenance_cli.py` (590 lines,
   0%) — both orphan modules with zero inbound
   imports outside each other. Already flagged in
   the source as "Removed" in `workflows/__init__.py:328`.
   Top picks on the rubric purely because the score
   formula doesn't penalize dead code.

**Rubric refinement (flagged not committed):** add an
"inbound-import count" column to
`scripts/score_test_quality.py`. Modules with 0
external consumers should auto-flag as retirement
candidates rather than coverage targets. This is the
third cycle in a row where the working-set head
turned out to be unused or silently-skipped — the
rubric needs a usage signal, not just a coverage-gap
signal.


## memory/security/secrets_detector.py

**Date:** 2026-05-14
**Rubric score at pick time:** 1.79 (rubric-reported,
weight=3 × gap=0.40 × risk=1.5)
**Picked because:** Cleanest non-collision pick from the
fresh rubric. The top entries by score were either new
in-flight modules from concurrent sessions
(`ops/routes/runs_history.py`, `discovery_sweep/*`) or
known retirement candidates (`workflows/test_lifecycle.py`,
`test_maintenance_cli.py`). secrets_detector was an
established, data-handling-risk module with no recent PR
activity touching it.
**Outcome:** 1 test file added
(`tests/security/test_secrets_detector_edge_paths.py`, 9
tests). Coverage 90.96% → 100.00% line+branch. **Zero
production bugs surfaced.**

**Meta-finding (logged in COVERAGE_BUG_LOG.md):** the
rubric reported 60.3% coverage but actual was 90.96%
because the rubric input `coverage.xml` was generated
with `pytest tests/unit/` only — `tests/security/` was
outside scope. The "focused fallback-paths" pattern
applied (existing surface had 28 tests covering the
real-content matching paths; the gap was 4 specific
defensive edges):
- `_create_context_snippet` line-number bounds + long-line
  truncation (both left-edge and right-edge cases,
  including the asymmetric `end < len(line)` where end
  is bounded by len(redacted_line))
- `_calculate_entropy` empty-string fast path
- `_filter_overlapping_detections` different-line
  continue branch

**Rubric refinement:** the next rubric refresh should
use `pytest tests/` (not `tests/unit/`) to avoid
falsely-low coverage scores for modules tested under
`tests/security/`, `tests/integration/`, etc. Easy to
miss — leads to picking modules that are already well
covered.

**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-14 — sixteenth module under test-quality-program"


## memory/short_term/queues.py

**Date:** 2026-05-14
**Rubric score at pick time:** 1.71 (weight=3 × gap=0.38 × risk=1.5)
**Picked because:** Top viable pick from the corrected-scope
rubric refresh (post-PR #348). Tied at 1.71 with
`workflows/release_prep.py` but lower active-development
collision risk — `workflows/` had concurrent discovery-sweep
work in flight; `memory/short_term/` was quiet. No existing
dedicated test file; the 62.1% reported coverage came from
sibling tests indirectly hitting mock-mode paths.
**Outcome:** 1 test file added (`test_queues.py`, 24 tests).
Coverage 62.1% → 100.00% line + branch. **Zero production
bugs surfaced.** First explicit coverage of the real-Redis
branches (push/pop/length/peek) via real BaseOperations +
MagicMock client.

**Implementation note logged in COVERAGE_BUG_LOG.md:**
`BaseOperations(use_mock=False)` auto-flips to True when Redis
auto-detect fails. Tests needing real-Redis branches against a
fake client must force `base.use_mock = False` post-init.
Documented in the fixture docstrings for future readers.

**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-14 — seventeenth module under test-quality-program"


## workflows/release_prep.py

**Date:** 2026-05-16
**Rubric score at pick time:** 1.71 (weight=3 × gap=0.569 × risk=1.0)
**Picked because:** Top viable pick (excluding `?` coverage-omit
artifacts) from the 2026-05-14 rubric cache. Deferred two days ago
in favor of `memory/short_term/queues.py` due to "active development
collision risk" with discovery-sweep work — that work shipped (#411)
and `workflows/release_prep.py` is now quiet. SDK-shell archetype:
6 existing tests covered only class attributes; `execute()` and
`_run_agent_prep()` had zero behavioral coverage. The reusable test
scaffold pattern from CLAUDE.md ("SDK-native workflow shell scaffold
is reusable across 6+ siblings — single-pass rename") applied
cleanly; release-prep is the first 4-subagent variant in the family
(siblings have 2 or 3).
**Outcome:** 1 test file added
(`tests/unit/workflows/test_release_prep_execute.py`, 22 tests).
Coverage 43.1% → **100.00%** line + branch (52/52 statements,
6/6 branches). **Zero production bugs surfaced.**

**Pattern notes for future SDK-shell cycles:**
- The 4-subagent count was the only meaningful adaptation from the
  3-subagent sibling templates — system prompt + subagent set + the
  `test_passes_subagent_definitions` assertion. Everything else
  (depth mapping, exception handling, _error_result shape, real-SDK
  message fixtures) carried over verbatim.
- Stage name in `_error_result` returns `self.name` =
  `"release-prep"` (the workflow's external name), not the internal
  stage list value `"agent-prep"`. Test asserts on `"release-prep"`.

**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-16 — eighteenth module under test-quality-program"


## models/auth_strategy.py

**Date:** 2026-06-12
**Rubric score at pick time:** n/a — picked via **mutation testing**,
not the coverage rubric. The module already had high line coverage
(the `*_coverage_boost.py` suite); mutation testing exposed that the
coverage was padded.
**Picked because:** QA #2 phase 2 mutation-hardened the
`get_recommended_mode` spend-routing slice ([PR #793]), and a
clean-cache `mutmut==2.4.4` pass over the whole module surfaced
**128 / 270 survivors (~53%)** — a coverage-padded suite confirmed
with a hard number, exactly the handoff hypothesis.
**Outcome:** This module does **not** fit the one-module-one-PR loop.
Designated as a **sequenced multi-session behavioral rewrite** with
its own plan: [auth-strategy-mutation-rewrite.md]. `get_recommended_mode`
is already done (mutants 38–43 all killed, verified by apply/revert);
the remaining survivors are split into six per-function sub-slices
(serialization, cost estimation, pros/cons, persistence I/O,
interactive setup, utilities), each a future PR. No further code this
session for this module — the decision is to spec, not execute.

**Decision rationale (why spec, not slice-by-slice now):** carving the
serialization sub-slice this session was on the table, but the "20
remaining survivors" framing that motivated it was a **stale
incremental-cache artifact** from interrupted mutmut runs. The honest
clean-cache number (128) reframes the module as a rewrite, not a
hardening — so sequencing it as a plan beats peeling one slice under a
wrong premise.

**PR:** _(plan only — no code PR this session)_
**Bug log entry:** _(none yet — no production bug surfaced; mutation
gaps are test-quality, logged in the plan not the bug log)_

[PR #793]: https://github.com/Smart-AI-Memory/attune-ai/pull/793
[auth-strategy-mutation-rewrite.md]: ./auth-strategy-mutation-rewrite.md

---

## workflows/test_maintenance_cli.py + test_lifecycle.py — deleted (QA #6)

**Date:** 2026-06-14

The two orphan modules flagged in Phase 4 (tasks.md — "zero inbound
imports; source-marked 'Removed'") and deferred at the `test_runner.py`
pick ("ambiguous whether they should be measured at all; not
blocking") are now **deleted**, resolving that open ambiguity.

QA #6 began with a full-suite coverage baseline of `attune.workflows`
(90%). The two largest "gaps" were these modules at 0%
(`test_maintenance_cli.py` 590 lines / 317 missed, `test_lifecycle.py`
535 lines / 207 missed). Liveness triage confirmed they are dead:
zero inbound imports (`test_maintenance_cli` is imported by nothing;
`test_lifecycle` only by the dead CLI), never wired to the `attune`
entry point (`cli_minimal:main` only), no test files, and the only
`python -m …test_maintenance_cli` references are in their own
docstrings. The live `test-maintenance` *feature* runs via the
meta-workflow template (`TestMaintenanceWorkflow` in
`test_maintenance.py`, 67% — a genuine QA target kept). **Decision:
delete dead code rather than write tests for code nothing calls** (per
the "0% module is often dead code — grep inbound imports before
testing" lesson). Import + full collect (2606 tests) verified green
post-deletion.

---

## workflows/research_synthesis.py — 78%→100% (QA #6)

**Date:** 2026-06-14
**Rubric score at pick time:** top remaining real gap in
`attune.workflows` after the test_maintenance deletions (78%, 13
missed full-suite; 44% measured alone with only the attribute test).
**Picked because:** SDK-native workflow with an uncovered `execute()`
body and SDK query loop; clean scaffold available
(`test_dependency_check_execute.py`).
**Outcome:** Net-new `test_research_synthesis_execute.py` (32 tests).
Mocks only `claude_agent_sdk.query`, yielding **real**
`AssistantMessage`/`ResultMessage` instances so isinstance-based
collectors in `agent_sdk_adapter` fire (duck-typed fakes fail
silently). Covers path validation, depth→max_turns mapping, the
query loop (assistant+result / result-only / empty-stream), and all
three exception paths (`ImportError`, `Connection`/`Timeout`, generic
typed-error fallback). Module measured alone: **100%**. No production
bug found.
**PR:** https://github.com/Smart-AI-Memory/attune-ai/pull/892
**Bug log entry:** none

---

## workflows/coordination_mixin.py — 79%→97% (QA #6)

**Date:** 2026-06-14
**Rubric score at pick time:** second remaining real gap in
`attune.workflows` (79%, 22 missed). `progress_server.py` (0%) is in
the coverage `omit` list — not a real gap.
**Picked because:** `_get_adaptive_router` lazy-init body and the
three signal-method exception paths were untested by the existing
`test_workflow_coordination.py`.
**Outcome:** Net-new `test_coordination_mixin_coverage.py` (12 tests).
Covers `_get_adaptive_router` (successful init, telemetry-unavailable
disable, `ImportError` disable, cached short-circuit) plus the
exception swallow paths of `send_signal`/`wait_for_signal`/
`check_signal`. Lines 35-37 (module-level `ImportError` telemetry
guard) are unreachable when `attune.telemetry` imports cleanly, so
**97%** is the ceiling (predicted ~92%, beat it). No production bug
found.
**PR:** https://github.com/Smart-AI-Memory/attune-ai/pull/893
**Bug log entry:** none

---

## agents/release/base_agent.py — 70%→100% (QA #6, package #2)

**Date:** 2026-06-14
**Package ratification:** After `attune.workflows` finished, baselined
`agents` (82%), `meta_workflows` (83%), `telemetry` (93%). Telemetry is
effectively done. **The apparent big gaps were mostly illusory** — the
baseline runs `--cov-config=/dev/null`, so omitted modules show their
real (low) numbers. Confirmed against `pyproject.toml` `omit`:
- `meta_workflows/cli_commands/{template,config,memory,agent,analytics}_commands.py`
  — all OMITTED ("Interactive…/requires live Claude agent loop"). The
  129/87/76/51-missed "gaps" are not real.
- `agents/release/{release_parsing,release_prep_team,release_models}.py`
  — all OMITTED (LLM/model code).
The one **real** sub-80% module across all three packages was
`agents/release/base_agent.py` (70%, not omitted, 6 inbound importers,
existing test file). Picked it; `agents` is then effectively done too.
**Rubric note:** when the baseline shows a cluster of low-coverage
modules, cross-check the `omit` list FIRST — omitted modules are not
gaps, and a package's "real" gap can be a single module.
**Outcome:** Net-new `test_base_agent_coverage.py` (10 tests) extending
the existing 25. Covers LLM client init (key present/absent), the Redis
exception swallows in `_register_heartbeat`/`_signal_completion`, the
`_signal_completion` scalar-only-summary publish, and `_call_llm` with a
live client (success+cost tracking, empty content, no-`.text` block,
exception fallback). All externals mocked (anthropic SDK patched —
keyless-safe). Module measured alone: **100%**. No production bug found.
**PR:** https://github.com/Smart-AI-Memory/attune-ai/pull/896
**Bug log entry:** none

---

## Omit-list audit + conversions (QA #6, 2026-06-14)

**Audit:** `docs/specs/test-quality-program/omit-audit.md` (PR #900).
Probed every `omit` entry whose comment claimed a testability barrier:
nearly all import cleanly **keyless** — the LLM/Redis/server dep is
call-time (mockable), not import-time. The `omit` comments described
"why a naive test would hit the network," not a real barrier; several
were mislabeled and two were stale.

**Conversions shipped (each: remove `omit` line + net-new test, all
out-of-class so human/admin-merged):**

- `agents/release/release_models.py` — was "Requires LLM API calls",
  actually Enums + dataclasses + console formatting. **77→96%**
  (#901, merged). Remaining 4 lines = redis/anthropic import guards.
- `agents/release/release_parsing.py` — pure multi-strategy parser.
  **→100%** (#904, admin-merged).
- `agents/release/release_agents.py` — re-export shim. **→100%**
  (#904).
- `cache/hybrid.py` — **stale** omit (src/attune/cache/ deleted);
  pattern removed (#904).

**Deferred — `cross_session.py` stale-glob:** the audit flagged
`*/memory/cross_session.py` as mismatching the real path
`memory/short_term/cross_session.py`. Verification was inconclusive
(multiple cross_session test files target a different module), so the
removal was held out of #904 — needs a full-suite coverage check
before touching, not a blind removal.

**Tier-2 backlog (mislabeled/wrongly-omitted, real mocking effort —
ranked, each its own out-of-class PR):**

1. `memory/claude_memory.py` (309) — dataclasses + Claude at call time;
   mock the client (cf. research_synthesis scaffold).
2. `monitoring/otel_backend.py` (268) — mock the otel SDK.
3. `orchestration/_strategies/base.py` (203) + `execution_strategies.py`
   (109) — inject mock agents.
4. `core_modules/short_term_memory.py` (222) — mock redis.
5. `meta_workflows/cli_commands/{memory,analytics,agent,template,config}_commands.py`
   — cf. existing `tests/unit/cli_commands` patterns (mock stdin/Prompt).

**Tier-3 (more harness effort):** `models/auth_cli.py`,
`monitoring/alerts_cli.py`, `core_modules/interaction.py` (interactive
`input()`), `memory/control_panel_api.py` (FastAPI `TestClient`),
`memory/short_term/sessions.py`, `socratic/collaboration*.py` (verify
not deprecated first).

**Hygiene follow-up:** `omit` comments should state the *real* reason;
consider a check that flags `omit` entries whose files import cleanly
keyless (the mislabel that let this debt accumulate). Tracked in
omit-audit.md §Recommendations.

## Tier-2 #1 resolved — claude_memory was an omit-mask illusion (2026-07-21, #1569)

The backlog entry read "memory/claude_memory.py (309) — mock the
client". Reality (QA#6 pattern — cross-check `omit` first): the module
is pure file I/O, its 57-test suite in `tests/memory/` runs keyless in
0.24s, and it already measured **96%**; the `omit` label "Requires
Claude API" was false. The 309-missed number was the omit mask, not a
gap. Close-out: one net-new behavioral file
(`test_claude_memory_standard_path.py` — the `/etc/claude/CLAUDE.md`
fallthrough branch, precedence + negative cases), omit entry removed
with a dated tombstone comment. Module now **100.00%** under the repo
exclude rules. No client mocking was ever needed — Tier-2 rank 1 cost
~an hour, not the estimated mocking effort. Next Tier-2 pick:
`monitoring/otel_backend.py`.

## Candidate policy — lane yield weighting + a 90% routine cap (2026-07-30, UNRULED)

**Status: chair decision candidate, captured at Patrick's request —
not a ruling. Nothing changes until ruled.**

Evidence from the 2026-07-30 modules-needing-work session (#1788,
#1791–#1796): ~260 new tests across 14 modules produced ONE real
production bug (the `attune.ops` Config-shadowing find — from the
cheapest lane, the Tier 3 shims, not the big clusters). That is ~7%
of modules vs the program's historical ~22% bug-find rate — and the
delta is consistent with D14's freshness thesis
(feature-lead-governance): settled, mock-heavy modules yield less
per test than recently-churned code.

**Candidate (two parts):**

1. **Pick-order weighting** — `scripts/modules_needing_work.py`
   ranks lane candidates by miss-volume alone; add bug-find
   likelihood signals (recent churn via `git log --since`, module
   age, seam density) so lanes chase yield, not just coverage
   points.
2. **A ~90% routine-lane cap** — stop routine lanes at ~90% instead
   of 100%; the last ten points are mostly error-path theater on
   settled code.

**Counter-case (carried per COUNTER-CASE discipline):**
coverage-as-floor is a RATCHET, and ratchets work because they are
not negotiated per-module. A cap invites lane-by-lane drift and
weakens the "modules at 100%" accounting that the bug log's
find-rate denominator depends on. If adopted, the cap must be a
deliberate ruled policy with a bright line (e.g. "routine lanes
target 90%; 100% remains the bar for modules touched by a bug fix"),
never an ad-hoc stopping point. Also: tonight's 7% is one session's
n=14 — a chair may reasonably want one more session of data first.
