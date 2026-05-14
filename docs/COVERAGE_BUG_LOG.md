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

## 2026-05-14 — sixteenth module under test-quality-program (Opus 4.7)

Sixteenth module run, first after returning from a multi-day
gap. Selected via fresh rubric scoring:
`memory/security/secrets_detector.py`, weight 3, score 1.79
(rubric-reported 60.3% covered, actual 90.96% — see meta-finding
below). **Zero production bugs surfaced.**

- `memory/security/secrets_detector.py` — no bugs. Module's 28
  existing tests (`tests/security/test_secrets_detector.py`)
  already cover the real-content pattern-matching surface
  well. The remaining 4 spots were defensive edge cases:
  - `_create_context_snippet` invalid-line-number guard
  - `_create_context_snippet` long-line truncation (both
    left-edge and right-edge ellipsis branches, including the
    asymmetric `end < len(line)` comparison where end is
    bounded by `len(redacted_line)`)
  - `_calculate_entropy` empty-string `return 0.0` fast path
  - `_filter_overlapping_detections` different-line continue
    branch (loop skip when entropy and pattern detections sit
    on different lines)

**Coverage delta:** 90.96% → 100.00% (line + branch).

**Tests:** 9 added under
`tests/security/test_secrets_detector_edge_paths.py`. Per the
"focused fallback-paths" pattern from the test-quality-program
CLAUDE.md lesson — left the existing 435-line test file
untouched. Determinism verified across 3 back-to-back runs and
under `-n auto` alongside the full `tests/security/` subtree
(321 passed in 10.37s, no cross-test interference).

### Meta-finding: rubric input must include ALL test dirs

The rubric reported `secrets_detector.py` at 60.3% but the
actual coverage from `tests/security/test_secrets_detector.py`
running alone was 90.96%. Root cause: the rubric input
`coverage.xml` was generated with `pytest tests/unit/` only,
omitting `tests/security/`, `tests/integration/`, and other
non-unit subdirs. Any module whose primary tests live outside
`tests/unit/` shows up with spuriously low coverage in
`rubric_cache.csv`.

**Fix for next rubric refresh:** run coverage against `tests/`
(not `tests/unit/`) to capture all test paths. The default
`testpaths = ["tests"]` in `pyproject.toml` is already correct
for full collection; only the rubric-input command needs the
path widening.

---

## 2026-05-13 — fifteenth module under test-quality-program (Opus 4.7)

Fifteenth module run. Selected via the rubric's
top non-stale viable pick: `memory/short_term/transactions.py`,
weight 3, score 1.992, **55.7% covered → 96.30%**. **Zero bugs
surfaced.** Module is small (61 stmts / 20 branches), single
public method (`atomic_promote_pattern`), with clean mock/real
branching and explicit validation guards.

Highlights of the new test surface
(`tests/unit/memory/short_term/test_transactions.py`, 17 tests):

- Validation guards (empty pattern_id, out-of-range
  min_confidence) → `ValueError` with expected messages.
- Authorization gate (observer/contributor rejected;
  steward accepted) tested via real `AgentCredentials` +
  `AccessTier` instances.
- Mock-mode branches: not-found, expired-via-mock-timestamp,
  confidence-below-threshold (storage preserved), and
  successful promotion (storage deleted + cache invalidated).
- Real-Redis branches via the documented
  `base._client = MagicMock()` injection pattern: `client=None`,
  pattern-not-found, below-threshold, successful pipeline
  delete + cache invalidation, `redis.WatchError` race handler,
  and the best-effort `unwatch()` exception in `finally`.

Remaining 3 uncovered lines:
- Line 39 (`redis = None`) — unreachable fallback when `redis`
  is not installed.
- Lines 189-190 (`redis.WatchError` handler) — handler is
  exercised by a passing test, but coverage instrumentation
  doesn't credit it under the local non-xdist coverage run on
  this interpreter. PyO3 binding init-once quirk; xdist run
  shows green.

Lesson reinforced: when a test needs to raise a class from an
optional dep (`redis.WatchError`), reference it via the
already-imported source module (`_transactions_mod.redis.WatchError`)
rather than importing the optional dep again at test-module
top. This sidesteps the
"PyO3 modules compiled for CPython 3.8 or older may only be
initialized once" error path on macOS/Python 3.10.

---

## 2026-05-12 — fourteenth module under test-quality-program (Opus 4.7)

Fourteenth module run. Selected via the fresh
rubric: `workflows/test_runner_helpers.py`, weight 3,
score 2.125, **29.2% covered**. **Two Bug Class 2
findings — neither fixed inline.**

- `workflows/test_runner_helpers.py` (pytest output
  parsing + coverage XML analysis + test discovery)
  — primarily pure functions. Three helpers
  (`_get_previous_coverage`, `_log_file_test`) touch
  the telemetry store, mocked. `_find_test_file`
  walks the real filesystem in `tmp_path` via
  `monkeypatch.chdir`.

**Bug Class 2 #1 (this module):** `_find_test_file`
at lines 165-172 has a `try/except (ValueError,
IndexError): pass` block guarding
`source_path.parts.index("src")` and
`source_path.parts[src_idx + 1 : -1]`. The
surrounding `if "src" in source_path.parts:` guard
makes the `ValueError` impossible (we already
confirmed "src" is in parts). The slice operation
`parts[a:b]` never raises `IndexError` in Python.
Dead defensive code. The right fix is to drop the
try/except — not write a test for an unreachable
branch. Flagged for a sibling cleanup PR.

**Bug Class 2 #2 (related modules — skipped this
cycle):** `workflows/test_lifecycle.py` (535 lines,
0% covered) and `workflows/test_maintenance_cli.py`
(590 lines, 0% covered) are dead code.
`workflows/__init__.py:328` says "test-maintenance:
Removed — utility class, not a BaseWorkflow."
Neither module is imported anywhere outside its
sibling. Score 3.0 each on the rubric makes them
top picks, but writing tests for unused code is
exactly the trap the bug-log preamble warns
against. Flagged for a retirement PR similar to
`scaffolding` / `orchestrated_release_prep`
(referenced in tasks.md §Out-of-scope follow-ups).

**Coverage delta:** 29.2% → 98% line+branch on
`workflows/test_runner_helpers.py`. The 2% gap is
the dead-code try/except branch (line 171-172)
documented above. Will close to 100% when the dead
code is removed.

**Tests:** 26 added under
`tests/unit/workflows/test_test_runner_helpers.py`:
- `_parse_pytest_output` (5 tests including
  all-passing, mixed, errors, no-summary,
  unparseable)
- `_parse_pytest_failures` (4 tests including
  malformed FAILED lines + 10-entry cap)
- `_get_previous_coverage` (4 tests — 2-or-more
  records, single, empty, store-exception)
- `_analyze_coverage_files` (5 tests covering
  well-covered/critical/untested/mid-coverage
  thresholds + 10-entry caps)
- `_find_test_file` (6 tests — __init__ skip,
  module dir match, standard dir match, rglob
  fallback, no-match, no-tests-dir)
- `_log_file_test` (2 tests — happy + store
  exception)

**Pattern observation (informational):** This is
the second consecutive cycle where the rubric's
top measured-coverage picks were either dead code
or already well-covered (existing 16 silent-skip
tests in #287, dead defensive branches here). The
working-set picks are getting harder to
distinguish from "modules nobody actually uses."
A useful rubric refinement would tag modules by
**inbound-import count** — anything with zero
external consumers should drop off the working
set or get a retirement flag rather than a "low
coverage" flag. Not committing the change here;
flagged for a future rubric script update.

---

## 2026-05-12 — thirteenth module under test-quality-program (Opus 4.7)

Thirteenth module run. Selected via the fresh
rubric: `workflows/test_runner.py`, weight 3, score
2.649, **11.7% covered**. **0 production bugs
surfaced.**

- `workflows/test_runner.py` (Tier 1 telemetry
  wrappers) — no bugs. The module exposes three
  primary functions:
  - `run_tests_with_tracking()` — runs pytest via
    subprocess, parses output for pass/fail/skip
    counts, logs to `TelemetryStore`.
  - `track_coverage()` — parses `coverage.xml`,
    computes trend (improving/declining/stable) vs
    previous, logs to store.
  - `track_file_tests()` — runs per-file pytest,
    classifies the result, detects staleness when
    source mtime > test mtime.
  Plus two thin wrappers (`get_file_test_status`,
  `get_files_needing_tests`) that delegate to the
  store.

  All four exception paths (TimeoutExpired in main
  runner, generic Exception in main runner, same
  pair in `track_file_tests`) recover to a
  best-effort error record without crashing.
  Telemetry log failures are also caught with
  warnings, never propagated — a deliberate design
  choice given Tier 1 tracking is opt-in.

**Coverage delta:** 11.7% → 92% line+branch.

**Tests:** 24 added under
`tests/unit/workflows/test_test_runner.py`. Mocks
only `subprocess.run` (would actually run pytest)
and `get_telemetry_store` (would write to
`~/.attune/telemetry/...`); pytest-output parsing,
coverage.xml parsing (via `xml.etree` /
`defusedxml`), and `FileTestRecord` construction
use real implementations.

**Remaining 8%:** the `defusedxml` ImportError
fallback (line 19-20) which would require
selectively breaking defusedxml import (cross-test
contamination risk per CLAUDE.md lesson), plus
three classifier branches at lines 342-347
(`errors > 0` / `skipped == total` / final else)
that need precisely-shaped pytest output to
trigger. Stopping at 92% — marginal cost exceeds
marginal value for these specific branches.

**Coverage-omit note (informational):** the
`workflows/test_runner.py` filename starts with
`test_` which the `*/test_*.py` omit pattern in
pyproject.toml's `[tool.coverage.run]` config
should match — but the fresh `coverage.xml` does
record measurements for the file (line-rate
0.1169). The omit appears to NOT match nested
paths the way the lesson at the top of CLAUDE.md
suggests. Either the lesson is outdated, the
pattern matches only direct children, or coverage
.py instruments the file but then excludes it from
some other report path. Worth a follow-up
investigation but not blocking this cycle.

---

## 2026-05-12 — twelfth module under test-quality-program (Opus 4.7)

Twelfth module run. First cycle this session that
surfaced a real production bug — and notably, it's
exactly **Bug Class 3** from the log preamble:
"Tests that mocked around the bug — tests pass
because they mock the broken caller; coverage at
100% looks fine, production code is wrong."

Selected via a **fresh** rubric refresh (the morning
csv was stale by ~12 cycles): top measured-coverage
pick was `cli_commands/help_commands.py`, weight 5,
score 4.497, **10.1% covered**. Closer inspection
revealed the 10% was misleading: 16 tests existed in
`tests/unit/cli_commands/test_help_commands.py` but
all were silently skipped via
`pytest.importorskip("frontmatter")` because
`python-frontmatter` is only a transitive dep of
`attune-help`/`attune-author` (in the `[author]`
extra, NOT in `[dev]`).

**Bug Class 3 — variant: silently-skipped tests
masquerading as test coverage.** The 16 tests were
written, reviewed, and merged, but never ran in CI.
The `importorskip` guard was defensive (the module
references `attune.help.engine.populate` which uses
`frontmatter` internally), but the dep wasn't in any
extra that CI installed. Net effect: a weight-5 CLI
entry point shipped with effective 0% test coverage
despite appearing to have 16 tests.

**Fix (inline, sibling change):** added
`python-frontmatter>=1.0.0,<2.0.0` to the `[dev]`
extra in `pyproject.toml` with an inline comment
documenting why. `uv lock` confirmed clean 2-line
update to `uv.lock`. With the dep installed, the 16
existing tests run and lift coverage 5% → 73%.

**New tests (this PR):** 15 added under
`tests/unit/cli_commands/test_help_commands_gaps.py`
covering the remaining ~27%:
- `_get_generated_dir()` path resolution
- `_list_categories()` missing-category-dir +
  no-cross-links branches
- `_list_category()` empty-files branch
- `_show_template()` prefixed-name-not-found branch
- `_list_all_tags()` empty-tags branch
- `_record_feedback()` invalid-rating + happy +
  prefix-resolution branches (entire function had
  zero coverage)
- `cmd_help()` --feedback routing + missing-topic
  branch
- `cmd_help()` --deep / --detail verbosity branches

Patches use the source-module pattern (e.g.
`patch("attune.help.engine.list_tags", ...)`) per
CLAUDE.md lesson on lazy-imported names not being
patchable at the consuming module.

**Coverage delta:** 5% (effective 0%) → 100%
line+branch.

**Lesson captured separately in CLAUDE.md:** when
the rubric points at a "user-typed entry point" with
suspiciously low coverage AND nominal test files
exist, grep for `pytest.importorskip` in those test
files first. If a test file gates the entire module
on an `importorskip`, the dep is either misclassified
(should be in `[dev]`) or the tests are
defensive-only and never run in CI. Either way:
fix the gate before adding new tests, otherwise the
new tests also silently skip.

---

## 2026-05-12 — eleventh module under test-quality-program (Opus 4.7)

Eleventh module run. Second non-SDK pick after the
six SDK-native cycles. Selected via the rubric:
`memory/control_panel.py`, score 2.073. **0 production
bugs surfaced.**

**Rubric staleness flagged:** rubric_cache.csv from
2026-05-12 morning reported `covered_pct=53.9` for
this module, but at session time the existing
`tests/memory/test_control_panel.py` (851 lines),
`tests/memory/test_control_panel_security.py` (345),
`tests/unit/memory/test_control_panel.py` (849), and
`tests/unit/memory/test_control_panel_display.py`
(678) — together 2,723 lines of existing tests —
already gave 93% line+branch coverage. The csv
snapshot pre-dates work that landed earlier today.
Rubric refresh needed before the next cycle to avoid
re-picking already-saturated modules.

**Remaining 7% (this PR's target):** four
error-handling fallback branches:

- `get_statistics()` storage_bytes `Exception` →
  fallback to 0 (lines 229-231). Exercised by patching
  `Path.glob` to raise `OSError`.
- `get_statistics()` long-term `get_statistics()`
  `Exception` → log warning, leave counts at dataclass
  defaults (241-242). Exercised by patching
  `_get_long_term` to return a fake that raises.
- `health_check()` long-term unavailable branch
  (415-419). Exercised by pointing `storage_dir` at a
  nonexistent path.
- `_count_patterns()` `OSError`/`PermissionError`
  handler (491-493). Exercised by patching
  `Path.glob`.

**Coverage delta:** 93% → 99% line+branch. Only line
497 (`if __name__ == "__main__": main()`) remains
uncovered.

**Tests:** 7 added under
`tests/unit/memory/test_control_panel_error_paths.py`.
Uses `tmp_path` for real filesystem isolation;
patches `Path.glob` / `_get_long_term` at strategic
points to surface the fallback branches without
mocking the whole subsystem.

**Pattern observation:** When existing test files
already cover the happy path well, the right move is
a small targeted file that exercises the remaining
error-handling branches by name (commented line
references in the docstring). Cheaper than rewriting
the existing tests, keeps the diff focused.

---

## 2026-05-12 — tenth module under test-quality-program (Opus 4.7)

Tenth module run. Sixth Agent SDK-native workflow
through the program — `document_gen/workflow.py`.
Same shell pattern as the five prior SDK cycles
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`, `doc_audit`). One small divergence:
this workflow exposes a `default_context()` classmethod
for `WorkflowContext` composition (wires up
`PromptService` + `ParsingService`); three extra tests
cover it. **0 production bugs surfaced.**

- `workflows/document_gen/workflow.py`
  (`DocumentGenerationWorkflow`) — no bugs. Thin async
  shell around `claude_agent_sdk.query()` with three
  subagents (`outline-planner`, `content-writer`,
  `polish-reviewer`). The `default_context()`
  classmethod is a real composition surface but adds
  no behavior beyond constructing the two services
  with the given `xml_config` kwarg.

**Coverage delta:** 46.4% → 100% line+branch.

**Tests:** 24 added under
`tests/unit/workflows/document_gen/test_workflow_execute.py`
(21 SDK-shell + 3 `default_context()`). Also added
empty `__init__.py` for the new test sub-package to
match the existing `doc_audit/` layout.

**Generator-script ROI threshold crossed (informational):**
Six consecutive cycles from the same scaffold. The
generator script case is now stronger but I'm deferring
because the next likely module on the rubric
(`memory/control_panel.py`, weight 3, score 2.073)
isn't an SDK shell — it's a memory subsystem. Writing
the generator now would optimize for a pattern that's
about to recede from the working set. Re-evaluate if
two more SDK shells surface in a future rubric refresh.

---

## 2026-05-12 — ninth module under test-quality-program (Opus 4.7)

Ninth module run. Fifth Agent SDK-native workflow
through the program — `doc_audit/workflow.py`. Same
shell pattern as the four prior SDK cycles
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`). The scaffold transferred verbatim
with a subagent-name rename. **0 production bugs
surfaced.**

- `workflows/doc_audit/workflow.py` (`DocAuditWorkflow`)
  — no bugs. Thin async shell around
  `claude_agent_sdk.query()` with three
  `AgentDefinition` subagents (`staleness-checker`,
  `accuracy-reviewer`, `gap-finder`). Validates `path`,
  maps depth → max_turns, four-branch exception
  handling (`ImportError` / `ConnectionError` /
  `TimeoutError` / generic). Identical to its sibling
  workflows.

**Coverage delta:** 43.1% → 100% line+branch.

**Tests:** 21 added under
`tests/unit/workflows/doc_audit/test_workflow_execute.py`.
Same real-SDK-dataclass fixtures pattern; only
`claude_agent_sdk.query` mocked.

**Pattern note:** This is the fifth consecutive cycle
from the same scaffold (`dependency_check`,
`bug_predict`, `perf_audit`, `refactor_plan`,
`doc_audit`). The case for a generator script
(`scripts/scaffold_sdk_workflow_tests.py` taking
module path + subagent list as inputs) is increasingly
strong but still flagged-not-committed — each cycle
takes ~5 min by hand, so the script's payoff threshold
hasn't been crossed for one-off uses. If
`workflows/document_gen/workflow.py` (next obvious
sibling on the rubric) follows the same shape, the
script becomes a clear win.

---

## 2026-05-12 — eighth module under test-quality-program (Opus 4.7)

Eighth module run. First non-SDK cycle in today's
sequence after four consecutive Agent SDK shells
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`). Selected via the rubric working set:
`memory/short_term/caching.py`, score 2.287.
**0 production bugs surfaced.**

- `memory/short_term/caching.py` (`CacheManager`) — no
  bugs. The module is a 233-line pure-Python LRU cache
  with TTL fields (timestamps tracked but never expired
  by the cache itself — callers handle TTL semantics).
  Two-tier strategy: local in-memory dict-backed cache
  sitting in front of Redis. The LRU eviction path
  (`min(self._cache, key=lambda k: self._cache[k][2])`)
  fires only when `len(self._cache) >= self.max_size`;
  exercised with a 3-entry cache and a deliberate
  access-order shuffle. Disabled-mode branches in
  `get` / `add` / `contains` all return early. No dead
  code; no crash paths.

**Coverage delta:** 49.2% → 100% line+branch.

**Tests:** 28 added under
`tests/unit/memory/short_term/test_caching.py`. No
mocks needed — pure stdlib `time.sleep(0.001)` between
adds to ensure `last_access` ordering for the LRU
eviction tests. `get_stats()` hit-rate computation
exercised both with traffic (66.67%) and with zero
requests (the `if total > 0 else 0.0` guard).

**Pattern observation:** First module today where the
test design wasn't a single-pass rename. The
SDK-native scaffold doesn't transfer here — pure-Python
state-machine classes need explicit branch coverage
(disabled-mode return-early paths, division-by-zero
guards, LRU ordering invariants). Worth noting for
future rubric picks: SDK-native shells cluster in
`workflows/*`; pure data-structure modules cluster in
`memory/short_term/*`. The test scaffold should fork
along that boundary.

---

## 2026-05-12 — seventh module under test-quality-program (Opus 4.7)

Seventh module run. Fourth (and final) Agent SDK-native
workflow through the program — direct sibling of
`dependency_check.py` (PR #265), `bug_predict.py` (PR #266),
and `perf_audit.py` (PR #273). Pattern transfer test: the
test file was scaffolded by copying
`test_dependency_check_execute.py` and renaming
`DependencyCheck`/`inventory-assessor`/`update-advisor` →
`RefactorPlan`/`debt-scanner`/`impact-analyzer`/`plan-generator`,
adjusting the system prompt substring assertion, and bumping the
subagent count from 2 to 3. Everything else (fixture shape,
real-SDK-message construction, depth-mapping, exception
handling, `_error_result` shape) carried over unchanged.
**0 production bugs surfaced.**

- `workflows/refactor_plan.py` (`RefactorPlanWorkflow`) — no
  bugs. The module is a ~260-line thin async shell around
  `claude_agent_sdk.query()`: validates `path`, maps depth →
  max_turns, defines three `AgentDefinition` subagents
  (`debt-scanner`, `impact-analyzer`, `plan-generator`),
  collects `AssistantMessage` + `ResultMessage` stream output
  via `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`. Same
  four-branch exception conversion as `dependency_check`
  (`ImportError` / `ConnectionError` / `TimeoutError` /
  generic, with `# noqa: BLE001` on the catch-all). No dead
  code, no crash paths.

**Coverage delta:** 44.44% → 100.00% (line + branch).

**Tests:** 21 added under
`tests/unit/workflows/test_refactor_plan_execute.py`. Same
fixture/mocking shape as PRs #265, #266, #273: only
`claude_agent_sdk.query` is patched, with real SDK dataclass
instances (`AssistantMessage`, `ResultMessage`, `TextBlock`)
yielded by the fake generator so isinstance-based collectors
fire correctly. Determinism verified back-to-back and under
the full `tests/unit/workflows/` selection.

**Scaffold completion:** with `refactor_plan.py` shipped, all
four SDK-native sibling workflows
(`dependency_check`/`bug_predict`/`perf_audit`/`refactor_plan`)
have reached 96-100% coverage from the same one-page test
template. Four consecutive cycles with verbatim transfer makes
the case for codifying the scaffold as
`scripts/scaffold_sdk_workflow_tests.py` (flagged in
decisions.md by the perf_audit cycle). Zero production bugs
across all four — the pattern reliably finds nothing because
the modules are pure plumbing.

---

## 2026-05-12 — fifth module under test-quality-program (Opus 4.7)

Fifth module run. Second Agent SDK-native workflow through
the program (sibling pattern to the `dependency_check`
module shipped earlier today). Selected via the rubric
working set: `workflows/bug_predict.py`, score 2.636 —
top entry with measured coverage after the four `?`
coverage-omit artifacts above it. **0 production bugs
surfaced.**

- `workflows/bug_predict.py` (`BugPredictionWorkflow`) —
  no bugs. The module is a ~270-line thin async shell
  around `claude_agent_sdk.query()`: validates `path`,
  maps depth → max_turns, defines three `AgentDefinition`
  subagents (`pattern-scanner`, `risk-correlator`,
  `prevention-advisor`), collects `AssistantMessage` +
  `ResultMessage` stream output via
  `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`.
  Each specific exception type (`ImportError`,
  `ConnectionError`, `TimeoutError`, generic `Exception`)
  is converted to a structured `_error_result`. The
  catch-all `except Exception` is documented intentional
  with `# noqa: BLE001`. No dead code; no crash paths.
  Structurally identical to `dependency_check.py` — the
  test scaffold transferred with a one-pass rename
  (`_run_agent_check` → `_run_agent_predict`, two
  subagents → three, stage name "dependency-check" →
  "bug-predict", task-prompt phrase swap).

**Coverage delta:** 47.3% → 97% (line + branch). The
one uncovered line (271) is the bottom-of-file
`if __name__ == "__main__": main()` guard — standard
untestable boilerplate.

**Tests:** 21 added under
`tests/unit/workflows/test_bug_predict_execute.py`,
matching the shape established by
`test_dependency_check_execute.py`. Only
`claude_agent_sdk.query` is mocked; the
`AssistantMessage`, `ResultMessage`, and `TextBlock`
instances yielded by the fake generator are **real SDK
dataclass instances** (per CLAUDE.md lesson on
duck-typed fakes failing isinstance-based collectors).

**Pattern observation (continues prior session):** the
SDK-native shape is uniform across the four sibling
workflows (`dependency_check`, `bug_predict`, plus
unprocessed `perf_audit`, `refactor_plan`). Each ships
zero production bugs and lifts coverage to 97-100% via
the same test scaffold. After two consecutive cycles
with this pattern (#265 + this PR), it's reusable
enough to script as a per-workflow template; flagged
for consideration but not blocking. Composed data-
handling helpers (memory/security) remain the bug-rich
shape; the SDK-native shells are pure plumbing.

---

## 2026-05-12 — fourth module under test-quality-program (Opus 4.7)

Fourth module run. First Agent SDK-native workflow through
the program. Selected via the rubric working set after
`ops/cli.py` shipped (`workflows/dependency_check.py`,
score 2.685 — top entry with measured coverage data; the
score-4.0/3.0 rows above it are coverage-omit artifacts of
the `*/test_*.py` pattern in `pyproject.toml`, see note
below). **0 production bugs surfaced.**

- `workflows/dependency_check.py`
  (`DependencyCheckWorkflow`) — no bugs. The module is a
  ~230-line thin async shell around
  `claude_agent_sdk.query()`: validates `path`, maps depth
  → max_turns, defines two `AgentDefinition` subagents
  (`inventory-assessor`, `update-advisor`), collects
  `AssistantMessage` + `ResultMessage` stream output via
  `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`.
  Each specific exception type (`ImportError`,
  `ConnectionError`, `TimeoutError`, generic `Exception`)
  is converted to a structured `_error_result`. The
  catch-all `except Exception` is documented intentional
  with `# noqa: BLE001`. No dead code; no crash paths.

**Coverage delta:** 41.67% → 100.00% (line + branch).

**Tests:** 21 added under
`tests/unit/workflows/test_dependency_check_execute.py`.
Only `claude_agent_sdk.query` is mocked (would otherwise
make real API calls); the `AssistantMessage`,
`ResultMessage`, and `TextBlock` instances yielded by the
fake generator are **real SDK dataclass instances**, not
duck-typed `MagicMock`s — per the existing CLAUDE.md
lesson "Duck-typed test fakes fail isinstance-based
collectors silently." Determinism verified across 3
back-to-back runs and under `-n auto` alongside the full
`tests/unit/workflows/` + `tests/workflows/` subtree
(2373 passed, no cross-test interference).

**Rubric note (operational, not a bug):** the rubric's
top 11 rows above `dependency_check` all sit at `?`
covered_pct (scores 4.0 and 3.0 across
`workflows/test_*.py` files and
`workflows/test_gen/test_templates.py`). These are real
production modules but coverage.py never measures them
because the `*/test_*.py` omit pattern in
`pyproject.toml` matches their filenames. The rubric
should filter `?` covered_pct rows out of the
working-set top, or the omit pattern should be tightened
to `tests/test_*.py` so production modules with
"test_" in their name remain measurable. Flagged for a
follow-up rubric refinement; not blocking this cycle's
ship.

**Pattern observation (extends prior session's note):**
the bug-find pattern continues — composed data-handling
helpers (memory/security/query.py) surfaced 1 class-1
crash bug, while customer-facing entry points
(ops/cli.py) and now SDK-native orchestrators
(workflows/dependency_check.py) surface zero. The
SDK-native shape is uniform across `bug_predict`,
`perf_audit`, `refactor_plan` and the test pattern
established here should transfer with minor renames.

---

## 2026-05-12 — third module under test-quality-program (Opus 4.7)

Third module run, first weight-5 (user-typed entry) pick. Selected
via the rubric working set after `memory/short_term/conflicts.py`
shipped (`ops/cli.py`, score 3.19). **0 production bugs surfaced.**

- `ops/cli.py` (`attune ops` entry) — no bugs. Module is a thin
  argparse + uvicorn launcher (151 lines). Two minor style smells
  noted but not fixed in this PR: (a) line 82 imports uvicorn just
  to check availability and line 135 re-imports — redundant but
  cheap due to Python's import cache; (b) line 146
  `parser.parse_args(["ops", *sys.argv[1:]])` could double-inject
  "ops" if a user runs `python -m attune.ops ops --port 8000`,
  but the case is unrealistic. Not in scope.

**Coverage delta:** 36.2% → 100.00% (line + branch).

**Tests:** 19 added under `tests/unit/ops/test_cli.py`. Real
argparse, real `build_config`, real `create_app`. Only `uvicorn.run`
(would block) and `webbrowser.open` (would open real browser)
patched. Determinism verified across 3 back-to-back runs and under
`-n auto` alongside the full ops test subtree (142 passed, no
cross-test interference).

**Pattern observation:** weight-5 modules surfaced no bugs while
weight-3 data-handling modules surfaced 1 in 2 sessions. Early but
suggestive — customer-facing entry points tend to be defensively
written. The bug-hunt yield concentrates in composed helpers, not
in user-typed entry points. Worth re-evaluating after 5+ modules.

---

## 2026-05-12 — second module under test-quality-program (Opus 4.7)

Second module run after the PoC. Selected via the rubric working
set after the first pair shipped (score 3.35, third row at the
time). **0 production bugs surfaced.**

- `memory/short_term/conflicts.py` (`ConflictNegotiation`) —
  no bugs. Every public method validates inputs (empty
  conflict_id → `ValueError`, non-dict positions/interests →
  `TypeError`), gates permissions (CONTRIBUTOR for create,
  VALIDATOR for resolve, any tier for read), and round-trips
  cleanly through `ConflictContext.to_dict/from_dict` with
  documented TTLs. The 41 previously-uncovered lines were
  legitimate uncovered behavior, not hidden defects.

**Coverage delta:** 25.4% → 100.00% (line + branch).

**Tests:** 44 added under
`tests/unit/memory/short_term/test_conflicts.py`. Real
`BaseOperations(use_mock=True)` host (the established
short_term test pattern in `test_short_term.py`) composed
with `ConflictNegotiation`. No mocks of storage — the
mock-mode BaseOperations is a real in-memory store, faithful
to production semantics. Determinism verified across 3
back-to-back runs and under `-n auto` alongside the full
memory test subtree (1411 passed, no cross-test interference).

**Test-reliability note (class 5 nudge, not a bug):** structlog
emits to stdout, not Python's `logging` module. The two
log-event verification tests initially used `caplog`, which
returned empty records. Switched to `capsys` per the existing
CLAUDE.md lesson "structlog default output pollutes
stdout-captured CLI tests." Fixed inline before commit.

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
