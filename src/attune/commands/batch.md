---
name: batch
description: Batch API processing with 50% cost savings
category: hub
aliases: [bulk]
tags: [batch, api, cost, async, bulk]
version: "1.0.0"
question:
  header: "Batch API"
  question: "What would you like to do with batch processing?"
  multiSelect: false
  options:
    - label: "Submit a batch"
      description: "Queue tasks for async processing (50% cost savings)"
    - label: "Check batch status"
      description: "View progress of a running batch"
    - label: "Get batch results"
      description: "Retrieve completed batch results"
    - label: "Wait for batch"
      description: "Block until a batch completes"
---

# batch

Batch API processing — submit tasks for asynchronous
execution at 50% cost savings via the Anthropic Batch API.

**Batch requests are processed within 24 hours.** Use this
for non-urgent, high-volume tasks where cost matters more
than latency.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/batch submit <tasks>` | Submit tasks for batch processing |
| `/batch status <id>` | Check status of a running batch |
| `/batch results <id>` | Retrieve completed batch results |
| `/batch wait <id>` | Wait for a batch to complete |

## Natural Language

Describe what you need:

- "submit these files for batch review"
- "check my batch status"
- "get the results from my last batch"
- "process these tasks in bulk"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST
execute the workflow, not answer ad-hoc.**

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/batch submit` | Collect tasks, submit via Anthropic Batch API |
| `/batch status <id>` | Query batch status and show progress |
| `/batch results <id>` | Fetch and display completed results |
| `/batch wait <id>` | Poll until batch completes, then show results |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "submit", "queue", "process", "bulk" | Submit batch |
| "status", "progress", "check" | Check batch status |
| "results", "output", "completed" | Get batch results |
| "wait", "block", "until done" | Wait for completion |

**IMPORTANT:** When arguments are provided, DO NOT just
display documentation. EXECUTE the action.

### How It Works

1. Tasks are serialized and sent to the Anthropic Batch API
2. Processing happens asynchronously (up to 24 hours)
3. Cost is 50% less than synchronous API calls
4. Results are retrieved when processing completes

### CLI Reference

```bash
uv run attune batch submit --tasks <file>
uv run attune batch status --id <batch_id>
uv run attune batch results --id <batch_id>
uv run attune batch wait --id <batch_id>
```
