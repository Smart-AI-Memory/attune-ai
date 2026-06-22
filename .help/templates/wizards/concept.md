---
type: concept
feature: wizards
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Wizards

Interactive, multi-step workflows that guide users through complex development tasks by breaking them into sequential steps with prompts, questions, and validation.

## Core structure

Wizards are built from these components:

**`WizardStep`** — A single step in the workflow, containing an ID, name, description, execution type, and optional prompt template. Steps can be questions that collect user input or automated actions that process data.

**`WizardConfig`** — Metadata describing the wizard's purpose, domain (like "development"), estimated cost and duration, and version information.

**`BaseWizard`** — The abstract foundation that all wizards inherit from. It handles step execution, context building, and result collection through a standardized `run()` method.

**`WizardResult`** — The final output containing the wizard ID, completion status, collected data, generated output, and execution metrics like cost and duration.

## Built-in wizard types

Attune includes five specialized wizards for common development scenarios:

- **`DebugWizard`** — Guides systematic debugging with step-by-step problem identification
- **`RefactorWizard`** — Walks through code restructuring with safety checks
- **`ReleasePrepWizard`** — Automates release preparation tasks and validation
- **`SecurityWizard`** — Conducts guided security audits with risk assessment
- **`TestGenWizard`** — Generates comprehensive test suites through interactive prompting

Each wizard customizes the base workflow by implementing `build_prompt_context()` to prepare AI prompts and `process_step_result()` to handle user responses.

## Step execution flow

Wizards execute through a consistent pattern:

1. Each step defines its execution mode via `StepType` (question vs. automated action)
2. The wizard builds context using the step's prompt template and current session data
3. For question steps, the wizard presents forms to collect user input
4. For action steps, the wizard processes data automatically
5. Results are validated and stored before moving to the next step
6. The final `WizardResult` contains all collected data and generated outputs

## Custom wizard creation

You can create custom wizards by extending `BaseWizard` or by saving YAML definitions that define steps, prompts, and validation rules. The `save_custom_wizard()` function stores these definitions for reuse, while `register_wizard()` makes wizard classes available to the system.
