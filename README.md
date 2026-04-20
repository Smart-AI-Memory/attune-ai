# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**The 21st century help system for developer tools.**

[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-15%2C359%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-88%25-green)](https://github.com/Smart-AI-Memory/attune-ai)
[![CodeQL](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/codeql.yml)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

**Ecosystem overview.** `attune-ai` is the hub: CLI,
multi-agent workflows, MCP tools, and Claude Code skills.
It depends on **`attune-help`** (progressive-depth
template runtime; core PyPI dep), and optionally pulls in
**`attune-rag`** via the `[rag]` extra (retrieval +
citation-forced generation — source of the faithfulness
numbers in [Accuracy & Faithfulness](#accuracy--faithfulness))
and **`attune-author`** via the `[author]` extra (authoring
& staleness detection, used by the weekly freshness
automation). Separate repos, separate release cadences,
separate PyPI packages.

> The Claude Code plugin marketplace for help content
> moved to
> [`Smart-AI-Memory/attune-docs`](https://github.com/Smart-AI-Memory/attune-docs)
> in early 2026. If you installed `attune-help` or
> `attune-author` from this marketplace previously, see
> [Migration](#migration).

---

Static docs rot. READMEs go stale the moment you merge.
Help pages don't know if you're a beginner or an expert.
Nobody maintains them — and it shows.

Attune AI is a different approach. Documentation is
**authored once as templates**, **rendered at runtime**
with audience awareness, **maintained automatically** by
AI agents, and **learned from** based on how people
actually use it. The result is a living knowledge base
that stays accurate, adapts to who's reading, and
improves over time — without anyone manually updating
markdown files.

The same system powers 18 multi-agent workflows, 14
auto-triggering skills, and 36 MCP tools — all of which
double as the authoring and assistance toolkit for
building and maintaining knowledge bases at scale.

---

## How It Works

### 1. Authored as Templates

633 templates across 11 types — errors, warnings, tips,
references, tasks, FAQs, notes, quickstarts, concepts,
troubleshooting, and comparisons. Each template has
structured frontmatter (tags, related links, audience
hints) and a markdown body. Templates are the source of
truth; rendered output is ephemeral.

### 2. Rendered at Runtime

Help adapts to the reader. **Progressive depth**
escalates across template types as you ask again:

```text
First ask   → concept   (what is this?)
Second ask  → task      (how do I use it?)
Third ask   → reference (show me the details)
```

**Audience adaptation** adjusts verbosity and framing
for Claude Code users, CLI users, and marketplace
readers — from the same source template.

**Precursor warnings** surface relevant errors and
warnings *before* you hit them, based on the file
you're editing.

### 3. Maintained by AI

A 5-phase maintenance workflow detects stale templates,
prioritizes by usage feedback, regenerates via batch API,
rebuilds cross-links, and validates the result — all
without manual intervention.

```text
detect → map → regenerate → rebuild → validate
```

Templates that help people more get maintained first.
Templates nobody reads get deprioritized. The knowledge
base optimizes itself.

### 4. Learned from Usage

Every template lookup is tracked. Feedback ratings
adjust template confidence scores. Usage telemetry
weights priorities so the maintenance workflow focuses
on what matters. The help system gets better the more
you use it.

---

## The Toolkit

The help system doesn't just *contain* knowledge — it
comes with tools to build, maintain, and deliver it.
These same tools power attune-ai's own 633 templates,
proving the approach works at scale.

| | |
| --- | --- |
| **18 Multi-Agent Workflows** | Code review, security audit, test gen, release prep — specialist teams of 2-6 Claude subagents that also serve as knowledge-authoring pipelines |
| **36 MCP Tools** | Every workflow exposed as a native Claude Code tool via Model Context Protocol, including `help_lookup` (4 modes) and `help_maintain` (auto-regeneration) |
| **14 Auto-Triggering Skills** | Say "review my code" and Claude picks the right skill — each skill integrates contextual help from the template engine |
| **Portable Security Hooks** | PreToolUse guard blocks eval/exec and path traversal; PostToolUse auto-formats Python |
| **Socratic Discovery** | Workflows ask questions before executing, not the other way around |

---

## Accuracy & Faithfulness

Two separate accuracy axes ship with attune-ai, each
benchmarked against an in-repo golden-query set. The
fixtures and raw A/B reports are committed so results
are reproducible and open to external review.

### RAG grounding — hallucination down 46.7% → 6.7%

When the `rag-code-gen` workflow (via the `attune-rag`
dependency) answers a question grounded in retrieved
code, its prompt enforces citation-per-claim against
numbered passages. Measured on a 15-query golden set
with retrieval held constant:

| Prompt variant | Hallucination rate | Mean faithfulness |
|---|---|---|
| baseline (no grounding rule) | 46.67% | 0.938 |
| strict ("answer only from context") | 26.67% | 0.968 |
| **citation (shipped default)** | **6.67%** | **0.996** |

Retrieval quality (P@1 = 73.3%) was identical across
variants — the gain comes from the prompting contract,
not from moving the retrieval needle. Full methodology
and raw JSON:

- [`docs/rag/faithfulness-decision-2026-04-19.md`](docs/rag/faithfulness-decision-2026-04-19.md)
  — decision writeup with pre-committed gate
- [`docs/rag/ab-report-2026-04-19.json`](docs/rag/ab-report-2026-04-19.json)
  — machine-readable results (all four variants,
  per-query judgments)
- Faithfulness judge: `FaithfulnessJudge` in attune-rag,
  LLM-as-judge via Anthropic forced tool-use for
  guaranteed-schema JSON output; decomposes each answer
  into atomic claims and marks each
  supported/unsupported against the retrieved passages.

attune-rag ≥ 0.1.5 (the pin in `[rag]`) additionally
wraps retrieved passages in
`<passage id="P1">...</passage>` sentinel tags with a
system-prompt injection-defense clause — adversarial
bytes inside a corpus document are treated as data, not
instructions.

### Help resolver — 48/48 benchmark queries pass at P@1

The help-system resolver (`resolve_topic()` in
`attune-help`) is benchmarked against 52 hand-crafted
queries across three difficulty buckets:

| Bucket | Count | P@1 | Notes |
|---|---|---|---|
| easy | 22 | 22/22 (100%) | feature-name synonyms |
| medium | 26 | 26/26 (100%) | paraphrases + industry terminology |
| hard | 4 | 0/4 (XFAIL by design) | shared-tag collisions — structural ambiguity, not a resolver gap |

The 4 hard queries (e.g. `"review"` matches both
`code-quality` and `deep-review`) document a known
semantic ceiling — resolution requires a contract change
(return a list of candidates for user disambiguation),
not more tags. They run as `pytest.xfail` so future
retriever changes that unexpectedly pass show up as
XPASS regressions. Fixtures and test:

- [`tests/unit/help/fixtures/golden_queries.yaml`](tests/unit/help/fixtures/golden_queries.yaml)
- Re-run with `pytest tests/unit/help/test_golden_queries.py`

---

## Get Started in 60 Seconds

### Plugin (works standalone)

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Then say "what can attune do?" in Claude Code. That's it.

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

The plugin works standalone — skills guide Claude
through analysis using your existing subscription,
with no additional costs. Add the Python package
when you want MCP tool execution, CLI automation,
help system maintenance, or multi-agent orchestration.

> **Note:** The Python package's CLI and MCP tools
> use the Anthropic API directly, which requires an
> API key and incurs usage-based charges. See
> [API Mode](#api-mode) for details.

---

## Cheat Sheet

All 14 skills trigger automatically from natural
language — just describe what you need:

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

Skills run using your **Claude subscription** — no API
key needed, no additional charges.

---

## Why Attune?

| | Attune AI | Static Docs | Agent Frameworks | Coding CLIs |
| --- | --- | --- | --- | --- |
| **Self-maintaining docs** | AI-maintained, usage-weighted | Manual, rots immediately | None | None |
| **Progressive depth** | concept → task → reference | One-size-fits-all | None | None |
| **Audience adaptation** | Adapts per reader | Write multiple versions | None | None |
| **Ready-to-use workflows** | 18 built-in | None | Build from scratch | None |
| **Multi-agent teams** | 2-6 agents per workflow | None | Yes | No |
| **MCP integration** | 36 native tools | None | No | No |
| **Portable security hooks** | PreToolUse + PostToolUse | None | No | No |

---

## Workflows

Every workflow runs as a multi-agent team. Each agent
reads your code with `Read`, `Glob`, and `Grep` tools
and reports findings to an orchestrator that synthesizes
a unified result.

| Workflow | Agents | What It Does |
| --- | --- | --- |
| **code-review** | security, quality, perf, architect | 4-perspective code review |
| **security-audit** | vuln-scanner, secret-detector, auth-reviewer, remediation | Finds vulnerabilities and generates fix plans |
| **deep-review** | security, quality, test-gap | Multi-pass deep analysis |
| **perf-audit** | complexity, bottleneck, optimization | Identifies bottlenecks and O(n^2) patterns |
| **bug-predict** | pattern-scanner, risk-correlator, prevention | Predicts likely failure points |
| **health-check** | dynamic team (2-6) | Project health across tests, deps, lint, CI, docs, security |
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

## Installation Options

```bash
# Recommended (agents, memory)
pip install 'attune-ai[developer]'

# Minimal (CLI + workflows only)
pip install attune-ai

# With RAG-grounded code generation (rag-code-gen workflow
# + rag_knowledge_query MCP tool; see "RAG grounding" below)
pip install 'attune-ai[rag]'

# All features
pip install 'attune-ai[all]'

# Development (contributing)
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

### RAG grounding (optional)

When installed with the `[rag]` extra, `attune-ai` gains:

- **`rag-code-gen` workflow** — grounds LLM code generation in
  the bundled attune-help corpus (633 templates) and emits a
  `## Sources` block with clickable citations alongside the
  generated output.
- **`rag_knowledge_query` MCP tool** — returns retrieval hits
  and an augmented prompt string ready to feed to any LLM.
  Does not call an LLM itself.
- **Optional feedback kwarg** — pass `feedback="good"|"bad"`
  to the workflow to record verdicts against every cited
  template for future tuning.

The retrieval engine is the standalone
[attune-rag](https://github.com/Smart-AI-Memory/attune-rag)
package — LLM-agnostic and corpus-pluggable, usable on its
own outside the attune-ai ecosystem.

See [docs/rag/index.md](docs/rag/index.md) for the full
walkthrough and
[docs/rag/embeddings-decision-2026-04-17.md](docs/rag/embeddings-decision-2026-04-17.md)
for the engineering decision record.

---

## API Mode

The plugin's skills use your Claude subscription at no
extra cost. The Python package's CLI and MCP tools
work differently — they spawn Agent SDK subagents
that make
**direct Anthropic API calls**, which require an API key
and incur usage-based charges.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # Required
export REDIS_URL="redis://localhost:6379"  # Optional
```

### Model Routing

Each subagent is assigned a model based on task
complexity to balance cost and quality:

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

Every CLI/MCP workflow enforces a budget cap:

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

- Path traversal protection on all file operations
  (CWE-22)
- Memory ownership checks (`created_by` validation)
- MCP rate limiting (60 calls/min per tool)
- Hook import restriction (`attune.*` modules only)
- PreToolUse security guard (blocks eval/exec, path
  traversal)
- Prompt input sanitization (backticks, control chars,
  truncation)
- PII scrubbing in telemetry
- Automated security scanning (CodeQL, bandit,
  detect-secrets)

See [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) for vulnerability
reporting and full security details.

---

## Migration

`attune-help` and `attune-author` have moved to their own
marketplace at
[Smart-AI-Memory/attune-docs](https://github.com/Smart-AI-Memory/attune-docs).
If you previously installed either of them via the
`attune-ai` marketplace, move your installation with the
three commands below.

1. Add the new marketplace:

   ```text
   /plugin marketplace add Smart-AI-Memory/attune-docs
   ```

2. Uninstall from the old marketplace:

   ```text
   /plugin uninstall attune-help@attune-ai
   /plugin uninstall attune-author@attune-ai
   ```

3. Install from the new marketplace:

   ```text
   /plugin install attune-help@attune-docs
   /plugin install attune-author@attune-docs
   ```

New users: add `Smart-AI-Memory/attune-docs` directly —
no migration steps needed.

---

## Links

- [Full Documentation](https://smartaimemory.com/framework-docs/)
- [Plugin Setup](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/README.md)
- [GitHub Repository](https://github.com/Smart-AI-Memory/attune-ai)

**Apache License 2.0** — Free and open source.

If you find Attune useful,
[give it a star](https://github.com/Smart-AI-Memory/attune-ai) —
it helps others discover the project.

## Acknowledgments

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

**Built by Patrick Roebuck using Claude Code.**

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
