---
name: workflows
description: AI-powered analysis workflows
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

| `list` | List available workflows |

## Usage

```bash
/workflows                       # Ask which workflow
/workflows run security-audit    # Security audit
/workflows run bug-predict       # Bug prediction
/workflows run perf-audit        # Performance audit
/workflows list                  # List all workflows
```

## Fast-Path Detection

When the user provides a workflow name AND a path,
skip `AskUserQuestion` and execute directly:

- `/workflows run security-audit ./src` → execute
- `/workflows run bug-predict src/auth` → execute
- `/workflows run security-audit` → ask for path
- `/workflows` → ask which workflow

**Rule:** If both workflow and target are provided,
proceed to execution. If either is missing, use
`AskUserQuestion`.

## Behavior

### run security-audit

If a path argument was provided (e.g.,
`/workflows run security-audit ./src`), skip
`AskUserQuestion` and execute immediately.

Otherwise, use `AskUserQuestion` to scope:

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

### run code-review

Use `AskUserQuestion` to scope:

- Which path or files to review?
- Focus area: quality, security, performance,
  or all?

Then run:

```bash
uv run attune workflow run code-review --path <target>
```

### list

Run:

```bash
uv run attune workflow list
```

Display results in a table format.
