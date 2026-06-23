---
feature: wizards
summary: Multi-step guided interactive workflows that walk users through complex tasks
tags: [wizards, interactive]
source_globs:
  - src/attune/wizards/**
nav:
  help: wizards
  mkdocs:
    how-to: how-to/wizards
    architecture: architecture/wizards
    reference: reference/wizards
---

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

## Quickstart

List the built-in wizards, then run one. `run()` is a coroutine, so
drive it with `asyncio.run`:

```python
import asyncio

from attune.wizards import get_wizard, list_wizards


async def main() -> None:
    for cfg in list_wizards():
        print(cfg.wizard_id, "-", cfg.name)

    wizard_cls = get_wizard("debug")
    if wizard_cls is not None:
        result = await wizard_cls().run()
        print(result.success, result.wizard_id)


asyncio.run(main())
```

`get_wizard` returns the wizard class (or `None` if the id is
unknown); instantiate it and `await run()`.

## Tasks

### Run a built-in wizard

**Goal:** run a guided wizard and read its result.

**Steps:**

```python
import asyncio

from attune.wizards import get_wizard


async def main() -> None:
    wizard_cls = get_wizard("security")
    if wizard_cls is None:
        print("unknown wizard")
        return

    result = await wizard_cls().run(initial_context={"path": "src/"})
    print("success:", result.success)
    print("output:", result.generated_output)
    print("cost:", result.total_cost)


asyncio.run(main())
```

**Verify:** `run()` is a coroutine — `await` it. The result is a
`WizardResult` with `success`, `collected_data`, `generated_output`,
`tasks`, `total_cost`, `total_duration_ms`, and `error` on failure.
`initial_context` seeds the run.

### Discover what's available

**Goal:** list the registered wizards and their metadata.

**Steps:**

```python
from attune.wizards import get_wizard, list_wizards

for cfg in list_wizards():
    print(f"{cfg.wizard_id}: {cfg.name} ({cfg.domain})")
    print(f"  ~{cfg.estimated_duration_minutes} min, {cfg.estimated_cost_range}")

cls = get_wizard("test-gen")   # -> TestGenWizard class, or None
```

**Verify:** `list_wizards()` returns `WizardConfig` objects (sync). The
five built-ins are `debug`, `refactor`, `release-prep`, `security`,
and `test-gen`. `get_wizard(id)` returns the class or `None`.

### Register a custom wizard

**Goal:** make your own wizard discoverable.

**Steps:**

```python
from attune.wizards import BaseWizard, register_wizard


class MyWizard(BaseWizard):
    def build_prompt_context(self, step):
        ...

    def process_step_result(self, step, result):
        ...


register_wizard("my-wizard", MyWizard)
```

**Verify:** after `register_wizard`, `get_wizard("my-wizard")` returns
your class and it appears in `list_wizards()`. For a config-only
wizard, build a `ConfigDrivenWizard(config, steps)` or persist a
definition with `save_custom_wizard(data)`.

## Reference

The public surface is the registry functions and the wizard
classes/dataclasses, all re-exported from `attune.wizards`.

### Registry functions — `attune.wizards`

| Function | Purpose |
|----------|---------|
| `list_wizards() -> list[WizardConfig]` | All registered wizard configs (built-in + custom). |
| `get_wizard(wizard_id) -> type[BaseWizard] \| None` | The wizard class for an id, or `None`. |
| `register_wizard(wizard_id, wizard_class) -> None` | Register a `BaseWizard` subclass. |
| `save_custom_wizard(wizard_data, base_dir=None) -> Path` | Persist a config-driven wizard definition; returns the saved path. |
| `delete_custom_wizard(wizard_id, base_dir=None) -> bool` | Remove a saved custom wizard. |

### Classes — `attune.wizards`

| Symbol | Purpose |
|--------|---------|
| `BaseWizard(ask_user_callback=None, provider=None, **kwargs)` | Abstract base; async `run(initial_context=None) -> WizardResult`; hooks `build_prompt_context(step)` and `process_step_result(step, result)`. |
| `ConfigDrivenWizard(config, steps, **kwargs)` | A wizard built from a `WizardConfig` + `list[WizardStep]`, no subclass needed. |
| `WizardSession` | Per-run session state. |
| `TaskDecomposer` / `DecomposedTask` | Back the `task_decompose` step type (XML task decomposition). |

### Dataclasses — `attune.wizards`

| Type | Fields |
|------|--------|
| `WizardConfig` | `wizard_id`, `name`, `description`, `domain`, `version`, `source`, `estimated_cost_range`, `estimated_duration_minutes`. |
| `WizardStep` | `id`, `name`, `description`, `step_type`, `prompt_template`, `tier`, `questions`, `condition`, `max_tokens`, `prompt_context_template`, `review_source_step_id`. |
| `WizardResult` | `wizard_id`, `run_id`, `success`, `steps_completed`, `collected_data`, `generated_output`, `tasks`, `total_cost`, `total_duration_ms`, `error`. |
| `StepType` | `question`, `llm_call`, `task_decompose`, `review`, `preview`, `confirm`. |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python | `get_wizard(<id>)`, then `await <cls>().run()`; `list_wizards()` to discover. |
| Skill | `/wizard` in a Claude Code conversation. |

No `attune wizard` CLI command and no MCP tool exist for wizards.

## Comparison

Wizards differ from workflows in interaction model:

| | Wizards | Workflows |
|--|---------|-----------|
| Interaction | Interactive — collect input mid-run via `question`/`confirm` steps | Non-interactive — run to completion from inputs |
| Entry | `get_wizard(id)` + `await run()`, or `/wizard` skill | `attune workflow run <slug>` / the workflow class |
| Output | `WizardResult` (collected data + generated output) | `WorkflowResult` |

Reach for a **wizard** when the task needs the user in the loop
(answering questions, confirming gates); reach for a **workflow** when
the run is fully specified up front. Several builtins mirror a
workflow (`release-prep`, `security`, `test-gen`) but wrap it in a
guided, interactive flow.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'BaseWizard.run' was never awaited` | `run()` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `AttributeError: 'NoneType' object has no attribute ...` after `get_wizard` | The wizard id is unknown; `get_wizard` returned `None` | Check `get_wizard(id) is not None`; list ids with `list_wizards()` | high |
| A `question` step never prompts / hangs | No `ask_user_callback` wired (outside Claude Code) | Pass an `ask_user_callback` to the wizard, or run via the `/wizard` skill | medium |
| `WizardResult.success` is `False` with a populated `error` | A step failed (LLM call, validation, or an aborted confirm) | Read `result.error` and `result.steps_completed` to see where it stopped | medium |
| Custom wizard not found by `get_wizard` | It was never `register_wizard`'d (or `save_custom_wizard`'d) | Register the class or save the definition first | low |

### Risk areas

- **`run()` is async.** Forgetting to `await` it is the most common
  mistake.
- **There is no registry class.** Use the module-level functions
  (`list_wizards`, `get_wizard`, …) — not a `WizardRegistry`.
- **`question` steps need a callback.** Outside the `/wizard` skill,
  supply an `ask_user_callback` or the wizard can't collect input.

### Diagnosis order

1. Confirm you are awaiting: `await get_wizard(id)().run()`.
2. Confirm the id exists: `get_wizard(id) is not None` /
   `list_wizards()`.
3. On failure, read `result.error` and `result.steps_completed`.
4. If a `question` step stalls, check the `ask_user_callback` wiring.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** How do I run a wizard?
  **A:** `get_wizard(id)` returns the class; instantiate it and
  `await run()`. Or use the `/wizard` skill in a conversation. There's
  no `attune wizard` CLI command.
- **Q:** Which wizards ship built in?
  **A:** Five — `debug`, `refactor`, `release-prep`, `security`,
  `test-gen` (`list_wizards()` to confirm).
- **Q:** Are the calls async?
  **A:** `run()` is a coroutine — `await` it. The registry functions
  (`list_wizards`, `get_wizard`) are synchronous.
- **Q:** Is there a `WizardRegistry` class?
  **A:** No. The registry is module-level functions in
  `attune.wizards` (`list_wizards`, `get_wizard`, `register_wizard`,
  `save_custom_wizard`, `delete_custom_wizard`).
- **Q:** How do I add my own wizard?
  **A:** Subclass `BaseWizard` and `register_wizard(id, cls)`, or build
  a `ConfigDrivenWizard` / `save_custom_wizard(data)`.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  the registry functions plus `BaseWizard`, `ConfigDrivenWizard`, the
  `WizardConfig` / `WizardStep` / `WizardResult` dataclasses, `StepType`,
  and `WizardSession` — all from `attune.wizards`.
- **`await` the run.** `run()` is the only async method; the registry
  functions are sync.
- **Use the skill for interactive runs.** `/wizard` wires the
  `ask_user_callback` to `AskUserQuestion`; a bare Python run needs you
  to supply one for `question` steps.
- **Discover before you run.** `list_wizards()` gives ids, names,
  domains, and cost/duration estimates.

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
