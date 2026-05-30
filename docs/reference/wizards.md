---
description: Reference for `attune.wizards` — guided multi-step wizards with XML task decomposition. Covers the 5 built-in developer wizards, the `BaseWizard` lifecycle, and config-driven YAML wizards.
---

# Wizards

`attune.wizards` is the runtime for **guided, multi-step interactive
wizards** in Attune AI. A wizard is an ordered sequence of typed steps
(questions, LLM calls, task decomposition, review, preview, confirm)
that walks a user through a task with structured prompts and
checkpoints.

It ships with 5 built-in developer-focused wizards and a config-driven
mode that lets users define custom wizards in YAML — no Python
required.

> **Note**: This is not a collection of "industry-specific" or
> "domain-compliance" wizards. The package has no Healthcare, Finance,
> Legal, HIPAA, or SOC2 wizards. Earlier docs that described such a
> surface were fiction — see the `doc-fiction-cleanup` spec.

---

## Public API at a glance

```python
from attune.wizards import (
    BaseWizard,
    ConfigDrivenWizard,
    DecomposedTask,
    StepType,
    TaskDecomposer,
    WizardConfig,
    WizardResult,
    WizardSession,
    WizardStep,
    delete_custom_wizard,
    get_wizard,
    list_wizards,
    register_wizard,
    save_custom_wizard,
)
```

These are the only names exported from `attune.wizards`
(`src/attune/wizards/__init__.py`).

---

## Listing and running wizards

### Listing wizards (Python)

`list_wizards()` is a module-level function. It returns a list of
`WizardConfig` objects sorted by `wizard_id`, covering built-ins plus
any custom YAML wizards loaded from `.attune/wizards/`.

```python
from attune.wizards import list_wizards

for cfg in list_wizards():
    print(f"{cfg.wizard_id:14} {cfg.name:30} ({cfg.source})")
```

### Getting and running a wizard (Python)

```python
import asyncio
from attune.wizards import get_wizard

WizardCls = get_wizard("debug")          # type[BaseWizard] | None
wizard = WizardCls(ask_user_callback=None)
result = asyncio.run(wizard.run({"error": "TypeError: ..."}))

print(result.success, result.steps_completed)
```

`get_wizard()` checks the in-memory registry, then triggers entry-point
discovery (group `empathy.wizards`), then loads built-ins, then loads
custom YAML wizards from `.attune/wizards/`. Returns `None` if the
wizard ID is not found.

### Listing and running wizards (Claude Code skill)

In Claude Code, the `/wizard` skill drives the runtime. Routes (from
`.claude/skills/wizard/SKILL.md`):

```text
/wizard                      Ask what to do
/wizard list                 List available wizards
/wizard run debug            Debug wizard
/wizard run test-gen         Test generation wizard
/wizard run refactor         Refactoring wizard
/wizard run security         Security wizard
/wizard run release-prep     Release prep wizard
/wizard create               Create a custom wizard
/wizard edit                 Edit a wizard
```

The skill aliases (e.g. `wizard-debug`, `wizard-create`) are listed in
`src/attune/cli_router.py`.

> There is currently no top-level `attune wizard ...` subcommand on
> the Python CLI. `attune health` does include a wizard discovery
> probe — it calls `list_wizards()` and reports the count.

---

## The 5 built-in wizards

The built-in set is defined in
`src/attune/wizards/builtin/__init__.py` as the `BUILTIN_WIZARDS` dict:

| Wizard ID      | Class               | Domain      | What it does                                                |
|----------------|---------------------|-------------|-------------------------------------------------------------|
| `debug`        | `DebugWizard`       | development | Gather error details, analyze root cause, decompose a fix   |
| `test-gen`     | `TestGenWizard`     | testing     | Pick a target, analyze untested paths, plan test files      |
| `refactor`     | `RefactorWizard`    | development | Describe goal, analyze structure, plan incremental refactor |
| `security`     | `SecurityWizard`    | (varies)    | Scope a scan, generate findings, plan remediations          |
| `release-prep` | `ReleasePrepWizard` | release     | Version info, readiness check, optional changelog, plan     |

Each built-in subclasses `BaseWizard`, defines a `WizardConfig`, and
declares an ordered `steps` list. For example, `DebugWizard` runs:

1. `gather_info` (QUESTION) — error description, file, stack-trace flag
2. `analyze` (LLM_CALL, `bug-analysis` template, `capable` tier)
3. `review_analysis` (REVIEW of the `analyze` result)
4. `decompose_fix` (TASK_DECOMPOSE)
5. `preview` (PREVIEW)
6. `confirm` (CONFIRM)

`RefactorWizard` and `SecurityWizard` additionally delegate their
analysis step to a heavier workflow (`RefactorPlanWorkflow` and
`SecurityAuditWorkflow` respectively) for multi-stage scanning while
preserving the wizard-guided UX.

---

## Step types

The wizard runtime supports six step types, defined as the `StepType`
enum in `src/attune/wizards/_types.py`:

| `StepType`        | What it does                                                                                  |
|-------------------|-----------------------------------------------------------------------------------------------|
| `QUESTION`        | Collect user input via `AskUserQuestion` (rendered through `SocraticFormEngine`).             |
| `LLM_CALL`        | Render an XML prompt and call an LLM at the step's tier (`cheap` / `capable` / `premium`).    |
| `TASK_DECOMPOSE`  | Use `TaskDecomposer` to break the current problem into structured XML sub-tasks.              |
| `REVIEW`          | Show the result of a prior `LLM_CALL` step and ask "does this look right?" (up to 2 retries). |
| `PREVIEW`         | Format collected data, step results, and tasks into a preview block and store it.             |
| `CONFIRM`         | Final yes/no gate; "no" aborts the wizard cleanly.                                            |

A step can also carry a `condition: Callable[[WizardSession], bool]`
that, when it returns `False`, causes the step to be skipped.
`ReleasePrepWizard` uses this to skip changelog generation when the
user opts out.

---

## `BaseWizard` lifecycle

`BaseWizard` (in `src/attune/wizards/base.py`) is an abstract class.
Subclasses must define:

- `config: WizardConfig` — wizard identity and cost/duration estimates.
- `steps: list[WizardStep]` — the ordered step list.
- `build_prompt_context(step) -> PromptContext` — builds the prompt
  context for `LLM_CALL` and `TASK_DECOMPOSE` steps from session state.
- `process_step_result(step, result) -> None` — stores or transforms
  the LLM response for use by later steps.

Everything else — step dispatch, retries, the session, the form
engine, the XML prompt rendering, the preview/confirm UX — is provided
for free.

`BaseWizard.run(initial_context=None)` is the single entry point. It
is `async`, creates a fresh `WizardSession`, iterates over `self.steps`,
dispatches each one by `StepType`, and returns a `WizardResult` with:

- `success: bool`
- `steps_completed: list[str]`
- `collected_data: dict[str, Any]` (everything from QUESTION steps)
- `generated_output: str | dict` (the PREVIEW text)
- `tasks: list[dict]` (from TASK_DECOMPOSE)
- `total_cost: float` and `total_duration_ms: float`
- `error: str | None` if the run failed

If a `CONFIRM` step gets a "no" answer, the wizard raises an internal
`_WizardAbort` and exits cleanly with `success=True` but no further
steps.

### Minimal custom wizard (Python)

```python
from typing import Any
from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.wizards import BaseWizard, StepType, WizardConfig, WizardStep


class HelloWizard(BaseWizard):
    config = WizardConfig(
        wizard_id="hello",
        name="Hello Wizard",
        description="Trivial example",
    )

    steps = [
        WizardStep(
            id="ask",
            name="Ask name",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="name",
                    text="What's your name?",
                    type=QuestionType.TEXT_INPUT,
                ),
            ],
        ),
        WizardStep(
            id="greet",
            name="Generate greeting",
            step_type=StepType.LLM_CALL,
            tier="cheap",
        ),
        WizardStep(id="preview", name="Preview", step_type=StepType.PREVIEW),
        WizardStep(id="confirm", name="Confirm", step_type=StepType.CONFIRM),
    ]

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        name = self._session.get("name", "stranger")
        return PromptContext(
            role="friendly assistant",
            goal=f"Write a one-sentence greeting for {name}.",
            instructions=["Be warm and concise."],
            input_type="name",
            input_payload=name,
        )

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        self._session.set("greeting", result.get("summary", ""))
```

Register it (once per process) with `register_wizard("hello", HelloWizard)`,
or expose it via the `empathy.wizards` entry-point group for automatic
discovery.

---

## Config-driven wizards (YAML)

`ConfigDrivenWizard` lets users author wizards entirely in YAML. A
custom wizard is a single file under `.attune/wizards/<wizard_id>.yaml`.

### YAML schema (v1.0)

Required top-level fields (validated by `_validate_schema` in
`config_driven.py`):

- `wizard_id`
- `name`
- `steps` (non-empty list)

Optional: `description`, `domain`, `version`,
`estimated_cost_range` (list of two floats),
`estimated_duration_minutes`, `schema_version`.

Each step must include `id` and a valid `step_type`
(`question`, `llm_call`, `task_decompose`, `review`, `preview`, `confirm`).
For `llm_call` steps, supply a declarative `prompt_context` block —
`role`, `goal`, `instructions`, `constraints`, `input_type`,
`input_payload` — with `{session.var_name}` placeholders that the
runtime substitutes from current session state.

### Example

```yaml
schema_version: "1.0"
wizard_id: "code-migration"
name: "Code Migration Wizard"
description: "Guide through migrating code between frameworks"
domain: "development"

steps:
  - id: "gather_info"
    name: "Migration Scope"
    step_type: "question"
    questions:
      - id: "source"
        text: "Migrating FROM which framework?"
        type: "text_input"
  - id: "analyze"
    step_type: "llm_call"
    tier: "capable"
    prompt_context:
      role: "migration specialist"
      goal: "Plan migration from {session.source}"
```

### Lifecycle helpers

- `save_custom_wizard(data, base_dir=None)` — validate, write
  `<wizard_id>.yaml` under `.attune/wizards/` (or `base_dir`), and
  register the wizard.
- `delete_custom_wizard(wizard_id, base_dir=None)` — remove the YAML
  and unregister. Raises `ValueError` if `wizard_id` is a built-in
  (the five IDs in `BUILTIN_WIZARDS`).

---

## Sessions

`WizardSession` (in `src/attune/wizards/session.py`) is the mutable
state object that lives for the duration of one `wizard.run()` call.
It is created automatically; subclasses interact with it via
`self._session` in `build_prompt_context` and `process_step_result`.

Key fields: `wizard_id`, `run_id` (12-hex), `initial_context`,
`collected_data`, `step_results`, `tasks`, `steps_completed`,
`steps_skipped`, `generated_output`, `total_cost`, `started_at`.

`session.get(key, default)` does a layered lookup —
`collected_data` first, then `initial_context`.

---

## Discovery & registration

`get_wizard()` and `list_wizards()` both trigger three loaders, each
guarded so they run at most once per process:

1. `_discover_wizards()` — entry-point group `empathy.wizards`
2. `_load_builtins()` — the `BUILTIN_WIZARDS` dict
3. `_load_custom_wizards()` — YAML files in `.attune/wizards/`

`register_wizard(wizard_id, wizard_class)` is the manual hook — useful
for tests or in-process registration of Python wizards.

---

## See also

- `src/attune/wizards/` — implementation (start with `__init__.py`,
  `base.py`, `_types.py`, `registry.py`, `config_driven.py`).
- `src/attune/wizards/builtin/` — the five built-in wizards.
- `.claude/skills/wizard/SKILL.md` — the Claude Code skill that drives
  the wizard runtime in a session.
- `attune health` — includes a wizard discovery probe that calls
  `list_wizards()`.
