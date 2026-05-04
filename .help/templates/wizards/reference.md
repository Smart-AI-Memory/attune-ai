---
type: reference
feature: wizards
depth: reference
generated_at: 2026-05-04T02:40:16.892185+00:00
source_hash: 76c270cd6e9ba25a7ffd711122874b94ee586d10897f8210e8c4844f8ecd9f81
status: generated
---

# Wizards reference

Build and run interactive, multi-step workflows. Register built-in wizards for debugging, refactoring, security audits, and test generation. Create custom wizards from YAML definitions.

## Classes

| Class | Description |
|-------|-------------|
| `StepType` | Execution mode for a wizard step |
| `WizardStep` | Definition of a single wizard step |
| `WizardConfig` | Metadata for a wizard |
| `WizardResult` | Result from a completed wizard run |
| `BaseWizard` | Abstract base class for interactive, multi-step wizards |
| `DebugWizard` | Guided debugging wizard |
| `RefactorWizard` | Guided refactoring wizard |
| `ReleasePrepWizard` | Guided release preparation wizard |
| `SecurityWizard` | Guided security audit wizard |
| `TestGenWizard` | Guided test generation wizard |

## WizardStep fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Step identifier |
| `name` | `str` | | Display name |
| `description` | `str` | `''` | Step description |
| `step_type` | `StepType` | `StepType.QUESTION` | Execution mode |
| `prompt_template` | `str | None` | `None` | Template for LLM prompts |
| `tier` | `str` | `'capable'` | Model tier requirement |
| `questions` | `list[FormQuestion] | None` | `None` | User input questions |
| `condition` | `Callable[[WizardSession], bool] | None` | `None` | Step execution condition |
| `max_tokens` | `int` | `4096` | Maximum response tokens |
| `prompt_context_template` | `dict[str, Any] | None` | `None` | Context for prompt rendering |
| `review_source_step_id` | `str | None` | `None` | Step to review for output |

## WizardConfig fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `wizard_id` | `str` | | Unique wizard identifier |
| `name` | `str` | | Display name |
| `description` | `str` | | Wizard description |
| `domain` | `str` | `'development'` | Application domain |
| `version` | `str` | `'1.0.0'` | Wizard version |
| `source` | `str` | `'builtin'` | Source type |
| `estimated_cost_range` | `tuple[float, float]` | `(0.01, 0.5)` | Cost estimate range |
| `estimated_duration_minutes` | `int` | `5` | Time estimate |

## WizardResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `wizard_id` | `str` | | Wizard that ran |
| `run_id` | `str` | | Unique run identifier |
| `success` | `bool` | | Whether wizard completed successfully |
| `steps_completed` | `list[str]` | `[]` | IDs of completed steps |
| `collected_data` | `dict[str, Any]` | `{}` | Data gathered from user |
| `generated_output` | `str | dict[str, Any]` | `''` | Wizard output |
| `tasks` | `list[dict[str, Any]]` | `[]` | Generated task list |
| `total_cost` | `float` | `0.0` | Total API cost |
| `total_duration_ms` | `float` | `0.0` | Total execution time |
| `error` | `str | None` | `None` | Error message if failed |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `register_wizard` | `wizard_id: str, wizard_class: type[BaseWizard]` | `None` | Register a wizard class |
| `get_wizard` | `wizard_id: str` | `type[BaseWizard] | None` | Get a wizard class by ID |
| `list_wizards` | | `list[WizardConfig]` | List all registered wizard configs |
| `save_custom_wizard` | `wizard_data: dict[str, Any], base_dir: str | None = None` | `Path` | Save a custom wizard definition to YAML |
| `delete_custom_wizard` | `wizard_id: str, base_dir: str | None = None` | `bool` | Delete a custom wizard definition |

## BaseWizard methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `ask_user_callback: AskUserQuestionCallback | None = None, provider: str | None = None, **workflow_kwargs: Any` | `None` | Initialize wizard with callbacks |
| `run` | `initial_context: dict[str, Any] | None = None` | `WizardResult` | Run the wizard workflow |
| `build_prompt_context` | `step: WizardStep` | `PromptContext` | Build context for step prompts |
| `process_step_result` | `step: WizardStep, result: dict[str, Any]` | `None` | Process step execution results |

## WizardResult methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Convert result to dictionary |

## Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `save_custom_wizard` | `ValueError` | `'Cannot write wizard YAML: {...}'` |
| `delete_custom_wizard` | `ValueError` | `"Cannot delete built-in wizard: '{...}'"` |

## Constants

| Constant | Value |
|----------|-------|
| `SCHEMA_VERSION` | `'1.0'` |
