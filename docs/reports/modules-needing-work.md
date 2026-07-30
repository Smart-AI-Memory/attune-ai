# Modules needing work

**Generated:** 2026-07-30 20:16 UTC by `scripts/modules_needing_work.py` — regenerate in place, don't hand-edit (the dated 2026-07-30 report is the historical first edition).

**Source:** Codecov main — project total 94.57% across 699 files. Candidate list for coverage lanes (test-quality program #1569).

## Tier 1 — measured below the 85% bar (53 modules)

### Clusters by miss volume

| Cluster | Modules | Missed lines |
|---|---|---|
| `workflows` | 9 | 135 |
| `authoring` | 6 | 131 |
| `memory` | 6 | 127 |
| `monitoring` | 4 | 38 |
| `telemetry` | 1 | 29 |
| `(top-level)` | 2 | 28 |
| `commands` | 2 | 28 |
| `roundtable` | 1 | 27 |
| `cli_commands` | 2 | 26 |
| `learning` | 1 | 25 |
| `config` | 2 | 23 |
| `mcp` | 1 | 23 |
| `context` | 1 | 23 |
| `ops` | 4 | 20 |
| `hooks` | 1 | 20 |
| `llm` | 2 | 18 |
| `agents_md` | 1 | 14 |
| `help` | 1 | 8 |
| `models` | 1 | 7 |
| `gates` | 1 | 6 |
| `pipeline_learner` | 1 | 6 |
| `agents` | 1 | 4 |
| `orchestration` | 1 | 2 |
| `wizards` | 1 | 2 |

### Full list (ascending coverage)

| Cover | Lines | Miss | Module |
|---|---|---|---|
| 0.00% | 7 | 7 | `src/attune/coordination.py` |
| 0.00% | 1 | 1 | `src/attune/ops/__main__.py` |
| 50.00% | 8 | 4 | `src/attune/ops/__init__.py` |
| 58.49% | 53 | 17 | `src/attune/memory/short_term/patterns.py` |
| 68.68% | 99 | 20 | `src/attune/workflows/context_proxy_mixin.py` |
| 68.75% | 96 | 21 | `src/attune/redis_config.py` |
| 69.09% | 55 | 11 | `src/attune/memory/file_session_patterns.py` |
| 69.23% | 26 | 6 | `src/attune/authoring/ground_truth/cli_help.py` |
| 70.58% | 34 | 7 | `src/attune/models/telemetry/run_context.py` |
| 71.23% | 73 | 15 | `src/attune/authoring/fact_check/numeric_refs.py` |
| 71.26% | 87 | 19 | `src/attune/authoring/ground_truth/dataclass_refs.py` |
| 71.42% | 7 | 2 | `src/attune/memory/short_term/__init__.py` |
| 74.07% | 27 | 6 | `src/attune/config/__init__.py` |
| 74.44% | 90 | 18 | `src/attune/authoring/fact_check/cli_refs.py` |
| 75.20% | 121 | 22 | `src/attune/authoring/ground_truth/public_api.py` |
| 75.40% | 305 | 51 | `src/attune/authoring/source_introspection.py` |
| 77.41% | 93 | 20 | `src/attune/hooks/executor.py` |
| 77.47% | 111 | 22 | `src/attune/memory/file_session.py` |
| 77.50% | 40 | 7 | `src/attune/monitoring/metrics.py` |
| 77.96% | 59 | 6 | `src/attune/cli_commands/curator.py` |
| 78.85% | 227 | 29 | `src/attune/telemetry/approval_gates.py` |
| 79.16% | 192 | 33 | `src/attune/memory/cross_session/coordinator.py` |
| 79.27% | 111 | 22 | `src/attune/workflows/dependency_check_report.py` |
| 79.54% | 44 | 6 | `src/attune/gates/lifecycle/runner.py` |
| 80.21% | 91 | 14 | `src/attune/agents_md/parser.py` |
| 80.46% | 215 | 42 | `src/attune/memory/short_term/facade.py` |
| 80.72% | 192 | 25 | `src/attune/learning/storage.py` |
| 80.76% | 52 | 9 | `src/attune/workflows/post_simplification_mixin.py` |
| 80.88% | 136 | 15 | `src/attune/workflows/bug_predict_patterns.py` |
| 81.03% | 58 | 5 | `src/attune/llm/security.py` |
| 81.19% | 117 | 10 | `src/attune/workflows/test_gen/ast_analyzer.py` |
| 81.25% | 112 | 17 | `src/attune/config/loader.py` |
| 81.25% | 16 | 2 | `src/attune/orchestration/_strategies/__init__.py` |
| 81.48% | 162 | 24 | `src/attune/workflows/dependency_check_parsers.py` |
| 81.48% | 54 | 4 | `src/attune/ops/routes/runs_history.py` |
| 81.57% | 76 | 12 | `src/attune/monitoring/multi_backend.py` |
| 81.75% | 137 | 16 | `src/attune/commands/parser.py` |
| 81.77% | 192 | 27 | `src/attune/roundtable/triage_appendix.py` |
| 81.81% | 132 | 15 | `src/attune/workflows/discovery_sweep/sources/pattern_scan.py` |
| 81.92% | 83 | 12 | `src/attune/monitoring/notifications.py` |
| 82.35% | 102 | 12 | `src/attune/commands/loader.py` |
| 82.45% | 57 | 4 | `src/attune/agents/release/coverage_agent.py` |
| 82.55% | 86 | 8 | `src/attune/help/staleness.py` |
| 82.73% | 168 | 23 | `src/attune/mcp/memory_handlers.py` |
| 83.06% | 189 | 23 | `src/attune/context/compaction.py` |
| 83.33% | 126 | 20 | `src/attune/cli_commands/cost_commands.py` |
| 83.33% | 90 | 7 | `src/attune/workflows/doc_orch_scout.py` |
| 83.33% | 84 | 13 | `src/attune/llm/providers/anthropic_batch.py` |
| 83.83% | 99 | 13 | `src/attune/workflows/services/parsing_service.py` |
| 83.87% | 31 | 2 | `src/attune/wizards/builtin/debug_wizard.py` |
| 84.09% | 88 | 11 | `src/attune/ops/routes/curator.py` |
| 84.09% | 44 | 6 | `src/attune/pipeline_learner/scaffold.py` |
| 84.12% | 63 | 7 | `src/attune/monitoring/validators.py` |

## Tier 2 — omitted from measurement (un-omit-audit candidates)

Production entries still in the `pyproject.toml` omit list. Every stated reason is a hypothesis until probed — 12 labels have been falsified so far.

- `*/agent_factory/crews/*` — CrewAI deprecated - use meta-workflows
- `*/agent_factory/adapters/autogen_adapter.py` — Deprecated adapter
- `*/agent_factory/adapters/crewai_adapter.py` — CrewAI deprecated
- `*/agent_factory/adapters/haystack_adapter.py` — Deprecated adapter
- `*/agent_factory/adapters/langchain_adapter.py` — Use native adapter
- `*/agent_factory/memory_integration.py` — Optional integration module
- `*/agent_factory/resilient.py` — Optional resilience module
- `*/wizards/technology_wizard.py` — Example wizard
- `*/wizards/customer_support_wizard.py` — Example wizard
- `*/workflows/progress_server.py` — Progress streaming server
- `*/models/auth_cli.py` — Interactive auth setup
- `*/monitoring/alerts_cli.py` — Monitoring CLI
- `attune_software/cli/*.py` — Plugin CLI subcommands
- `*/memory/control_panel_api.py` — FastAPI REST server
- `*/hooks/scripts/evaluate_session.py` — Standalone hook
- `*/hooks/scripts/first_time_init.py` — Standalone hook
- `*/hooks/scripts/session_end.py` — Standalone hook
- `*/hooks/scripts/session_start.py` — Standalone hook
- `*/hooks/scripts/suggest_compact.py` — Standalone hook
- `*/hooks/scripts/telemetry_hook.py` — Standalone hook
- `*/core_modules/interaction.py` — Interaction stubs
- `*/core_modules/short_term_memory.py` — Memory stubs
- `*/mcp/__init__.py` — MCP package init
- `*/commands/__init__.py` — Commands package init
- `*/memory/storage/__init__.py` — Storage package init
- `*/core_modules/__init__.py` — Core modules init
- `*/models/__main__.py` — Models CLI entry point
- `*/hooks/scripts/help_freshness_nudge.py` — Standalone hook script (not importable via pytest)
- `*/attune/config.py` — Shadowed by attune/config/ package — unreachable import

## How lanes run (parallel delegation)

Modules with disjoint files are independent lanes. Emit briefs with `--briefs N` (or `--briefs-dir`) and dispatch them as PARALLEL delegated lanes: seats implement advisory on fresh branches, the lead re-runs every receipt centrally before the chair-armed merge. A lane's self-report is never the receipt.
