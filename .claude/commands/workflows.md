---
name: workflows
description: AI-powered analysis workflows
category: primary
aliases: [wf, w]
tags: [workflows, security, bugs, performance, analysis]
version: "1.0.0"
question:
  header: "Workflow"
  question: "Which analysis workflow do you want to run?"
  multiSelect: false
  options:
    - label: "Security audit"
      description: "Scan for vulnerabilities and security issues"
    - label: "Bug prediction"
      description: "Predict likely bugs using pattern analysis"
    - label: "Performance audit"
      description: "Find performance bottlenecks"
    - label: "List available"
      description: "Show all available workflows"
---

# workflows

AI-powered analysis workflows for security, bugs,
and performance.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `run security-audit` | Security vulnerability scan |
| `run bug-predict` | Bug prediction analysis |
| `run perf-audit` | Performance audit |
| `run code-review` | Code review workflow |
| `run seo-optimization` | SEO analysis |
| `list` | List available workflows |

## Usage

```bash
/workflows                       # Ask which workflow
/workflows run security-audit    # Security audit
/workflows run bug-predict       # Bug prediction
/workflows run perf-audit        # Performance audit
/workflows list                  # List all workflows
```

## Behavior

### run security-audit

Use `AskUserQuestion` to scope:

- Which path? `src/`, specific module, or full project?

Then run:

```bash
uv run attune workflow run security-audit --path <target>
```

### run bug-predict

Use `AskUserQuestion` to scope:

- Which path to scan?

Then run:

```bash
uv run attune workflow run bug-predict --path <target>
```

### run perf-audit

Use `AskUserQuestion` to scope:

- Which path to audit?

Then run:

```bash
uv run attune workflow run perf-audit --path <target>
```

### list

Run:

```bash
uv run attune workflow list
```

Display results in a table format.
