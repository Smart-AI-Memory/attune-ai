---
name: bulk
description: "Batch API processing for 50% cost savings on non-urgent bulk analysis. Triggers on: batch, bulk process, batch API, cheap bulk, process many, overnight analysis, 50% savings."
argument-hint: "<what to batch>"
---

# Bulk Batch Processing

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="bulk", mode="preamble")` and display
the returned `preamble` text as a blockquote. Then tell the
user they can say "tell me more" for a step-by-step guide, or
answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Bulk** — Submits tasks to the Anthropic Batch API for 50% cost savings. Runs asynchronously (up to 24h), so it's ideal for non-urgent, high-volume analysis rather than interactive work.

## Scoping

Before submitting, ask:

1. **What to batch**: "Which tasks should I batch — e.g. a
   workflow run across many files, or many independent
   analyses?"
2. **How many / which targets**: "List the items (files,
   modules, or task inputs) to process."
3. **Urgency check**: "Batch results take up to 24h. Is
   non-urgent turnaround acceptable? If you need it now, run
   the single-shot workflow instead."

## Execution

Call the `analyze_batch` MCP tool with a `requests` array,
one entry per task:

```
analyze_batch(requests=[
  {"task_id": "<unique-id>", "task_type": "<e.g. analyze_logs>",
   "input_data": {...}, "model_tier": "capable"},
  ...
])
```

- `task_id` and `task_type` and `input_data` are required per
  request; `model_tier` is optional (`cheap` / `capable` /
  `premium`, default `capable`).
- **Premium tier policy:** interactive premium = `claude-fable-5`
  (with server-side opus fallback); **batch premium =
  `claude-opus-4-8`** — the Batch API rejects the `fallbacks`
  param, so fable models are downgraded at request-build time.
- The call returns a batch id and submits asynchronously — it
  does not block for results.

## Output

Report back:

- The **batch id** and submitted task count.
- That processing is asynchronous (up to 24h) at 50% cost.
- How to retrieve results later (re-invoke and reference the
  batch id).

## When to use

- Multi-workflow analysis runs, project-wide audits, nightly
  / CI jobs — anything non-interactive where cost matters more
  than latency.
- For a single urgent analysis, use the matching workflow
  skill directly (e.g. security-audit, bug-predict) instead.
