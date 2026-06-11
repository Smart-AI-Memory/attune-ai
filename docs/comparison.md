# Attune AI vs. The Landscape

How Attune AI compares to other AI developer frameworks, coding CLI tools, and code review platforms.

---

## At a Glance

| Feature | Attune AI | LangGraph | AutoGen | Aider | Claude Code | CodeRabbit |
| ------- | --------- | --------- | ------- | ----- | ----------- | ---------- |
| **Primary focus** | Developer workflows | Graph orchestration | Agent dialogue | Pair programming | Autonomous coding | PR review |
| **Built-in workflows** | 27+ | None | None | None | None | None |
| **Multi-agent** | 4 strategies | Graph nodes | Conversations | No | No | No |
| **Cost optimization** | 3-tier routing | No | No | No | No | No |
| **Claude Code integration** | Native plugin | No | No | No | N/A | No |
| **MCP tools** | 18 | No | No | No | Built-in | No |
| **Code editing** | No (delegates) | No | No | Yes | Yes | No |
| **Pricing** | Free (OSS) | Free (OSS) | Free (OSS) | Free (OSS) | Subscription | Freemium |
| **Provider support** | Claude-native | Multi-provider | Multi-provider | Multi-provider | Claude only | Multi-provider |

---

## Comparison by Category

### vs. Multi-Agent Frameworks (LangGraph, AutoGen)

These are **general-purpose toolkits** for building custom agent systems. You define agents, tools, and orchestration logic from scratch.

**Attune is different because:**

- **Batteries included** — 27+ production-ready workflows out of the box. Type `/attune security` and get a security audit. No agent definitions, no graph design, no boilerplate.
- **Cost-aware by default** — 3-tier model routing (Haiku/Sonnet/Opus) automatically selects the cheapest model that can handle each task, saving 34-86% on LLM costs.
- **$0 in Claude Code** — Workflows run as skills through Claude's Task tool, using your subscription instead of API credits.
- **Socratic CLI** — Natural language routing (`/attune "find security vulnerabilities"`) instead of configuration files.

**When to choose a general framework instead:**

- You need custom agent topologies with arbitrary graph structures
- You're building a non-developer-tool product
- You need provider-agnostic agents across OpenAI, Gemini, etc.

---

### vs. AI Coding CLI Tools (Aider, Claude Code, Codex CLI)

These tools **write and edit code** directly in your codebase. They're autonomous coding agents.

**Attune is different because:**

- **Complements, doesn't compete** — Attune extends Claude Code as a plugin rather than replacing it. It adds workflows, memory, and orchestration on top of Claude Code's editing capabilities.
- **Higher-level operations** — While coding CLIs edit files, Attune orchestrates multi-agent audits, release readiness checks, and test generation pipelines.
- **Structured output** — Workflows produce scored reports (security: 100/100, coverage: 85%) rather than code diffs.

**When to choose a coding CLI instead:**

- You need direct code editing and pair programming
- You want a standalone tool, not a plugin
- Your primary need is writing code, not validating it

---

### vs. AI Code Review Tools (CodeRabbit, Greptile, Sweep)

These are **SaaS platforms** that review pull requests automatically in your CI pipeline.

**Attune is different because:**

- **Broader scope** — Not just code review but a full validation suite: security audit, performance audit, bug prediction, test generation, and release readiness (with a 4-agent team).
- **Runs locally** — No data leaves your machine. No SaaS dependency.
- **Developer-initiated** — You run audits when you want, not just on PRs.

**When to choose a review platform instead:**

- You need automatic PR reviews for a team
- You want GitHub/GitLab integration without CLI usage
- You need team collaboration features (comments, approvals)

---

## Why Attune AI

### 1. Cost optimization is a first-class feature

No other framework has built-in 3-tier model routing with savings tracking. Attune automatically selects Haiku for simple tasks, Sonnet for analysis, and Opus only when needed.

```bash
attune telemetry savings --days 30
```

### 2. $0 in Claude Code

Running as skills through the Task tool means zero API cost for Claude subscription users. Every competitor charges per API call.

### 3. Production-ready workflows, not a toolkit

You don't build workflows from scratch. You type `/attune security` and get a scored security audit. `/attune release` runs a 4-agent team that checks security, coverage, quality, and documentation.

### 4. Socratic discovery

Natural language routing means you describe what you need, not which tool to invoke:

```bash
/attune "find security vulnerabilities"    # routes to security-audit
/attune "check code performance"           # routes to perf-audit
/attune "prepare for release"              # routes to release-prep
```

### 5. Multi-agent orchestration included

4 execution strategies (parallel, sequential, two-phase, delegation), quality gates, state persistence, and recovery — built in, not bolted on.

---

## Quick Start

```bash
pip install attune-ai
attune setup
```

Then in Claude Code:

```bash
/attune
```

---

## Links

- [PyPI](https://pypi.org/project/attune-ai/)
- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [Documentation](https://smartaimemory.com/framework-docs/)
