# Empathy Framework v2.4.0

**AI-powered developer workflows with cost optimization and multi-agent orchestration.**

Run code review, debugging, testing, and release workflows from your terminal or Claude Code. Smart tier routing saves 34-86% on LLM costs.

@./python-standards.md

---

## Quick Start

### Authentication Strategy
```bash
python -m attune.models.auth_cli setup    # Interactive configuration
python -m attune.models.auth_cli status   # View current settings
```

### Agent Coordination Dashboard
```bash
python examples/dashboard_demo.py             # Open at localhost:8000
```

### Natural Language Commands
Use conversational language to access features:
- "setup authentication" → Auth CLI
- "show me the dashboard" → Agent dashboard
- "rapidly generate tests" → Batch test generation
- "find security vulnerabilities" → Security audit workflow

---

## Key Capabilities

**🤖 Multi-Agent Orchestration** - Full support for custom agents and Anthropic LLM agents with 6 coordination patterns (heartbeats, signals, events, approvals, quality feedback, demo mode)

**🔐 Authentication Strategy** - Intelligent routing between Claude subscriptions and Anthropic API based on codebase size. Small/medium modules use subscription (free), large modules use API.

**💰 Cost Optimization** - Smart tier routing (cheap/capable/premium) with automatic model selection saves 34-86% on costs.

**📊 Natural Language Routing** - Intent detection and keyword mapping allow conversational access to all features.

**🧪 Comprehensive Testing** - 13,800+ tests passing at 80%+ coverage with 0 security findings.

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
| `/agent` | create, list, run, release-prep | Agent management |

**Examples:**

```bash
/dev debug "authentication fails on login"
/testing coverage
/workflows security
/release prep
/agent release-prep
```

---

## Lifecycle Hooks

Registered in `.claude/settings.json`, these hooks run automatically:

| Event | Script | Purpose |
| ----- | ------ | ------- |
| SessionStart | `session_start.py` | Loads previous context, patterns, and learned skills |
| Stop | `session_end.py` | Saves session state and triggers cleanup |
| PreToolUse (Bash) | `security_guard.py` | Blocks eval/exec, __import__, rm -rf / |
| PreToolUse (Edit/Write) | `security_guard.py` | Validates file paths, blocks system directory writes |
| PostToolUse (Bash/Edit/Write) | `telemetry_hook.py` | Records tool usage for cost tracking and analytics |

Hook scripts live in `attune_llm/hooks/scripts/` and follow the Claude Code stdin JSON protocol.

---

## Coding Standards

@./rules/empathy/coding-standards-index.md

**Critical rules enforced across all code:**

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations

---

## Project Structure

```
src/attune/
├── workflows/          # AI-powered workflows (7 integrated with auth strategy)
├── models/            # Authentication strategy and LLM providers
├── dashboard/         # Agent Coordination Dashboard (6 patterns)
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Multi-agent coordination and pattern learning
├── telemetry/         # Cost tracking and cache monitoring
└── cli_router.py      # Natural language command routing
```

---

## Documentation

- [AUTH_STRATEGY_GUIDE.md](../docs/AUTH_STRATEGY_GUIDE.md) - Authentication configuration
- [AUTH_CLI_IMPLEMENTATION.md](../docs/AUTH_CLI_IMPLEMENTATION.md) - CLI command reference
- [AUTH_WORKFLOW_INTEGRATIONS.md](../docs/AUTH_WORKFLOW_INTEGRATIONS.md) - Integration patterns
- [CHANGELOG.md](../CHANGELOG.md) - Version history and release notes
- [Full Documentation](https://smartaimemory.com/framework-docs/)

---

**Version:** 2.4.0 (2026-02-08)
**License:** Apache 2.0 - Free and open source
**Repository:** https://github.com/Smart-AI-Memory/attune-ai
