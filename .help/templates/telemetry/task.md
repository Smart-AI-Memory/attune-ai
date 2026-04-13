---
feature: telemetry
depth: task
generated_at: 2026-04-13T17:01:49.548610+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Work with telemetry

Use telemetry when you need to track agent performance, coordinate multi-agent workflows, or analyze cost savings from model fallbacks.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/telemetry/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what telemetry
   does today before making changes.
   The primary functions are:
   - `main()` in `src/attune/telemetry/__main__.py` — Telemetry CLI entry point.
   - `cmd_sonnet_opus_analysis()` in `src/attune/telemetry/cli_analysis.py` — Show Sonnet 4.5 -> Opus 4.5 fallback analysis and cost savings.
   - `cmd_file_test_status()` in `src/attune/telemetry/cli_analysis.py` — Show per-file test status.
   - `cmd_tier1_status()` in `src/attune/telemetry/cli_automation.py` — Show comprehensive Tier 1 automation status.
   - `cmd_task_routing_report()` in `src/attune/telemetry/cli_automation.py` — Show detailed task routing report.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "telemetry"`.

## Key files

- `src/attune/telemetry/**`

## Common modifications

Functions you are most likely to modify:

- `main()` in `src/attune/telemetry/__main__.py`
- `cmd_sonnet_opus_analysis()` in `src/attune/telemetry/cli_analysis.py`
- `cmd_file_test_status()` in `src/attune/telemetry/cli_analysis.py`
- `cmd_tier1_status()` in `src/attune/telemetry/cli_automation.py`
- `cmd_task_routing_report()` in `src/attune/telemetry/cli_automation.py`
- `cmd_test_status()` in `src/attune/telemetry/cli_automation.py`
- `cmd_agent_performance()` in `src/attune/telemetry/cli_automation.py`
- `cmd_telemetry_show()` in `src/attune/telemetry/cli_core.py`
