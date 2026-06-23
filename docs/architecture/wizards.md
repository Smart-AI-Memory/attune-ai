# Wizards

## Overview

Wizards are **interactive, multi-step workflows** that guide a user
through a complex development task by breaking it into sequential steps
— questions that collect input, LLM calls, task decomposition, and
review/confirm gates. Each wizard runs to a `WizardResult` carrying the
collected data, generated output, and cost/duration metrics.

The registry is a set of **module-level functions** in
`attune.wizards` (there is no registry class): `list_wizards()`,
`get_wizard(id)`, `register_wizard(...)`, `save_custom_wizard(...)`, and
`delete_custom_wizard(...)`. Five wizards ship built in — `debug`,
`refactor`, `release-prep`, `security`, and `test-gen`.

You reach wizards two ways:

- the Python API — `from attune.wizards import get_wizard, list_wizards`
  (the primary surface, documented throughout);
- the **`/wizard`** skill, inside a Claude Code conversation.

There is **no `attune wizard` CLI command and no MCP tool** — wizards
run through the Python API or the skill. A wizard's `run()` method is
**async** — `await` it.

## Concepts

### The four core types

| Type | Role |
|------|------|
| `WizardStep` | One step — `id`, `name`, `description`, `step_type`, an optional `prompt_template`, `questions`, a `tier`, and a `condition`. |
| `WizardConfig` | Wizard metadata — `wizard_id`, `name`, `description`, `domain`, `version`, `source`, `estimated_cost_range`, `estimated_duration_minutes`. |
| `BaseWizard` | Abstract base all wizards inherit from; drives step execution via the async `run()` method. |
| `WizardResult` | The outcome — `wizard_id`, `run_id`, `success`, `steps_completed`, `collected_data`, `generated_output`, `tasks`, `total_cost`, `total_duration_ms`, `error`. |

### Step types

A step's `step_type` is a `StepType`: `question` (collect user input),
`llm_call` (run a model call), `task_decompose` (break work into an
XML task tree via `TaskDecomposer`), `review`, `preview`, and
`confirm` (human gates). The wizard walks the steps in order, honoring
each step's optional `condition`.

### Running a built-in wizard

`get_wizard(id)` returns the wizard **class** (or `None`); instantiate
it and `await` its `run()`:

- `BaseWizard(ask_user_callback=None, provider=None, **workflow_kwargs)`
  — the `ask_user_callback` is how the wizard collects input for
  `question` steps (wired to `AskUserQuestion` inside Claude Code);
- `run(initial_context=None)` is a coroutine returning a
  `WizardResult`.

A subclass customizes two hooks: `build_prompt_context(step)` (prepare
the model prompt) and `process_step_result(step, result)` (handle a
step's output).

### The built-in wizards

`list_wizards()` returns the registered `WizardConfig`s. Five ship
built in:

| `wizard_id` | Class | Guides |
|-------------|-------|--------|
| `debug` | `DebugWizard` | Systematic debugging, step by step. |
| `refactor` | `RefactorWizard` | Code restructuring with safety checks. |
| `release-prep` | `ReleasePrepWizard` | Release preparation and validation. |
| `security` | `SecurityWizard` | Guided security audit with risk assessment. |
| `test-gen` | `TestGenWizard` | Interactive test-suite generation. |

### Custom wizards — subclass or config-driven

Two ways to add a wizard:

- **Subclass `BaseWizard`** and implement `build_prompt_context` /
  `process_step_result`, then `register_wizard(id, cls)` to make it
  discoverable.
- **Config-driven** — build a `ConfigDrivenWizard(config, steps)` from
  a `WizardConfig` + a list of `WizardStep`s (no subclass needed), or
  persist a definition with `save_custom_wizard(data, base_dir=None)`
  (returns the saved `Path`) and remove it with
  `delete_custom_wizard(id, base_dir=None)`.

## Design & extension

### Design decisions

- **Functions, not a registry class.** The registry is a small set of
  module-level functions over a dict of wizard classes — simpler than a
  class, and the built-ins register themselves at import.
- **Steps as data.** A wizard is a sequence of `WizardStep`s with typed
  `StepType`s; `ConfigDrivenWizard` runs a config + steps with no
  subclass, so simple wizards need no code.
- **Interactive by design.** `question` / `confirm` steps put the user
  in the loop via the `ask_user_callback`, distinguishing wizards from
  fire-and-forget workflows.
- **The result is data.** `run()` returns a `WizardResult` (collected
  data, generated output, tasks, cost/duration) — the skill and any
  caller render the same object.

### Extension points

- **Add a wizard:** subclass `BaseWizard` + `register_wizard`, or build
  a `ConfigDrivenWizard` from a config + steps.
- **Persist a definition:** `save_custom_wizard(data)` /
  `delete_custom_wizard(id)`.
- **Customize prompting:** override `build_prompt_context(step)` and
  `process_step_result(step, result)`.
- **Decompose work:** use a `task_decompose` step (backed by
  `TaskDecomposer`) to break a task into an XML task tree.

<!-- attune-generated: source_hash=0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0 feature=wizards kind=architecture generated_at=2026-06-23 -->
