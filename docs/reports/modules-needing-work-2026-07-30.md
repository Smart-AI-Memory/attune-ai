# Modules needing work — 2026-07-30

Candidate list for the next product-targeted passes (test-quality
program #1569; "delegated lanes eat product backlog" ranking rule).

**Data sources** (all fresh as of 2026-07-30):

- Codecov per-file report for `main` — project total **93.82%**
  (698 files, 59,360 lines, 2,549 misses).
- `pyproject.toml` `[tool.coverage.run] omit` list (production
  entries only).
- Issue #1569 current-state notes.

The stale local `.coverage` file (Jul 18, partial run) was NOT used.

---

## Tier 1 — measured below the 85% local bar (64 modules)

### Top picks by miss volume

| Module | Cover | Miss | Notes |
|---|---|---|---|
| `authoring/generator.py` | 60.51% | 213 | Largest single gap in the tree |
| `authoring/source_introspection.py` | 75.40% | 51 | Authoring cluster (see below) |
| `workflows/dependency_check_*.py` (report + parsers) | 79–81% | 55 | One workflow, two files |
| `memory/short_term/facade.py` | 80.46% | 42 | Plus `patterns.py` 58.49%/17 |
| `ops/memory_data.py` | 82.22% | 37 | Ops-dashboard data layer |
| `memory/cross_session/coordinator.py` | 79.16% | 33 | |
| `diagnosis/triage.py` | 68.26% | 30 | Diagnosis cluster (see below) |
| `telemetry/approval_gates.py` | 78.85% | 29 | |

### Clusters (one lane could sweep each)

- **authoring/** — `generator.py` 60.51%, `source_introspection.py`
  75.40%, `ground_truth/{cli_help,dataclass_refs,public_api}.py`
  69–75%, `fact_check/{numeric_refs,cli_refs}.py` 71–74%.
  ~360 missed lines total; biggest cluster by far.
- **diagnosis/** — `triage.py` 68.26%, `engine.py` 78.57%,
  `priors.py` 79.71%, `store.py` 80.00%, plus
  `cli_commands/diagnosis_commands.py` 34.61%. ~80 misses.
- **ops/** — `routes/pending_writes.py` 74.52%, `collab_data.py`
  76.97%, `session_summary_cache.py` 77.55%, `memory_data.py`
  82.22%, `routes/{runs_history,curator}.py` ~81–84%,
  `__init__.py` 50%, `__main__.py` 0%. ~120 misses.
- **cli_commands/** — `gates_commands.py` 18.18%,
  `diagnosis_commands.py` 34.61%, `cost_commands.py` 83.33%,
  `curator.py` 77.96%.
- **memory/short_term** — `patterns.py` 58.49%, `facade.py`
  80.46%, `file_session{,_patterns}.py` ~69–77%.

### Full list (Codecov main, ascending)

| Cover | Lines | Miss | Module |
|---|---|---|---|
| 0.00% | 7 | 7 | `coordination.py` (deprecation shim — see Tier 3) |
| 0.00% | 1 | 1 | `ops/__main__.py` |
| 18.18% | 22 | 18 | `cli_commands/gates_commands.py` |
| 34.61% | 26 | 17 | `cli_commands/diagnosis_commands.py` |
| 50.00% | 8 | 4 | `ops/__init__.py` |
| 58.49% | 53 | 17 | `memory/short_term/patterns.py` |
| 60.51% | 623 | 213 | `authoring/generator.py` |
| 68.26% | 104 | 30 | `diagnosis/triage.py` |
| 68.68% | 99 | 20 | `workflows/context_proxy_mixin.py` |
| 68.75% | 96 | 21 | `redis_config.py` |
| 69.09% | 55 | 11 | `memory/file_session_patterns.py` |
| 69.23% | 26 | 6 | `authoring/ground_truth/cli_help.py` |
| 70.58% | 34 | 7 | `models/telemetry/run_context.py` |
| 71.23% | 73 | 15 | `authoring/fact_check/numeric_refs.py` |
| 71.26% | 87 | 19 | `authoring/ground_truth/dataclass_refs.py` |
| 71.42% | 7 | 2 | `memory/short_term/__init__.py` |
| 74.07% | 27 | 6 | `config/__init__.py` |
| 74.44% | 90 | 18 | `authoring/fact_check/cli_refs.py` |
| 74.52% | 106 | 21 | `ops/routes/pending_writes.py` |
| 75.20% | 121 | 22 | `authoring/ground_truth/public_api.py` |
| 75.40% | 305 | 51 | `authoring/source_introspection.py` |
| 76.97% | 139 | 26 | `ops/collab_data.py` |
| 77.41% | 93 | 20 | `hooks/executor.py` |
| 77.47% | 111 | 22 | `memory/file_session.py` |
| 77.50% | 40 | 7 | `monitoring/metrics.py` |
| 77.55% | 98 | 19 | `ops/session_summary_cache.py` |
| 77.96% | 59 | 6 | `cli_commands/curator.py` |
| 78.57% | 84 | 15 | `diagnosis/engine.py` |
| 78.85% | 227 | 29 | `telemetry/approval_gates.py` |
| 79.16% | 192 | 33 | `memory/cross_session/coordinator.py` |
| 79.27% | 111 | 22 | `workflows/dependency_check_report.py` |
| 79.54% | 44 | 6 | `gates/lifecycle/runner.py` |
| 79.71% | 69 | 9 | `diagnosis/priors.py` |
| 80.00% | 75 | 11 | `diagnosis/store.py` |
| 80.21% | 91 | 14 | `agents_md/parser.py` |
| 80.46% | 215 | 42 | `memory/short_term/facade.py` |
| 80.72% | 192 | 25 | `learning/storage.py` |
| 80.76% | 52 | 9 | `workflows/post_simplification_mixin.py` |
| 80.88% | 136 | 15 | `workflows/bug_predict_patterns.py` |
| 81.03% | 58 | 5 | `llm/security.py` |
| 81.19% | 117 | 10 | `workflows/test_gen/ast_analyzer.py` |
| 81.25% | 112 | 17 | `config/loader.py` |
| 81.25% | 16 | 2 | `orchestration/_strategies/__init__.py` |
| 81.48% | 162 | 24 | `workflows/dependency_check_parsers.py` |
| 81.48% | 54 | 4 | `ops/routes/runs_history.py` |
| 81.57% | 76 | 12 | `monitoring/multi_backend.py` |
| 81.75% | 137 | 16 | `commands/parser.py` |
| 81.77% | 192 | 27 | `roundtable/triage_appendix.py` |
| 81.81% | 132 | 15 | `workflows/discovery_sweep/sources/pattern_scan.py` |
| 81.92% | 83 | 12 | `monitoring/notifications.py` |
| 82.22% | 270 | 37 | `ops/memory_data.py` |
| 82.35% | 102 | 12 | `commands/loader.py` |
| 82.45% | 57 | 4 | `agents/release/coverage_agent.py` |
| 82.55% | 86 | 8 | `help/staleness.py` |
| 82.73% | 168 | 23 | `mcp/memory_handlers.py` |
| 83.33% | 126 | 20 | `cli_commands/cost_commands.py` |
| 83.33% | 90 | 7 | `workflows/doc_orch_scout.py` |
| 83.33% | 84 | 13 | `llm/providers/anthropic_batch.py` |
| 83.59% | 189 | 23 | `context/compaction.py` |
| 83.83% | 99 | 13 | `workflows/services/parsing_service.py` |
| 83.87% | 31 | 2 | `wizards/builtin/debug_wizard.py` |
| 84.09% | 88 | 11 | `ops/routes/curator.py` |
| 84.09% | 44 | 6 | `pipeline_learner/scaffold.py` |
| 84.12% | 63 | 7 | `monitoring/validators.py` |

All paths relative to `src/attune/`.

---

## Tier 2 — omitted from measurement (un-omit-audit candidates)

Production entries still in the `pyproject.toml` omit list. Zero
coverage data exists for these. The omit-audit passes (#1569, PRs
#1575/#1740/#1784 etc.) have so far removed **10 entries whose
labels proved false** — each stated reason below is a hypothesis,
not a fact, until probed.

| Module | Stated reason | Probe suggestion |
|---|---|---|
| `mcp/server.py` | Infrastructure server | #1785 just landed a server-handler suite — this label may already be false; check first |
| `workflows/progress_server.py` | Infrastructure server | Handler/scoring logic may be unit-testable |
| `models/auth_cli.py` | Interactive CLI | Non-TTY branches testable |
| `monitoring/alerts_cli.py` | Interactive CLI | Same |
| `meta_workflows/cli_meta_workflows.py` | CLI entry | The five sibling cli_commands labels were all false (99–100%) |
| `memory/control_panel_api.py` | FastAPI server | httpx TestClient needs no live server |
| `memory/short_term/sessions.py` | Requires Redis | fakeredis / mocked-backend pattern exists in tree |
| `attune_software/cli/*.py` | Legacy plugin CLI | Or deprecate/delete (subsystem-value gate) |
| `hooks/scripts/{evaluate_session, first_time_init, session_end, session_start, suggest_compact, telemetry_hook}.py` | Standalone hooks | subprocess round-trip pattern (help_hooks tests exist) |
| `core_modules/{interaction,short_term_memory}.py` | Stubs | If truly stubs — delete? (removing-dead-code gate) |
| `wizards/{technology,customer_support}_wizard.py` | Example wizards | Keep omitted or move to examples/ |
| `agent_factory/{memory_integration,resilient}.py` | Optional modules | Optional ≠ untestable |
| `models/__main__.py` | CLI entry | Trivial; low value |
| `hooks/scripts/help_freshness_nudge.py` | Not pytest-importable | subprocess round-trip |
| `attune/config.py` | Shadowed by `config/` package — unreachable | **Delete candidate**, not test candidate |

Deprecated `agent_factory` adapters/crews stay omitted (retirement
path, not test debt).

---

## Tier 3 — stale trackers to correct (cheap, do first)

- **Issue #1569's "next candidates" are stale**: it names
  `telemetry/agent_coordination.py` (81%) and `agent_tracking.py`
  (80%) — both now measure **~97%** on main. Update the issue body
  so the next lane doesn't chase closed gaps.
- **`coordination.py` (0%, 7 lines)** — PEP 562 deprecation shim
  from v6.8.0. Either a 10-line test of the ImportError message or
  a `# pragma: no cover`; also a candidate for eventual removal.
- **`ops/__main__.py` (0%, 1 line)** — `if __name__` guard style
  fix or pragma.

---

## Recommended pick order (product-ratio inversion)

1. **`authoring/generator.py`** — 213 misses at 60.5%; the single
   biggest measured product gap. Good delegated-lane target
   (serializable data shapes, suite receipt).
2. **diagnosis cluster + `cli_commands/{gates,diagnosis}_commands.py`**
   — lowest percentages in the tree, moderate size.
3. **ops/ data-layer cluster** — user-facing dashboard surface.
4. **Tier 2 omit-audit pass 3** — highest-yield entries:
   `mcp/server.py` (label likely already false after #1785),
   `meta_workflows/cli_meta_workflows.py`, `memory/short_term/sessions.py`.
5. Tier 3 corrections — 15 minutes, do alongside anything above.
