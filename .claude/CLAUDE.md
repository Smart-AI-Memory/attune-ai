# Attune AI Framework v2.10.3

AI-powered developer workflows with cost optimization and multi-agent orchestration.

@./python-standards.md

---

## Quick Start

```bash
python -m attune.models.auth_cli setup    # Configure authentication
python examples/dashboard_demo.py         # Agent dashboard at localhost:8000
```

**CLI:** `attune <command>` (canonical) or `python -m attune.cli` (full). See `docs/reference/cli-reference.md`.

---

## Command Hubs

Use `/hub-name` to access organized workflows:

| Hub | Key Routes | Description |
| --- | ---------- | ----------- |
| `/attune` | Socratic discovery | Natural language routing to all workflows |
| `/dev` | debug, review, commit, pr, refactor, quality | Developer tools |
| `/testing` | run, coverage, generate, tdd | Test runner and generation |
| `/workflows` | security, bugs, perf, review, list | Automated analysis |
| `/plan` | feature, tdd, refactor, architecture | Planning and strategy |
| `/docs` | generate, readme, changelog, explain | Documentation |
| `/release` | prep, security, health, publish | Release preparation |
| `/brainstorm` | discover, plan, export | Guided brainstorming and ideation |
| `/agent` | create, list, run, release-prep | Agent management |
| `/batch` | submit, status, results, wait | Batch API (50% savings) |

---

## Markdown Formatting

All `.md` files should follow these rules:

- Start every `.md` file with a single `#` (h1) heading
- Heading levels must increment by one (don't skip from
  `#` to `###`)
- Put a single space after `#` in headings
- Surround headings with blank lines (one above, one below)
- Surround fenced code blocks (```) with blank lines
- Surround lists with blank lines
- Use `-` (dash) for unordered list markers, not `*` or `+`
- No trailing whitespace on lines
- No hard tabs — use spaces
- No multiple consecutive blank lines
- End files with a single trailing newline
- Keep lines under 80 characters (except tables and URLs)
- Do not manually pad or align table cells with extra
  spaces — tables are exempt from trailing space rules

---

## Critical Rules

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations

---

## Socratic Interaction Rule

**ALWAYS use `AskUserQuestion` to guide users through workflow discovery and scoping. NEVER skip straight to execution.**

This is the core design principle of Attune AI's developer experience. When a user invokes `/attune` or any workflow:

1. **Initial discovery**: Use `AskUserQuestion` to understand their goal (what are you trying to accomplish?)
2. **Scoping**: Use `AskUserQuestion` to narrow scope (which files? what test subset? what level of detail?)
3. **Confirmation**: Use `AskUserQuestion` if there are meaningful choices before execution (approach, format, targets)
4. **Then execute**: Only run CLI commands or tools after the user has been guided through the relevant decisions

**Examples of when to ask:**

- User says "run tests" → Ask: which tests? full suite, CLI only, or quick smoke test?
- User says "security audit" → Ask: which path? src/, tests/, or full project?
- User says "review code" → Ask: which files or area? what focus (security, quality, performance)?
- User says "commit" → Ask: which files to stage? what kind of change is this?

**Do NOT:**

- Jump straight to running commands without scoping
- Assume the user wants the broadest possible execution
- Skip questions just because the next step seems obvious

This rule applies to ALL workflow interactions, not just `/attune`.

---

## Project Structure

```text
src/attune/
├── agents/            # Agent SDK, state persistence, recovery
│   ├── sdk/           # SDKAgent, SDKAgentTeam, adapters
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── workflows/         # AI-powered workflows with state & multi-agent mixins
├── models/            # Authentication strategy and LLM providers
├── dashboard/         # Agent Coordination Dashboard (6 patterns)
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, pattern learning
├── telemetry/         # Cost tracking and cache monitoring
└── cli_router.py      # Natural language command routing
```

---

**Version:** 2.10.3 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
