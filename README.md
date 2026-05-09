# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Multi-agent developer workflows for Claude Code.**

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-16%2C900%2B%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-88%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

18 multi-agent workflows, 14 auto-triggering Claude Code skills, and
36 MCP tools — specialist teams of 2–6 Claude subagents that review
your code, surface vulnerabilities, generate tests, and plan refactors.
The same system doubles as the authoring and assistance toolkit for
building and maintaining knowledge bases at scale.

**Managing and creating help content and docs?**
That's [`attune-gui`](https://github.com/Smart-AI-Memory/attune-gui)
— a dedicated Living Docs dashboard wrapping `attune-rag`,
`attune-help`, and `attune-author` in a single UI. `attune-ai` is the
developer workflow hub; `attune-gui` is the docs hub.

---

## Ecosystem

| Package | Role | Install |
| ------- | ---- | ------- |
| **`attune-ai`** | Developer workflow hub (this package) | `pip install attune-ai` |
| **`attune-gui`** | Living Docs dashboard — create, manage, search help content | standalone app |
| **`attune-rag`** | RAG pipeline (core dep of attune-ai, v0.1.11+) | bundled |
| **`attune-author`** | Help content authoring, staleness detection | `pip install 'attune-ai[author]'` |
| **`attune-help`** | Progressive-depth template runtime | `pip install attune-help` |

`attune-rag` ships as a **core dependency** of `attune-ai`
(v0.1.11, `>=0.1.5,<0.2`). `attune-help` is standalone — not pulled
in by a standard `attune-ai` install, but available as an optional
corpus for `attune-rag` via `pip install 'attune-rag[attune-help]'`.

---

## How It Works

### 1. Skills trigger automatically

Say what you need in Claude Code and the right skill activates:

```text
"review my code"        → code-quality skill
"scan for vulns"        → security-audit skill
"generate tests"        → smart-test skill
"plan this feature"     → planning skill
```

No command to remember. Claude reads your intent and picks the skill.
Each skill runs a specialist multi-agent team, not a single prompt.

### 2. Multi-agent teams, not single prompts

Every workflow dispatches 2–6 subagents in parallel. Each reads your
code with `Read`, `Glob`, and `Grep`. An orchestrator synthesizes
their findings into a unified result:

```text
security-audit → vuln-scanner + secret-detector + auth-reviewer + remediation-planner
code-review    → security + quality + perf + architect
test-gen       → identifier + designer + writer
```

Subagents are assigned models by task complexity — Opus for deep
reasoning, Sonnet for analysis, Haiku for fast scanning — keeping
cost proportional to value.

### 3. Socratic before execution

Workflows ask questions before executing, not after. The `spec`
workflow brainstorms, then plans, then executes. `planning` clarifies
scope before writing a line of code. This eliminates the most common
failure mode: confidently solving the wrong problem.

### 4. RAG-grounded generation

`attune-rag` (core dep) grounds LLM generation in retrieved corpus
passages and enforces citation-per-claim, cutting hallucination from
46.7% → 6.7% on the benchmark set. Retrieved passages are wrapped in
sentinel tags to prevent prompt injection. The Claude provider
automatically caches the stable RAG context prefix, eliminating
repeated token costs across calls.

---

## Get Started in 60 Seconds

### Plugin (works standalone)

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Then say "what can attune do?" in Claude Code.

### Add Python Package (unlocks CLI + MCP)

```bash
pip install 'attune-ai[developer]'
```

### What Each Layer Adds

| Capability | Plugin only | Plugin + pip |
| ---------- | ----------- | ------------ |
| 14 auto-triggering skills | Yes | Yes |
| Security hooks | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| 36 MCP tools | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Help system maintenance | -- | Yes |
| CI/CD automation | -- | Yes |

> **Note:** Skills use your Claude subscription at no extra cost.
> CLI and MCP tools make direct Anthropic API calls — API key
> required. See [API Mode](#api-mode).

---

## Cheat Sheet

| Input | What Happens |
| ----- | ------------ |
| "what can attune do?" | Auto-triggers `attune-hub` — guided discovery |
| "build this feature from scratch" | Auto-triggers `spec` — brainstorm, plan, execute |
| "review my code" | Auto-triggers `code-quality` skill |
| "scan for vulnerabilities" | Auto-triggers `security-audit` skill |
| "generate tests for src/" | Auto-triggers `smart-test` skill |
| "fix failing tests" | Auto-triggers `fix-test` skill |
| "predict bugs" | Auto-triggers `bug-predict` skill |
| "generate docs" | Auto-triggers `doc-gen` skill |
| "plan this feature" | Auto-triggers `planning` skill |
| "refactor this module" | Auto-triggers `refactor-plan` skill |
| "prepare a release" | Auto-triggers `release-prep` skill |
| "tell me more" | Auto-triggers `coach` — progressive depth help |
| "run all workflows" | Auto-triggers `workflow-orchestration` skill |

---

## Workflows

| Workflow | Agents | What It Does |
| --- | --- | --- |
| **code-review** | security, quality, perf, architect | 4-perspective code review |
| **security-audit** | vuln-scanner, secret-detector, auth-reviewer, remediation | Finds vulnerabilities and generates fix plans |
| **deep-review** | security, quality, test-gap | Multi-pass deep analysis |
| **perf-audit** | complexity, bottleneck, optimization | Identifies bottlenecks and O(n²) patterns |
| **bug-predict** | pattern-scanner, risk-correlator, prevention | Predicts likely failure points |
| **health-check** | dynamic team (2–6) | Project health across tests, deps, lint, CI, docs, security |
| **test-gen** | identifier, designer, writer | Writes pytest code for untested functions |
| **test-audit** | coverage, gap-analyzer, planner | Audits coverage and prioritizes gaps |
| **doc-gen** | outline, content, polish | Generates documentation from source |
| **doc-audit** | staleness, accuracy, gap-finder | Finds stale docs and drift |
| **dependency-check** | inventory, update-advisor | Audits outdated packages and advisories |
| **refactor-plan** | debt-scanner, impact, plan-generator | Plans large-scale refactors |
| **simplify-code** | complexity, simplification, safety | Proposes simplifications with safety review |
| **release-prep** | health, security, changelog, assessor | Go/no-go readiness check |
| **doc-orchestrator** | inventory, outline, content, polish | Full-project documentation |
| **secure-release** | security, health, dep-auditor, gater | Release pipeline with risk scoring |
| **research-synthesis** | summarizer, pattern-analyst, writer | Multi-source research synthesis |

---

## MCP Tools

36 tools organized into 4 categories:

### Workflow (20)

`security_audit` `code_review` `bug_predict`
`performance_audit` `refactor_plan` `simplify_code`
`deep_review` `test_generation` `test_audit`
`test_gen_parallel` `doc_gen` `doc_audit`
`doc_orchestrator` `release_prep` `health_check`
`dependency_check` `secure_release` `research_synthesis`
`analyze_batch` `analyze_image`

### Help (5)

`help_lookup` `help_init` `help_status` `help_update`
`help_maintain`

### Memory (4)

`memory_store` `memory_retrieve` `memory_search`
`memory_forget`

### Utility (7)

`auth_status` `auth_recommend` `telemetry_stats`
`context_get` `context_set` `attune_get_level`
`attune_set_level`

---

## Accuracy & Faithfulness

### RAG grounding — hallucination down 46.7% → 6.7%

Measured on a 15-query golden set with retrieval held constant:

| Prompt variant | Hallucination rate | Mean faithfulness |
|---|---|---|
| baseline (no grounding rule) | 46.67% | 0.938 |
| strict ("answer only from context") | 26.67% | 0.968 |
| **citation (shipped default)** | **6.67%** | **0.996** |

The gain comes from the prompting contract (citation-per-claim), not
from retrieval. Full methodology:

- [`docs/rag/faithfulness-decision-2026-04-19.md`](docs/rag/faithfulness-decision-2026-04-19.md)
- [`docs/rag/ab-report-2026-04-19.json`](docs/rag/ab-report-2026-04-19.json)

### Help resolver — 48/48 benchmark queries pass at P@1

| Bucket | Count | P@1 | Notes |
|---|---|---|---|
| easy | 22 | 22/22 (100%) | feature-name synonyms |
| medium | 26 | 26/26 (100%) | paraphrases + industry terminology |
| hard | 4 | 0/4 (XFAIL) | shared-tag collisions — structural ambiguity |

- [`tests/unit/help/fixtures/golden_queries.yaml`](tests/unit/help/fixtures/golden_queries.yaml)

---

## Why Attune?

| | Attune AI | Static Docs | Agent Frameworks | Coding CLIs |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 18 built-in | None | Build from scratch | None |
| **Multi-agent teams** | 2–6 agents per workflow | None | Yes | No |
| **MCP integration** | 36 native tools | None | No | No |
| **Auto-triggering skills** | 14 skills, natural language | None | None | None |
| **Socratic discovery** | Questions before execution | None | None | None |
| **Portable security hooks** | PreToolUse + PostToolUse | None | No | No |

---

## Installation Options

```bash
# Recommended (agents, memory, RAG)
pip install 'attune-ai[developer]'

# Minimal (CLI + workflows + RAG)
pip install attune-ai

# With help authoring (generate / maintain .help/ templates)
pip install 'attune-ai[author]'

# All features
pip install 'attune-ai[all]'

# Development (contributing)
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

The `[rag]` extra is a **no-op alias** kept for backward
compatibility — `attune-rag` is now a core dependency included in
every install.

---

## API Mode

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # Required
export REDIS_URL="redis://localhost:6379"  # Optional
```

### Model Routing

| Model | Agents | Rationale |
| --- | --- | --- |
| **Opus** | security, vuln, architect | Deep reasoning |
| **Sonnet** | quality, plan, research | Balanced analysis |
| **Haiku** | complexity, lint, coverage | Fast scanning |

```bash
export ATTUNE_AGENT_MODEL_SECURITY=sonnet  # Save cost
export ATTUNE_AGENT_MODEL_DEFAULT=opus     # Max quality
```

### Budget Controls

| Depth | Budget | Use Case |
| --- | --- | --- |
| `quick` | $0.50 | Fast checks |
| `standard` | $2.00 | Normal analysis (default) |
| `deep` | $5.00 | Thorough multi-pass review |

```bash
export ATTUNE_MAX_BUDGET_USD=10.0  # Override
```

---

## Security

- Path traversal protection on all file operations (CWE-22)
- Memory ownership checks (`created_by` validation)
- MCP rate limiting (60 calls/min per tool)
- Hook import restriction (`attune.*` modules only)
- PreToolUse security guard (blocks eval/exec, path traversal)
- Prompt input sanitization (backticks, control chars, truncation)
- PII scrubbing in telemetry
- Automated security scanning (CodeQL, bandit, detect-secrets)

See [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) for vulnerability
reporting and full security details.

---

## Session continuity

Three lightweight surfaces keep long Claude Code sessions
oriented and recoverable. All are opt-in via plugin install
and silent until they have something to say.

| Surface | Event | When it fires |
|---------|-------|---------------|
| `spec_orient.py` | `SessionStart` | On `startup` / `resume` / `clear`, prints up to 3 in-flight spec slugs. On `compact`, prints the most-recent spec body so the model keeps the spec in fresh post-compact context. |
| `compact_warning.py` | `Stop` | Once per session when transcript size crosses ~70% of the context window. Emits a copy-pasteable resume prompt and recommends starting a fresh session. |
| `/handoff` | slash command | On demand. Prints the same resume prompt as the auto-warning AND appends it to `~/.attune/last-handoff.md` so you can recover it later. |

### Tunable defaults

- `ATTUNE_AI_COMPACT_WARNING_THRESHOLD` (default `0.70`) — fraction of context window before the warning fires.
- `ATTUNE_AI_CHARS_PER_TOKEN` (default `4.0`) — utilization estimator's chars-to-tokens factor.
- `ATTUNE_AI_CONTEXT_WINDOW_TOKENS` (default `200000`) — context window assumed by the estimator.
- `ATTUNE_AI_WORKSPACE_ROOTS` (colon-separated paths) — override the workspace roots scanned for `specs/`.
- `ATTUNE_AI_SENTINEL_DIR` (default `~/.attune`) — directory for the once-per-session warning sentinel.

The transcript-size proxy is crude but monotonic: the warning
fires when the user's total content characters cross the
threshold once. If your real auto-compact triggers consistently
earlier or later than the warning, drop the threshold to `0.65`
or raise it to `0.75`.

---

## Migration

`attune-help` and `attune-author` have moved to their own
marketplace at
[Smart-AI-Memory/attune-docs](https://github.com/Smart-AI-Memory/attune-docs).
If you previously installed either from the `attune-ai` marketplace:

1. ```text
   /plugin marketplace add Smart-AI-Memory/attune-docs
   ```

2. ```text
   /plugin uninstall attune-help@attune-ai
   /plugin uninstall attune-author@attune-ai
   ```

3. ```text
   /plugin install attune-help@attune-docs
   /plugin install attune-author@attune-docs
   ```

New users: add `Smart-AI-Memory/attune-docs` directly.

---

## Links

- [Full Documentation](https://smartaimemory.com/framework-docs/)
- [Plugin Setup](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/README.md)
- [attune-gui](https://github.com/Smart-AI-Memory/attune-gui) — Living Docs dashboard
- [GitHub Repository](https://github.com/Smart-AI-Memory/attune-ai)

**Apache License 2.0** — Free and open source.

If you find Attune useful,
[give it a star](https://github.com/Smart-AI-Memory/attune-ai) —
it helps others discover the project.

## Acknowledgments

- **[Anthropic](https://www.anthropic.com/)** — For Claude AI, the
  Model Context Protocol, and the Agent SDK patterns behind the
  multi-agent orchestration layer
- **[Boris Cherny](https://x.com/bcherny)** — Creator of Claude Code,
  whose workflow posts validated Attune's plan-first, multi-agent approach
- **[Affaan Mustafa](https://github.com/affaan-m/everything-claude-code)** — For battle-tested Claude Code configurations that inspired the hook system

[View Full Acknowledgements](https://github.com/Smart-AI-Memory/attune-ai/blob/main/ACKNOWLEDGMENTS.md)

---

**Built by Patrick Roebuck using Claude Code.**

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
