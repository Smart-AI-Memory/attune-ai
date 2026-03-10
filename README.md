# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**AI-powered developer workflows with cost optimization and intelligent routing.**

The easiest way to run code review, debugging, testing, and release workflows from your terminal or Claude Code. Just type `/attune` and let Socratic discovery guide you. Smart tier routing saves 34-86% on LLM costs.

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-16%2C966%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-84%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

```bash
pip install 'attune-ai[developer]'
```

---

## What's New in v3.9.3

- **Anthropic Agent SDK adapters** — Code review and deep
  review workflows now have Agent SDK adapter layers,
  beginning native SDK integration.
- **Workflow validation framework** — Input/output contract
  validation for all workflows.
- **100% public API docstrings** — Added missing docstrings
  across source files.
- **`datetime.utcnow()` migration** — Replaced deprecated
  naive datetimes with timezone-aware `datetime.now(UTC)`
  across the codebase.
- **16,900+ tests** — 290 new tests covering pipeline,
  validation, behavioral, and SDK adapter modules.

<details>
<summary>Previous releases</summary>

### v3.9.2

- **CostReport bug fix** — `WorkflowBatchRunner` crashed
  when accessing `CostReport` dataclass as a dict.
- **Exception handling hardened** — Narrowed broad
  `except Exception` to specific types across 16 files.
- **Batch API rename** — `/batch` renamed to `/bulk` to
  avoid collision with Claude Code's built-in `/batch`.

### v3.9.0

- **33 MCP tools** — All 17 workflows now exposed as MCP
  tools (was 6). Includes doc-audit, test-audit,
  dependency-check, health-check, and more.
- **`attune doctor`** — Single command to check Python
  version, API key, workflows, wizards, MCP, and optional
  deps.
- **Fast-path slash commands** — Power users who provide
  both action and target skip Socratic scoping questions.

### v3.8.0

- **TestAuditWorkflow** — 4-stage coverage audit pipeline.
- **DocAuditWorkflow** — 10-check documentation audit.
- **1,636 new unit tests** at 84% coverage.

- **v3.7.0** — Mixin MRO fix, dashboard removal began,
  CI test coverage expanded
- **v3.6.6** — Wizard REVIEW step, 82 new workflow tests,
  BEP middleware removed
- **v3.6.5** — Dashboard module removed
- **v3.6.4** — EscalationChain retry-with-feedback wrapper
- **v3.6.0** — attune-redis plugin, FeedbackLoop, in-memory
  fallback

</details>

---

## Why Attune?

| | Attune AI | Agent Frameworks (LangGraph, AutoGen) | Coding CLIs (Aider, Codex) | Review Bots (CodeRabbit) |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 17 built-in | Build from scratch | None | PR review only |
| **Cost optimization** | 3-tier auto-routing | None | None | None |
| **Cost in Claude Code** | $0 for most tasks | API costs | API costs | SaaS pricing |
| **Multi-agent teams** | 4 strategies | Yes | No | No |
| **MCP integration** | 17 native tools | No | No | No |

Attune is a **workflow operating system for Claude** — it sits above coding agents and below general orchestration frameworks, providing production-ready developer workflows with intelligent cost routing. [Full comparison](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/comparison.md)

---

## Key Features

### Claude-Native Architecture

Attune AI is built exclusively for Anthropic/Claude, unlocking features impossible with multi-provider abstraction:

- **Automatic Prompt Caching** - Built on Anthropic's auto-caching: cached tokens cost 10% of standard price, delivering up to 90% cost savings and 85% faster responses. Zero configuration required.
- **Semantic Caching** - Optional HybridCache (via sentence-transformers) detects similar prompts and reuses cached responses, avoiding redundant API calls entirely. ~57% measured hit rate on workflows.
- **Flexible Context** - 200K via subscription, up to 1M via API for large codebases
- **Extended Thinking** - Access Claude's internal reasoning process
- **Advanced Tool Use** - Optimized for agentic workflows

### Multi-Agent Orchestration

Full support for custom agents, dynamic teams, and Anthropic Agent SDK:

- **Dynamic Team Composition** - Build agent teams from templates, specs, or MetaOrchestrator plans with 4 execution strategies (parallel, sequential, two-phase, delegation)
- **14 Agent Templates** - Pre-built archetypes (security auditor, code reviewer, test coverage, etc.) with custom template registration
- **Agent State Persistence** - `AgentStateStore` records execution history, saves checkpoints, and enables recovery from interruptions
- **Workflow Composition** - Compose entire workflows into `DynamicTeam` instances for orchestrated parallel/sequential execution
- **Progressive Tier Escalation** - Agents start cheap and escalate only when needed (CHEAP -> CAPABLE -> PREMIUM)
- **Inter-Agent Communication** - Heartbeats, signals, events, approval gates, and 6 coordination patterns
- **Quality Gates** - Per-agent and cross-team quality thresholds with required/optional gate enforcement

### Modular Architecture

Clean, maintainable codebase built for extensibility:

- **Small, Focused Files** - Most files under 700 lines; logic extracted into mixins and utilities
- **Cross-Platform CI** - Tested on Ubuntu, macOS, and Windows with Python 3.10-3.13
- **16,900+ tests** - Security, unit, integration, and behavioral test coverage

### Intelligent Cost Optimization

- **$0 for most Claude Code tasks** - Standard workflows run as skills through Claude's Task tool at no extra cost
- **API costs for large contexts** - Tasks requiring extended context (>200K tokens) or programmatic/CI usage route through the Anthropic API
- **Smart Tier Routing** - Automatically selects the right model for each task
- **Authentication Strategy** - Routes between subscription and API based on codebase size

### Socratic Workflows

Workflows guide you through discovery instead of requiring upfront configuration:

- **Interactive Discovery** - Asks targeted questions to understand your needs
- **Context Gathering** - Collects relevant code, errors, and constraints
- **Dynamic Agent Creation** - Assembles the right team based on your answers

---

## Claude Code Plugin

Install the attune-ai plugin in Claude Code for integrated workflow, memory, and orchestration access. The plugin provides the `/attune` command, 17 MCP tools, and 17 skills. See the `plugin/` directory.

---

## Quick Start

### 1. Install

```bash
pip install 'attune-ai[developer]'
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
attune workflow run test-audit             # Coverage-driven test gap analysis
attune workflow run doc-audit              # 10-check documentation audit
attune telemetry show
```

### What Does It Look Like?

```text
$ attune workflow run security-audit --path src/

[security-audit] Stage 1/3: scan (haiku) ... done (0.8s)
[security-audit] Stage 2/3: analyze (sonnet) ... done (2.1s)
[security-audit] Stage 3/3: report (sonnet) ... done (1.4s)

Security Audit Results
Score: 95/100

| Severity | Count | Example                       |
|----------|-------|-------------------------------|
| High     | 1     | Broad except in cli.py:42     |
| Medium   | 3     | Missing type hints            |
| Low      | 2     | TODO comments                 |

Total cost: $0.025 (saved 78% via tier routing)
```

### Optional Features

**Redis-enhanced memory** (auto-detected when installed):

```bash
pip install 'attune-ai[memory]'
# Redis is automatically detected and enabled — no env vars needed
```

**All features** (includes memory, agents, semantic caching):

```bash
pip install 'attune-ai[all]'
```

**Check what's available:**

```bash
attune features
```

See [Feature Availability Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/FEATURES.md) for detailed information about core vs optional features.

---

## Command Hubs

Workflows are organized into hubs for easy discovery:

| Hub               | Command       | Description                                  |
| ----------------- | ------------- | -------------------------------------------- |
| **Developer**     | `/dev`        | Debug, commit, PR, code review, quality      |
| **Testing**       | `/testing`    | Run tests, coverage audit, test generation   |
| **Documentation** | `/docs`       | Generate docs, changelog, doc audit          |
| **Release**       | `/release`    | Release prep, security scan, publishing      |
| **Workflows**     | `/workflows`  | Automated analysis (security, bugs, perf)    |
| **Plan**          | `/plan`       | Feature planning, brainstorm, refactoring    |
| **Agent**         | `/agent`      | Create and manage custom agents              |

**Natural Language Routing:**

```bash
/workflows "find security vulnerabilities"  # → security-audit
/workflows "check code performance"         # → perf-audit
/plan "review my code"                      # → code-review
```

---

## Cost Optimization

### Skills in Claude Code

Most workflows run as skills through the Task tool using your
Claude subscription — no additional API costs:

```bash
/dev           # Uses your Claude subscription
/testing       # Uses your Claude subscription
/release       # Uses your Claude subscription
```

**When API costs apply:** Tasks that exceed your subscription's
context window (e.g., large codebases >2000 LOC), or
programmatic/CI usage, route through the Anthropic API.
The auth strategy automatically handles this routing.

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

- **17 Tools Available** - Workflow tools (security_audit, bug_predict, code_review, test_generation, performance_audit, release_prep) plus utility, memory, and context tools
- **Automatic Discovery** - Claude Code finds tools via `.claude/mcp.json`
- **Natural Language Access** - Describe your need and Claude invokes the appropriate tool

```bash
# Verify MCP integration
echo '{"method":"tools/list","params":{}}' | PYTHONPATH=./src python -m attune.mcp.server
```

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
# Recommended (agents, memory, semantic caching)
pip install 'attune-ai[developer]'

# Minimal (CLI + workflows only)
pip install attune-ai

# All features
pip install 'attune-ai[all]'

# Development (contributing)
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

**What's in each option:**

| Option | What You Get |
| --- | --- |
| `[developer]` | CLI, workflows, agents, memory, semantic caching |
| Base | CLI, workflows, Anthropic SDK |
| `[all]` | Everything including enterprise features |

---

## Environment Setup

**In Claude Code:** No API key needed — workflows run as
skills using your Claude subscription. Just type `/attune`.

**For CLI usage** (`attune workflow run ...`):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Required for CLI workflows
export REDIS_URL="redis://localhost:6379"  # Optional: memory features
```

**How to tell which you need:**

- Using Claude Code interactively? No key needed.
- Running `attune workflow run` from terminal/CI? Set
  `ANTHROPIC_API_KEY`.

---

## Security

- Path traversal protection on all file operations (`_validate_file_path()` — single source in `security/path_validation.py`)
- JWT authentication with rate limiting
- PII scrubbing in telemetry
- GDPR compliance options
- Automated security scanning with continuous remediation

```bash
# Run security audit
attune workflow run security-audit --path ./src
```

See [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) for vulnerability reporting.

---

## Documentation

- [Quick Start Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/quickstart.md)
- [CLI Reference](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/cli-reference.md)
- [Authentication Strategy Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/AUTH_STRATEGY_GUIDE.md)
- [Orchestration API Reference](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/ORCHESTRATION_API.md)
- [Workflow Coordination Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/WORKFLOW_COORDINATION.md)
- [Architecture Overview](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/ARCHITECTURE.md)
- [Full Documentation](https://smartaimemory.com/framework-docs/)

---

## Contributing

See [CONTRIBUTING.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CONTRIBUTING.md) for guidelines.

---

## License

**Apache License 2.0** - Free and open source. Use it, modify it, build commercial products with it. [Details →](LICENSE)

---

## Acknowledgements

Special thanks to:

- **[Anthropic](https://www.anthropic.com/)** — For Claude AI, the Model Context Protocol, and the documentation that shaped our workflow patterns
- **[Boris Cherny](https://x.com/bcherny)** — Creator of Claude Code, whose candid workflow posts validated and refined Attune's approach to plan-first execution, verification loops, and multi-agent orchestration
- **[Affaan Mustafa](https://github.com/affaan-m/everything-claude-code)** — For battle-tested Claude Code configurations that inspired our hook system and markdown agent format
- **[LangChain](https://github.com/langchain-ai/langchain)** — Agent framework foundations
- **[FastAPI](https://github.com/tiangolo/fastapi)** — Modern Python web framework

[View Full Acknowledgements →](https://github.com/Smart-AI-Memory/attune-ai/blob/main/ACKNOWLEDGMENTS.md)

---

**Built by [Smart AI Memory](https://smartaimemory.com)** · [Docs](https://smartaimemory.com/framework-docs/) · [Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
