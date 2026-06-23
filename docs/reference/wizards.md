# Wizards

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

<!-- attune-generated: source_hash=0383bd1ba48703a82f700d50a22fc06aa7d00b38cf01550ca0a1f41adea84bc0 feature=wizards kind=reference generated_at=2026-06-23 -->
