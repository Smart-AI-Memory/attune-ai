---
type: task
name: export-telemetry
tags: [cli, telemetry]
source: src/attune/cli_minimal.py
---

# Task: Export telemetry data

Export your workflow usage data to CSV or JSON for analysis. Useful for tracking costs and identifying most-used workflows.

## Prerequisites

- At least one workflow run to have data

## Steps

1. **View usage summary**

   ```
   attune telemetry show --days 30
   ```

2. **Export to JSON**

   ```
   attune telemetry export --output usage.json --format json
   ```

3. **Export to CSV**

   ```
   attune telemetry export --output usage.csv --format csv
   ```


## Related Topics

_No related topics yet._
