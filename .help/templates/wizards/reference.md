---
type: reference
feature: wizards
depth: reference
generated_at: 2026-04-14T15:27:21.691764+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards reference

## Classes

### Data Types

| Class | Description |
|-------|-------------|
| `StepType` | Execution mode for a wizard step |
| `WizardStep` | Definition of a single wizard step |
| `WizardConfig` | Metadata for a wizard |
| `WizardResult` | Result from a completed wizard run |

### Base Classes

| Class | Description |
|-------|-------------|
| `BaseWizard` | Abstract base class for interactive, multi-step wizards |

### Built-in Wizards

| Class | Description |
|-------|-------------|
| `DebugWizard` | Guided debugging wizard |
| `RefactorWizard` | Guided refactoring wizard |
| `ReleasePrepWizard` | Guided release preparation wizard |
| `SecurityWizard` | Guided security audit wizard |
| `TestGenWizard` | Guided test generation wizard |

## Dataclass Fields

### WizardStep

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `name` | `str` | — |
| `description` | `str` | `''` |
| `step_type` | `StepType` | `StepType.QUESTION` |
| `prompt_template` | `str \| None` | `None` |
| `tier` | `str` | `'capable'` |
| `questions` | `list[FormQuestion] \| None` | `None` |
| `condition` | `Callable[[WizardSession], bool] \| None` | `None` |
| `max_tokens` | `int` | `4096` |
| `prompt_context_template` | `dict[str, Any] \| None` | `None` |
| `review_source_step_id` | `str \| None` | `None` |

### WizardConfig

| Field | Type | Default |
|-------|------|---------|
| `wizard_id` | `str` | — |
| `name` | `str` | — |
| `description` | `str` | — |
| `domain` | `str` | `'development'` |
| `version` | `str` | `'1.0.0'` |
| `source` | `str` | `'builtin'` |
| `estimated_cost_range` | `tuple[float, float]` | `(0.01, 0.5)` |
| `estimated_duration_minutes` | `int` | `5` |

### WizardResult

| Field | Type | Default |
|-------|------|---------|
| `wizard_id` | `str` | — |
| `run_id` | `str` | — |
| `success` | `bool` | — |
| `steps_completed` | `list[str]` | `field(default_factory=list)` |
| `collected_data` | `dict[str, Any]` | `field(default_factory=dict)` |
| `generated_output` | `str \| dict[str, Any]` | `''` |
| `tasks` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `total_cost` | `float` | `0.0` |
| `total_duration_ms` | `float` | `0.0` |
| `error` | `str \| None` | `None` |

## Methods

### BaseWizard

| Method | Parameters | Returns |
|--------|------------|---------|
| `__init__` | `ask_user_callback: AskUserQuestionCallback \| None = None, provider: str \| None = None, **workflow_kwargs: Any` | `None` |
| `run` | `initial_context: dict[str, Any] \| None = None` | `WizardResult` |
| `build_prompt_context` | `step: WizardStep` | `PromptContext` |
| `process_step_result` | `step: WizardStep, result: dict[str, Any]` | `None` |

### WizardResult

| Method | Parameters | Returns |
|--------|------------|---------|
| `to_dict` | — | `dict[str, Any]` |

### Wizard Subclasses

All built-in wizard classes (`DebugWizard`, `RefactorWizard`, `ReleasePrepWizard`, `SecurityWizard`, `TestGenWizard`) inherit from `BaseWizard` and override:

- `build_prompt_context(step: WizardStep) -> PromptContext`
- `process_step_result(step: WizardStep, result: dict[str, Any]) -> None`

`RefactorWizard` and `SecurityWizard` also override `__init__(**kwargs: Any) -> None`.

## Functions

| Function | Parameters | Returns | Raises |
|----------|------------|---------|--------|
| `register_wizard` | `wizard_id: str, wizard_class: type[BaseWizard]` | `None` | — |
| `get_wizard` | `wizard_id: str` | `type[BaseWizard] \| None` | — |
| `list_wizards` | — | `list[WizardConfig]` | — |
| `save_custom_wizard` | `wizard_data: dict[str, Any], base_dir: str \| None = None` | `Path` | `ValueError` |
| `delete_custom_wizard` | `wizard_id: str, base_dir: str \| None = None` | `bool` | `ValueError` |

### Exception Messages

| Function | Exception | Message |
|----------|-----------|---------|
| `save_custom_wizard` | `ValueError` | `'Cannot write wizard YAML: {...}'` |
| `delete_custom_wizard` | `ValueError` | `"Cannot delete built-in wizard: '{...}'"` |

## Constants

| Constant | Value |
|----------|-------|
| `SCHEMA_VERSION` | `'1.0'` |
