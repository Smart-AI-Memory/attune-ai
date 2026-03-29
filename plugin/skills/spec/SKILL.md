---
name: spec
description: "Spec-driven development — brainstorm, plan, review, and execute with quality gates. Triggers on: spec, brainstorm and build, plan and execute, idea to code, build from scratch."
argument-hint: "<what to build, or 'resume'>"
---

# Spec-Driven Development

One skill to go from idea to shipped code, with quality
gates and your approval at every step.

## Scoping

Use `AskUserQuestion` to determine the mode:

```yaml
question: "What would you like to do?"
header: "Spec"
options:
  - label: "Start a new spec"
    description: "Brainstorm, decompose into tasks, then execute"
  - label: "Resume an in-progress spec"
    description: "Pick up where you left off"
  - label: "Import a spec file"
    description: "Load a plan from another project or path"
  - label: "Execute a spec"
    description: "Review and execute tasks from a saved plan"
```

If the user provides arguments (e.g., "resume" or a file
path), skip the picker and route directly.

## How It Works

Five stages, one flow:

1. **Create** — Brainstorm your idea, auto-decompose
   into XML tasks, save to `.claude/plans/`
2. **Review** — See each task in plain language. Power
   users can edit the XML directly in the plan file.
3. **Approve** — Commit to the plan
4. **Execute** — Tasks run one at a time. After each:
   approve, redo with new instructions, or auto-run
   the rest.
5. **Resume** — Session ended mid-execution? Next
   invocation picks up where you left off.

## Import

When the user chooses "Import a spec file":

1. Ask for the file path
2. Validate with `_validate_file_path()`
3. Copy to `.claude/plans/` if not already there
4. Load and validate tasks:

   ```python
   from attune.pipeline.spec_reader import read_spec
   tasks = read_spec(imported_path)
   ```

5. If tasks found, proceed to Review stage
6. If no tasks, tell the user the file has no XML
   `<task>` blocks and offer to create a spec instead

## Stage 1: Create

When the user chooses "Start a new spec":

1. Run the brainstorm conversation flow (same phases
   as brainstorm: Context, Problem, Goals, End State)
2. When the end state is clear, auto-decompose the
   approach into XML `<task>` blocks
3. Save to `.claude/plans/{topic-slug}.md` with both
   prose summary and XML task blocks
4. Use `AskUserQuestion`: "Spec saved with N tasks.
   Ready to review?"

## Stage 2: Review

1. Load tasks:

   ```python
   from attune.pipeline.spec_reader import read_spec
   ```

2. Present the task table:

   ```python
   from attune.spec import present_tasks, load_state
   tasks = read_spec(plan_path)
   state = load_state(plan_path)
   print(present_tasks(tasks, state))
   ```

3. For each task, show detail:

   ```python
   from attune.spec import present_task_detail
   print(present_task_detail(task))
   ```

4. Use `AskUserQuestion`: "Does this plan look right?"
   - "Looks good, proceed to execution"
   - "I want to edit the plan file"
   - "Start over"

## Stage 3: Approve

Show final summary: task count, scope, risks. Then:

Use `AskUserQuestion`: "Ready to start executing?"

- "Start executing"
- "Go back to review"

## Stage 4: Execute

For each pending task:

1. Show progress:

   ```python
   from attune.spec import format_progress_bar
   print(format_progress_bar(completed, total))
   ```

2. Show task detail with `present_task_detail(task)`
3. **Implement the task** — create/modify files as
   specified in the XML task block
4. Run quality gates:

   ```python
   from attune.pipeline import PipelineOrchestrator
   orch = PipelineOrchestrator(plan_path)
   result = await orch.run_gates_for_task(task)
   ```

5. Show result with `present_task_result(task, result)`
6. **Severity-gated approval:**

   If `"high"` severity (score < 50):
   Use `AskUserQuestion` with 2 options:
   - "Fix and retry"
   - "Acknowledge risk and continue"

   If `"medium"` or `"low"` severity:
   Use `AskUserQuestion` with 3 options:
   - "Approve and continue"
   - "Redo with new instructions"
   - "Auto-run remaining tasks"

7. Save state after each decision:

   ```python
   from attune.spec import save_state
   state.completed.append(task.task_id)
   save_state(state)
   ```

## Stage 5: Resume

On invocation, check for resumable plans:

```python
from attune.spec import find_resumable_plans
plans = find_resumable_plans()
```

If resumable plans exist, show them with
`AskUserQuestion`:

- "Resume {plan name} ({completed}/{total} done)"
- "Start a new spec"

## Critical Rules

- **ALWAYS use AskUserQuestion** between stages
- **ALWAYS save_state()** after each task approval
- **Show progress bar** before each task
- **Voice layer**: use the attune voice personality
  — friendly senior engineer
- **Power users**: the plan file is always editable.
  If the user says "let me edit the plan," pause and
  wait for them to re-invoke
