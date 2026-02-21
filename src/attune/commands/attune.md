---
name: attune
description: AI-powered developer workflows with Socratic discovery
category: primary
aliases: [a]
tags: [navigation, discovery, socratic]
version: "2.2.0"
question:
  header: "What brings you here?"
  question: "What are you trying to accomplish right now?"
  multiSelect: false
  options:
    - label: "🔧 Fix or improve something"
      description: "Debug issues, review code, refactor, or improve quality"
    - label: "✅ Validate my work"
      description: "Run tests, check coverage, audit security, or verify quality"
    - label: "🚀 Ship my changes"
      description: "Commit, create PR, prepare release, or publish"
    - label: "🏗️ Create or extend"
      description: "Build custom wizards, agents, teams, or generate docs"
---

# attune

Your AI-powered developer workflow assistant with Socratic discovery.

**One command. Every workflow.** Type `/attune` to browse, or jump straight to any workflow below.

## Workflow Directory

### Developer Tools — [/dev](src/attune/commands/dev.md)

| Command | Description |
| ------- | ----------- |
| [Debug](src/attune/commands/dev.md) `/dev debug` | Investigate errors, trace execution, find root causes |
| [Code Review](src/attune/commands/dev.md) `/dev review` | Quality analysis, security review, performance review |
| [Commit](src/attune/commands/dev.md) `/dev commit` | Stage and commit with conventional commit messages |
| [Pull Request](src/attune/commands/dev.md) `/dev pr` | Push branch, create PR with summary and test plan |
| [Refactor](src/attune/commands/dev.md) `/dev refactor` | Analyze structure, suggest and apply improvements |
| [Bug Predict](src/attune/commands/dev.md) `/dev quality` | Detect patterns likely to produce bugs |

### Testing — [/testing](src/attune/commands/testing.md)

| Command | Description |
| ------- | ----------- |
| [Run Tests](src/attune/commands/testing.md) `/testing run` | Execute pytest test suite |
| [Coverage](src/attune/commands/testing.md) `/testing coverage` | Run tests with coverage report and gap analysis |
| [Generate Tests](src/attune/commands/testing.md) `/testing generate` | Auto-generate behavioral tests for a module |
| [TDD](src/attune/commands/testing.md) `/testing tdd` | Test-driven development: write test first, then implement |

### Analysis Workflows — [/workflows](src/attune/commands/workflows.md)

| Command | Description |
| ------- | ----------- |
| [Security Audit](src/attune/commands/workflows.md) `/workflows security` | Scan for eval, path traversal, secrets, injection risks |
| [Bug Prediction](src/attune/commands/workflows.md) `/workflows bugs` | Detect broad exceptions, incomplete code, risky patterns |
| [Performance Audit](src/attune/commands/workflows.md) `/workflows perf` | Find bottlenecks, memory issues, optimization opportunities |
| [Code Review](src/attune/commands/workflows.md) `/workflows review` | Comprehensive quality and style analysis |
| [List Workflows](src/attune/commands/workflows.md) `/workflows list` | Show all available analysis workflows |

### Planning — [/plan](src/attune/commands/plan.md)

| Command | Description |
| ------- | ----------- |
| [Plan Feature](src/attune/commands/plan.md) `/plan feature` | Break down a feature into tasks, files, deps, and risks |
| [TDD Scaffolding](src/attune/commands/plan.md) `/plan tdd` | Design test cases first, then plan implementation |
| [Refactoring Strategy](src/attune/commands/plan.md) `/plan refactor` | Plan safe incremental refactoring steps |
| [Architecture Review](src/attune/commands/plan.md) `/plan architecture` | Evaluate architecture, propose improvements |

### Documentation — [/docs](src/attune/commands/docs.md)

| Command | Description |
| ------- | ----------- |
| [Generate Docs](src/attune/commands/docs.md) `/docs generate` | Create or update Google-style docstrings for a module |
| [Update README](src/attune/commands/docs.md) `/docs readme` | Review and improve README.md |
| [Update Changelog](src/attune/commands/docs.md) `/docs changelog` | Draft CHANGELOG entries from recent commits |
| [Explain Code](src/attune/commands/docs.md) `/docs explain` | Produce clear human-readable explanation of code |
| [Architecture Overview](src/attune/commands/docs.md) `/docs architecture` | Generate architecture docs with component relationships |

### Release — [/release](src/attune/commands/release.md)

| Command | Description |
| ------- | ----------- |
| [Prepare Release](src/attune/commands/release.md) `/release prep` | Version bump, changelog, pre-flight checks |
| [Security Scan](src/attune/commands/release.md) `/release security` | Pre-release vulnerability audit |
| [Health Check](src/attune/commands/release.md) `/release health` | Full project health: tests + coverage + lint + bandit |
| [Publish](src/attune/commands/release.md) `/release publish` | Build and publish to PyPI |

### Agents — [/agent](src/attune/commands/agent.md)

| Command | Description |
| ------- | ----------- |
| [Create Agent](src/attune/commands/agent.md) `/agent create` | Define a new specialized agent with role and tools |
| [List Agents](src/attune/commands/agent.md) `/agent list` | Show all available agents and capabilities |
| [Run Agent Team](src/attune/commands/agent.md) `/agent run` | Execute a multi-agent collaboration |
| [Release Prep](src/attune/commands/agent.md) `/agent release-prep` | Run the release readiness agent team (4 agents) |

### Deep Review — [/deep-review](src/attune/commands/deep-review.md)

| Command | Description |
| ------- | ----------- |
| [Full Review](src/attune/commands/deep-review.md) `/deep-review <path>` | Security + quality + test gap analysis |
| [Security Only](src/attune/commands/deep-review.md) `/deep-review security` | CWE-focused vulnerability scan |
| [Quality Only](src/attune/commands/deep-review.md) `/deep-review quality` | Code quality and style analysis |
| [Test Gaps Only](src/attune/commands/deep-review.md) `/deep-review tests` | Coverage analysis and missing test detection |

### Wizards — [/wizard](src/attune/commands/wizard.md)

| Command | Description |
| ------- | ----------- |
| [Run Wizard](src/attune/commands/wizard.md) `/wizard run <id>` | Execute a guided multi-step wizard by ID |
| [List Wizards](src/attune/commands/wizard.md) `/wizard list` | Show all wizards (built-in + custom) with metadata |
| [Create Wizard](src/attune/commands/wizard.md) `/wizard create` | Define a new custom guided workflow via YAML |
| [Edit Wizard](src/attune/commands/wizard.md) `/wizard edit <id>` | Modify an existing custom wizard |

### Batch API — [/batch](src/attune/commands/batch.md)

| Command | Description |
| ------- | ----------- |
| [Submit Batch](src/attune/commands/batch.md) `/batch submit` | Queue tasks for async processing (50% savings) |
| [Batch Status](src/attune/commands/batch.md) `/batch status <id>` | Check progress of a running batch |
| [Batch Results](src/attune/commands/batch.md) `/batch results <id>` | Retrieve completed batch results |
| [Wait for Batch](src/attune/commands/batch.md) `/batch wait <id>` | Block until a batch completes |

### Utilities — [/utilities](src/attune/commands/utilities.md)

| Command | Description |
| ------- | ----------- |
| [Dependency Check](src/attune/commands/utilities.md) `/utilities deps` | Audit dependencies for vulnerabilities |
| [Research](src/attune/commands/utilities.md) `/utilities research <topic>` | Investigate and analyze a topic |
| [Validate Config](src/attune/commands/utilities.md) `/utilities validate` | Check attune configuration and API keys |
| [Show Features](src/attune/commands/utilities.md) `/utilities features` | List available features and status |

### Brainstorm — [/brainstorm](src/attune/commands/brainstorm.md)

| Command | Description |
| ------- | ----------- |
| [Brainstorm](src/attune/commands/brainstorm.md) `/brainstorm` | Open guided discovery conversation |
| [Brainstorm Topic](src/attune/commands/brainstorm.md) `/brainstorm "topic"` | Start with context pre-filled |
| [Brainstorm Plan](src/attune/commands/brainstorm.md) `/brainstorm plan` | Skip to goals and planning |

## Natural Language

Just describe what you need — no need to memorize commands:

- "find security vulnerabilities"
- "why is this test failing"
- "generate tests for config.py"
- "review my authentication code"
- "prepare for release 2.0"
- "explain how caching works"
- "this function is too long"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the workflow via CLI, not answer ad-hoc.**

### No-Argument Behavior: Socratic Funnel

**When invoked without arguments (`/attune` alone), use AskUserQuestion to present a clickable 2-step discovery flow.**

**Step 1 — Goal Discovery:** Present this AskUserQuestion:

- Header: `"Attune"`
- Question: `"What are you trying to accomplish?"`
- Options (4 max):
  1. **Fix or improve code** — "/dev - Debug, review, refactor, commit, PR"
  2. **Validate my work** — "/testing + /workflows - Tests, coverage, security, perf"
  3. **Ship my changes** — "/release + /plan - Plan features, prepare release, publish"
  4. **Create or extend** — "/wizard + /agent - Create wizards, agents, teams, or generate docs"

**Step 2 — Hub Selection:** Based on their choice, present a second AskUserQuestion with the specific hubs:

- "Fix or improve code" → Options: `/dev`, `/deep-review`, `/wizard run`
- "Validate my work" → Options: `/testing run`, `/testing coverage`, `/workflows security`, `/workflows perf`
- "Ship my changes" → Options: `/release prep`, `/release health`, `/plan feature`, `/plan architecture`
- "Create or extend" → Options: `/wizard create`, `/agent create`, `/docs generate`, `/docs explain`

**Step 3 — Execute:** Invoke the selected hub skill via the Skill tool.

**Do NOT dump the full Workflow Directory tables.** The tables above are reference documentation — the primary interface is the clickable AskUserQuestion funnel.

### Shortcut Routing (SCOPE THEN EXECUTE)

When the user types a shortcut, **use AskUserQuestion to scope before executing**:

| Input | Scoping Question | CLI Command |
| ----- | ---------------- | ----------- |
| `/attune security` | "What target? src/, a specific module, or full project?" | `uv run attune workflow run security-audit --path <target>` |
| `/attune test` | "What scope? Full suite, CLI tests only, specific file, or quick smoke test?" | `uv run pytest <scope>` |
| `/attune coverage` | "What scope? Full project, specific module, or just changed files?" | `uv run pytest --cov=src --cov-report=term-missing <scope>` |
| `/attune perf` | "What target? src/, a specific module, or full project?" | `uv run attune workflow run perf-audit --path <target>` |
| `/attune review` | "What focus? Quality, security, performance, or all? Which files?" | `uv run attune workflow run code-review --path <target>` |
| `/attune bug-predict` | "What target? src/, a specific module, or full project?" | `uv run attune workflow run bug-predict --path <target>` |
| `/attune test-gen` | "What target? A specific file, module, or directory?" | `uv run attune workflow run test-gen --path <target>` |
| `/attune commit` | "Which files? All staged changes, specific files, or let me review first?" | Use git to stage and commit changes |
| `/attune pr` | "What base branch? What kind of change is this?" | Use gh to create a pull request |
| `/attune release` | "What stage? Prep check, changelog update, or full publish?" | `uv run attune workflow run release-prep` |
| `/attune debug` | "What's the issue? Error message, unexpected behavior, or performance problem?" | Start interactive debugging session |
| `/attune refactor` | "What area? Which files or functions need refactoring?" | Analyze code and suggest refactoring |
| `/attune docs` | "What kind? API docs, README update, architecture overview, or changelog?" | Generate documentation |
| `/attune explain` | "What code? Which file, function, or module do you want explained?" | Read and explain the specified code |
| `/attune wizard` | "What do you need? Run, create, list, or edit a wizard?" | Invoke `/wizard` hub |
| `/attune create` | "What do you want to create? A wizard, agent, agent team, or docs?" | Route to `/wizard create`, `/agent create`, or `/docs generate` |
| `/attune agent` | "What do you need? Create, list, or run an agent?" | Invoke `/agent` hub |

### Natural Language Routing (SCOPE THEN EXECUTE)

When the user provides natural language, **use AskUserQuestion to scope**, then map to the appropriate CLI command:

| Pattern | CLI Command |
| ------- | ----------- |
| "security", "vulnerabilities", "audit" | `uv run attune workflow run security-audit` |
| "test", "tests", "run tests" | `uv run pytest` |
| "coverage", "test coverage" | `uv run pytest --cov=src --cov-report=term-missing` |
| "generate tests", "write tests" | `uv run attune workflow run test-gen` |
| "review", "code review" | `uv run attune workflow run code-review` |
| "performance", "perf", "bottleneck" | `uv run attune workflow run perf-audit` |
| "bugs", "predict bugs" | `uv run attune workflow run bug-predict` |
| "release", "ship", "publish" | `uv run attune workflow run release-prep` |
| "dependency", "deps", "outdated" | `uv run attune workflow run dependency-check` |
| "research", "investigate", "explore" | `uv run attune workflow run research` |
| "brainstorm", "think through" | Route to `/brainstorm` |
| "batch", "bulk process" | Route to `/batch` |
| "create", "build", "new wizard", "new agent" | Route to `/wizard create` or `/agent create` |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. Use `AskUserQuestion` to scope, THEN execute the CLI command.

### CLI Reference

```bash
# Workflows
uv run attune workflow run security-audit --path <target>
uv run attune workflow run perf-audit --path <target>
uv run attune workflow run bug-predict --path <target>
uv run attune workflow run code-review --path <target>
uv run attune workflow run test-gen --path <target>
uv run attune workflow run release-prep
uv run attune workflow run dependency-check
uv run attune workflow run research --query <topic>

# Batch API
uv run attune batch submit --tasks <file>
uv run attune batch status --id <batch_id>

# Testing
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run pytest -k "test_name"

# Telemetry
uv run attune telemetry show
```

## Philosophy

**Socratic over menus.** Ask "What are you trying to accomplish?" not "Which tool do you want?"

**Teaching over telling.** Help users understand *why*, not just *what*.

**Questions before actions.** ALWAYS use `AskUserQuestion` to guide users through decisions at every step — goal identification, scoping, and confirmation. Never assume scope or jump to execution. This is the #1 rule of the Attune workflow experience.
