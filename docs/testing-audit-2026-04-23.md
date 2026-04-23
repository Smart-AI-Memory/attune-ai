# Testing Audit — attune-ai

**Date:** 2026-04-23
**Branch:** feat/help-aggregator-tests
**Coverage data source:** `coverage.json` from 2026-03-19 (5 weeks old; shapes are stable)
**Analysis method:** Static grep analysis + existing coverage.json parsing

---

## Executive Summary

| Metric | Value |
|---|---|
| Test files | 589 |
| Test count | 1,382+ |
| Overall line coverage | 83.75% |
| pyproject.toml threshold | 85% |
| CI threshold | 83% |
| Skip/xfail tests | ~155 total |
| Entire test files skipped | 3 (107 tests permanently hidden) |
| Redis mocking refactor backlog | 12 tests |
| Unimplemented API tests | 13 tests |
| Assert-free tests (approx) | 255 (many false positives; real count ~80-100) |
| Coverage batch files | 9 (934 tests, mixed quality) |
| MCP server.py coverage measured | **0%** (explicitly omitted) |

---

## 1. Per-Module Coverage Heat Map

Coverage from `coverage.json` (2026-03-19), grouped by top-level package.
Lines = measured statements; excludes omitted files.

### Red ( < 70% )

| Module | Lines | Coverage | Key files at 0% |
|---|---|---|---|
| `wizards` | 898 | **34.0%** | `base.py`, `registry.py`, `config_driven.py`, all `builtin/` wizards |
| `config.py` (root) | 166 | **0.0%** | entire file |

### Amber ( 70–84% )

| Module | Lines | Coverage | Notable sub-files |
|---|---|---|---|
| `workflows` | 13,176 | **78.9%** | 8 workflow sub-files at 0% (see §1a) |
| `patterns` | 835 | 81.1% | — |
| `cache_monitor.py` | 132 | 80.3% | — |
| `redis_config.py` | 92 | 75.0% | — |
| `monitoring` | 458 | 84.1% | — |
| `memory` | 5,572 | **85.0%** | `short_term/conflicts.py` 18%, `short_term/security.py` 32% |

### Green ( ≥ 85% )

Most modules are green. Notably:
- `socratic`: 88.8% on 3,826 measured lines — **but** 25 source files have zero
  test references (they are simply missing from coverage.json because they
  are never imported by tests).
- `mcp`: 90.2% — **misleading**: `server.py` (885 lines) is explicitly omitted.
- `orchestration`: 88.9% on 2,279 lines.

### 1a. Workflows Sub-Files at 0% Coverage

These are production code paths with no test coverage whatsoever:

| File | Stmts | Notes |
|---|---|---|
| `workflows/release_prep_stages.py` | 164 | Release workflow stages |
| `workflows/security_audit_triage.py` | 103 | Security triage logic |
| `workflows/perf_audit_stages_mixin.py` | 110 | Perf audit stages |
| `workflows/code_review_architect.py` | 93 | Architect review step |
| `workflows/code_review_classify.py` | 59 | Classifier mixin |
| `workflows/code_review_crew_mixin.py` | 41 | Crew mixin |
| `workflows/perf_audit_optimize_mixin.py` | 50 | Optimization mixin |
| `workflows/document_gen/chunked_generation.py` | 153 | Doc generation |
| `workflows/dependency_check_report.py` | 118 | 2.1% coverage |
| `workflows/bug_predict_report.py` | 98 | 2.5% coverage |
| `workflows/security_audit_stages.py` | 163 | 7.2% coverage |

**Total unmeasured workflow code:** ~1,156 statements at 0–7%.

---

## 2. Coverage Exclusion Audit

**Total exclusion rules:** 72 `omit` patterns + 8 `exclude_lines` = 80 total.

### Legitimate (keep)

~60 patterns. Correctly exclude:
- Interactive CLIs (`auth_cli.py`, `socratic/cli.py`, `monitoring/alerts_cli.py`)
- Infrastructure servers (FastAPI `control_panel_api.py`, `mcp/server.py`)
- Redis-dependent modules (`memory/cross_session.py`,
  `memory/short_term/sessions.py`)
- LLM-dependent release agents (`agents/release/*.py`)
- Hook scripts (run as standalone processes)
- Wizard examples (`technology_wizard.py`, `customer_support_wizard.py`)

### Questionable (review)

| Pattern | Concern |
|---|---|
| `*/mcp/server.py` | 885 lines of core MCP dispatch logic. Could be unit-tested at handler level — `tests/unit/mcp/` already does this but the file itself is excluded, hiding total exposure |
| `*/project_index/index.py` | 500 lines; comment says "integration-tested" but no integration test exists for it |
| `*/project_index/scanner_parallel.py` | 205 lines; parallel scanner has no tests at all |
| `*/cache/hybrid.py` | Hybrid cache — user-visible feature with no coverage |
| `*/monitoring/otel_backend.py` | 265 lines — could at least be smoke-tested |

### Outdated (delete the entry)

Comment in `pyproject.toml` mentions: "Deleted in v2.9.0: cli/, cli_unified.py,
security/, pattern modules." Those omit entries are dead. Keeping them is
harmless but misleading — they make the exclusion list look larger than it is.

### Threshold Discrepancy

`pyproject.toml` sets `fail_under = 85` but CI runs
`--cov-fail-under=83`. The CI gate is softer than the local gate.
Choose one value and use it in both places.

---

## 3. Skip / Xfail Disposition Table

Total skip/xfail instances: ~155 across ~110 test functions.

### Category A: Correct — Architectural (keep as-is)

| Count | Pattern | Example |
|---|---|---|
| 12 | Requires live Anthropic API key | `agent_factory/test_*.py` |
| 8 | Platform guards (Windows symlinks, `/proc`, `chmod`) | `scanner_security.py`, `config_core.py` |
| ~20 | Optional dep guards (redis, cryptography, tiktoken, yaml) | throughout |
| 1 | mypy removed from CI | `test_workflow_yaml.py:307` |
| 1 | Requires Linux `/proc` | `test_config_store.py:854` |

### Category B: Tech Debt — Needs Refactoring

| Count | Reason | File | Action |
|---|---|---|---|
| 12 | "Redis mocking API changed" | `tests/unit/memory/test_cross_session.py` | Rewrite mocks to use `memory._base._client` pattern (see Lessons) |
| 7 | "Classification not yet implemented" / "Learning loop not implemented" | `test_memory_architecture.py` | Decide: implement or delete |
| 4 | "WorkflowHistoryStore methods not yet implemented" | `test_security_remediation.py` | `save_run`/`get_run` don't exist — decide: implement or delete |
| 4 | Private method mocking too hard | `test_meta_orchestration_architecture.py` | Tests for `_choose_composition_pattern` — test via public API instead |

### Category C: Obsolete — Should Be Deleted

| Count | Reason | File |
|---|---|---|
| 40 | `wizard_factory_cli` module removed | `tests/integration/test_api_endpoints.py` |
| 5 | Tests legacy JSON storage (now SQLite) | `tests/workflows/test_workflow_base.py` |
| 5 | Multi-provider removed in v5.0.0 (Ollama, OpenAI, HYBRID) | `tests/unit/models/test_provider_config_extended.py` |
| 2 | `test_fallback.py`: "Anthropic-only architecture" | `tests/models/test_fallback.py` |

### Category D: Entire Files Permanently Skipped

| File | Tests Hidden | Reason | Action |
|---|---|---|---|
| `tests/integration/test_api_endpoints.py` | 40 | Module removed | **Delete the file** |
| `tests/unit/memory/test_short_term_failures.py` | 24 | Requires live Redis | Correct — add `@pytest.mark.redis` and exclude in CI |
| `tests/unit/memory/test_cross_session.py` | 12 of 43 | Redis mocking API changed | Refactor the 12 skipped tests |

**CI issue:** `tests/integration/test_api_endpoints.py` is still explicitly
listed in CI's "Run new Phase 1 tests" step even though the file is entirely
skipped at module level. The step runs but silently produces 40 skips.

---

## 4. Integration Test Adequacy

### Covered

| Interface | Test location |
|---|---|
| CLI → LLM providers | `tests/integration/test_llm_integration.py` |
| Hooks execution | `tests/integration/test_hooks_integration.py` |
| Context store | `tests/integration/test_context_integration.py` |
| Telemetry | `tests/integration/test_telemetry_integration.py` |
| Meta-workflow E2E | `tests/integration/test_meta_workflow_e2e.py` |
| Full workflow smoke | `tests/integration/test_critical_workflows_smoke.py` |

### Not Covered (gaps)

| Interface | Gap |
|---|---|
| **MCP server ↔ workflow dispatch** | No integration test for `call_tool` → `_dispatch_tool` → workflow path |
| **Memory ↔ Redis** | No test in `tests/integration/` — only in `tests/memory/` (Redis tests skip in CI) |
| **Plugin components ↔ MCP tools** | No end-to-end test that installs plugin and verifies MCP tool names resolve |
| **project_index/index.py** | Claimed "integration-tested" in omit comment; no such test exists |
| **Agent SDK adapter ↔ workflows** | SDK-native workflows are unit-mocked only; no real agent invocation test |

---

## 5. Test Quality Assessment

### 5a. Assert-Free Tests

Automated scan found ~255 tests with no `assert` statement in their body
(detecting false positives: tests that only use `capsys.readouterr()`,
`pytest.raises`, or side-effect checks).

Confirmed true cases (sample of real assert-free tests):
- `test_mcp_memory_tools.py`: several tests that only verify a return code == 0
- `test_coverage_batch7.py`: 3 tests that call CLI handlers but never check output
- `test_meta_orchestrator_interactive.py`: 3 tests calling methods with no
  assertion (pure smoke tests that ensure no exception)

**Verdict:** Pure smoke tests are acceptable when the goal is "does it not
crash", but they should be marked `@pytest.mark.smoke` so they're
distinguishable from behavioral tests.

### 5b. Coverage Batch Files

9 files (`test_coverage_batch1–10.py`) containing 934 tests generated to
boost coverage metrics. Quality is mixed:

| File | Tests | Assert ratio | Mock lines | Quality |
|---|---|---|---|---|
| `batch3.py` | 73 | 3.0 | 183 | Good — real behavioral assertions |
| `batch5.py` | 128 | 2.2 | 31 | OK |
| `batch1.py` | 160 | 2.4 | 85 | OK |
| `batch9.py` | 173 | 1.6 | 135 | Mixed — some assert-free |
| `batch10.py` | 81 | 2.2 | 295 | Mostly CLI output checks via mock |
| `batch7.py` | 165 | 1.6 | 106 | Mixed |
| `batch4.py` | 9 | 1.1 | 0 | Thin |

**Concern:** `batch10` tests CLI output via heavy mocking (295 mock uses).
These measure that code runs without testing what it does behaviorally.

### 5c. Telemetry Tests Reading Real Files

`tests/unit/test_telemetry.py` reads from relative `.attune/costs.json`,
`.attune/health.json`, `.attune/workflow_runs.json` — real files in the
repo root. All tests `pytest.skip` if the file doesn't exist, so in CI
these effectively never run. They provide **zero CI coverage** of the
telemetry module.

---

## 6. MCP Server Testing Completeness

### Handler Coverage

23 handlers across `server.py` and mixin files. Tests exist for:

| Handler group | Test file |
|---|---|
| Memory handlers (store/retrieve/search/forget) | `tests/unit/mcp/handlers/test_memory_handlers.py` |
| Context handlers (get/set) | `tests/unit/mcp/handlers/test_context_handlers.py` |
| Help handlers (lookup/init/status/update/maintain) | `tests/unit/mcp/test_help_handlers.py` |
| Personal memory (capture/recall/topics/forget) | `tests/unit/mcp/test_server.py` |
| Attune level (get/set) | `tests/unit/test_mcp_memory_tools.py` |

**Handlers with no dedicated test:**
- `_handle_help_lookup_impl` (internal, called by `_handle_help_lookup`)
- `_handle_list_tools`, `_handle_list_resources`, `_handle_list_prompts`,
  `_handle_get_prompt` (MCP protocol plumbing)

These are lower risk but worth a basic smoke test.

### Hardcoded Count

```
tests/unit/test_mcp_memory_tools.py:32: assert len(tools) == 46
```

Schema functions return **41 tools** (21 workflow + 7 utility + 5 help
+ 4 personal_memory + 4 memory). The test expects 46 = 41 core + 5 from
the `attune-redis` plugin. The test only passes when `attune-redis` is
installed. This should be made conditional or split into two assertions:
one for core (41) and one for the with-redis case (46).

---

## 7. Hardcoded Registry / Count Assertions

| Test | Asserts | Actual | Status |
|---|---|---|---|
| `test_mcp_memory_tools.py:32` | `len(tools) == 46` | 41 core + 5 redis | Conditional on attune-redis install |
| `agent_factory/test_base.py:91` | `len(AgentRole) == 15` | 15 base roles | **CORRECT** |
| Various `len(results) == 10/20/50` | Page size checks | N/A | **Correct** (testing pagination limits) |

No widespread count drift found. The MCP count is the only structural issue.

---

## 8. Branch Coverage

`coverage.json` was generated **without** `--cov-branch` (CI also omits it).
Branch coverage is not currently measured. This is a gap, particularly for:

- `src/attune/security/path_validation.py` — many conditional branches for
  OS paths, null bytes, symlinks
- `src/attune/mcp/server.py` — omitted entirely
- `src/attune/models/` — auth fallback logic has complex branching

**Recommendation:** Add `--cov-branch` to the CI pytest invocation.
Expected: branch coverage ~5–10 pts below line coverage (i.e., ~73–78%),
which may drop CI below the 83% gate until branches in Red/Amber modules
are covered.

---

## 9. CI Health Assessment

### Issues Found

| Issue | Severity | Detail |
|---|---|---|
| Skipped file explicitly invoked in CI | Low | `test_api_endpoints.py` in "Phase 1 tests" CI step produces 40 silent skips |
| Threshold mismatch | Low | `pyproject.toml fail_under=85` vs CI `--cov-fail-under=83` |
| No branch coverage tracking | Medium | Branch gaps in security-critical code are invisible |
| `ANTHROPIC_API_KEY` in CI env | Info | `test_sonnet_opus_fallback.py` now correctly uses `pytestmark = pytest.mark.network`; this is fixed |
| `hot_reload` dead code with 94% coverage | Info | Module has no inbound imports but 94% test coverage (confirming the "dead code looks alive" lesson) |

### What's Working Well

- 12-platform matrix (3 OS × 4 Python) with `fail-fast: false`
- `conftest.py` has autouse `_disable_help_telemetry` fixture (prevents
  real file writes during tests)
- `conftest.py` has autouse `_setup_test_env` fixture patching empathy dir
  to a temp path
- `tests/unit/ci/test_zsh_readonly_assignments.py` guards against
  `status=` assignments in shell scripts

---

## 10. Conftest and Fixture Health

### Root conftest.py (18 KB)

Three autouse fixtures confirmed:
1. Line 67: `autouse=True` — test env setup
2. Line 376: `autouse=True, scope="function"` — disables telemetry writes
3. Line 420: `autouse=True, scope="function"` — disables help telemetry via env var

**This is good.** Telemetry pollution is guarded.

### Relative `.attune/` Path Risk

`tests/unit/test_telemetry.py` reads `Path(".attune/costs.json")` without
`tmp_path`. All three tests skip if the file doesn't exist — so no CI
writes occur — but these tests only run on developer machines with
pre-existing telemetry data. They should be rewritten to use `tmp_path`
and create fixture data.

### `tests/unit/meta_workflows/test_pattern_learner.py`

Uses `TemplateRegistry(storage_dir=".attune/meta_workflows/templates")` in
multiple tests. These write to a relative path during test execution. If
the tests don't clean up, they leave artifacts in the repo root. Should
use `tmp_path`.

---

## Priority Recommendations

Ordered by risk × effort (high risk, low effort first):

### P1 — Quick wins (1–4 hours)

1. **Delete `tests/integration/test_api_endpoints.py`** (40 dead tests,
   breaks CI narrative, no fix needed — wizard_factory_cli is gone)

2. **Remove `test_api_endpoints.py` from CI "Phase 1 tests" step** in
   `.github/workflows/tests.yml`

3. **Delete 5 v5.0.0 removal tests** in `test_provider_config_extended.py`
   and `test_fallback.py` (multi-provider, Ollama, OpenAI)

4. **Delete 5 legacy JSON storage tests** in `test_workflow_base.py`

5. **Fix threshold mismatch** — align CI `--cov-fail-under` with
   `pyproject.toml fail_under` (pick 85)

### P2 — Coverage gaps in active code (1–2 days)

6. **Wizard module coverage** — 34% on 898 lines is the worst measured
   module. `wizards/base.py` (13%), `wizards/registry.py` (14%), and
   `wizards/config_driven.py` (17%) are the highest-value targets. These
   are user-facing code paths.

7. **Workflows sub-file 0% cluster** — `release_prep_stages.py`,
   `security_audit_stages.py`, `security_audit_triage.py` together
   represent ~430 statements at 0–7%. Security audit and release prep
   are high-trust code paths.

8. **`attune/config.py` at 0%** — 166 statements. Root config module
   with zero coverage.

### P3 — Test hygiene (2–4 hours)

9. **Refactor 12 Redis mocking tests** in `test_cross_session.py` — use
   `memory._base._client` injection pattern (documented in Lessons Learned).

10. **Fix MCP tool count assertion** — split `assert len(tools) == 46`
    into `assert len(core_tools) == 41` + conditional check for redis
    plugin. This will stop breaking for contributors without `attune-redis`.

11. **Fix `test_telemetry.py`** — replace relative `.attune/` reads with
    `tmp_path` fixtures and actual fixture data.

12. **Fix `test_pattern_learner.py`** — replace `.attune/meta_workflows/`
    with `tmp_path`.

### P4 — Branch coverage (1 day)

13. **Add `--cov-branch`** to CI pytest invocation. Baseline the new
    metric and set a branch threshold. Focus first on
    `security/path_validation.py` and `models/` auth paths.

### P5 — Integration test gaps (2–3 days)

14. **MCP server ↔ workflow dispatch integration test** — the
    `call_tool → _dispatch_tool → workflow.execute()` path is the core
    value chain and has no integration test.

15. **project_index/index.py** — either add an integration test or remove
    the "integration-tested" claim from the omit comment.

---

## Appendix: Modules with 0 Test File References (Socratic)

25 socratic source files are never imported by any test:

`generated_workflow`, `domain_models`, `collaboration_invitations`,
`collaboration_sync`, `html_renderer`, `llm_analyzer_types`,
`collaboration_models`, `react_editor`, `success_models`, `explainer_types`,
`feedback_models`, `editor_models`, `form_builders`, `workflow_visualizer`,
`success_templates`, `react_schemas`, `generator_registry`,
`workflow_templates`, `api_helpers`, `llm_analyzer_prompts`,
`domain_registry`, `ab_testing/models`, `ab_testing/workflow_tester`,
`ab_testing/statistics`, `ab_testing/manager`, `ab_testing/allocator`

Several of these (`collaboration_*`, `mcp_server`) are excluded from
coverage via omit patterns. The rest appear in the 88.8% `socratic`
module aggregate only because the tested files pull them in indirectly.
True per-file coverage for the untested socratic files is likely 0–20%.
