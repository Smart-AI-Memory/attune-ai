# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Production-ready AI workflows for Claude Code, aligned
with Anthropic best practices.**

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-15%2C446%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

## Get Started in 60 Seconds

### Plugin (works standalone)

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Then say "what can attune do?" in Claude Code. That's it.

### Add Python Package (optional — unlocks CLI + MCP)

```bash
pip install 'attune-ai[developer]'
```

---

## Cheat Sheet

All 13 skills trigger automatically from natural
language — just describe what you need:

| Input | What Happens |
| ----- | ------------ |
| "what can attune do?" | Auto-triggers `attune-hub` — guided discovery |
| "build this feature from scratch" | Auto-triggers `spec` — brainstorm → plan → execute |
| "review my code" | Auto-triggers `code-quality` skill |
| "scan for vulnerabilities" | Auto-triggers `security-audit` skill |
| "generate tests for src/" | Auto-triggers `smart-test` skill |
| "fix failing tests" | Auto-triggers `fix-test` skill |
| "predict bugs" | Auto-triggers `bug-predict` skill |
| "generate docs" | Auto-triggers `doc-gen` skill |
| "plan this feature" | Auto-triggers `planning` skill |
| "refactor this module" | Auto-triggers `refactor-plan` skill |
| "prepare a release" | Auto-triggers `release-prep` skill |
| "run all workflows" | Auto-triggers `workflow-orchestration` skill |

Skills run using your **Claude subscription** — no API
key needed.

### What the Output Looks Like

```text
$ attune workflow run security-audit --path src/

Looking solid — this is in great shape.

## Findings
Score: 95/100
3 issues found (1 medium, 2 low)

  Cost & Time
  $0.03 (saved 58% vs premium) | 12.4s

  What I'd Do Next
  I'd run `attune workflow run bug-predict` next —
  your spec has work remaining.
```

Every workflow speaks in the same voice, with contextual
next-step suggestions based on what just happened and
what your spec says should come next.

---

## Key Features

| | |
| --- | --- |
| **18 Multi-Agent Workflows** | Code review, security audit, test gen, release prep — each runs a specialist team of 2-6 Claude subagents |
| **31 MCP Tools** | Every workflow exposed as a native Claude Code tool via Model Context Protocol |
| **13 Auto-Triggering Skills** | Say "review my code" and Claude picks the right skill — fully skills-centric, zero commands |
| **Skills-First Plugin** | Install via `claude plugin install attune-ai@attune-ai` — skills auto-trigger from natural language |
| **Portable Security Hooks** | PreToolUse guard blocks eval/exec and path traversal; PostToolUse auto-formats Python |
| **Intelligent Cost Routing** | Opus for security, Sonnet for analysis, Haiku for scanning — right model per task |
| **Socratic Discovery** | Workflows ask questions before executing, not the other way around |
| **Budget Controls** | $0.50 quick / $2.00 standard / $5.00 deep — configurable per workflow |

---

## What's New

### v5.3 — Skills-Centric Architecture

**v5.3.2** migrates the plugin to a skills-first
architecture per Anthropic's official guidance. Skills
auto-trigger from natural language — no slash commands
needed. Installs directly from GitHub as a Claude Code
marketplace. attune-lite deprecated and merged.

| Feature | What It Does |
| ------- | ------------ |
| **Skills-first plugin** | 14 commands → 0 commands + 13 auto-triggering skills |
| **Marketplace install** | `claude plugin install attune-ai@attune-ai` — no pip required for the plugin |
| **`bug-predict` skill** | New skill migrated from command with scoping questions |
| **attune-lite deprecated** | All skills merged into attune-ai; repo archived |
| **Compliant frontmatter** | All descriptions under 250 chars; only official fields used |
| **`spec` skill** | Brainstorm → plan → review → execute lifecycle with approval gates |
| **CrewAI removal** | Deleted ~18K lines of deprecated code — all workflows SDK-native |
| **API reference rewrite** | Updated from v3.8.0 to v5.3.2, covering all 16 modules |

<details>
<summary>v5.2 — Voice Layer & Short Commands</summary>

### v5.2 — Voice Layer & Short Commands

**v5.2.0** adds a unified voice layer for consistent
output personality and contextual next-step suggestions.
**v5.2.1** adds short command wrappers so every skill
is accessible without namespacing.

| Feature | What It Does |
| ------- | ------------ |
| **Unified voice layer** | Friendly senior engineer personality across all output — greetings, score commentary, voiced next steps |
| **Spec-aware suggestions** | When `.claude/plans/` has an active spec, next steps follow the lifecycle |
| **11 auto-triggering skills** | Say "review my code" and Claude picks the right skill — no slash commands needed |
| **5 path traversal fixes** | `_validate_file_path()` added to pattern persistence and agent parser I/O |

<details>
<summary>v5.1.0 — v5.1.6 patch notes</summary>

**v5.1.6** — Custom cache removed (~8K lines, ~420MB
deps). Anthropic SDK alignment: batch tool, vision tool,
extended thinking, model ID fix.

**v5.1.5** — Security hardening (7 fixes), ghost command
cleanup (30+ stale refs), workflow discovery diagnostics.

**v5.1.4** — SessionStart welcome hook for first-run
discovery, path validation on read paths, TOCTOU fix.

**v5.1.3** — Architecture analyzer, `deep_review` MCP
tool (#31), 145+ new tests, commands-to-skills migration,
7 security findings resolved.

**v5.1.2** — 3 security fixes (CWE-22 path traversal
in MCP handlers and wizard YAML, CWE-918 SSRF in
webhook executor), 73 new tests.

**v5.1.1** — 3 new skills from attune-lite (`doc-gen`,
`smart-test`, `fix-test`), bringing the plugin to 10
skills total.

**v5.1.0** — Full Plugin SDK compliance. Every workflow
reachable as a native MCP tool, every tool wired through
an auto-invoking skill, security hooks ship with the
plugin for zero-config protection.

</details>

</details>

<details>
<summary>v5.0 — Anthropic Best Practices</summary>

### v5.0 — Anthropic Best Practices

**v5.0.0** aligned all 15 SDK-native workflows with
Anthropic's recommended patterns for the Claude Agent
SDK. This is the foundation everything else builds on.

| Feature | What It Does |
| ------- | ------------ |
| **System prompt separation** | Each workflow splits persona from task instructions, passed via `system_prompt=` on `ClaudeAgentOptions` |
| **Per-agent model routing** | Security/architect to Opus, quality/planning to Sonnet, lint/coverage to Haiku. Override with env vars |
| **Budget safety nets** | $0.50 quick / $2.00 standard / $5.00 deep — configurable per workflow, override with `ATTUNE_MAX_BUDGET_USD` |
| **Cost and usage tracking** | `AgentRunResult` captures actual cost, token counts, duration, and session ID from every run |
| **Structured output** | JSON schema output for code-review and security-audit with confidence scores and findings |
| **26 new SDK tests** | Budget caps, model routing, cost extraction, structured output adapter |

<details>
<summary>v5.0.1 — v5.0.2 patch notes</summary>

**v5.0.2** — Fixed all 15 Agent SDK workflows. Added
`collect_agent_output()` to collect from both
`ResultMessage` and `AssistantMessage` content blocks.

**v5.0.1** — Security hardening: memory ownership
checks, workspace isolation, MCP rate limiter (60/min),
hook import guard (`attune.*` only), path validation
on state manager.

</details>

</details>

---

## How to Access Workflows

There are three ways to run workflows, depending on
your context:

| How | When to Use | Example |
| --- | ----------- | ------- |
| **Natural language** | In Claude Code (recommended) | "scan this for security issues" |
| **`attune-hub` skill** | When you're not sure which workflow | "what can attune do?" |
| **CLI** | Terminal, CI/CD, automation | `attune workflow run security-audit --path src/` |

Skills use your **Claude subscription**. CLI mode
requires `ANTHROPIC_API_KEY`.

---

## Plugin & Skills

The attune-ai plugin provides 13 auto-triggering skills
and zero commands. Every capability is a skill — describe
what you need and Claude picks the right one.

### Install

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Update an existing install:

```bash
claude plugin update attune-ai
```

### Skills

| Skill | Triggers On |
| ----- | ----------- |
| `attune-hub` | "what can attune do", "help", "capabilities" |
| `spec` | "build from scratch", "brainstorm and execute", "spec" |
| `security-audit` | "security", "vulnerability", "scan" |
| `code-quality` | "review", "quality", "bugs", "code smell" |
| `bug-predict` | "predict bugs", "risky code", "what might break" |
| `doc-gen` | "generate docs", "documentation", "README" |
| `smart-test` | "test gaps", "generate tests", "coverage" |
| `fix-test` | "fix test", "broken test", "debug test" |
| `workflow-orchestration` | "workflow", "analyze", "run" |
| `planning` | "plan", "feature", "architecture", "TDD" |
| `refactor-plan` | "refactor", "tech debt", "simplify" |
| `release-prep` | "release", "publish", "deploy" |
| `memory-and-context` | "memory", "store", "retrieve" |

### Portable Hooks

The plugin ships two hooks that run automatically:

- **PreToolUse** — `security_guard.py` blocks `eval()`,
  `exec()`, path traversal, and `rm -rf /` in Bash
  commands; validates file paths in Edit/Write operations
- **PostToolUse** — `format_on_save.py` runs `black` and
  `ruff --fix` on every Python file after Write/Edit

---

## MCP Integration

31 tools organized into 6 categories:

### Analysis (6)

`security_audit` `code_review` `bug_predict`
`performance_audit` `refactor_plan` `simplify_code`

### Testing (3)

`test_generation` `test_audit` `test_gen_parallel`

### Documentation (3)

`doc_gen` `doc_audit` `doc_orchestrator`

### Release (4)

`release_prep` `health_check` `dependency_check`
`secure_release`

### Memory & Context (8)

`memory_store` `memory_retrieve` `memory_search`
`memory_forget` `context_get` `context_set`
`attune_get_level` `attune_set_level`

### Utility (7)

`auth_status` `auth_recommend` `telemetry_stats`
`research_synthesis` `deep_review` `analyze_batch`
`analyze_image`

### Resources (3)

`workflows` `auth_config` `telemetry`

All tools are accessible through Claude Code's natural
language interface. Describe what you need and Claude
invokes the appropriate tool.

---

## Workflows

Every workflow runs as a multi-agent team. Each agent is
a specialist — it reads your code with `Read`, `Glob`,
and `Grep` tools and reports findings to an orchestrator
that synthesizes a unified result.

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
| **doc-orchestrator** | inventory-scanner, outline-planner, content-writer, polish-reviewer | End-to-end documentation orchestration across an entire project | Full-project doc generation or refresh |
| **orchestrated-health-check** | dynamic team (2-6 based on mode) | Extended health check with dynamic agent team and severity scoring | Comprehensive project health assessment |
| **secure-release** | security-scanner, health-checker, dep-auditor, release-gater | Go/no-go release pipeline with combined risk scoring and blocker detection | Pre-publish security gate |
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
export ATTUNE_AGENT_MODEL_SECURITY=sonnet  # Save cost
export ATTUNE_AGENT_MODEL_DEFAULT=opus     # Max quality
```

### Budget Controls

Every workflow enforces a budget cap based on depth:

| Depth | Budget | Use Case |
| --- | --- | --- |
| `quick` | $0.50 | Fast checks, smoke tests |
| `standard` | $2.00 | Normal analysis (default) |
| `deep` | $5.00 | Thorough multi-pass review |

```bash
export ATTUNE_MAX_BUDGET_USD=10.0  # Override
export ATTUNE_MAX_BUDGET_USD=0     # Disable caps
```

---

## Quick Start

### Option A: Plugin Only (zero-config)

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Then in Claude Code, just say what you need:

- "review my code" — triggers code-quality skill
- "scan for security issues" — triggers security-audit
- "what can attune do?" — triggers attune-hub discovery
- "build this from a spec" — triggers spec-driven dev

### Option B: Plugin + Python Package (full power)

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
pip install 'attune-ai[developer]'
```

```bash
attune doctor    # Verify environment
attune auth      # Configure API key or subscription
```

### What Each Layer Adds

| Capability | Plugin only | Plugin + pip |
| ---------- | ----------- | ------------ |
| 13 auto-triggering skills | Yes | Yes |
| Security hooks | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| 31 MCP tools | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Cost tracking + routing | -- | Yes |
| CI/CD automation | -- | Yes |

The plugin works standalone — skills guide Claude through
analysis without any dependencies. Add the Python package
when you want MCP tool execution, CLI automation, or
multi-agent orchestration.

### CLI Usage

Run workflows directly from terminal:

```bash
attune workflow run code-review --path ./src
attune workflow run security-audit --path ./src
attune workflow run release-prep
attune telemetry show
```

---

## Why Attune?

| | Attune AI | Agent Frameworks | Coding CLIs | Review Bots |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 18 built-in | Build from scratch | None | PR review only |
| **Per-agent model routing** | Opus/Sonnet/Haiku per role | Manual | None | None |
| **Budget controls** | Depth-based caps | None | None | SaaS pricing |
| **Multi-agent teams** | 2-6 agents per workflow | Yes | No | No |
| **MCP integration** | 36 native tools | No | No | No |
| **Slash commands** | 11 short commands | No | No | No |
| **Portable security hooks** | PreToolUse + PostToolUse | No | No | No |
| **Structured output** | JSON schema with fallback | Manual | No | No |

---

## Cost Optimization

### Skills in Claude Code

All workflows run as skills using your Claude
subscription — no additional API costs:

```bash
/security          # Uses your Claude subscription
/smart-test        # Uses your Claude subscription
/release           # Uses your Claude subscription
```

### API Mode (CI/CD, Automation)

| Tier | Model | Use Case | Cost |
| --- | --- | --- | --- |
| CHEAP | Haiku | Formatting, simple tasks | ~$0.005 |
| CAPABLE | Sonnet | Bug fixes, code review | ~$0.08 |
| PREMIUM | Opus | Architecture, complex design | ~$0.45 |

---

## Installation Options

```bash
# Recommended (agents, memory)
pip install 'attune-ai[developer]'

# Minimal (CLI + workflows only)
pip install attune-ai

# All features
pip install 'attune-ai[all]'

# Development (contributing)
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

## Environment Setup

**In Claude Code:** No API key needed — workflows run as
skills using your Claude subscription. Just type `/attune`.

**For CLI usage** (`attune workflow run ...`):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # Required
export REDIS_URL="redis://localhost:6379"  # Optional
```

---

## Security

- Path traversal protection on all file operations
  (CWE-22)
- Memory ownership checks (`created_by` validation)
- MCP rate limiting (60 calls/min per tool)
- Hook import restriction (`attune.*` modules only)
- PreToolUse security guard (blocks eval/exec, path
  traversal)
- PII scrubbing in telemetry
- Automated security scanning (CodeQL, bandit,
  detect-secrets)

See [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) for vulnerability
reporting and full security details.

---

## Links

- [Full Documentation](https://smartaimemory.com/framework-docs/)
- [Plugin Setup](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/README.md)
- [GitHub Repository](https://github.com/Smart-AI-Memory/attune-ai)

**Apache License 2.0** — Free and open source.

**Built by [Smart AI Memory](https://smartaimemory.com)**

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
