---
type: concept
feature: wizards
depth: concept
generated_at: 2026-04-14T15:26:55.563097+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards

Wizards are interactive, multi-step workflows that guide you through complex development tasks by breaking them into structured, AI-assisted steps.

## Architecture

Each wizard follows a three-layer structure:

**Configuration layer** — `WizardConfig` defines metadata like the wizard's name, domain (development, security, etc.), and estimated cost/duration. This helps you choose the right wizard before starting.

**Step definition layer** — `WizardStep` objects define individual workflow stages. Each step specifies its execution mode (`StepType`), prompt templates for AI interactions, conditional logic for branching workflows, and form questions for user input.

**Execution layer** — `BaseWizard` orchestrates the workflow by processing steps sequentially, building context for AI prompts, collecting user responses, and producing a `WizardResult` with collected data, generated outputs, and execution metadata.

## Built-in wizards

Attune includes five specialized wizards for common development workflows:

- **DebugWizard** — Systematically diagnoses and fixes code issues
- **RefactorWizard** — Guides code restructuring while preserving functionality
- **ReleasePrepWizard** — Prepares releases with version bumps, changelogs, and validation
- **SecurityWizard** — Conducts security audits and identifies vulnerabilities
- **TestGenWizard** — Generates comprehensive test suites for existing code

Each wizard customizes `build_prompt_context()` to inject domain-specific information and `process_step_result()` to handle specialized data collection patterns.

## Wizard registry

The registry system lets you register custom wizards alongside built-ins:

- `register_wizard()` adds new wizard classes to the global registry
- `get_wizard()` retrieves wizard classes by ID for instantiation
- `save_custom_wizard()` persists custom wizard definitions to YAML files
- `list_wizards()` enumerates all available wizards with their configurations

This registry enables dynamic wizard discovery and supports both code-based and configuration-driven wizard definitions.
