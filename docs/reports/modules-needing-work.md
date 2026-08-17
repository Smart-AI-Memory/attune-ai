# Modules needing work

**Generated:** 2026-08-17 13:09 UTC by `scripts/modules_needing_work.py` — regenerate in place, don't hand-edit (the dated 2026-07-30 report is the historical first edition).

**Source:** Codecov main — project total 96.16% across 717 files. Candidate list for coverage lanes (test-quality program #1569).

## Tier 1 — measured below the 85% bar (0 modules)

Nothing below 85% — the floor is the ceiling today.

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

## How lanes run (parallel delegation)

Modules with disjoint files are independent lanes. Emit briefs with `--briefs N` (or `--briefs-dir`) and dispatch them as PARALLEL delegated lanes: seats implement advisory on fresh branches, the lead re-runs every receipt centrally before the chair-armed merge. A lane's self-report is never the receipt.
