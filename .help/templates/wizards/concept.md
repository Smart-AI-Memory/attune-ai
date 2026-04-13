---
feature: wizards
depth: concept
generated_at: 2026-04-13T17:03:17.987170+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards

## How it works

XML-enhanced interactive workflows that guide you through multi-step processes like debugging, refactoring, and security audits.

The main building blocks are:

- **`StepType`** — Execution mode for a wizard step.
- **`WizardStep`** — Definition of a single wizard step.
- **`WizardConfig`** — Metadata for a wizard.
- **`WizardResult`** — Result from a completed wizard run.
- **`BaseWizard`** — Abstract base class for interactive, multi-step wizards.

Under the hood, this feature spans 14 source
files covering:

- Data types for the wizard framework.
- Base wizard class for XML-enhanced interactive workflows.
- Built-in wizards for debugging, refactoring, release preparation, security audits, and test generation.

## What connects to it

This feature relates to: wizards, interactive.

Other parts of the codebase interact with
wizards through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `StepType` | Execution mode for a wizard step. | `src/attune/wizards/_types.py` |
| `WizardStep` | Definition of a single wizard step. | `src/attune/wizards/_types.py` |
| `WizardConfig` | Metadata for a wizard. | `src/attune/wizards/_types.py` |
| `WizardResult` | Result from a completed wizard run. | `src/attune/wizards/_types.py` |
| `BaseWizard` | Abstract base class for interactive, multi-step wizards. | `src/attune/wizards/base.py` |
