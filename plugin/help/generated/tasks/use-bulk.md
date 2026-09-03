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
   ### Shared command workspace (preferred)

   Open adapter `bulk` with either the provider-ready `requests` list or an
   existing `batch_id`. Present the widget or returned Markdown. New submissions
   must consume the bound, explicitly confirmed `submit_batch` action before
   calling `analyze_batch`; a reconnect uses the read-only `check_batch` action.
   Publish the real provider response as `submission_result` or `status_result`.
   Only a response with the exact accepted task count and a non-empty batch id may
   render as submitted. Rejections and timeouts must render “did not submit” (or
   “did not complete” for status), never a synthetic batch id. Preserve the same
   decision and receipt in compact text when the shared tools are unavailable.

   The workspace status receipt completes the interactive invocation; `pending`
   does not mean the remote work completed. Reinvoke later with the returned
   `batch_id` to reconnect.

   Call the `analyze_batch` MCP tool with a `requests` array,
   one entry per task:

   ```
   analyze_batch(requests=[
     {"task_id": "<unique-id>", "task_type": "<e.g. analyze_logs>",
      "input_data": {...}, "model_tier": "capable"},
     ...
   ])
   ```

5. **Review bulk execution guidance**
   - `task_id` and `task_type` and `input_data` are required per
     request; `model_tier` is optional (`cheap` / `capable` /
     `premium`, default `capable`).
   - **Premium tier policy:** interactive premium = `claude-fable-5-1`
     (with server-side opus fallback); **batch premium =
     `claude-opus-4-8`** — the Batch API rejects the `fallbacks`
     param, so fable models are downgraded at request-build time.
   - The call returns a batch id and submits asynchronously — it
     does not block for results.


## Related Topics
- **Reference**: Skill: bulk — full reference
