---
name: spec
description: "Spec Ladders — goal-driven spec development: brainstorm, plan, review, and execute a gated task ladder with recorded approvals. Triggers on: spec, spec ladders, brainstorm and build, plan and execute, idea to code, build from scratch."
argument-hint: "<what to build, or 'resume'>"
---

# Spec-Driven Development

**Model recommendation:** Spec planning and XML-enhanced-prompt
authoring benefit from the Opus tier (`claude-opus-4-8`). Before
proceeding, suggest a model switch once:

> "This is spec work — recommend `/model claude-opus-4-8` for
> stronger structured reasoning. Want to switch?"

Defer to the user's choice if they've already picked a model.

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="spec-engine", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Spec** — Walks you from idea to working code through brainstorm, plan, review, approve, and execute phases.

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

### New-spec intake (one form, not N questions)

When the route is "Start a new spec", gather the framing as ONE
form per the Socratic rule — never as sequential question turns:

```bash
python -m attune.elicitation.spec_intake
```

The JSON payload carries a validated form definition
(`attune.elicitation.spec_intake.build_spec_intake_form`) —
outcome, done-when acceptance, primary code area (options derived
from the tree's packages), and an optional slug — plus
`taken_slugs` for collision awareness. Render it widget-first with
the `AskUserQuestion` fallback (batching opts in via
`metadata.source` containing "form"). If the user's invocation
already stated what to build, carry it into the outcome field
instead of asking again.

Compose the answers into the session-contract block that seeds
Stage 1:

```bash
echo '<answers JSON>' | python -m attune.elicitation.spec_intake --compose
```

A slug collision renders as a WARNING, not an error — offer to
amend the existing spec before forking a new one.

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

1. **Kickoff form (one batched turn).** Gather the
   *independent* dimensions of the kickoff as a single
   form via the `elicit` skill, instead of asking them
   one button at a time. The dimensions:

   - `outcome` — what should be true when done (one line)
   - `scope` — where it focuses (area / files / subsystem)
   - `concerns` — which quality dimensions matter
     (multi-select: correctness, security, performance,
     tests, docs)

   Build the declarative form, then **prefer the rich
   widget surface** so the kickoff renders as one form
   with the controls each dimension deserves —
   `outcome`/`scope` as multi-line textareas and
   `concerns` as a multi-select checkbox group, instead
   of three flat button turns. Render it with
   `elicitation_render_widget` and pass the returned
   `html` to `mcp__visualize__show_widget`; when the
   user submits, parse the `__elicitation_response__`
   postback and validate with
   `elicitation_collect_response`.

   **Fall back to the portable AskUserQuestion mapping**
   — `elicitation_render_form` → one `AskUserQuestion`
   call with `metadata: {"source": "elicit-form"}` (the
   opt-in the one-question-per-turn guard requires) →
   `elicitation_collect_response` — when the widget
   surface is unavailable. Per decisions D10, treat an
   elicitation `decline` you did **not** see the user
   make as "surface unavailable" and fall back; never
   read it as the user saying no. The `elicit` skill
   owns both round-trips (its "Widget surface" section
   and steps 2–4); this stage just supplies the three
   fields.

   **Omit any dimension the user already stated** — the
   `<what to build>` argument usually answers `outcome`,
   so drop that field rather than re-ask. If only one
   dimension is left open, ask it as a single question —
   never force a one-field form (the §4 batching rule:
   batch only genuinely-open, independent dimensions).

2. Run the brainstorm conversation flow for the parts a
   form can't batch — Problem → Goals → End State build on
   each other, so they stay **sequential** — seeded by the
   kickoff answers.
3. When the end state is clear, auto-decompose the
   approach into XML `<task>` blocks
4. Save to `.claude/plans/{topic-slug}.md` with both
   prose summary and XML task blocks
5. Use `AskUserQuestion`: "Spec saved with N tasks.
   Ready to review?"

### Boundary gate (spec-lifecycle-gates, G5)

When the plan belongs to a spec under `docs/specs/<slug>/`, run the
lifecycle gates before presenting the review:

```bash
attune gates check tasks --spec <slug> --changed <paths the plan touches>
```

Render every receipt to the user. G5 semantics are binding: exit 2
(`BLOCKED`) — do NOT proceed to review; the findings must be fixed
first. Exit 1 (`CHAIR_REQUIRED`) — present the receipts and proceed
only after the user explicitly acknowledges them (record the
acknowledgment in the session). Exit 0 — proceed.

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

5. **Pushback gate — a `pushback` construct.** If the user's
   edit/rejection makes the plan *weaker* than what you drafted
   AND you can render the concrete alternative (the
   decision-routine "pushback discipline"), do not silently
   comply — surface the disagreement as a `pushback` construct
   (the user's approach tagged "your approach", your alternative
   badged "I'd suggest instead", a "Why I'd push back"
   rationale) via the `elicit` skill's widget surface
   (`elicitation_render_widget` → `show_widget`), falling back to
   its `AskUserQuestion` mapping (alternative first, rationale as
   the lead-in) when the widget surface is unavailable. The
   `elicit` skill owns the round-trip and validation — see its
   "pushback construct" section. The user overrules (keeps their
   edit) or switches with one pick. Skip this gate when you
   genuinely agree with the edit, or when you cannot render a
   concrete alternative — pushback without an artifact is hedging.

## Stage 3: Approve

Show final summary: task count, scope, risks. Then:

Use `AskUserQuestion`: "Ready to start executing?"

- "Start executing"
- "Go back to review"

## Stage 4: Execute

Before the first task, when the plan belongs to a
`docs/specs/<slug>/` spec, run the execution-boundary gates
(`attune gates check execution --spec <slug> --changed <paths>`)
with the same G5 semantics as the Stage 2 gate — hard-stop on
`BLOCKED`, explicit user acknowledgment on `CHAIR_REQUIRED`.

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
6. **Severity-gated approval — a `decision` gate.** You have
   just run the quality gates, so you hold a *recommendation*,
   not a neutral menu. Render this as a `decision` construct
   (recommended option + rationale + per-option tradeoffs) via
   the `elicit` skill's widget surface
   (`elicitation_render_widget` → `show_widget`), and fall back
   to its `AskUserQuestion` mapping (recommended option first
   with `" (Recommended)"`, each tradeoff folded into that
   option's description, `rationale` as the lead-in) when the
   widget surface is unavailable. The `elicit` skill owns the
   round-trip and validation — see its "decision construct"
   section. It stays ONE question: the cards are presentation,
   not extra fields.

   If `"high"` severity (score < 50) — recommend **Fix and
   retry**:

   - options: "Fix and retry", "Acknowledge risk and continue"
   - `recommended`: "Fix and retry"
   - `rationale`: name the gate(s) that failed and the score —
     a high-severity task shipped forward compounds risk.
   - `option_notes`:
     - "Fix and retry": "Address the finding now, before it lands"
     - "Acknowledge risk and continue": "Ship as-is — risk moves
       downstream"

   If `"medium"` or `"low"` severity — recommend **Approve and
   continue**:

   - options: "Approve and continue", "Redo with new
     instructions", "Auto-run remaining tasks"
   - `recommended`: "Approve and continue"
   - `rationale`: gates passed at acceptable severity — the task
     is ready to land.
   - `option_notes`:
     - "Approve and continue": "Accept this task, move to the next"
     - "Redo with new instructions": "Re-run the task with changes"
     - "Auto-run remaining tasks": "Stop gating; run the rest
       unattended"

7. Save state after each decision:

   ```python
   from attune.spec import save_state
   state.completed.append(task.task_id)
   save_state(state)
   ```

### Execution status report — a `progress` construct

At a multi-task checkpoint — **on resume** (Stage 5), and **after an
"Auto-run remaining tasks" batch finishes** — report where the run
stands as a `progress` construct rather than prose. This is the
multi-task overview; it complements the per-task `decision` gate above
(that gates ONE task; this summarizes ALL of them).

Build one `progress` field and render it via the `elicit` skill's widget
surface (`elicitation_render_widget` → `show_widget`), falling back to
its `AskUserQuestion` mapping — see the `elicit` skill's "progress
construct" section:

- `progress_items`: one `{label, status, detail?}` per task — `done`
  for completed tasks, `in_flight` for the current task, `blocked` for
  any task that failed a high-severity gate and was deferred
  ("Acknowledge risk and continue"). Use the task name as `label` and
  the failing gate + score as `detail`.
- `options`: the labels of the `blocked` tasks (must equal the blocked
  subset). The picker asks **"which blocked task to fix/retry?"** —
  selecting one re-enters the per-task implement + gate flow for it.
- `recommended`: the blocked task to tackle first (e.g. highest
  severity); badged "suggested next".
- `rationale`: a one-line run summary (e.g. "6/8 done, 2 deferred on
  gate failures").

When **no task is blocked**, build it display-only (`options: []`,
`required: false`) — it renders as a clean done/in_flight status board
with no picker.

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

- **Batch the kickoff, not the gates.** Stage 1's kickoff
  (outcome + scope + concerns) is the ONE place to batch
  fields into a single form (via `elicit`). Every other
  prompt — the mode picker and the review / approve /
  execute gates — stays a **single** question: they're
  sequential decisions that branch on the prior answer, so
  the §4 rule keeps them one at a time. A single question
  may still be a `decision` construct (Stage 4's approval
  gate) — that enriches one choice with a recommendation
  and tradeoffs; it does **not** batch multiple fields, so
  it honours the one-question rule.
- **ALWAYS use AskUserQuestion** between stages
- **ALWAYS save_state()** after each task approval
- **Show progress bar** before each task
- **Voice layer**: use the attune voice personality
  — friendly senior engineer
- **Power users**: the plan file is always editable.
  If the user says "let me edit the plan," pause and
  wait for them to re-invoke
