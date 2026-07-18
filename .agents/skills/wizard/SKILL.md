---
name: wizard
description: Guided multi-step wizards with XML task decomposition
---
# wizard

Guided multi-step wizards with XML task decomposition
for complex workflows.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `run debug` | Debug wizard |
| `run test-gen` | Test generation wizard |
| `run refactor` | Refactoring wizard |
| `run security` | Security wizard |
| `run release-prep` | Release prep wizard |
| `create` | Create a custom wizard |
| `list` | List available wizards |
| `edit` | Edit a wizard |

## Usage

```bash
/wizard                      # Ask what to do
/wizard run debug            # Debug wizard
/wizard run test-gen         # Test gen wizard
/wizard run refactor         # Refactoring wizard
/wizard run security         # Security wizard
/wizard run release-prep     # Release prep wizard
/wizard create               # Create custom wizard
/wizard list                 # List wizards
```

## Behavior

### run

Handles all built-in wizards (`debug`, `test-gen`,
`refactor`, `security`, `release-prep`). When invoked
with a specific wizard (e.g., `/wizard run debug`),
skip the wizard selection question.

Use `AskUserQuestion` to scope:

- Which wizard to run? (if not specified)
- What target files or path?

Then execute the wizard step-by-step, using
`AskUserQuestion` at each decision point.

### create

Guide the user through wizard creation:

1. Name and description
2. Steps definition
3. XML task templates
4. Validation criteria

### list

Show available wizards with descriptions.

### edit

Use `AskUserQuestion`:

- Which wizard to edit?
- What to change?

Then modify the wizard definition.

## Built-in Wizards

| Wizard | Description |
| ------ | ----------- |
| `debug` | Guided debugging session |
| `test-gen` | Test generation with coverage goals |
| `refactor` | Structured refactoring workflow |
| `security` | Security audit and remediation |
| `release-prep` | Release readiness checklist |
