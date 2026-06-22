---
type: note
feature: wizards
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 322dc43a8cc4749920887d066cffb815d8c6faee0b2e93968e78ac53228d58b1
status: generated
---

# Note: wizards

## Context

The wizards system provides XML-enhanced interactive workflows that guide users through complex, multi-step processes in Attune AI. Each wizard breaks down tasks like debugging, refactoring, or security auditing into structured steps with AI-powered prompts and user interactions.

## Architecture

The wizards system separates data types from execution logic:

**Core data types** (`_types.py`):
- `WizardStep` — Defines individual workflow steps with prompts, questions, and execution modes
- `WizardConfig` — Contains wizard metadata like name, domain, and estimated cost
- `WizardResult` — Captures completion status, collected data, and execution metrics
- `StepType` — Enum for step execution modes (question, action, review)

**Base execution** (`base.py`):
- `BaseWizard` — Abstract class that orchestrates step execution, context building, and result processing

**Registry management** (`registry.py`):
- Functions to register, retrieve, save, and delete wizard definitions
- Support for both built-in and custom wizards stored as YAML

## Built-in wizards

Five specialized wizards extend `BaseWizard`:

- `DebugWizard` — Guides systematic debugging workflows
- `RefactorWizard` — Structures code refactoring processes
- `ReleasePrepWizard` — Orchestrates release preparation tasks
- `SecurityWizard` — Facilitates security audit procedures
- `TestGenWizard` — Assists with test generation workflows

Each wizard customizes `build_prompt_context()` and `process_step_result()` to handle domain-specific logic while following the common execution pattern.

## Source files

- `src/attune/wizards/**`

**Tags:** `wizards`, `interactive`
