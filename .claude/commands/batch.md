---
name: batch
description: Batch API processing (50% cost savings)
category: primary
aliases: [b]
tags: [batch, api, cost-savings, bulk]
version: "1.0.0"
question:
  header: "Batch"
  question: "What batch operation do you need?"
  multiSelect: false
  options:
    - label: "Submit a batch"
      description: "Submit workflows for batch processing"
    - label: "Check status"
      description: "Check status of a running batch"
    - label: "Get results"
      description: "Retrieve completed batch results"
    - label: "Wait for completion"
      description: "Wait for a batch to finish"
---

# batch

Batch API processing for 50% cost savings on
non-interactive workflows.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `submit` | Submit workflows for batch processing |
| `status` | Check batch status |
| `results` | Retrieve batch results |
| `wait` | Wait for batch completion |

## Usage

```bash
/batch                  # Ask what to do
/batch submit           # Submit a batch
/batch status           # Check status
/batch results          # Get results
/batch wait             # Wait for completion
```

## Behavior

### submit

Use `AskUserQuestion` to understand:

- Which workflows to run? (security-audit,
  bug-predict, perf-audit, code-review)
- Which path to analyze?
- Run all at once or select specific ones?

Then submit via the Anthropic Batch API for 50%
cost savings.

### status

Check the status of a running batch:

- Show progress percentage
- List completed vs pending items
- Estimated time remaining

### results

Retrieve and display results from a completed batch:

- Format as readable tables
- Highlight critical findings
- Provide actionable summaries

### wait

Wait for a batch to complete, showing progress
updates periodically.

## Cost Savings

Batch API provides 50% cost reduction compared to
real-time API calls. Ideal for:

- Multi-workflow analysis runs
- CI/CD pipeline integrations
- Comprehensive project audits
- Nightly analysis jobs
