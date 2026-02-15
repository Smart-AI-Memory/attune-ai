---
name: wizard
description: Create, manage, and run guided multi-step wizards
category: hub
aliases: [wizards, wiz]
tags: [wizard, guided, xml, decompose, interactive, create, manage]
version: "2.0.0"
question:
  header: "Wizard Hub"
  question: "What would you like to do with wizards?"
  multiSelect: false
  options:
    - label: "Run a wizard"
      description: "Execute a built-in or custom wizard by ID"
    - label: "List wizards"
      description: "Show all available wizards with metadata"
    - label: "Create a wizard"
      description: "Define a new custom guided workflow"
    - label: "Edit a wizard"
      description: "Modify an existing custom wizard"
---

# wizard

Create, manage, and run guided multi-step wizards with XML task decomposition.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/wizard run <id>` | Execute a wizard (debug, test-gen, refactor, security, release-prep) |
| `/wizard list` | Show all available wizards (built-in + custom) |
| `/wizard create` | Define a new custom wizard step by step |
| `/wizard edit <id>` | Modify a custom wizard's configuration |

## Natural Language

Describe what you need:

- "run the debug wizard"
- "show me available wizards"
- "create a new wizard for code migration"
- "edit my custom wizard"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the action, not answer ad-hoc.**

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/wizard run <id>` | Execute the wizard's multi-step flow |
| `/wizard list` | List all registered wizards as a table |
| `/wizard create` | Start the guided wizard creation flow |
| `/wizard edit <id>` | Load and modify a custom wizard |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "run", "execute", "start" | Run wizard by ID |
| "list", "show", "available" | List all wizards |
| "create", "new", "define", "build" | Create a new wizard |
| "edit", "modify", "update", "change" | Edit an existing wizard |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the action.

---

## Action: `/wizard run <id>`

Execute a wizard's guided multi-step flow. Each wizard follows this pattern:

1. **Gather info** — Use AskUserQuestion to collect context from the user
2. **Analyze** — Run LLM analysis with XML-enhanced prompts
3. **Decompose** — Break work into structured XML `<task>` specifications
4. **Preview** — Show findings and task list for review
5. **Confirm** — Get approval before applying changes

### Running a Built-in Wizard

First, use AskUserQuestion to ask which wizard to run (if no ID was specified):

| ID | Name | Domain | Steps |
| -- | ---- | ------ | ----- |
| `debug` | Debugging Wizard | development | question → analyze → decompose → preview → confirm |
| `test-gen` | Test Generation Wizard | testing | question → analyze → decompose → preview → confirm |
| `refactor` | Refactoring Wizard | development | question → analyze → decompose → preview → confirm |
| `security` | Security Audit Wizard | security | question → scan → fix → decompose → preview |
| `release-prep` | Release Preparation Wizard | release | question → readiness → changelog → decompose → preview → confirm |

Then execute the wizard step by step:

**Debug wizard** — Ask: error description, target file, has stack trace? Then analyze root cause, decompose fix into tasks, preview, confirm.

**Test-gen wizard** — Ask: target path, test style, framework? Then analyze coverage gaps, decompose into test file tasks, preview, confirm.

**Refactor wizard** — Ask: refactor type, target file, goal? Then analyze structure, decompose into incremental steps, preview, confirm.

**Security wizard** — Ask: scope, target path, focus areas? Then scan for vulnerabilities, generate fixes for high/critical findings, decompose remediation, preview.

**Release-prep wizard** — Ask: version type, run tests, generate changelog? Then readiness check, optional changelog, decompose release tasks, preview, confirm.

---

## Action: `/wizard list`

List all registered wizards. Run:

```python
from attune.wizards import list_wizards
wizards = list_wizards()
```

Format the output as a table:

| ID | Name | Domain | Source | Est. Cost |
| -- | ---- | ------ | ------ | --------- |
| debug | Debugging Wizard | development | builtin | $0.02-0.30 |
| test-gen | Test Generation Wizard | testing | builtin | $0.02-0.40 |
| refactor | Refactoring Wizard | development | builtin | $0.02-0.35 |
| security | Security Audit Wizard | security | builtin | $0.03-0.50 |
| release-prep | Release Preparation Wizard | release | builtin | $0.03-0.40 |

Custom wizards will show `source: custom`.

---

## Action: `/wizard create`

Guide the user through creating a custom wizard definition, saved as YAML in `.attune/wizards/`.

### Step 1: Basic Info

Use AskUserQuestion:

- **Q1:** "What should this wizard be called?" (text input) → `wizard_id` and `name`
- **Q2:** "What does this wizard do? (one sentence)" → `description`
- **Q3:** "Domain?" (select: Development, Testing, Security, Release) → `domain`

### Step 2: Define Steps (iterative)

For each step, use AskUserQuestion:

- **Q:** "What type of step?" (select):
  1. "Ask the user questions" → QUESTION step
  2. "Analyze with AI" → LLM_CALL step
  3. "Break into sub-tasks" → TASK_DECOMPOSE step
  4. "Preview results" → PREVIEW step

For **QUESTION** steps, ask:

- Question text, type (text input / select / boolean), options if select

For **LLM_CALL** steps, ask:

- AI role (e.g., "security specialist")
- Goal (e.g., "analyze code for vulnerabilities")
- Key instructions (list of strings)
- Supports `{session.variable_name}` placeholders for dynamic prompts

For **TASK_DECOMPOSE** and **PREVIEW** steps: auto-configured with sensible defaults.

After each step: "Add another step?" (Yes/No). A CONFIRM step is auto-appended at the end.

### Step 3: Save

Show the generated YAML preview. Ask: "Save this wizard?" (Yes / No).

Save to `.attune/wizards/{wizard_id}.yaml` using:

```python
from attune.wizards import save_custom_wizard
path = save_custom_wizard(wizard_data)
```

### YAML Schema Reference

```yaml
schema_version: "1.0"
wizard_id: "my-wizard"
name: "My Custom Wizard"
description: "Does something useful"
domain: "development"

steps:
  - id: "gather_info"
    name: "Collect Context"
    step_type: "question"
    questions:
      - id: "target"
        text: "Which file or module?"
        type: "text_input"
        help_text: "e.g. src/module.py"

  - id: "analyze"
    name: "Analyze"
    step_type: "llm_call"
    tier: "capable"
    prompt_context:
      role: "specialist"
      goal: "Analyze {session.target}"
      instructions:
        - "Identify issues"
        - "Suggest improvements"

  - id: "decompose"
    name: "Plan Tasks"
    step_type: "task_decompose"

  - id: "preview"
    name: "Review"
    step_type: "preview"

  - id: "confirm"
    name: "Confirm"
    step_type: "confirm"
```

Session variables use `{session.variable_name}` syntax — these are replaced with values from earlier question steps at runtime.

---

## Action: `/wizard edit <id>`

Edit a custom wizard's YAML definition.

1. Load the wizard YAML from `.attune/wizards/{id}.yaml`
2. Display current configuration summary
3. Use AskUserQuestion to ask what to modify:
   - "Add a step"
   - "Remove a step"
   - "Edit a step"
   - "Change basic info"
4. Apply changes and re-save

**Note:** Built-in wizards cannot be edited. To customize a built-in wizard, create a new custom wizard based on it.

---

## Programmatic API

```python
from attune.wizards import (
    BaseWizard, ConfigDrivenWizard,
    get_wizard, list_wizards,
    save_custom_wizard, delete_custom_wizard,
)

# List all wizards
for config in list_wizards():
    print(f"{config.wizard_id}: {config.name} ({config.source})")

# Run a built-in wizard
wizard_cls = get_wizard("debug")
wizard = wizard_cls(ask_user_callback=my_callback)
result = await wizard.run({"error": "TypeError: ..."})

# Load a custom wizard from YAML
wizard = ConfigDrivenWizard.from_yaml(".attune/wizards/my-wizard.yaml")
result = await wizard.run()

# Save a new custom wizard
save_custom_wizard({
    "wizard_id": "my-wizard",
    "name": "My Wizard",
    "steps": [{"id": "gather", "step_type": "question", ...}]
})

# Delete a custom wizard
delete_custom_wizard("my-wizard")
```
