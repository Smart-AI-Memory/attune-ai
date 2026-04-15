---
type: comparison
feature: wizards
depth: comparison
generated_at: 2026-04-14T15:29:13.364553+00:00
source_hash: 655cede9671032e7ccc7f39a9f47afbc96ce8855aa0b1bbe2c6567c1a091bf8b
status: generated
---

# Wizards vs direct AI calls

## Overview

Wizards provide structured, multi-step interactive workflows that guide users through complex development tasks. They differ from direct AI calls by offering predefined steps, form-based input collection, and built-in progress tracking.

## Feature comparison

| Feature | Wizards | Direct AI calls |
|---------|---------|-----------------|
| **Structure** | Predefined steps with clear progression | One-off prompts without guidance |
| **User interaction** | Form questions with validation | Free-form text input only |
| **Progress tracking** | Built-in step completion and duration metrics | Manual tracking required |
| **Cost estimation** | Predefined ranges (e.g., $0.01-$0.50) | No cost prediction |
| **Reusability** | Registered and shareable across team | Ad-hoc, not reusable |
| **Context management** | Automatic prompt context building | Manual context assembly |
| **Error handling** | Structured error reporting and recovery | Basic error messages |
| **Output format** | Consistent structured results | Variable response format |

## Built-in wizard types

The system includes five specialized wizards:

- **DebugWizard**: Guided debugging with systematic problem isolation
- **RefactorWizard**: Step-by-step code refactoring with safety checks
- **ReleasePrepWizard**: Release checklist automation and validation
- **SecurityWizard**: Security audit workflows with threat modeling
- **TestGenWizard**: Comprehensive test generation for code coverage

## When to use wizards

Choose wizards when you need:

- **Consistent workflows**: Repeatable processes that team members execute regularly
- **Guided interaction**: Users benefit from structured questions rather than open prompts
- **Progress tracking**: You need to monitor completion rates and duration
- **Quality gates**: Built-in validation and review steps are essential
- **Cost control**: Predefined token limits and cost estimates matter
- **Team standardization**: Multiple developers need the same workflow experience

Examples: code reviews, security audits, release preparation, debugging complex issues.

## When to use direct AI calls

Choose direct AI calls when you need:

- **Exploratory work**: One-off questions or experimental prompts
- **Maximum flexibility**: Custom prompting without workflow constraints
- **Simple interactions**: Single-step operations that don't need structure
- **Rapid iteration**: Testing different approaches without setup overhead
- **Custom context**: Highly specific context that doesn't fit wizard patterns

Examples: quick code explanations, ad-hoc refactoring ideas, experimental feature brainstorming.

## Recommendation

**Use wizards as your default for development workflows.** They provide better user experience, cost predictability, and team consistency. The built-in types (debug, refactor, release prep, security, test generation) cover most common scenarios.

Fall back to direct AI calls only for exploratory work or when you need prompting flexibility that wizards don't support. You can always prototype with direct calls, then create a custom wizard if the workflow proves valuable.

**Source files:** `src/attune/wizards/**`
