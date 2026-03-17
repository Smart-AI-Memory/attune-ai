# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Production-ready AI workflows for Claude Code, aligned with
Anthropic best practices.**

15 multi-agent workflows for code review, security, testing,
and release — each backed by specialized Claude subagents with
intelligent model routing, budget controls, and structured
output. Just type `/attune` and go.

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-15%2C555%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

```bash
pip install 'attune-ai[developer]'
```

---

## What's New in v5.0.1 — Security Hardening

v5.0.1 hardens memory isolation, hook execution, and MCP
rate limiting across the plugin surface. Built on top of
v5.0.0's Anthropic best practices alignment.

| Feature | What It Does |
| --- | --- |
| **Memory ownership** | Retrieve/delete checks `created_by` before allowing access |
| **Workspace isolation** | INTERNAL classification enforces cross-project boundaries |
| **MCP rate limiter** | 60 calls/min per tool prevents abuse |
| **Hook import guard** | Only `attune.*` modules can be loaded via hooks |
| **Path validation** | State manager and morning workflow now validate all file paths |

<details>
<summary>Previous releases</summary>

### v5.0.0 — Anthropic Best Practices Release

v5.0.0 aligns all 15 SDK-native workflows with Anthropic's
recommended patterns for the Claude Agent SDK. Every workflow
now uses proper system prompts, per-agent model routing,
budget safety nets, cost/usage tracking, and structured output.

**5 features across all 15 workflows:**

| Feature | What It Does | Why It Matters |
| --- | --- | --- |
| **System Prompt Separation** | Persona in `system_prompt`, task in user message | How Anthropic designed the API — better agent behavior |
| **Cost & Usage Tracking** | Surfaces `total_cost_usd`, tokens, turns, session ID | Full visibility into what each workflow costs |
| **Budget Safety Nets** | `max_budget_usd` caps per depth (quick/standard/deep) | Prevents runaway costs; override with `ATTUNE_MAX_BUDGET_USD` |
| **Per-Agent Model Routing** | Opus for security/architecture, Haiku for scanning | Right model for each task; override with env vars |
| **Structured Output** | JSON schema output with text-parsing fallback | Reliable extraction instead of regex; piloting on 2 workflows |

### v4.1.0

- **Smart test selection** — `/smart-test` runs only tests
  affected by your changes using git-diff file mapping.
- **Auto-fix failing tests** — `/fix-test` diagnoses
  failures, applies fixes, and re-runs with up to 3 retries.
- **Testing hub upgrade** — `/testing smart` and
  `/testing fix` routes with natural language routing.

### v4.0.0

- **Full Agent SDK integration** — 15 workflows now have
  Agent SDK adapters for parallel, contextual code analysis.
- **Smart workflow routing** — `get_workflow()` resolves to
  SDK variant when available, with transparent fallback.

### v3.9.x

- **33 MCP tools** — All workflows exposed as MCP tools.
- **`attune doctor`** — Health check for your install.
- **TestAuditWorkflow** and **DocAuditWorkflow** added.
- **Exception handling hardened** across 16 files.

</details>

---

## Workflows

Every workflow runs as a multi-agent team. Each agent is a
specialist — it reads your code with `Read`, `Glob`, and
`Grep` tools and reports findings to an orchestrator that
synthesizes a unified result.

| Workflow | Agents | What It Does | When to Use |
| --- | --- | --- | --- |
| **code-review** | security-reviewer, quality-reviewer, perf-reviewer, architect-reviewer | 4-perspective code review covering security, quality, performance, and architecture | Before merging a PR or after significant changes |
| **security-audit** | vuln-scanner, secret-detector, auth-reviewer, remediation-planner | Finds vulnerabilities, leaked secrets, auth issues, and generates fix plans | Pre-release security gate, compliance checks |
| **deep-review** | security-reviewer, quality-reviewer, test-gap-reviewer | Multi-pass deep analysis with configurable focus areas | Complex modules needing thorough inspection |
| **perf-audit** | complexity-analyzer, bottleneck-finder, optimization-advisor | Identifies O(n^2) patterns, bottlenecks, and optimization opportunities | Slow endpoints, large data processing |
| **bug-predict** | pattern-scanner, risk-correlator, prevention-advisor | Scans for bug-prone patterns and predicts likely failure points | Proactive quality — find bugs before users do |
| **health-check** | test-checker, dep-checker, lint-checker, ci-checker, doc-checker, security-checker | Dynamic agent team (2-6 agents based on mode) for project health | Daily health monitoring, onboarding to a new repo |
| **test-gen** | function-identifier, test-designer, test-writer | Identifies untested functions, designs test cases, writes pytest code | Boosting coverage on undertested modules |
| **test-audit** | coverage-auditor, gap-analyzer, test-planner | Audits test coverage, finds gaps, and prioritizes what to test next | Coverage-driven test improvement |
| **doc-gen** | outline-planner, content-writer, polish-reviewer | Generates documentation from source code with structured outlines | Creating docs for undocumented modules |
| **doc-audit** | staleness-checker, accuracy-reviewer, gap-finder | Checks for stale docs, broken links, and documentation drift | Keeping docs accurate after refactors |
| **dependency-check** | inventory-assessor, update-advisor | Audits dependencies for outdated packages and security advisories | Pre-release dependency review |
| **refactor-plan** | debt-scanner, impact-analyzer, plan-generator | Scans tech debt, analyzes refactoring impact, generates migration plans | Planning large-scale refactors |
| **simplify-code** | complexity-scanner, simplification-designer, safety-reviewer | Finds over-engineered code and proposes simplifications with safety review | Reducing complexity after feature sprints |
| **release-prep** | health-checker, security-scanner, changelog-generator, release-assessor | 4-agent readiness check: health, security, changelog, and go/no-go | Before cutting a release |
| **research-synthesis** | source-summarizer, pattern-analyst, synthesis-writer | Multi-source research synthesis with pattern extraction | Technical research, RFC preparation |

### Model Routing

Each agent is assigned a model based on task complexity:

| Model | Agents | Rationale |
| --- | --- | --- |
| **Opus** | security, vuln, architect | Deep reasoning for security and architecture |
| **Sonnet** | quality, plan, research | Balanced analysis for synthesis and planning |
| **Haiku** | complexity, lint, coverage, dep | Fast scanning for detection tasks |
| **Inherited** | All others | Uses the parent orchestrator's model |

Override any assignment with environment variables:

```bash
# Override security agents to use sonnet (save cost)
export ATTUNE_AGENT_MODEL_SECURITY=sonnet

# Override all agents to use opus (max quality)
export ATTUNE_AGENT_MODEL_DEFAULT=opus

# Let lint agents inherit parent model
export ATTUNE_AGENT_MODEL_LINT=inherit
```

### Budget Controls

Every workflow enforces a budget cap based on depth:

| Depth | Budget | Use Case |
| --- | --- | --- |
| `quick` | $0.50 | Fast checks, smoke tests |
| `standard` | $2.00 | Normal analysis (default) |
| `deep` | $5.00 | Thorough multi-pass review |

```bash
# Override budget for all workflows
export ATTUNE_MAX_BUDGET_USD=10.0

# Disable budget caps entirely
export ATTUNE_MAX_BUDGET_USD=0
```

For **subscription users**, budget caps act as complexity
bounds (the SDK limits resource usage even without per-token
billing). For **API-key users**, they're hard dollar caps.

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

This installs `/attune` to `~/.claude/commands/` for Claude
Code.

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
/testing smart     # Run only tests affected by changes
/attune security   # Security audit
/attune commit     # Create commit
/attune pr         # Create pull request
```

### CLI Usage

Run workflows directly from terminal:

```bash
attune workflow run code-review --path ./src
attune workflow run security-audit --path ./src
attune workflow run release-prep
attune workflow run test-audit
attune telemetry show
```

### What Does It Look Like?

```text
$ attune workflow run security-audit --path src/

[security-audit] vuln-scanner (opus) ........... done
[security-audit] secret-detector (opus) ........ done
[security-audit] auth-reviewer (opus) .......... done
[security-audit] remediation-planner (opus) .... done

Security Audit Results
Score: 95/100 | Cost: $0.03 | Turns: 12

| Severity | Count | Example                       |
|----------|-------|-------------------------------|
| High     | 1     | Broad except in cli.py:42     |
| Medium   | 3     | Missing type hints            |
| Low      | 2     | TODO comments                 |
```

---

## Why Attune?

| | Attune AI | Agent Frameworks (LangGraph, AutoGen) | Coding CLIs (Aider, Codex) | Review Bots (CodeRabbit) |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 15 built-in | Build from scratch | None | PR review only |
| **Per-agent model routing** | Opus/Sonnet/Haiku per role | Manual | None | None |
| **Budget controls** | Depth-based caps | None | None | SaaS pricing |
| **Cost in Claude Code** | $0 for most tasks | API costs | API costs | SaaS pricing |
| **Multi-agent teams** | 2-6 agents per workflow | Yes | No | No |
| **MCP integration** | 17 native tools | No | No | No |
| **Structured output** | JSON schema with fallback | Manual | No | No |

Attune is a **workflow operating system for Claude** — it
sits above coding agents and below general orchestration
frameworks, providing production-ready developer workflows
with intelligent cost routing.

---

## Key Features

### Anthropic Best Practices (v5.0.0)

All 15 workflows follow Anthropic's recommended patterns:

- **System Prompt Separation** — Persona/behavior preamble
  in `system_prompt`, task instructions in user message
- **Per-Agent Model Selection** — Each subagent gets the
  right model for its role via `AgentDefinition.model`
- **Budget Safety Nets** — `max_budget_usd` on every
  `ClaudeAgentOptions` call, configurable per depth
- **Cost/Usage Extraction** — `AgentRunResult` captures
  `total_cost_usd`, `usage`, `num_turns`, `session_id`
- **Structured Output** — JSON schema via `output_format`
  with text-parsing fallback (piloting on code-review and
  security-audit)

### Claude-Native Architecture

Built exclusively for Anthropic/Claude:

- **Automatic Prompt Caching** — Cached tokens cost 10% of
  standard price, delivering up to 90% savings
- **Flexible Context** — 200K via subscription, up to 1M
  via API for large codebases
- **Extended Thinking** — Access Claude's internal reasoning
- **Advanced Tool Use** — Optimized for agentic workflows

### Multi-Agent Orchestration

- **Dynamic Team Composition** — 4 execution strategies
  (parallel, sequential, two-phase, delegation)
- **14 Agent Templates** — Pre-built archetypes with custom
  template registration
- **Agent State Persistence** — Execution history,
  checkpoints, and recovery from interruptions
- **Progressive Tier Escalation** — Start cheap, escalate
  only when needed

### Socratic Workflows

Workflows guide you through discovery instead of requiring
upfront configuration:

- **Interactive Discovery** — Asks targeted questions
- **Context Gathering** — Collects relevant code and errors
- **Dynamic Agent Creation** — Assembles the right team

---

## Command Hubs

Workflows are organized into hubs for easy discovery:

| Hub | Command | Description |
| --- | --- | --- |
| **Developer** | `/dev` | Debug, commit, PR, code review, quality |
| **Testing** | `/testing` | Run tests, smart test, coverage, test gen |
| **Documentation** | `/docs` | Generate docs, changelog, doc audit |
| **Release** | `/release` | Release prep, security scan, publishing |
| **Workflows** | `/workflows` | Automated analysis (security, bugs, perf) |
| **Plan** | `/plan` | Feature planning, brainstorm, refactoring |
| **Agent** | `/agent` | Create and manage custom agents |

**Natural Language Routing:**

```bash
/workflows "find security vulnerabilities"  # -> security-audit
/workflows "check code performance"         # -> perf-audit
/plan "review my code"                      # -> code-review
```

---

## Cost Optimization

### Skills in Claude Code

Most workflows run as skills through the Task tool using
your Claude subscription — no additional API costs:

```bash
/dev           # Uses your Claude subscription
/testing       # Uses your Claude subscription
/release       # Uses your Claude subscription
```

**When API costs apply:** Tasks that exceed your
subscription's context window or programmatic/CI usage route
through the Anthropic API.

### API Mode (CI/CD, Automation)

| Tier | Model | Use Case | Cost |
| --- | --- | --- | --- |
| CHEAP | Haiku | Formatting, simple tasks | ~$0.005 |
| CAPABLE | Sonnet | Bug fixes, code review | ~$0.08 |
| PREMIUM | Opus | Architecture, complex design | ~$0.45 |

```bash
# Track API usage and savings
attune telemetry savings --days 30
```

---

## Claude Code Plugin

Install the attune-ai plugin in Claude Code for integrated
workflow, memory, and orchestration access. The plugin
provides the `/attune` command, 17 MCP tools, and 17 skills.
See the `plugin/` directory.

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
export ANTHROPIC_API_KEY="sk-ant-..."  # Required for CLI
export REDIS_URL="redis://localhost:6379"  # Optional: memory
```

**Optional features:**

```bash
pip install 'attune-ai[memory]'   # Redis-enhanced memory
attune features                   # Check what's available
```

---

## MCP Server Integration

Attune AI includes a Model Context Protocol (MCP) server
that exposes all workflows as native Claude Code tools:

- **17 Tools Available** — Workflow, utility, memory, and
  context tools
- **Automatic Discovery** — Claude Code finds tools via
  `.claude/mcp.json`
- **Natural Language Access** — Describe your need and
  Claude invokes the appropriate tool

---

## Security

- Path traversal protection on all file operations
- JWT authentication with rate limiting
- PII scrubbing in telemetry
- GDPR compliance options
- Automated security scanning

See [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) for vulnerability reporting.

---

## Documentation

- [Quick Start Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/quickstart.md)
- [CLI Reference](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/cli-reference.md)
- [Authentication Strategy Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/AUTH_STRATEGY_GUIDE.md)
- [Orchestration API Reference](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/ORCHESTRATION_API.md)
- [Architecture Overview](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/ARCHITECTURE.md)
- [Full Documentation](https://smartaimemory.com/framework-docs/)

---

## Contributing

See [CONTRIBUTING.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CONTRIBUTING.md) for guidelines.

---

## License

**Apache License 2.0** — Free and open source. Use it,
modify it, build commercial products with it.
[Details](LICENSE)

---

## Acknowledgements

Special thanks to:

- **[Anthropic](https://www.anthropic.com/)** — For Claude
  AI, the Model Context Protocol, and the Agent SDK patterns
  that shaped v5.0.0
- **[Boris Cherny](https://x.com/bcherny)** — Creator of
  Claude Code, whose workflow posts validated Attune's
  approach to plan-first execution and multi-agent
  orchestration
- **[Affaan Mustafa](https://github.com/affaan-m/everything-claude-code)** — For battle-tested Claude Code configurations
  that inspired our hook system

[View Full Acknowledgements](https://github.com/Smart-AI-Memory/attune-ai/blob/main/ACKNOWLEDGMENTS.md)

---

**Built by [Smart AI Memory](https://smartaimemory.com)** ·
[Docs](https://smartaimemory.com/framework-docs/) ·
[Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
