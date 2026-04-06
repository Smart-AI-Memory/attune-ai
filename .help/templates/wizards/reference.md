---
feature: wizards
depth: reference
generated_at: 2026-04-06T04:36:18.090594+00:00
source_hash: fad88261e0dbe9f9ea2e6e67da0819f247e4b1e816131c4c3128024aadbdd904
status: generated
---

# Wizards reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `StepType` | Execution mode for a wizard step. | `src/attune/wizards/_types.py` |
| `WizardStep` | Definition of a single wizard step. | `src/attune/wizards/_types.py` |
| `WizardConfig` | Metadata for a wizard. | `src/attune/wizards/_types.py` |
| `WizardResult` | Result from a completed wizard run. | `src/attune/wizards/_types.py` |
| `BaseWizard` | Abstract base class for interactive, multi-step wizards. | `src/attune/wizards/base.py` |
| `DebugWizard` | Guides you through debugging code issues. | `src/attune/wizards/builtin/debug_wizard.py` |
| `RefactorWizard` | Guides you through code refactoring workflows. | `src/attune/wizards/builtin/refactor_wizard.py` |
| `ReleasePrepWizard` | Guides you through release preparation tasks. | `src/attune/wizards/builtin/release_prep_wizard.py` |
| `SecurityWizard` | Guides you through security audit procedures. | `src/attune/wizards/builtin/security_wizard.py` |
| `TestGenWizard` | Guides you through test generation workflows. | `src/attune/wizards/builtin/test_gen_wizard.py` |
| `ConfigDrivenWizard` | A wizard loaded from a YAML definition file. | `src/attune/wizards/config_driven.py` |
| `DecomposedTask` | A single task extracted from XML decomposition. | `src/attune/wizards/decomposer.py` |
| `TaskDecomposer` | Decomposes complex problems into structured XML tasks. | `src/attune/wizards/decomposer.py` |
| `WizardInternalWorkflow` | Thin BaseWorkflow wrapper that gives wizards access to all mixins. | `src/attune/wizards/internal_workflow.py` |
| `WizardSession` | Tracks mutable state across wizard steps. | `src/attune/wizards/session.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `register_wizard()` | Register a wizard class. | `src/attune/wizards/registry.py` |
| `get_wizard()` | Get a wizard class by ID. | `src/attune/wizards/registry.py` |
| `list_wizards()` | List all registered wizard configs. | `src/attune/wizards/registry.py` |
| `save_custom_wizard()` | Save a custom wizard definition to YAML. | `src/attune/wizards/registry.py` |
| `delete_custom_wizard()` | Delete a custom wizard definition. | `src/attune/wizards/registry.py` |


## Source files

- `src/attune/wizards/**`

## Tags

`wizards`, `interactive`
