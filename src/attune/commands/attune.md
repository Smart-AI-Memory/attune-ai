---
name: attune
description: AI-powered developer workflows with Socratic discovery
category: primary
aliases: [a]
tags: [navigation, discovery, socratic]
version: "3.0.0"
question:
  header: "What brings you here?"
  question: "What are you trying to accomplish right now?"
  multiSelect: false
  options:
    - label: "Fix or improve something"
      description: "Debug issues, review code, refactor, or improve quality"
    - label: "Validate my work"
      description: "Run tests, check coverage, audit security"
    - label: "Ship my changes"
      description: "Commit, create PR, prepare release, or publish"
    - label: "Build something new"
      description: "Spec-driven development, agents, wizards, or docs"
---

# attune

Your AI-powered developer workflow assistant with
Socratic discovery.

**One command. Every workflow.** Type `/attune` to browse,
or jump straight to any command below. Type `/help` for
the full reference.

## Quick Reference

| Command | What it does |
| ------- | ------------ |
| `/spec` | Spec-driven development with approval loop |
| `/security` | Security audit |
| `/smart-test` | Find test gaps, generate tests |
| `/release` | Release preparation and publishing |
| `/dev` | Debug, commit, PR, code review, refactoring |
| `/help` | Full command reference |

## All Commands

### Developer Tools

| Command | Description |
| ------- | ----------- |
| `/dev debug` | Investigate errors, trace execution |
| `/dev review` | Quality + security + performance review |
| `/dev commit` | Stage and commit with conventional messages |
| `/dev pr` | Push branch, create PR with summary |
| `/dev refactor` | Analyze structure, suggest improvements |
| `/code-quality` | Code review + bug prediction |
| `/refactor` | Refactoring analysis and roadmap |
| `/deep-review <path>` | Multi-pass security + quality + test gaps |

### Testing

| Command | Description |
| ------- | ----------- |
| `/smart-test` | Find test gaps, generate tests |
| `/fix-test` | Auto-diagnose and fix failing tests |

### Security and Quality

| Command | Description |
| ------- | ----------- |
| `/security` | Scan for eval, path traversal, secrets |
| `/code-quality` | Code review + bug prediction |

### Planning and Docs

| Command | Description |
| ------- | ----------- |
| `/spec` | Full spec-driven development lifecycle |
| `/plan feature` | Break down a feature into tasks |
| `/brainstorm` | Guided discovery conversation |
| `/doc-gen` | Generate documentation from source |
| `/remember` | Store and retrieve persistent memory |

### Release

| Command | Description |
| ------- | ----------- |
| `/release prep` | Version bump, changelog, pre-flight |
| `/release security` | Pre-release vulnerability audit |
| `/release health` | Tests + coverage + lint + bandit |
| `/release publish` | Build and publish to PyPI |

### Advanced

| Command | Description |
| ------- | ----------- |
| `/agent create` | Define a new specialized agent |
| `/wizard run <id>` | Execute a guided multi-step wizard |
| `/bulk submit` | Queue tasks for batch processing |

## Natural Language

Just describe what you need:

- "find security vulnerabilities"
- "why is this test failing"
- "generate tests for config.py"
- "review my authentication code"
- "prepare for release 2.0"
- "explain how caching works"
- "I want to build a new feature"

## CRITICAL: Workflow Execution Instructions

**When invoked with arguments, execute the workflow via
CLI — do not answer ad-hoc.**

### No-Argument Behavior: Socratic Funnel

**When invoked without arguments (`/attune` alone), use
AskUserQuestion to present a 2-step discovery flow.**

**Step 1 — Goal Discovery:**

- Header: `"Attune"`
- Question: `"What are you trying to accomplish?"`
- Options (4 max):
  1. **Fix or improve code** — `/dev`, `/deep-review`
  2. **Validate my work** — `/smart-test`, `/security`
  3. **Ship my changes** — `/release`, `/dev commit`
  4. **Build something new** — `/spec`, `/brainstorm`

**Step 2 — Command Selection:** Based on their choice,
present a second AskUserQuestion with specific commands:

- "Fix or improve code" → `/dev`, `/code-quality`,
  `/deep-review`, `/refactor`
- "Validate my work" → `/smart-test`, `/fix-test`,
  `/security`
- "Ship my changes" → `/dev commit`, `/dev pr`,
  `/release prep`
- "Build something new" → `/spec`, `/brainstorm`,
  `/agent create`, `/doc-gen`

**Step 3 — Execute:** Invoke the selected command.

**Do NOT dump the full command tables.** The tables above
are reference documentation — the primary interface is
the clickable AskUserQuestion funnel.

### Shortcut Routing (SCOPE THEN EXECUTE)

When the user types a shortcut, **use AskUserQuestion to
scope before executing**:

| Input | CLI Command |
| ----- | ----------- |
| `/attune security` | `uv run attune workflow run security-audit` |
| `/attune test` | `uv run pytest` |
| `/attune coverage` | `uv run pytest --cov=src` |
| `/attune review` | `uv run attune workflow run code-review` |
| `/attune commit` | Use git to stage and commit |
| `/attune pr` | Use gh to create a pull request |
| `/attune release` | `uv run attune workflow run release-prep` |
| `/attune docs` | Route to `/doc-gen` |
| `/attune spec` | Route to `/spec` |

### Natural Language Routing (SCOPE THEN EXECUTE)

| Pattern | Route to |
| ------- | -------- |
| "security", "vulnerabilities" | `/security` |
| "test", "tests", "run tests" | `/smart-test` |
| "generate tests", "write tests" | `/smart-test` |
| "review", "code review" | `/code-quality` |
| "bugs", "predict bugs" | `/code-quality` |
| "release", "ship", "publish" | `/release` |
| "brainstorm", "think through" | `/brainstorm` |
| "spec", "build", "new feature" | `/spec` |
| "create wizard", "new agent" | `/wizard` or `/agent` |

### CLI Reference

```bash
# Workflows
uv run attune workflow run security-audit --path <target>
uv run attune workflow run perf-audit --path <target>
uv run attune workflow run bug-predict --path <target>
uv run attune workflow run code-review --path <target>
uv run attune workflow run test-gen --path <target>
uv run attune workflow run release-prep

# Testing
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run pytest -k "test_name"
```

## Philosophy

**Socratic over menus.** Ask "What are you trying to
accomplish?" not "Which tool do you want?"

**Questions before actions.** ALWAYS use `AskUserQuestion`
to guide users through decisions at every step. Never
assume scope or jump to execution.
