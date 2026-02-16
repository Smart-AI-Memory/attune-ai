# Attune AI

**AI-powered developer workflows with cost optimization and intelligent routing.**

The easiest way to run code review, debugging, testing, and release workflows from your terminal or Claude Code. Just type `/attune` and let Socratic discovery guide you. Smart tier routing saves 34-86% on LLM costs.

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-14915%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

```bash
pip install attune-ai[developer]
```

---

## What's New in v2.9.0

- **XML Prompt Benchmark Suite** - A/B testing harness (`benchmarks/xml_vs_plain/`) that measures XML vs plain text prompt quality on Claude 4.x with 5 automated metrics. Real API results: 100% parse success, +68% quality score.
- **Data-Driven XML Configuration** - Per-workflow XML settings based on 30-call benchmark on Sonnet 4.5. Security-audit uses XML (+30% quality, +15% cost). Code-review and perf-audit use plain text (lower cost, same quality).
- **XML Enabled by Default** - All 10 XML templates and 5 wizards now use structured XML prompts unless explicitly disabled. Enables machine-parseable output for dashboards and automation.
- **14,915 Tests Passing** - 83% coverage across security, unit, integration, and behavioral tests.

---

## Why Attune?

| | Attune AI | Agent Frameworks (LangGraph, AutoGen) | Coding CLIs (Aider, Codex) | Review Bots (CodeRabbit) |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 15 built-in | Build from scratch | None | PR review only |
| **Cost optimization** | 3-tier auto-routing | None | None | None |
| **Cost in Claude Code** | $0 (skill-based) | API costs | API costs | SaaS pricing |
| **Multi-agent teams** | 4 strategies | Yes | No | No |
| **MCP integration** | 18 native tools | No | No | No |

Attune is a **workflow operating system for Claude** — it sits above coding agents and below general orchestration frameworks, providing production-ready developer workflows with intelligent cost routing. [Full comparison](docs/comparison.md)

---

## Key Features

### Claude-Native Architecture

Attune AI is built exclusively for Anthropic/Claude, unlocking features impossible with multi-provider abstraction:

- **Prompt Caching** - 90% cost reduction on repeated prompts
- **Flexible Context** - 200K via subscription, up to 1M via API for large codebases
- **Extended Thinking** - Access Claude's internal reasoning process
- **Advanced Tool Use** - Optimized for agentic workflows

### Multi-Agent Orchestration

Full support for custom agents, dynamic teams, and Anthropic Agent SDK:

- **Dynamic Team Composition** - Build agent teams from templates, specs, or MetaOrchestrator plans with 4 execution strategies (parallel, sequential, two-phase, delegation)
- **13 Agent Templates** - Pre-built archetypes (security auditor, code reviewer, test coverage, etc.) with custom template registration
- **Agent State Persistence** - `AgentStateStore` records execution history, saves checkpoints, and enables recovery from interruptions
- **Workflow Composition** - Compose entire workflows into `DynamicTeam` instances for orchestrated parallel/sequential execution
- **Progressive Tier Escalation** - Agents start cheap and escalate only when needed (CHEAP -> CAPABLE -> PREMIUM)
- **Agent Coordination Dashboard** - Real-time monitoring with 6 coordination patterns
- **Inter-Agent Communication** - Heartbeats, signals, events, and approval gates
- **Quality Gates** - Per-agent and cross-team quality thresholds with required/optional gate enforcement

### Modular Architecture

Clean, maintainable codebase built for extensibility:

- **Small, Focused Files** - No file exceeds 1,000 lines; logic extracted into mixins and utilities
- **Cross-Platform CI** - Tested on Ubuntu, macOS, and Windows with Python 3.10-3.13
- **14,915+ Unit Tests** - Security, unit, integration, and behavioral test coverage at 83% coverage

### Intelligent Cost Optimization

- **$0 in Claude Code** - Workflows run as skills through Claude's Task tool
- **Smart Tier Routing** - Automatically selects the right model for each task
- **Authentication Strategy** - Routes between subscription and API based on codebase size

### Socratic Workflows

Workflows guide you through discovery instead of requiring upfront configuration:

- **Interactive Discovery** - Asks targeted questions to understand your needs
- **Context Gathering** - Collects relevant code, errors, and constraints
- **Dynamic Agent Creation** - Assembles the right team based on your answers

---

## Claude Code Plugin

Install the attune-ai plugin in Claude Code for integrated workflow, memory, and orchestration access. The plugin provides the `/attune` command, 18 MCP tools, and 3 skills (memory-and-context, workflow-orchestration, refactor-plan). See the `plugin/` directory.

---

## Quick Start

### 1. Install

```bash
pip install attune-ai
```

### 2. Setup Slash Commands

```bash
attune setup
```

This installs `/attune` to `~/.claude/commands/` for Claude Code.

### 3. Use in Claude Code

Just type:

```bash
/attune
```

Socratic discovery guides you to the right workflow.

**Or use shortcuts:**

```bash
/attune debug      # Debug an issue
/attune test       # Run tests
/attune security   # Security audit
/attune commit     # Create commit
/attune pr         # Create pull request
```

### CLI Usage

Run workflows directly from terminal:

```bash
attune workflow run release-prep           # 4-agent release readiness check
attune workflow run security-audit --path ./src
attune workflow run test-gen --path ./src
attune telemetry show
```

### Optional Features

**Redis-enhanced memory** (for multi-session coordination, real-time events):

```bash
pip install 'attune-ai[memory]'
```

**All features** (includes memory, dashboard, agents):

```bash
pip install 'attune-ai[all]'
```

**Check what's available:**

```bash
attune features
```

See [Feature Availability Guide](docs/FEATURES.md) for detailed information about core vs optional features.

---

## Command Hubs

Workflows are organized into hubs for easy discovery:

| Hub               | Command       | Description                                  |
| ----------------- | ------------- | -------------------------------------------- |
| **Developer**     | `/dev`        | Debug, commit, PR, code review, quality      |
| **Testing**       | `/testing`    | Run tests, coverage analysis, benchmarks     |
| **Documentation** | `/docs`       | Generate and manage documentation            |
| **Release**       | `/release`    | Release prep, security scan, publishing      |
| **Workflows**     | `/workflows`  | Automated analysis (security, bugs, perf)    |
| **Plan**          | `/plan`       | Planning, TDD, code review, refactoring      |
| **Agent**         | `/agent`      | Create and manage custom agents              |

**Natural Language Routing:**

```bash
/workflows "find security vulnerabilities"  # → security-audit
/workflows "check code performance"         # → perf-audit
/plan "review my code"                      # → code-review
```

---

## Cost Optimization

### Skills = $0 (Claude Code)

When using Claude Code, workflows run as skills through the Task tool - **no API costs**:

```bash
/dev           # $0 - uses your Claude subscription
/testing       # $0
/release       # $0
```

### API Mode (CI/CD, Automation)

For programmatic use, smart tier routing saves 34-86%:

| Tier    | Model         | Use Case                     | Cost    |
| ------- | ------------- | ---------------------------- | ------- |
| CHEAP   | Haiku         | Formatting, simple tasks     | ~$0.005 |
| CAPABLE | Sonnet        | Bug fixes, code review       | ~$0.08  |
| PREMIUM | Opus          | Architecture, complex design | ~$0.45  |

```bash
# Track API usage and savings
attune telemetry savings --days 30
```

---

## MCP Server Integration

Attune AI includes a Model Context Protocol (MCP) server that exposes all workflows as native Claude Code tools:

- **10 Tools Available** - security_audit, bug_predict, code_review, test_generation, performance_audit, release_prep, and more
- **Automatic Discovery** - Claude Code finds tools via `.claude/mcp.json`
- **Natural Language Access** - Describe your need and Claude invokes the appropriate tool

```bash
# Verify MCP integration
echo '{"method":"tools/list","params":{}}' | PYTHONPATH=./src python -m attune.mcp.server
```

---

## Agent Coordination Dashboard

Real-time monitoring with 6 coordination patterns:

- Agent heartbeats and status tracking
- Inter-agent coordination signals
- Event streaming across agent workflows
- Approval gates for human-in-the-loop
- Quality feedback and performance metrics
- Demo mode with test data generation

```bash
# Launch dashboard (requires Redis 7.x or 8.x)
python examples/dashboard_demo.py
# Open http://localhost:8000
```

**Redis 8.4 Support:** Full compatibility with RediSearch, RedisJSON, RedisTimeSeries, RedisBloom, and VectorSet modules.

---

## Authentication Strategy

Intelligent routing between Claude subscription and Anthropic API:

```bash
# Interactive setup
python -m attune.models.auth_cli setup

# View current configuration
python -m attune.models.auth_cli status

# Get recommendation for a file
python -m attune.models.auth_cli recommend src/module.py
```

**Automatic routing:**

- Small/medium modules (<2000 LOC) → Claude subscription (free)
- Large modules (>2000 LOC) → Anthropic API (pay for what you need)

---

## Installation Options

```bash
# Base install (CLI + workflows)
pip install attune-ai

# Full developer experience (multi-LLM, agents, memory)
pip install attune-ai[developer]

# With semantic caching (70% cost reduction)
pip install attune-ai[cache]

# Enterprise (auth, rate limiting, telemetry)
pip install attune-ai[enterprise]

# Development
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e .[dev]
```

**What's in each option:**

| Option         | What You Get                                   |
| -------------- | ---------------------------------------------- |
| Base           | CLI, workflows, Anthropic SDK                  |
| `[developer]`  | + OpenAI, Google AI, LangChain agents, memory  |
| `[cache]`      | + Semantic similarity caching                  |
| `[enterprise]` | + JWT auth, rate limiting, OpenTelemetry       |

---

## Environment Setup

**In Claude Code:** No setup needed - uses your Claude subscription.

**For CLI/API usage:**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Required for CLI workflows
export REDIS_URL="redis://localhost:6379"  # Optional: for memory features
```

---

## Security

- Path traversal protection on all file operations (`_validate_file_path()` on 22 write operations)
- JWT authentication with rate limiting
- PII scrubbing in telemetry
- GDPR compliance options
- Automated security scanning (517 findings remediated to 0 across codebase)

```bash
# Run security audit
attune workflow run security-audit --path ./src
```

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [CLI Reference](docs/cli-reference.md)
- [Authentication Strategy Guide](docs/AUTH_STRATEGY_GUIDE.md)
- [Orchestration API Reference](docs/ORCHESTRATION_API.md)
- [Workflow Coordination Guide](docs/WORKFLOW_COORDINATION.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Full Documentation](https://smartaimemory.com/framework-docs/)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

**Apache License 2.0** - Free and open source. Use it, modify it, build commercial products with it. [Details →](LICENSE)

---

## Acknowledgements

Special thanks to:

- **[Anthropic](https://www.anthropic.com/)** - For Claude AI and the Model Context Protocol
- **[LangChain](https://github.com/langchain-ai/langchain)** - Agent framework powering our orchestration
- **[FastAPI](https://github.com/tiangolo/fastapi)** - Modern Python web framework

[View Full Acknowledgements →](ACKNOWLEDGEMENTS.md)

---

**Built by [Smart AI Memory](https://smartaimemory.com)** · [Docs](https://smartaimemory.com/framework-docs/) · [Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
