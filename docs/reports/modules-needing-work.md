# Modules needing work

**Generated:** 2026-09-07 13:07 UTC by `scripts/modules_needing_work.py` — regenerate in place, don't hand-edit (the dated 2026-07-30 report is the historical first edition).

**Source:** Codecov main — project total 95.84% across 742 files. Candidate list for coverage lanes (test-quality program #1569).

## Tier 1 — measured below the 85% bar (6 modules)

### Clusters by miss volume

| Cluster | Modules | Missed lines |
|---|---|---|
| `classes` | 4 | 74 |
| `workflows` | 1 | 14 |
| `hooks` | 1 | 11 |

### Full list (ascending coverage)

| Cover | Lines | Miss | Module |
|---|---|---|---|
| 75.96% | 104 | 22 | `src/attune/classes/teeth.py` |
| 80.70% | 114 | 15 | `src/attune/classes/mock_worklist.py` |
| 81.69% | 71 | 13 | `src/attune/classes/class_m.py` |
| 82.58% | 155 | 24 | `src/attune/classes/register.py` |
| 83.07% | 65 | 11 | `src/attune/hooks/scripts/worktree_add_guard.py` |
| 84.82% | 112 | 14 | `src/attune/workflows/__init__.py` |

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
- `*/core_modules/interaction.py` — Interaction stubs
- `*/core_modules/short_term_memory.py` — Memory stubs
- `*/mcp/__init__.py` — MCP package init
- `*/commands/__init__.py` — Commands package init
- `*/memory/storage/__init__.py` — Storage package init
- `*/core_modules/__init__.py` — Core modules init
- `*/models/__main__.py` — Models CLI entry point

## How lanes run (parallel delegation)

Modules with disjoint files are independent lanes. Emit briefs with `--briefs N` (or `--briefs-dir`) and dispatch them as PARALLEL delegated lanes: seats implement advisory on fresh branches, the lead re-runs every receipt centrally before the chair-armed merge. A lane's self-report is never the receipt.
