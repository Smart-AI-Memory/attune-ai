---
feature: telemetry
depth: task
generated_at: 2026-04-04T02:25:50.579509+00:00
source_hash: cdb506bfba26d96b90402bbc00b19c3dd80afaec88f6a4ae5de0c1c585b63162
status: generated
---

# Working with Telemetry

## Overview

Common tasks for modifying or extending telemetry.

## Key Files

- `src/attune/telemetry/**`


## Common Modifications

Functions you may need to modify:

- `main()` in `src/attune/telemetry/__main__.py`

- `cmd_sonnet_opus_analysis()` in `src/attune/telemetry/cli_analysis.py`

- `cmd_file_test_status()` in `src/attune/telemetry/cli_analysis.py`

- `cmd_tier1_status()` in `src/attune/telemetry/cli_automation.py`

- `cmd_task_routing_report()` in `src/attune/telemetry/cli_automation.py`

- `cmd_test_status()` in `src/attune/telemetry/cli_automation.py`

- `cmd_agent_performance()` in `src/attune/telemetry/cli_automation.py`

- `cmd_telemetry_show()` in `src/attune/telemetry/cli_core.py`
