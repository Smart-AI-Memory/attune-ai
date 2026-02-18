---
name: batch
description: Batch API processing — 50% cost savings via Anthropic Message Batches
category: hub
aliases: [batch-api, bulk]
tags: [batch, cost, bulk, async, optimization]
version: "1.0.0"
question:
  header: "Batch Processing"
  question: "What would you like to do with Batch API?"
  multiSelect: false
  options:
    - label: "Submit a new batch"
      description: "Create and submit batch requests (50% cost savings)"
    - label: "Check batch status"
      description: "Check processing status of a submitted batch"
    - label: "Get batch results"
      description: "Download results from a completed batch"
    - label: "Learn about Batch API"
      description: "Understand pricing, limits, and best practices"
---

# batch

Batch API processing hub — submit bulk requests at 50%
cost savings via the Anthropic Message Batches API.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/batch submit` | Guide through creating and submitting a batch |
| `/batch status <id>` | Check batch processing status |
| `/batch results <id>` | Download completed batch results |
| `/batch info` | Explain Batch API pricing and best practices |

## Natural Language

Describe what you need:

- "submit a batch of tasks"
- "check if my batch is done"
- "get the results from my batch"
- "how does the batch API save money?"
- "I want to run bulk analysis at a discount"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked, you MUST follow the
Socratic discovery flow below. NEVER skip to execution.**

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/batch submit` | Run Submit flow (see below) |
| `/batch submit <file>` | `uv run attune batch submit <file>` |
| `/batch status <id>` | `uv run attune batch status <id>` |
| `/batch status <id> --json` | `uv run attune batch status <id> --json` |
| `/batch results <id>` | Ask where to save, then `uv run attune batch results <id> <output>` |
| `/batch wait <id>` | Ask where to save, then `uv run attune batch wait <id> <output>` |
| `/batch info` | Show Batch API overview from docs/BATCH_API_GUIDE.md |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "submit", "create batch", "send batch" | Run Submit flow |
| "status", "check", "is it done" | Ask for batch ID, then run status |
| "results", "download", "get output" | Ask for batch ID + output path |
| "wait", "poll" | Ask for batch ID + output path |
| "info", "pricing", "how does it work" | Show Batch API overview |

### Submit Flow (Socratic Discovery)

When the user wants to submit a new batch, guide them
through these steps using `AskUserQuestion`:

**Step 1: What kind of tasks?**

Ask: "What type of tasks do you want to batch?"

Options:

- `analyze_logs` — Analyze error logs and identify issues
- `generate_report` — Generate reports from data
- `generate_tests` — Generate unit tests for code
- `generate_docs` — Generate documentation for code
- `classify_bulk` — Classify multiple items
- Custom — User describes their own task type

**Step 2: What data?**

Based on task type, ask the appropriate follow-up:

- For `analyze_logs`: "Paste the logs or provide a file path"
- For `generate_tests`/`generate_docs`: "Which source
  files?" (suggest using glob patterns or listing files)
- For `generate_report`: "What data should be summarized?"
- For `classify_bulk`: "What items need classification?"
- For custom: "Describe the input for each request"

**Step 3: Model tier?**

Ask: "Which model tier?"

Options:

- `cheap` (Haiku) — Fast and cheapest, good for simple
  tasks
- `capable` (Sonnet) — Best balance of quality and cost
  (Recommended)
- `premium` (Opus) — Highest quality for complex tasks

**Step 4: Create and submit**

1. Generate the `batch_requests.json` file from user input
2. Show the user what will be submitted (task count,
   estimated cost tier)
3. Ask: "Ready to submit?" (confirm before calling API)
4. Run: `uv run attune batch submit batch_requests.json`
5. Display the batch ID and follow-up commands

### Results Flow

When the user asks for results:

1. Ask for the batch ID if not provided
2. Check status first:
   `uv run attune batch status <id>`
3. If ended, ask where to save:
   "Where should I save the results?"
   (default: `batch_results.json`)
4. Download:
   `uv run attune batch results <id> <output>`
5. Read and summarize the results file

### Batch API Overview

When user asks for info, share these key points:

- **50% cost savings** vs standard API pricing
- **24-hour processing window** — not for real-time use
- **Up to 10,000 requests** per batch
- **Supported task types**: log analysis, test generation,
  documentation, reports, classification
- **Best for**: bulk operations, overnight processing,
  cost-sensitive workloads
- **Not for**: interactive workflows, time-sensitive tasks

Refer to `docs/BATCH_API_GUIDE.md` for full documentation.

### CLI Reference

```bash
# Submit batch from JSON file
uv run attune batch submit requests.json

# Check status
uv run attune batch status msgbatch_abc123
uv run attune batch status msgbatch_abc123 --json

# Download results
uv run attune batch results msgbatch_abc123 output.json

# Wait for completion + download
uv run attune batch wait msgbatch_abc123 output.json
uv run attune batch wait msgbatch_abc123 output.json \
  --poll-interval 600 --timeout 43200
```
