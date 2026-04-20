---
type: tip
feature: telemetry
depth: tip
generated_at: 2026-04-20T01:25:10.407489+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Tip: Use telemetry CLI commands to debug system health

Start with `python -m attune.telemetry` commands when you suspect performance issues or agent coordination problems. The CLI gives you immediate visibility into what's actually happening without writing debug code.

The built-in commands show you cost savings (`cmd_telemetry_savings`), agent performance (`cmd_agent_performance`), test execution status (`cmd_test_status`), and model tier routing (`cmd_task_routing_report`). Each command returns structured data you can pipe to other tools or save for later analysis.

Run these commands first before diving into logs or adding print statements — you'll often find the answer faster than writing custom debugging code.
