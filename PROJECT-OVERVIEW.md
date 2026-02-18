# Attune AI — Project Overview

AI-powered developer workflows with cost optimization
and multi-agent orchestration.

## At a Glance

| Detail | Value |
|--------|-------|
| **Version** | 2.10.2 |
| **License** | Apache 2.0 |
| **Python** | 3.11+ |
| **Status** | Active Development |
| **Repo** | [attune-ai](https://github.com/Smart-AI-Memory/attune-ai) |

## What It Does

Attune AI provides a Claude-native framework for
building intelligent developer workflows with 3-tier
cost routing, caching, and agent coordination.

### Key Capabilities

- **3-tier cost routing** — Route tasks to Haiku,
  Sonnet, or Opus based on complexity and budget
- **Workflow engine** — Prebuilt workflows for security
  audits, code review, bug prediction, and more
- **Agent coordination** — Spawn, track, and recover
  teams of cooperating agents
- **Unified memory** — Persistent context across sessions
  with Redis-backed storage
- **Cost telemetry** — Track spend per workflow, model,
  and tier in real time

## Architecture

```text
┌─────────────────────────────────────────────┐
│           CLI / Claude Code Skills           │
├──────────┬──────────┬───────────┬───────────┤
│ Workflows│  Agents  │  Memory   │ Telemetry │
├──────────┴──────────┴───────────┴───────────┤
│         Model Router (3-Tier Routing)        │
├─────────────┬───────────────┬───────────────┤
│ Haiku (Cheap)│Sonnet (Capable)│ Opus (Premium)│
└─────────────┴───────────────┴───────────────┘
```

### Source Layout

| Directory | Purpose |
|-----------|---------|
| `src/attune/agents/` | Agent SDK, state, recovery |
| `src/attune/workflows/` | AI-powered workflow engine |
| `src/attune/models/` | Auth strategy, LLM providers |
| `src/attune/dashboard/` | Coordination dashboard |
| `src/attune/meta_workflows/` | Intent detection, routing |
| `src/attune/orchestration/` | Dynamic teams, composition |
| `src/attune/memory/` | Unified memory system |
| `src/attune/telemetry/` | Cost tracking, cache stats |

## Workflows

Built-in workflows available out of the box:

| Workflow | Command | Description |
|----------|---------|-------------|
| Security Audit | `attune security` | Scan for vulnerabilities |
| Code Review | `attune review` | Quality and style analysis |
| Bug Prediction | `attune bugs` | Predict likely defect sites |
| Perf Audit | `attune perf` | Find performance hotspots |
| Refactor Plan | `attune refactor` | Generate refactoring steps |
| Release Prep | `attune release` | Pre-release checklist |
| Dependency Check | `attune deps` | Outdated/vulnerable deps |
| Test Generation | `attune testgen` | Generate test scaffolds |

## Getting Started

### Prerequisites

- Python 3.11 or later
- Redis (optional, for memory features)
- Anthropic API key (or Claude Code subscription)

### Quick Start

```bash
# Install
pip install attune-ai

# Configure authentication
python -m attune.models.auth_cli setup

# Run your first workflow
attune review --path src/

# Launch the dashboard
python examples/dashboard_demo.py
```

### Configuration

Attune reads configuration from these sources
(highest priority first):

1. CLI flags (`--model`, `--tier`, `--path`)
2. Environment variables (`ATTUNE_MODEL`, etc.)
3. Project config (`attune.config.yml`)
4. User config (`~/.attune/config.yml`)
5. Built-in defaults

## Model Tiers

Requests are routed through a tiered model system
that balances cost and capability:

| Tier | Model | Cost (in/out per M) | Use Case |
|------|-------|---------------------|----------|
| **Cheap** | Haiku 4.5 | $1 / $5 | Classification, triage |
| **Capable** | Sonnet 4.6 | $3 / $15 | Code review, analysis |
| **Premium** | Opus 4.6 | $5 / $25 | Architecture, reasoning |

The router automatically selects the cheapest tier
that meets the quality threshold for each task.

## Testing

```bash
# Run full test suite
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run security tests
pytest tests/unit/test_*_security.py -v
```

### Coverage Targets

| Area | Target | Current |
|------|--------|---------|
| Overall | 80% | 85% |
| Workflows | 80% | 82% |
| Security | 90% | 93% |
| Config | 80% | 88% |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the [coding standards](.claude/rules/attune/coding-standards-index.md)
4. Add tests for new functionality
5. Run `pre-commit run --all-files`
6. Open a pull request

### Code Quality Checks

| Tool | Purpose | Command |
|------|---------|---------|
| Black | Formatting | `black src/` |
| Ruff | Linting | `ruff check src/` |
| Bandit | Security | `bandit -r src/` |
| pytest | Tests | `pytest --cov=src` |

## Links

- [CLI Reference](docs/reference/cli-reference.md)
- [User Guide](docs/reference/USER_GUIDE.md)
- [API Reference](docs/reference/API_REFERENCE.md)
- [FAQ](docs/reference/FAQ.md)
- [Troubleshooting](docs/reference/TROUBLESHOOTING.md)
