---
name: attune
description: AI-powered developer workflows with Socratic discovery
---
# attune

Your AI-powered developer workflow assistant with Socratic discovery.

**One command. Every workflow.**

## How It Works

Type `/attune` and I'll guide you through questions to find the right workflow.

```bash
/attune                              # Start Socratic discovery
/attune "I need to fix a bug"        # Natural language
/attune debug                        # Direct shortcut
```

## Fast-Path Detection

When the user provides sufficient context inline,
**skip scoping questions and execute directly**.
This satisfies the Socratic requirement because the
user's explicit args provide the scoping context.

**Fast-path triggers (execute immediately):**

- Specific subcommand + target path:
  `/attune security-audit ./src`
- Natural language with clear scope:
  `/attune "review src/auth"`
- Explicit `--auto` flag:
  `/attune commit --auto`

**Socratic flow (ask questions first):**

- `/attune` (no args)
- `/attune "fix something"` (vague)

**Rule:** If input contains BOTH an action AND a target,
proceed to execution. If either is missing or ambiguous,
use `AskUserQuestion`.

## Workflows by Goal

### 🔧 Fix or Improve Something

**Debugging:**

- Investigate errors and exceptions
- Trace execution flow
- Identify root causes

**Code Review:**

- Quality and pattern analysis
- Security review
- Performance review

**Refactoring:**

- Improve structure and organization
- Extract functions/classes
- Simplify complex code

### ✅ Validate My Work

**Testing:**

- Run test suites
- Generate new tests

**Coverage:**

- Analyze test coverage
- Identify gaps
- Boost coverage

**Security Audit:**

- Vulnerability scanning
- Dependency analysis
- Code security review

**Performance Audit:**

- Identify bottlenecks
- Memory analysis
- Optimization recommendations

### 🚀 Ship My Changes

**Commit:**

- Stage and commit changes
- Generate commit messages
- Follow conventional commits

**Pull Request:**

- Create PR with description
- Review checklist
- Link to issues

**Release:**

- Version bump
- Changelog generation
- Security pre-checks
- Publish to registry

### 📚 Understand or Document

**Explain Code:**

- Understand how code works
- Trace through logic
- Learn patterns used

**Generate Docs:**

- API documentation
- README updates
- Architecture docs

**Feature Overview:**

- High-level summaries
- Component relationships
- Usage examples

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/attune debug` | Start debugging session |
| `/attune review` | Code review |
| `/attune refactor` | Refactoring session |
| `/attune test` | Run tests |
| `/attune coverage` | Coverage analysis |
| `/attune security` | Security audit |
| `/attune commit` | Create commit |
| `/attune pr` | Create pull request |
| `/attune release` | Prepare release |
| `/attune docs` | Documentation |
| `/attune explain` | Explain code |

## Natural Language

Just describe what you need:

- "find security vulnerabilities"
- "why is this test failing"
- "generate tests for config.py"
- "review my authentication code"
- "prepare for release 2.0"
- "explain how caching works"
- "this function is too long"

## CRITICAL: Socratic Discovery Before Execution

**ALWAYS use `AskUserQuestion` to scope and confirm before executing any workflow. NEVER skip straight to running commands.**

### Step 1: Understand the Goal

If invoked without arguments (`/attune`), use `AskUserQuestion` to ask what the user is trying to accomplish.

### Step 2: Scope the Work

Once the goal is identified, use `AskUserQuestion` to narrow scope. Examples:

- **Testing**: "What scope? Full suite, CLI tests only, quick smoke test, or coverage report?"
- **Security audit**: "What target? src/, a specific module, or full project?"
- **Code review**: "What focus? Quality, security, performance, or all?"
- **Commit**: "Which files? All staged changes, specific files, or let me review first?"
- **Release**: "What stage? Prep check, changelog update, or full publish?"

### Step 3: Execute

Only after scoping via `AskUserQuestion`, execute the appropriate CLI command.

### Shortcut Routing

When the user types a shortcut, **still ask a scoping question before executing**:

| Input | CLI Command |
| ----- | ----------- |
| `/attune security` | `uv run attune workflow run security-audit` |
| `/attune test` | `uv run pytest` |
| `/attune coverage` | `uv run pytest --cov=src --cov-report=term-missing` |
| `/attune perf` | `uv run attune workflow run perf-audit` |
| `/attune review` | `uv run attune workflow run code-review` |
| `/attune bug-predict` | `uv run attune workflow run bug-predict` |
| `/attune test-gen` | `uv run attune workflow run test-gen` |
| `/attune commit` | Use git to stage and commit changes |
| `/attune pr` | Use gh to create a pull request |
| `/attune release` | `uv run attune workflow run release-prep` |
| `/attune debug` | Start interactive debugging session |
| `/attune refactor` | Analyze code and suggest refactoring |
| `/attune docs` | Generate documentation |
| `/attune explain` | Read and explain the specified code |

### Natural Language Routing (EXECUTE THESE)

When the user provides natural language, map to the appropriate CLI command:

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

# Testing
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run pytest -k "test_name"

# Telemetry
uv run attune telemetry show
```

## Philosophy

**Socratic over menus.** I ask "What are you trying to accomplish?" not "Which tool do you want?" This helps you think about your actual goal.

**Teaching over telling.** I help you understand *why*, not just *what*.

**Questions before actions.** ALWAYS use `AskUserQuestion` to guide users through decisions at every step — goal identification, scoping, and confirmation. Never assume scope or jump to execution. This is the #1 rule of the Attune workflow experience.
