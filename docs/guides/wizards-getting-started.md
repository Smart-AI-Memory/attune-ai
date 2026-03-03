# Wizards: Getting Started

Get up and running with Attune AI wizards in under 10 minutes.

| Step | What You'll Do | Time |
|------|----------------|------|
| 1 | Run a built-in wizard | 3 min |
| 2 | Create a custom wizard (YAML) | 5 min |
| 3 | Explore the wizard registry | 2 min |

---

## Prerequisites

- Attune AI installed (`pip install attune-ai`)
- Python 3.10+

---

## Step 1: Run a Built-in Wizard

Attune ships with 5 built-in wizards:

| ID | Name | When to use |
|----|------|-------------|
| `debug` | Debugging Wizard | Investigating errors, finding root causes |
| `test-gen` | Test Generation Wizard | Creating tests for untested code |
| `refactor` | Refactoring Wizard | Planning safe, incremental refactoring |
| `security` | Security Audit Wizard | Scanning for vulnerabilities |
| `release-prep` | Release Preparation Wizard | Pre-release readiness checks |

### From Claude Code

Type `/wizard run debug` to start the Debugging Wizard.

Or use the Socratic funnel: type `/attune`, select **Create or extend**, then **Run a wizard**.

### From Python

```python
from attune.wizards import get_wizard

# Get the wizard class
DebugWizard = get_wizard("debug")

# Create an instance with an AskUserQuestion callback
wizard = DebugWizard(ask_user_callback=my_callback)

# Run the wizard
result = await wizard.run({"error": "TypeError: cannot add int to str"})

print(result.success)           # True
print(result.steps_completed)   # ['gather_info', 'analyze', 'decompose_fix', 'preview', 'confirm']
print(result.tasks)             # [{'task_id': '1', 'name': 'fix-type-coercion', ...}]
```

### What Happens During a Wizard Run

Every wizard follows a guided multi-step flow:

```text
1. QUESTION     — Collect context from the user (AskUserQuestion)
2. LLM_CALL     — Analyze with AI using XML-enhanced prompts
3. TASK_DECOMPOSE — Break work into structured XML <task> specs
4. PREVIEW      — Show findings and plan for review
5. CONFIRM      — Get approval before applying changes
```

Steps with conditions (like "generate fixes only if critical issues found") are automatically skipped when the condition isn't met.

---

## Step 2: Create a Custom Wizard (YAML)

Custom wizards let you define guided flows without writing Python. They're stored as YAML files in `.attune/wizards/`.

### 2a. Create the YAML File

Create `.attune/wizards/code-migration.yaml`:

```yaml
schema_version: "1.0"
wizard_id: "code-migration"
name: "Code Migration Wizard"
description: "Guide through migrating code between frameworks"
domain: "development"

steps:
  - id: "gather_info"
    name: "Migration Scope"
    step_type: "question"
    questions:
      - id: "source_framework"
        text: "Migrating FROM which framework?"
        type: "text_input"
        help_text: "e.g. Flask, Django, Express"
      - id: "target_framework"
        text: "Migrating TO which framework?"
        type: "text_input"
        help_text: "e.g. FastAPI, Next.js"
      - id: "target_path"
        text: "Which files or directory?"
        type: "text_input"
        default: "src/"

  - id: "analyze"
    name: "Analyze Compatibility"
    step_type: "llm_call"
    tier: "capable"
    prompt_context:
      role: "framework migration specialist"
      goal: "Analyze migration from {session.source_framework} to {session.target_framework}"
      instructions:
        - "Identify API differences between the frameworks"
        - "Flag breaking changes and incompatibilities"
        - "Suggest migration order (dependencies first)"
      constraints:
        - "Preserve existing test coverage"
        - "Minimize downtime risk"

  - id: "plan"
    name: "Migration Plan"
    step_type: "task_decompose"

  - id: "preview"
    name: "Review Plan"
    step_type: "preview"

  - id: "confirm"
    name: "Proceed"
    step_type: "confirm"
```

### 2b. Key Concepts

**Step types** — Each step has a `step_type`:

| Type | What it does |
|------|-------------|
| `question` | Collects user input via AskUserQuestion |
| `llm_call` | Calls an LLM with the prompt context you define |
| `task_decompose` | Breaks the problem into XML `<task>` specifications |
| `preview` | Shows results for user review |
| `confirm` | Final yes/no gate |

**Session variables** — Use `{session.variable_name}` in prompt contexts to reference answers from earlier question steps. The variable name matches the question's `id`.

**Tiers** — Control cost vs. quality:

| Tier | Use for | Cost |
|------|---------|------|
| `cheap` | Quick scans, classification | Lowest |
| `capable` | Analysis, code review | Medium |
| `premium` | Complex reasoning, architecture | Highest |

### 2c. Verify It Works

```python
from attune.wizards import list_wizards

for config in list_wizards():
    print(f"{config.wizard_id}: {config.name} ({config.source})")

# Output includes:
# code-migration: Code Migration Wizard (custom)
```

Or from Claude Code: `/wizard list`

### 2d. Run It

From Claude Code: `/wizard run code-migration`

From Python:

```python
from attune.wizards import ConfigDrivenWizard

wizard = ConfigDrivenWizard.from_yaml(".attune/wizards/code-migration.yaml")
result = await wizard.run()
```

---

## Step 3: Explore the Registry

### List All Wizards

```python
from attune.wizards import list_wizards

for config in list_wizards():
    print(f"  {config.wizard_id:15s} {config.name:30s} ${config.estimated_cost_range[0]:.2f}-{config.estimated_cost_range[1]:.2f}")
```

### Get a Specific Wizard

```python
from attune.wizards import get_wizard

wizard_cls = get_wizard("security")
print(wizard_cls.config.description)
# "Guided security vulnerability scanning and remediation"
```

### Save and Delete Custom Wizards

```python
from attune.wizards import save_custom_wizard, delete_custom_wizard

# Save from a dict
path = save_custom_wizard({
    "wizard_id": "my-wizard",
    "name": "My Wizard",
    "steps": [{"id": "gather", "step_type": "question", "questions": [...]}]
})

# Delete (built-in wizards are protected)
delete_custom_wizard("my-wizard")
```

---

## Next Steps

- [Wizard Architecture](wizard-architecture.md) — How the wizard system works internally
- Custom Wizard Development — Build Python-based wizards with workflow delegation
- [Software Wizards](../reference/software-wizards.md) — Full reference for all 16 software wizards
- [Industry Wizards](../reference/wizards.md) — Domain-specific wizards (Healthcare, Finance, Legal, etc.)
