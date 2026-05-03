---
name: check-costs
source: src/attune/cli_minimal.py
summary: This template explains how to view and analyze API costs for workflow runs
  using the `attune costs` command, including cost savings from tier routing, with
  an option to export the data for further analysis.
tags:
- cli
- telemetry
type: quickstart
---

# Quickstart: Check API Costs

Review the cost breakdown for your workflow runs, including any savings from tier routing.

```bash
attune costs
```

**Result:** A cost breakdown grouped by workflow, showing total spend and savings achieved through tier routing.

**Next step:** Export the data for further analysis with:

```bash
attune telemetry export -o costs.json
```

## Related Topics

- [Understanding Tier Routing](#)
- [Exporting Telemetry Data](#)
- [Managing Workflow Budgets](#)
