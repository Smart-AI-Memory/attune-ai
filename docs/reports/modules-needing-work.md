# Modules needing work

**Generated:** 2026-08-03 13:07 UTC by `scripts/modules_needing_work.py` — regenerate in place, don't hand-edit (the dated 2026-07-30 report is the historical first edition).

**Source:** Codecov main — project total 96.16% across 709 files. Candidate list for coverage lanes (test-quality program #1569).

## Tier 1 — measured below the 85% bar (4 modules)

### Clusters by miss volume

| Cluster | Modules | Missed lines |
|---|---|---|
| `config` | 1 | 6 |
| `memory` | 1 | 2 |
| `orchestration` | 1 | 2 |
| `wizards` | 1 | 2 |

### Full list (ascending coverage)

| Cover | Lines | Miss | Module |
|---|---|---|---|
| 71.42% | 7 | 2 | `src/attune/memory/short_term/__init__.py` |
| 74.07% | 27 | 6 | `src/attune/config/__init__.py` |
| 81.25% | 16 | 2 | `src/attune/orchestration/_strategies/__init__.py` |
| 83.87% | 31 | 2 | `src/attune/wizards/builtin/debug_wizard.py` |

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
