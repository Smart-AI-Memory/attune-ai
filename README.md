# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Production-ready AI workflows for Claude Code, aligned
with Anthropic best practices.**

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-15%2C026%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

## Get Started in 60 Seconds

```bash
pip install 'attune-ai[developer]'
attune setup
```

Then type `/attune` in Claude Code. That's it.

---

## Cheat Sheet

Every command works in Claude Code. Just type it.

| Command | What It Does |
| ------- | ------------ |
| `/attune` | Guided discovery — asks what you need |
| `/security` | Scan for vulnerabilities |
| `/code-quality` | Code review + bug prediction |
| `/smart-test` | Find test gaps, generate tests |
| `/fix-test` | Auto-diagnose failing tests |
| `/doc-gen` | Generate documentation |
| `/refactor` | Refactoring analysis + roadmap |
| `/spec` | Spec-driven dev — brainstorm → plan → execute |
| `/plan` | Feature, TDD, or architecture planning |
| `/release` | Pre-release health + security check |
| `/workflows` | Run any analysis workflow by name |
| `/remember` | Store/retrieve persistent memory |

Each command runs as a skill using your **Claude
subscription** — no API key needed.

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
| **36 MCP Tools** | Every workflow exposed as a native Claude Code tool via Model Context Protocol |
| **13 Slash Commands** | Short commands (`/security`, `/spec`, `/doc-gen`) that work directly — no namespacing needed |
| **Unified Voice Layer** | Consistent personality across all output with contextual next-step suggestions |
| **Anthropic Best Practices** | System prompt separation, per-agent model routing, budget safety nets, structured output |
| **Portable Security Hooks** | PreToolUse guard blocks eval/exec and path traversal; PostToolUse auto-formats Python |
| **Intelligent Cost Routing** | Opus for security, Sonnet for analysis, Haiku for scanning — right model per task |
| **Socratic Discovery** | Workflows ask questions before executing, not the other way around |
| **Budget Controls** | $0.50 quick / $2.00 standard / $5.00 deep — configurable per workflow |

---

## What's New

### v5.3 — Spec-Driven Dev & Dead Code Removal

**v5.3.0** adds `/spec` for spec-driven development and
removes ~18,000 lines of deprecated CrewAI code.

| Feature | What It Does |
| ------- | ------------ |
| **`/spec` command** | Brainstorm → plan → review → execute lifecycle with approval gates and state tracking |
| **CrewAI removal** | Deleted entire `agent_factory/crews/` subsystem (~18K lines) — all workflows are SDK-native since v5.0 |
| **MCP dispatch rewrite** | Replaced 29-branch if/elif chain with O(1) dict lookup; extracted schemas to `tool_schemas.py` |
| **`/bug-predict` command** | New short command for bug prediction workflow |
| **Ruff F821 fixes** | Forward reference errors in watcher and success templates |

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
| **11 short commands** | `/security`, `/doc-gen`, `/fix-test`, etc. — no more `/attune-lite:skill-name` |
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
| **Slash command** | In Claude Code (recommended) | `/security src/auth/` |
| **`/attune` hub** | When you're not sure which workflow | `/attune "find bugs"` |
| **CLI** | Terminal, CI/CD, automation | `attune workflow run security-audit --path src/` |

Slash commands and `/attune` use your **Claude
subscription**. CLI mode requires `ANTHROPIC_API_KEY`.

---

## Plugin & Skills

The attune-ai plugin integrates with Claude Code via
13 slash commands and 10 auto-invoking skills. Skills
trigger automatically based on what you describe — no
need to memorize commands.

### Skills

| Skill | Triggers On | Command |
| ----- | ----------- | ------- |
| `security-audit` | "security", "vulnerability", "scan" | `/security` |
| `code-quality` | "review", "quality", "bugs" | `/code-quality` |
| `doc-gen` | "generate docs", "documentation" | `/doc-gen` |
| `smart-test` | "test gaps", "generate tests" | `/smart-test` |
| `fix-test` | "fix test", "broken test" | `/fix-test` |
| `workflow-orchestration` | "workflow", "analyze" | `/workflows` |
| `planning` | "plan", "feature", "architecture" | `/plan` |
| `refactor-plan` | "refactor", "tech debt" | `/refactor` |
| `release-prep` | "release", "publish" | `/release` |
| `memory-and-context` | "memory", "store" | `/remember` |

### Portable Hooks

The plugin ships two hooks that run automatically:

- **PreToolUse** — `security_guard.py` blocks `eval()`,
  `exec()`, path traversal, and `rm -rf /` in Bash
  commands; validates file paths in Edit/Write operations
- **PostToolUse** — `format_on_save.py` runs `black` and
  `ruff --fix` on every Python file after Write/Edit

---

## MCP Integration

36 tools organized into 6 categories:

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

### 1. Install

```bash
pip install 'attune-ai[developer]'
```

### 2. Setup

```bash
# Install slash commands to ~/.claude/commands/
attune setup

# Verify environment (Python, Redis, MCP server)
attune doctor

# Check available features and dependencies
attune features

# Configure authentication (API key or subscription)
attune auth
```

### 3. Use in Claude Code

Type `/attune` for Socratic discovery, or use shortcuts:

```bash
/attune                # Guided — asks what you need
/spec                  # Spec-driven development
/security              # Security audit
/code-quality          # Code review + bug prediction
/smart-test            # Generate tests for gaps
/fix-test              # Auto-fix failing tests
/doc-gen               # Generate documentation
/refactor              # Refactoring roadmap
/plan                  # Feature/architecture planning
/release               # Release preparation
/workflows             # Run any workflow by name
```

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
