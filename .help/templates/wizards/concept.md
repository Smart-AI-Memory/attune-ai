---
feature: wizards
depth: concept
generated_at: 2026-04-06T04:36:04.699122+00:00
source_hash: fad88261e0dbe9f9ea2e6e67da0819f247e4b1e816131c4c3128024aadbdd904
status: generated
---

# Wizards

## How it works

XML-enhanced interactive workflows guide you through multi-step processes like debugging, refactoring, and security audits.

The main building blocks are:

- **`StepType`** — Execution mode for a wizard step.
- **`WizardStep`** — Definition of a single wizard step.
- **`WizardConfig`** — Metadata for a wizard.
- **`WizardResult`** — Result from a completed wizard run.
- **`BaseWizard`** — Abstract base class for interactive, multi-step wizards.

Under the hood, this feature spans 29 source
files covering:

- XML-enhanced wizard system data types
- Base wizard class for interactive workflows
- Built-in wizards for debugging, refactoring, release preparation, security audits, and test generation

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
