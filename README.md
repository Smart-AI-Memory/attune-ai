# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Persistent memory and receipt-verified workflows for Claude Code.**

🌐 **Docs & guides: [attune-ai.dev](https://attune-ai.dev)**

<!-- Badge maintenance: PyPI/Downloads/Coverage/Security are LIVE (auto-update,
     no upkeep). The tests count is a manually-maintained round FLOOR — bump it
     only on major drift (e.g. once the suite clears 25,000); a round floor
     can't go subtly stale the way a precise value does. `scripts/check_badge_freshness.py`
     (CI) fails if the floor ever over-claims or drifts too far below reality. -->
[![PyPI](https://img.shields.io/pypi/v/attune-ai?color=blue)](https://pypi.org/project/attune-ai/)
[![Downloads](https://static.pepy.tech/badge/attune-ai)](https://pepy.tech/projects/attune-ai)
[![Downloads/month](https://static.pepy.tech/badge/attune-ai/month)](https://pepy.tech/projects/attune-ai)
[![Downloads/week](https://static.pepy.tech/badge/attune-ai/week)](https://pepy.tech/projects/attune-ai)
[![Tests](https://img.shields.io/badge/tests-25%2C000%2B%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/codecov/c/github/Smart-AI-Memory/attune-ai?branch=main)](https://codecov.io/gh/Smart-AI-Memory/attune-ai)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

Your agent stops starting from zero, its word stops being the
evidence, and it asks you with structure instead of prose.

**Memory:** a stash → recall → promote loop carries decisions, bugs,
and hard-won lessons from one session into the next, and surfaces the
right lesson at the exact moment a prompt needs it. Local-first, from
a plain `pip install attune-ai`. Recall loads a few hundred
exactly-relevant tokens instead of your whole corpus — **67× fewer
tokens** on our own 800+ lesson store, retrieved at **P@3 96%** on a
frozen benchmark ([details](#the-memory-suite--measured)).

**Receipts:** state the outcome you want and how to verify it, and
get back a receipt — not a promise:

```bash
attune fix "imports resolve after the rename" \
  --workflow fix \
  --scope src/attune/cli_minimal.py \
  --probe "pytest tests/unit/test_cli_minimal.py" \
  --run
```

<!-- Recorded via scripts/demo/fix-receipts.tape (chair-approved
     2026-08-29); absolute URL so the image renders on PyPI too. -->
![attune fix repairing a broken import and producing a receipt: contract preview, attributed diff, probes re-run independently, exit 0](https://raw.githubusercontent.com/Smart-AI-Memory/attune-ai/main/scripts/demo/fix-receipts.gif)

The probes are re-run *independently* of the workflow that claims it
finished. Exit 0 means the probes passed — not that the agent felt
good about it.

**Interactive forms:** the agent asks with structure, not prose — a
decision card with its recommendation and tradeoffs, a pushback card
when it disagrees, a progress report, a ranking or triage — one tap
each, validated on the way back. One form renders to whatever surface
your client draws: a native dialog, a rich widget, or a plain menu
([the vocabulary](#interactive-forms--the-agent-asks-with-structure)).

Around that core: 21 workflows and <!-- cap:mcp_registered_tool_count -->65 MCP tools<!-- /cap -->
dispatching 2–6 domain-specific subagents behind Socratic quality
gates, RAG grounding with a citation-per-claim contract, and
generation fact-checking — one install, one MCP server. We run our
own knowledge base on it: the docs and 800+ engineering lessons at
[attune-ai.dev](https://attune-ai.dev) are authored, grounded, and
maintained by Attune's own stack.

**Contents:**
[Install](#get-started-in-60-seconds) ·
[Costs](#what-this-costs) ·
[Memory](#the-memory-suite--measured) ·
[Receipts](#receipts-not-promises) ·
[Multi-LLM](#multi-llm-collaboration) ·
[Workflows & tools](#workflows-and-mcp-tools) ·
[Forms](#interactive-forms--the-agent-asks-with-structure) ·
[Accuracy](#accuracy--faithfulness) ·
[Install options](#installation-options) ·
[Privacy](#security-privacy--telemetry)

---

## Get Started in 60 Seconds

**Recommended: install both — still free, no API key needed.**

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
pip install attune-ai
```

Then say "what can attune do?" in Claude Code, and run `attune` in
your terminal — it shows your next steps (`attune validate` checks
the setup). The plugin runs on your Claude subscription, and
memory, forms, and hooks never call a model; an API key is only
for direct CLI workflow runs
([What this costs](#what-this-costs)).

*Just want the skills?* The plugin alone (the first two commands)
works standalone — no Python required.

Setup fight you? [Tell me where](https://github.com/Smart-AI-Memory/attune-ai/discussions/1325) — I'm actively fixing this.

### What each layer adds

| Capability | Plugin only | Plugin + pip |
| ---------- | ----------- | ------------ |
| <!-- cap:skill_count -->28 auto-triggering skills<!-- /cap --> | Yes | Yes |
| Security hooks | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| <!-- cap:mcp_registered_tool_count -->65 MCP tools<!-- /cap --> | -- | Yes |
| `attune` CLI + multi-agent workflows | -- | Yes |
| Ops dashboard (`attune ops`) — run history, cost tiles, telemetry | -- | Yes |

---

## What this costs

| How you run it | What it costs |
| -------------- | ------------- |
| **Plugin in Claude Code** (skills, hooks, forms) | Your Claude subscription. No API key, no extra charge. |
| **`attune` CLI + MCP tools** | Direct Anthropic API calls — needs `ANTHROPIC_API_KEY` with **API credits**. |

**The one thing people get wrong:** a Claude Pro/Max subscription does
*not* include API credits — they are separate products. If you only
use the plugin, this never comes up. Free on either path (they never
call a model): elicitation forms, security hooks, path validation,
memory storage and recall, and every local transform.

---

<!-- ROTATING SLOT: this "New in <version>" section is replaced each
     release with the headline feature; the displaced content moves to
     a permanent section below. Don't stack a second "New in" here. -->

## New in 16.2.1 — strict dynamic forms render again

Guided Fix and Spec intake now omit optional field properties when they are
absent instead of serializing them as JSON `null`. Strict native MCP hosts can
accept the generated payload unchanged, so the dynamic form, scope picker, and
probe suggestions render instead of failing client-side schema validation.

The release-gate parser also rejects arrays and scalar values where an object
is required, allowing its remaining response strategies to recover instead of
reporting a misleading `quality_score 0.0` failure.

<details>
<summary>Previously new in 16.1.0 — harness-lite lands</summary>

16.0.0 executed the destructive half of the harness-lite
architecture ruling: nine dead framework-era modules deleted
(~2,200 lines, each verified caller-free before removal), every
15.x deprecation executed on schedule, and the ceremony
entry-point seams collapsed to direct registration. 16.1.0 closes
the loop on the removal: an extension still declaring the removed
`attune.plugins` / `attune.wizards` entry points used to fail by
silent non-loading — now a once-per-process warning names the
package and points at the migration guide.

**Upgrading is a no-op** if you use the CLI, the plugin, or the
MCP tools. The
[16.0.0 upgrade guide](docs/migration/upgrading-to-16.0.0.md)
opens with the one grep that tells you whether any of this touches
your code. The constructive half — the extension system — ships
later in 16.x.

</details>

<details>
<summary>Previously new in 15.0.0 — one obvious way to do each thing</summary>

**Every attune surface has exactly one name, one contract, and one
place to register.** 15.0.0 completed a consolidation that ran
across several releases: what the docs describe is what the
library has, with no second spelling of it kept alive out of
habit. One name for the MCP server (`AttuneMCPServer`); one
registration path per extension (collapsed further to direct
registration in 16.0.0); the 1–5 level dial retired from every
public API. A smaller surface to hold in your head, which is the
whole point: less API, and all of it real.

</details>

---

## The memory suite — measured

**Stash on stop. Recall at the door. Promote what endures.**

- **Stash** — a `Stop` hook extracts decisions, bugs, and references
  from the session and writes them to the memory store (local file by
  default, Redis Agent Memory Server when reachable).
- **Recall** — a `SessionStart` hook surfaces the most recent
  findings for your project; `/recall <topic>` searches on demand.
- **Promote** — a reviewed stash→curated path lands git-tracked
  `.md` files in your corpus. Files are the store; Redis serves them.
- **Lessons at the trap moment** — hooks retrieve the exact lesson a
  prompt or tool call needs, budget-capped no matter how large the
  corpus grows.

Memory is local-first — nothing leaves your machine. Redis is optional:
its role here is to provide enhanced memory features using Redis's
open-source options (semantic recall across sessions through the Agent
Memory Server). A plain install runs on the local file tier; you choose
once — a first-run notice asks, or `attune memory use auto|file|redis` —
and `attune memory status` / `attune doctor` always say which tier is live.
The economics are measured, not promised (2026-07-05 snapshot;
ratios improve as the corpus grows):

| Memory-suite recall | Instead of loading | You load | Win |
|---|--:|--:|--:|
| Trap-moment lessons | 202,042 tok (583 lessons) | ≤3,000 tok | **67× fewer tokens** |
| SessionStart digest | 16 corpus files (4.6 ms) | one Redis call (0.6 ms) | **~7× faster** |

Numbers from `benchmarks/memory_savings.py` on our dogfood store.

---

## Receipts, not promises

If you know acceptance-test-driven development, this is that rebuilt
for agent workflows: acceptance probes are declared up front, and the
agent's own word is never the evidence.

- **Fix Receipts** (`attune fix`) — outcome-first fixing. Preview a
  contract (done conditions, constraints, probes) with nothing
  executing; add `--run` for an attributed diff whose probes are
  re-run independently. Exit 0 only when the probes pass.
- **Spec Ladders** (`/spec`) — spec-driven development, with
  receipts: the approved spec *drives the agents* — Claude Code,
  Codex, or Antigravity alike. Requirements, design, and a gated
  task ladder the agent executes between your approvals —
  workflows dispatched, every ruling recorded in a decision file
  that outlives the session.
- **Guided intakes** — `/fix` and `/spec` compose their contracts
  through a form: goal pre-filled, scope picker from paths you've
  touched, probe suggestions from matching tests.
- **Receipts all the way down** — a failed or absent security auditor
  *fails* the Security gate; spec-closure claims draw a rotating
  skeptic seat; risk-class diffs authored by the lead model are
  reviewed by a *different* model before promotion.
- **Workflows prove they work** — a planted-defect harness runs
  every catalog workflow against a fixture carrying a known bug (a
  real `eval` call, a real CVE pin, a module with no docstrings);
  *finding it* is what keeps the workflow's "working" badge, with
  cost and verdict recorded in a tracked registry. Workflows under
  repair are hidden from the dashboard, CLI list, and MCP catalog
  until their probes pass.

---

## Multi-LLM collaboration

As of 10.6.0, attune treats Claude Code, OpenAI Codex, and Google
Antigravity as seats at the same table — with the discipline that a
claim without a receipt doesn't ship:

- **`/roundtable`** — the three models deliberate a question on a
  Redis-backed board; *you* chair what gets promoted.
- **`/cross-review`** — an advisory second opinion on a real diff
  from a *different* model than the one that wrote it.
- **Cross-provider handoff + shared session memory** — portable
  resume briefs and a provider-neutral stash/recall surface with a
  PII/secrets gate that redacts at rest and fails closed.
- **A projected collaboration contract** — one master file projects
  to `AGENTS.md` and per-provider mirrors.

Codex installs the same plugin from its marketplace
(`codex plugin install attune-ai@attune-ai`); Antigravity connects
over MCP. The 10.6.1 release exists because a cross-provider receipt
probe caught a protocol bug the primary client silently tolerated.

---

## Workflows and MCP tools

Skills trigger from natural language — "review my code", "scan for
vulns", "generate tests", "plan this feature" — and every workflow
dispatches 2–6 subagents (Opus for deep reasoning, Sonnet for
analysis, Haiku for fast scanning), synthesized by an orchestrator.
Ready-made Claude Code subagents (`security-reviewer`, `spec-author`,
`refactor-planner`, …) appear in your `/agents` list on install.

<details>
<summary><b>All 21 workflows</b></summary>

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
| **release-gate** | parallel agent team (4 stages) | Release readiness assessment / go-no-go gate |
| **release-notes** | agent-prep | Drafts release notes + LLM readiness advice |
| **doc-orchestrator** | inventory, outline, content, polish | Full-project documentation |
| **secure-release** | security, health, dep-auditor, gater | Release pipeline with risk scoring |
| **research-synthesis** | summarizer, pattern-analyst, writer | Multi-source research synthesis |
| **discovery-sweep** | pattern-scanner, verifier | Repo-wide bug-pattern sweep with verification |
| **rag-code-gen** | retriever, generator | Citation-forced code generation grounded in the local corpus |
| **orchestrated-health-check** | dynamic team | `health-check` with explicit meta-orchestration |
| **fix** | agent-fix | Minimal in-place fix within a contract's scope, verified by a receipt |

</details>

<details>
<summary><b>All 64 MCP tools</b> — 53 core in 7 categories, plus 11
memory tools registered by the bundled Redis plugin</summary>

**Workflow (22):** `security_audit` `code_review` `bug_predict`
`discovery_sweep` `performance_audit` `refactor_plan` `simplify_code`
`deep_review` `test_generation` `test_audit` `test_gen_parallel`
`doc_gen` `doc_audit` `doc_orchestrator` `release_notes`
`health_check` `dependency_check` `secure_release`
`research_synthesis` `analyze_batch` `analyze_image`
`rag_knowledge_query`

**Help (5):** `help_lookup` `help_init` `help_status` `help_update`
`help_maintain`

**Memory (4):** `memory_store` `memory_retrieve` `memory_search`
`memory_forget`

**Personal Memory (4):** `personal_memory_capture`
`personal_memory_recall` `personal_memory_topics`
`personal_memory_forget`

**Utility (6):** `auth_status` `auth_recommend` `telemetry_stats`
`context_get` `context_set` `list_capabilities`

**Elicitation (7):** `elicitation_ask` `elicitation_render_form`
`elicitation_collect_response` `elicitation_render_widget`
`chart_render_widget` `fix_workspace_preview`
`fix_workspace_collect_action`

**Handoff (2):** `handoff_create` `handoff_resume`

**Redis memory (11):** `session_memory_*`, `redis_memory_*`,
`redis_health_check`

</details>

---

## Interactive forms — the agent asks with structure

Agent↔you exchanges are interactive forms, not prose Q&A. The agent
presents a **decision** with its recommendation, rationale, and
per-option tradeoffs; disagrees through a **pushback** card (your
approach vs. its alternative, side by side); reports **progress** as
done / in-flight / blocked; and has you **rank**, **triage**,
**confirm**, deliberate, or review its **assumptions** — one tap each.
Every question is validated on the way back, so a malformed answer is
re-asked, not silently accepted.

![An attune-forms decision form being filled: an empty submit is
caught by validation, then a recommended decision card, multi-select
checkboxes, a dropdown, a number field, and a path are set and
submitted](https://raw.githubusercontent.com/Smart-AI-Memory/attune-ai/main/docs/assets/images/attune-forms-audit-demo.gif)

*One question, five control types — a recommended decision card with
per-option tradeoffs, multi-select, dropdown, bounded number, free
text. An empty submit is caught by validation, never silently
accepted. Rendered by the production widget pipeline
([regenerate](scripts/render_demo_forms.py)); [try it
live](https://smartaimemory.com/forms-demo/audit.html).*

One declarative form, written once, renders to the richest surface your
client supports — a native dialog, a rich HTML widget, or a plain
multiple-choice menu on a text-only surface — so the same question
works everywhere and degrades gracefully. The full construct vocabulary
ships via `attune-forms` 0.7.0 (new in 13.0.0). Chart specs render
through the same sealed SVG kernel (`chart_render_widget`, nine chart
types).

### State-bound command workspaces

Roundtable, Spec, Release Prep, Bug Predict, and the broader command cohort
use one state-bound dynamic workspace renderer. The same canonical action
contract reaches rich widgets, Markdown/text fallbacks, and terminal receipts;
stale or replayed actions fail closed instead of relying on presentation state.

Roundtable's seven-item promotion review completes in atomic `3 + 3 + 1`
batches: three submissions instead of seven, with the same terminal rulings.
That is 57.143% fewer ruling submissions and 66.667% fewer added navigation
rounds in the measured portable/headless path. These are interaction-mechanics
figures, not claims about human dwell or provider execution time. Consequential
actions use `attune-forms 0.12.2`'s visible inline two-click confirmation, so a
host-blocked native browser dialog cannot make the button appear inert.

---

## Accuracy & Faithfulness

RAG generation — powered by the bundled `attune-rag` engine —
enforces citation-per-claim: **0.97 mean per-claim faithfulness,
CI-gated** (40-query golden set, N=20 runs).
The contract was chosen by A/B measurement — the per-query
hallucination bucket rate dropped from 46.7% to 6.7% with it
([methodology](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/rag/faithfulness-decision-2026-04-19.md)).
Retrieved passages are sentinel-wrapped against prompt injection.
The help resolver passes 48/48 benchmark queries at P@1
([golden set](https://github.com/Smart-AI-Memory/attune-ai/blob/main/tests/unit/help/fixtures/golden_queries.yaml)).

---

## Installation Options

`pip install attune-ai` works out of the box — the CLI, all
workflows, the MCP server, RAG (`attune-rag` and `attune-verify` are
core dependencies), cross-session memory, and the Agent SDK. Memory
features activate when a Redis Stack server is reachable and degrade
with guidance when not. Add extras only for the surfaces you use:

| You want | Install |
| -------- | ------- |
| Everything most users need, incl. Redis memory | `pip install attune-ai` |
| Claude API mode + optional LangChain/LangGraph interop adapters | `pip install 'attune-ai[developer]'` |
| The ops dashboard (`attune ops`) | `pip install 'attune-ai[ops]'` |

Extras combine — `pip install 'attune-ai[developer,ops]'`. Keep the
quotes: zsh and bash treat square brackets as glob characters.

Contributing? Clone and install the dev toolchain instead:

```bash
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

### API mode

The CLI and MCP tools call the Anthropic API directly (the plugin
never needs this):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."      # requires API credits
export REDIS_URL="redis://localhost:6379"  # optional
```

Model routing assigns Opus/Sonnet/Haiku by task complexity
(`ATTUNE_AGENT_MODEL_*` to override); depth budgets run $0.50 /
$2.00 / $5.00 (`ATTUNE_MAX_BUDGET_USD` to override); `--cheap`
forces pattern-matching workflows onto Haiku. Live spend tiles on
the dashboard (`attune ops`).

<details>
<summary><b>Platform support</b></summary>

| Platform | Support |
| -------- | ------- |
| macOS / Linux / WSL2 | Full |
| Windows native + Git Bash | Supported (Bash tool, POSIX-ish syntax) |
| Windows native + PowerShell tool | Limited — security validation fails closed |

Redis has no native Windows build — use Docker
(`docker run -d -p 6379:6379 redis:7-alpine`). Without reachable
Redis, memory degrades gracefully to the file backend and
`attune.memory.session_stash.backend_status()` reports
`fallback: true`.

</details>

---

## Ecosystem

| Package | Role | Install |
| ------- | ---- | ------- |
| **`attune-ai`** | Developer workflow hub (this package) | `pip install attune-ai` |
| **`attune-rag`** | RAG pipeline (core dep) | bundled |
| **`attune-verify`** | Generation fact-checker (core dep) | bundled |
| **`attune.authoring`** | Help authoring + staleness detection (absorbed the former `attune-author` package in 11.0.0) | bundled |
| **`attune-help`** | Progressive-depth template runtime | `pip install attune-help` |

---

## Security, Privacy & Telemetry

Path traversal protection on all file ops, a PreToolUse guard that
blocks eval/exec, MCP rate limiting, prompt sanitization, and
automated scanning (CodeQL, bandit, detect-secrets) — details in
[SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md).

Usage data is local-first. An **opt-in, anonymous usage ping**
(OFF by default) carries only package, version, workflow name, OS,
Python version, a resettable anonymous id, and a timestamp — never
paths, code, prompts, or filenames; the payload is frozen in source
and guarded by a regression test. `attune telemetry status|enable|disable`;
`DO_NOT_TRACK=1` always wins.

---

## Links

- [Full Documentation](https://attune-ai.dev)
- [Plugin Setup](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/README.md)
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

[View Full Acknowledgements](https://github.com/Smart-AI-Memory/attune-ai/blob/main/ACKNOWLEDGEMENTS.md)

---

**Built by Patrick Roebuck using Claude Code.**

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->
