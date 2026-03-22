# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Production-ready AI workflows for Claude Code, aligned
with Anthropic best practices.**

18 multi-agent workflows for code review, security,
testing, and release — each backed by specialized Claude
subagents with intelligent model routing, budget controls,
and structured output. 31 MCP tools. 10 auto-invoking
skills. Just type `/attune` and go.

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-15%2C591%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

**1.** Install:

```bash
pip install 'attune-ai[developer]'
```

**2.** [Complete Quick Start →](#quick-start)

---

## Key Features

| | |
| --- | --- |
| **18 Multi-Agent Workflows** | Code review, security audit, test gen, release prep — each runs a specialist team of 2-6 Claude subagents |
| **31 MCP Tools** | Every workflow exposed as a native Claude Code tool via Model Context Protocol |
| **10 Auto-Invoking Skills** | Describe what you need and Claude triggers the right skill automatically |
| **Anthropic Best Practices** | System prompt separation, per-agent model routing, budget safety nets, structured output |
| **Portable Security Hooks** | PreToolUse guard blocks eval/exec and path traversal; PostToolUse auto-formats Python |
| **Intelligent Cost Routing** | Opus for security, Sonnet for analysis, Haiku for scanning — right model per task |
| **Socratic Discovery** | Workflows ask questions before executing, not the other way around |
| **Budget Controls** | $0.50 quick / $2.00 standard / $5.00 deep — configurable per workflow |

---

## What's New

### v5.2 — Voice Layer & Security Hardening

**v5.2.0** adds a unified voice layer for consistent
output personality and closes 5 path traversal gaps
found via bug-predict audit.

| Feature | What It Does |
| ------- | ------------ |
| **Unified voice layer** | Consistent output personality across all workflow results via `VoiceFormatter` |
| **5 path traversal fixes** | `_validate_file_path()` added to pattern persistence and agent parser I/O |
| **Integration tests** | End-to-end voice layer wiring tests for MCP and workflow printer |

<details>
<summary>v5.1.0 — v5.1.4 patch notes</summary>

**v5.1.4** — SessionStart welcome hook for first-run
discovery, path validation on read paths, TOCTOU fix.

**v5.1.3** — Architecture analyzer, `deep_review` MCP
tool (#31), 145+ new tests, commands→skills migration,
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

### v5.0 — Anthropic Best Practices

**v5.0.0** aligned all 15 SDK-native workflows with
Anthropic's recommended patterns for the Claude Agent
SDK. This is the foundation everything else builds on.

| Feature | What It Does |
| ------- | ------------ |
| **System prompt separation** | Each workflow splits persona from task instructions, passed via `system_prompt=` on `ClaudeAgentOptions` |
| **Per-agent model routing** | Security/architect → Opus, quality/planning → Sonnet, lint/coverage → Haiku. Override with env vars |
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

---

## Plugin & Skills

The attune-ai plugin integrates with Claude Code via
the `/attune` command and 10 auto-invoking skills. Skills
trigger automatically based on what you describe — no
need to memorize commands.

### Skills

| Skill | Triggers On | Manual Only? |
| ----- | ----------- | ------------ |
| `security-audit` | "security", "vulnerability", "scan" | No |
| `code-quality` | "review", "quality", "bugs" | No |
| `doc-gen` | "generate docs", "documentation", "docstrings" | No |
| `smart-test` | "test gaps", "generate tests", "coverage" | No |
| `fix-test` | "fix test", "broken test", "test failure" | Yes |
| `workflow-orchestration` | "workflow", "analyze", "test" | No |
| `planning` | "plan", "feature", "architecture" | No |
| `refactor-plan` | "refactor", "tech debt", "simplify" | No |
| `release-prep` | "release", "publish", "deploy" | Yes |
| `memory-and-context` | "memory", "store", "empathy" | Yes |

Skills marked "Manual Only" have
`disable-model-invocation: true` — they write data or
orchestrate agents, so they require explicit invocation
(`/attune release` or `/attune-ai:release-prep`).

### Portable Hooks

The plugin ships two hooks that run automatically:

- **PreToolUse** — `security_guard.py` blocks `eval()`,
  `exec()`, path traversal, and `rm -rf /` in Bash
  commands; validates file paths in Edit/Write operations
- **PostToolUse** — `format_on_save.py` runs `black` and
  `ruff --fix` on every Python file after Write/Edit

---

## MCP Integration

30 tools organized into 5 categories:

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

### Utility (6)

`auth_status` `auth_recommend` `telemetry_stats`
`research_synthesis` + 2 MCP resources

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
/attune security       # Security audit
/attune review         # Code review
/attune tests          # Generate tests
/attune perf           # Performance analysis
/attune release        # Release preparation
/attune health         # Project health check
/attune docs           # Generate documentation
/attune simplify       # Reduce code complexity
```

### CLI Usage

Run workflows directly from terminal:

```bash
attune workflow run code-review --path ./src
attune workflow run security-audit --path ./src
attune workflow run release-prep
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

| | Attune AI | Agent Frameworks | Coding CLIs | Review Bots |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 18 built-in | Build from scratch | None | PR review only |
| **Per-agent model routing** | Opus/Sonnet/Haiku per role | Manual | None | None |
| **Budget controls** | Depth-based caps | None | None | SaaS pricing |
| **Multi-agent teams** | 2-6 agents per workflow | Yes | No | No |
| **MCP integration** | 30 native tools | No | No | No |
| **Auto-invoking skills** | 10 with trigger descriptions | No | No | No |
| **Portable security hooks** | PreToolUse + PostToolUse | No | No | No |
| **Structured output** | JSON schema with fallback | Manual | No | No |

---

## Command Hubs

| Hub | Command | Description |
| --- | --- | --- |
| **Developer** | `/dev` | Debug, commit, PR, code review, quality |
| **Testing** | `/testing` | Run tests, smart test, coverage, test gen |
| **Documentation** | `/docs` | Generate docs, changelog, doc audit |
| **Release** | `/release` | Release prep, security scan, publishing |
| **Workflows** | `/workflows` | Automated analysis (security, bugs, perf) |
| **Plan** | `/plan` | Feature planning, brainstorm, refactoring |
| **Agent** | `/agent` | Create and manage custom agents |

---

## Cost Optimization

### Skills in Claude Code

Most workflows run as skills using your Claude
subscription — no additional API costs:

```bash
/dev           # Uses your Claude subscription
/testing       # Uses your Claude subscription
/release       # Uses your Claude subscription
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

See [SECURITY.md](SECURITY.md) for vulnerability
reporting and full security details.

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Coding Standards](docs/CODING_STANDARDS.md)
- [Plugin README](plugin/README.md)
- [Full Documentation](https://smartaimemory.com/framework-docs/)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

**Apache License 2.0** — Free and open source. Use it,
modify it, build commercial products with it.
[Details](LICENSE)

---

## Acknowledgements

Special thanks to:

- **[Anthropic](https://www.anthropic.com/)** — For
  Claude AI, MCP, and the Agent SDK patterns that
  shaped v5.0
- **[Boris Cherny](https://x.com/bcherny)** — Creator
  of Claude Code, whose workflow posts validated
  Attune's approach
- **[Affaan Mustafa](https://github.com/affaan-m/everything-claude-code)** — For battle-tested Claude Code configurations

[View Full Acknowledgements](ACKNOWLEDGMENTS.md)

---

**Built by [Smart AI Memory](https://smartaimemory.com)** ·
[Docs](https://smartaimemory.com/framework-docs/) ·
[Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
