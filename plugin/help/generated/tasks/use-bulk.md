---
type: task
name: use-bulk
tags: [skill, task]
source: plugin/skills/bulk/SKILL.md
---

# Task: Use the bulk skill

Batch API processing for 50% cost savings on non-urgent bulk analysis. Triggers on: batch, bulk process, batch API, cheap bulk, process many, overnight analysis, 50% savings.

Invoke with: `/bulk <what to batch>`

## Steps

1. **Define what to batch**
   "Which tasks should I batch — e.g. a workflow run across many files, or many independent analyses?"

2. **Define how many / which targets**
   "List the items (files, modules, or task inputs) to process."

3. **Define urgency check**
   "Batch results take up to 24h. Is non-urgent turnaround acceptable? If you need it now, run the single-shot workflow instead."

4. **Run the tool**
   Call the `analyze_batch` MCP tool with a `requests` array,
one entry per task: - `task_id` and `task_type` and `input_data` are required per
  request; `model_tier` is optional (`cheap` / `capable` /
  `premium`, default `capable`).
- **Premium tier policy:** interactive premium = `claude-fable-5`
  (with server-side opus fallback); **batch premium =
  `claude-opus-4-8`** — the Batch API rejects the `fallbacks`
  param, so fable models are downgraded at request-build time.
- The call returns a batch id and submits asynchronously — it
  does not block for results.

   ```
   analyze_batch(requests=[
  {"task_id": "<unique-id>", "task_type": "<e.g. analyze_logs>",
   "input_data": {...}, "model_tier": "capable"},
  ...
])
   ```


## Related Topics
- **Reference**: Skill: bulk — full reference
