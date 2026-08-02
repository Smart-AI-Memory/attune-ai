# Attune AI

<!-- mcp-name: io.github.Smart-AI-Memory/attune-ai -->

**Spec-driven development for Claude Code — turn requirements into reliable software.**

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
[![Tests](https://img.shields.io/badge/tests-20%2C000%2B%20passing-brightgreen)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/codecov/c/github/Smart-AI-Memory/attune-ai?branch=main)](https://codecov.io/gh/Smart-AI-Memory/attune-ai)
[![Security](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml/badge.svg)](https://github.com/Smart-AI-Memory/attune-ai/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

**Attune AI** gives Claude Code persistent memory. Your agent stops
starting from zero: a stash → recall → promote loop carries
decisions, bugs, and hard-won lessons from one session into the
next, and a retrievable lessons corpus surfaces the right lesson at
the exact moment a prompt needs it — local-first, working from a
plain `pip install attune-ai`. The economics are measured, not
promised: recall loads a few hundred exactly-relevant tokens instead
of your whole corpus — 67× fewer tokens on our own 800+ lesson
store, retrieved at P@3 96% on a frozen trap-moment benchmark
(details in [the memory suite](#the-memory-suite--out-of-the-box-measured)
below).

Around that memory core, the same package also ships **Fix
Receipts** — state the outcome you want and how to verify it,
preview the contract (nothing executes), then `--run` for an
attributed diff whose probes are re-run independently of the
workflow; exit 0 means the probes passed, not that the agent felt
good about it — plus a spec-driven,
multi-agent toolkit: 21 workflows and <!-- cap:mcp_registered_tool_count -->60 MCP tools<!-- /cap --> dispatching 2–6
domain-specific subagents behind Socratic quality gates, RAG
grounding with a citation-per-claim contract (mean per-claim
faithfulness CI-gated at ≥ 0.97; 0.98 currently measured, N=20 runs
on the 40-query golden set), and generation fact-checking — one
install, one MCP server.

We run our own knowledge base on it: the docs, help templates, and
800+ engineering lessons at [attune-ai.dev](https://attune-ai.dev)
are authored, grounded, and maintained entirely by Attune's own
stack.

**Managing and creating help-content, docs, or knowledge-bases?**
That's `attune-help` (progressive-depth runtime) plus `attune-author`
(AI authoring and staleness detection) — both installable from this
marketplace and driven from the CLI or Claude Code.

---

## What this costs

There are two ways to run Attune, and they bill differently. Pick the
row you're in:

| How you run it | What it costs |
| -------------- | ------------- |
| **Plugin in Claude Code** (skills, hooks, forms) | Your Claude subscription. No API key, no extra charge. |
| **`attune` CLI + MCP tools** | Direct Anthropic API calls — needs `ANTHROPIC_API_KEY` with **API credits**. |

**The one thing people get wrong:** a Claude Pro/Max subscription does
*not* include API credits. They are separate products. The subscription
powers Claude Code — and therefore the plugin — but the CLI and MCP
tools call the Anthropic API directly, so a key without pay-as-you-go
credit returns `credit balance is too low`. If you only use the plugin,
this never comes up.

Free on either path, because they never call a model: the elicitation
forms, the security hooks, path validation, memory storage and recall,
and every local transform. See [API Mode](#api-mode) for keys and
routing, and [Installation Options](#installation-options) for extras.

---

<!-- ROTATING SLOT: this "New in <version>" section is replaced each
     release with the headline feature; the displaced content moves to
     a permanent section below (see "Dynamic forms" for the pattern).
     Don't stack a second "New in" section here. -->

## New in 11.0.0 — attune-author invocation paths retired

Major version, one breaking change: the **`[author]` install extra is
removed**, along with the ops dashboard's help-regeneration surface
(`/api/help/regen*` and the Admin-page regen UI). `/help/admin` is now
report-only and points at `/coach maintain`, which is where
documentation regeneration lives.

**Are you affected?** Only if you install with
`pip install 'attune-ai[author]'` — that extra no longer resolves, so
drop it from your requirements. Plain `pip install attune-ai` is
unchanged, and no runtime API was removed. The extra existed to pull in
`attune-author`, which was archived after its capability was absorbed
here; keeping an extra that points at an archived package would have been
the dishonest option.

Also in this release: handoff packets now carry memory linkage and
report a real memory outcome instead of silence; the Health tab shows
which surface rendered each Python-routed form; `session_memory_*` tools
answer with per-verb summaries rather than a generic line; and the
release model tier resolves at call time, so a changed override is
observed without a restart.

## The memory suite — out of the box, measured

**Your agent stops starting from zero — with a plain
`pip install attune-ai`.** The memory suite matured across recent
releases (curated promotion in 9.5, files-canonical unification in
9.6, Redis / Agent Memory Server client as a core dependency in
9.7). The loop:

- **Stash on stop** — a `Stop` hook extracts decisions, bugs, and
  references from the session (local LLM when available, heuristic
  fallback) and writes them to the memory store: a local file by
  default, Redis Agent Memory Server when one is reachable.
- **Recall at the door** — a `SessionStart` hook surfaces the most
  recent findings for your project, and warns when the memory
  backend is unreachable instead of degrading silently.
- **Promote what endures** — a reviewed stash→curated path: the
  agent drafts a node per candidate, you verdict each one (the
  30-day test), and promotion lands a git-tracked `.md` file in
  the curated corpus. Files are the store; Redis serves them —
  recall pulls a few hundred exactly-relevant tokens on demand
  instead of re-reading whole files into context.
- **Lessons at the trap moment** — a `UserPromptSubmit` hook
  retrieves your project's engineering lessons (from
  `.claude/lessons.md` or `CLAUDE.md`) when a prompt hits a known
  trap; a `PreToolUse` hook surfaces curated rules at the exact
  tool call they govern.
- **On demand** — `/recall <topic>` searches both stores with
  results labeled by source; `/remember` captures and manages
  facts explicitly; a full MCP tool surface (memory, personal
  memory, Redis/AMS) gives agents the same access.

Memory is local-first — nothing leaves your machine, and without a
Redis server everything degrades to the file backend with clear
guidance. Your memory, your corpus: we dogfood the loop on our own
800+ engineering lessons, retrieved via attune-rag at **P@3 96%**
(100% on the high-severity subset) on a frozen trap-moment benchmark.

**The economics, measured (2026-07-05 snapshot; corpus has grown
since — the ratios below only improve as it does).** Durable memory
was 303,205 tokens across 752 docs at measurement time; a session
recalls only the relevant slice:

| Memory-suite recall | Instead of loading | You load | Win |
|---|--:|--:|--:|
| Trap-moment lessons | 202,042 tok (583 lessons) | ≤3,000 tok | **67× fewer tokens** |
| SessionStart digest | 16 corpus files (4.6 ms) | one Redis call (0.6 ms) | **~7× faster** |

The lessons injection stays budget-capped no matter how large the
corpus grows, and recall is a single warm Redis call — so both wins
widen as your memory does. Numbers from `benchmarks/memory_savings.py`
on our dogfood store (cl100k_base).

---

## Multi-LLM collaboration — three models, one repo, receipts required

**Your repo stops being single-provider.** As of 10.6.0, attune
treats Claude Code, OpenAI Codex, and Google Antigravity as seats at
the same table — with the discipline that a claim without a receipt
doesn't ship:

- **`/roundtable`** — convene Claude, Antigravity, and Codex to
  deliberate a question on a Redis-backed board. Seats post
  positions independently, synthesis compiles them, and *you* chair
  what gets promoted — nothing lands without a ruling. Headless
  routines run the same loop on a schedule.
- **`/cross-review`** — a one-seat advisory second opinion on a real
  diff from a *different* model than the one that wrote it.
  Advisory only, board-recorded.
- **Cross-provider session handoff** — `handoff_create` /
  `handoff_resume` MCP tools write a portable, verifiable resume
  brief so one agent can pick up where another stopped.
- **Provider-neutral session memory** — the `session_memory_*` MCP
  tools give every seat the same stash/recall/forget surface over
  the shared store, with a PII/secrets gate that redacts at rest
  and fails closed on secrets. Verified live from a Codex session:
  capture → recall (email stored as `[EMAIL]`) → forget →
  gone.
- **A projected collaboration contract** — one master file projects
  to `AGENTS.md` and per-provider mirrors, so any agent learns the
  repo's rules (read-only preflight, branch discipline, shared
  memory etiquette) without Claude-specific context.

Codex installs the same plugin from its marketplace
(`codex plugin install attune-ai@attune-ai`); Antigravity connects
over MCP. We dogfood all of it on this repository — the multi-model
release audit for 10.6.0 ran through the roundtable itself, and
10.6.1 exists because a cross-provider receipt probe caught a
protocol bug the primary client silently tolerated.

---

## Ecosystem

| Package | Role | Install |
| ------- | ---- | ------- |
| **`attune-ai`** | Developer workflow hub (this package) | `pip install attune-ai` |
| **`attune-rag`** | RAG pipeline (core dep of attune-ai, v0.7+) | bundled |
| **`attune-verify`** | Generation fact-checker — backs the `/verify` skill (core dep) | bundled |
| **`attune-author`** | Help content authoring, staleness detection | `pip install 'attune-ai[author]'` |
| **`attune-help`** | Progressive-depth template runtime | `pip install attune-help` |

`attune-rag` and `attune-verify` both ship as **core dependencies** of
`attune-ai` — retrieval grounding and generation fact-checking are
on by default, no extra needed. `attune-help` is standalone — not
pulled in by a standard `attune-ai` install, but available as an
optional corpus for `attune-rag` via
`pip install 'attune-rag[attune-help]'`.

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

**A head start on `/agents`, too.** Beyond the workflow teams above,
attune-ai ships a curated set of Claude Code subagents —
`security-reviewer`, `spec-author`, `refactor-planner`,
`release-prep-auditor`, and more — that appear in your `/agents` list the
moment the plugin installs. Claude Code gives you the *mechanism* to build
subagents; attune-ai gives you a *running start* — use them as-is, or fork
one as the scaffold for your own.

### 3. Socratic before execution

Workflows ask questions before executing, not after. The `spec`
workflow brainstorms, then plans, then executes. `planning` clarifies
scope before writing a line of code. This eliminates the most common
failure mode: confidently solving the wrong problem.

**Dynamic communication — the agent adapts how it talks to you.**
The headline of this release: instead of a fixed wall of prose, Attune
now *dynamically* shapes each exchange to fit the moment — rendering an
interactive form in response to your prompt whenever a structured turn
communicates better than text. A multi-part question becomes one form
you answer with a click; a recommendation arrives as weighable cards; a
disagreement is shown side-by-side so you can overrule it in one tap.
This is a deliberate effort to *improve human/AI communication* — making
the back-and-forth faster, clearer, and less ambiguous. Three of the
four constructs fire at a **fork** — a point where the conversation
can't move forward without your choice; the fourth (**progress**) is a
status report, not a fork. The agent picks the right *construct* for
the moment:

- **intake** *(fork)* — gathers several independent decisions as a
  single (multi-select-capable) form, instead of N back-and-forth
  questions.
- **decision** *(fork)* — offers a *recommended* option with a
  rationale and per-option tradeoffs, rendered as cards (consumed by
  the `/spec` approval gate).
- **pushback** *(fork)* — when the agent disagrees with your stated
  approach, it shows "your approach" beside "I'd suggest instead" with
  a "why", and you overrule or switch with one pick (`/spec` plan
  review).
- **progress** *(report)* — a done / in-progress / blocked status
  board whose blocked items are a picker for what to fix next (`/spec`
  execute).

All constructs share one declarative form model and validator, render
richly on widget-capable surfaces (e.g. claude.ai / Cowork) and degrade
gracefully to a recommendation-first menu elsewhere. The terse reply
vocab (`y` / `go` / `1`) answers any of them.

### 4. RAG-grounded generation

`attune-rag` (core dep) grounds LLM generation in retrieved corpus
passages and enforces citation-per-claim, delivering **0.98 mean
per-claim faithfulness on the current CI-gated benchmark** (40
queries, N=20 runs, floor ≥0.97) — the large majority of generated
claims are grounded in their cited passages. The citation-per-claim
design itself was chosen via an A/B comparison (2026-04-19): the
conservative per-query bucket rate (a single ungrounded claim
disqualifies the whole response) dropped from 46.7% without the
contract to 6.7% with it. Retrieved passages are wrapped in sentinel
tags to prevent prompt injection. The Claude provider automatically
caches the stable RAG context prefix, eliminating repeated token
costs across calls.

### 5. Memory that compounds across sessions

Most AI coding sessions start from zero. Attune ships a
cross-session memory loop — stash on stop, recall at the door,
reviewed promotion into a git-tracked curated corpus, and lessons
retrieved at the exact trap moment they guard against. Covered in
depth in "The memory suite" section at the top of this README; the
hook-by-hook mechanics and tunables live in the
"Session continuity & cross-session memory" section below.

---

## Dynamic forms — structured human/AI communication

Attune improves how you and the AI communicate by dynamically using
interactive forms (shipped in 9.3.0). Instead of a fixed wall of
prose, Attune renders the right form whenever a structured turn
communicates better than text — a multi-part question becomes one
form you answer with a click, a recommendation arrives as weighable
cards, and a disagreement is shown side-by-side so you can overrule
it in one tap. Three constructs fire at a **fork** — a point where
the conversation needs your choice to continue; the fourth
(**progress**) is a status report, not a fork:

- **intake** *(fork)* — gather several independent decisions in one
  form
- **decision** *(fork)* — a recommended option with rationale +
  per-option tradeoffs (`/spec` approval gate)
- **pushback** *(fork)* — agent dissent shown as "your approach" vs
  "I'd suggest instead"; overrule or switch in one pick (`/spec` plan
  review)
- **progress** *(report)* — a done / in-progress / blocked board
  whose blocked items are a fix-next picker (`/spec` execute)

All constructs share one declarative form model and validator, render
richly on widget-capable surfaces (e.g. claude.ai / Cowork) and degrade
gracefully to a recommendation-first menu elsewhere. The terse reply
vocab (`y` / `go` / `1`) answers any of them.

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
pip install attune-ai
attune            # shows your next steps
```

Then check your setup with `attune validate` and run your first
workflow: `attune workflow run code-review --path src/`.

Setup fight you? [Tell me where](https://github.com/Smart-AI-Memory/attune-ai/discussions/1325) — I'm actively fixing this.

The core install includes the CLI, all workflows, and the MCP
server. See [Installation Options](#installation-options) for
per-surface extras (API-mode agents, ops dashboard, Redis memory).

### What Each Layer Adds

| Capability | Plugin only | Plugin + pip |
| ---------- | ----------- | ------------ |
| <!-- cap:skill_count -->27 auto-triggering skills<!-- /cap --> | Yes | Yes |
| Security hooks | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| <!-- cap:mcp_registered_tool_count -->60 MCP tools<!-- /cap --> | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Help system maintenance | -- | Yes |
| CI/CD automation | -- | Yes |
| Ops dashboard (`attune ops`) — run history, cost tiles, telemetry | -- | Yes |

> **Note:** Skills use your Claude subscription at no extra cost.
> CLI and MCP tools make direct Anthropic API calls — API key with
> credits required. See [What this costs](#what-this-costs).

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
| **release-gate** | parallel agent team (4 stages) | Release readiness assessment / go-no-go gate |
| **release-notes** | agent-prep | Drafts release notes + LLM readiness advice |
| **doc-orchestrator** | inventory, outline, content, polish | Full-project documentation |
| **secure-release** | security, health, dep-auditor, gater | Release pipeline with risk scoring |
| **research-synthesis** | summarizer, pattern-analyst, writer | Multi-source research synthesis |
| **discovery-sweep** | pattern-scanner, verifier | Repo-wide bug-pattern sweep with verification, dashboard chips, and run drill-in |
| **rag-code-gen** | retriever, generator | Citation-forced code generation grounded in the local attune-help corpus |
| **orchestrated-health-check** | dynamic team via meta-orchestration | Same intent as `health-check` with explicit meta-orchestration of the sub-team |

---

## MCP Tools

49 tools organized into 7 categories:

### Workflow (22)

`security_audit` `code_review` `bug_predict`
`discovery_sweep` `performance_audit` `refactor_plan`
`simplify_code` `deep_review` `test_generation`
`test_audit` `test_gen_parallel` `doc_gen` `doc_audit`
`doc_orchestrator` `release_notes` `health_check`
`dependency_check` `secure_release` `research_synthesis`
`analyze_batch` `analyze_image` `rag_knowledge_query`

### Help (5)

`help_lookup` `help_init` `help_status` `help_update`
`help_maintain`

### Memory (4)

`memory_store` `memory_retrieve` `memory_search`
`memory_forget`

### Personal Memory (4)

`personal_memory_capture` `personal_memory_recall`
`personal_memory_topics` `personal_memory_forget`

### Utility (8)

`auth_status` `auth_recommend` `telemetry_stats`
`context_get` `context_set` `attune_get_level`
`attune_set_level` `list_capabilities`

### Elicitation (4)

`elicitation_ask` `elicitation_render_form`
`elicitation_collect_response` `elicitation_render_widget`

### Handoff (2)

`handoff_create` `handoff_resume`

---

## Accuracy & Faithfulness

### RAG grounding — 0.996 per-claim faithfulness (over 99%)

Measured on a 15-query golden set with retrieval held constant. The
**per-claim faithfulness** score (how much of what the model says is
grounded in cited passages) is the headline metric. The conservative
**per-query bucket rate** (a single ungrounded claim disqualifies the
whole response) is shown alongside for completeness — they measure
related-but-different things, and the per-claim number is the right
"how trustworthy is each statement" answer:

| Prompt variant | Per-claim faithfulness | Per-query hallucination |
|---|---|---|
| baseline (no grounding rule) | 0.938 | 46.67% |
| strict ("answer only from context") | 0.968 | 26.67% |
| **citation (shipped default)** | **0.996** | **6.67%** |

The gain comes from the prompting contract (citation-per-claim), not
from retrieval. Full methodology:

- [`docs/rag/faithfulness-decision-2026-04-19.md`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/rag/faithfulness-decision-2026-04-19.md)
- [`docs/rag/ab-report-2026-04-19.json`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/rag/ab-report-2026-04-19.json)

### Help resolver — 48/48 benchmark queries pass at P@1

| Bucket | Count | P@1 | Notes |
|---|---|---|---|
| easy | 22 | 22/22 (100%) | feature-name synonyms |
| medium | 26 | 26/26 (100%) | paraphrases + industry terminology |
| hard | 4 | 0/4 (XFAIL) | shared-tag collisions — structural ambiguity |

- [`tests/unit/help/fixtures/golden_queries.yaml`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/tests/unit/help/fixtures/golden_queries.yaml)

---

## Why Attune?

| | Attune AI | Static Docs | Agent Frameworks | Coding CLIs |
| --- | --- | --- | --- | --- |
| **Ready-to-use workflows** | 20 built-in | None | Build from scratch | None |
| **Multi-agent teams** | 2–6 agents per workflow | None | Yes | No |
| **MCP integration** | 49 native tools | None | No | No |
| **Auto-triggering skills** | 26 skills, natural language | None | None | None |
| **Socratic discovery** | Questions before execution | None | None | None |
| **Portable security hooks** | PreToolUse + PostToolUse | None | No | No |

---

## Installation Options

`pip install attune-ai` works out of the box — the CLI, all
workflows, the MCP server, RAG, cross-session memory (the Redis /
Agent Memory Server client is a core dependency as of 9.7.0), and
the Agent SDK. Memory features activate when a Redis Stack server
is reachable and degrade with guidance when not. Add extras only
for the surfaces you use:

| You want | Install |
| -------- | ------- |
| Everything most users need, incl. Redis memory | `pip install attune-ai` |
| Claude API mode + optional LangChain/LangGraph interop adapters | `pip install 'attune-ai[developer]'` |
| The ops dashboard (`attune ops`) | `pip install 'attune-ai[ops]'` |
| Help authoring (generate / maintain `.help/` templates) | `pip install 'attune-ai[author]'` |

(`[redis]` remains as an empty backward-compat alias.) Extras
combine — for example
`pip install 'attune-ai[developer,ops]'`. Keep the quotes:
zsh and bash treat square brackets as glob characters.

Contributing? Clone and install the dev toolchain instead:

```bash
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

The `[rag]` extra is a **no-op alias** kept for backward
compatibility — `attune-rag` is now a core dependency included in
every install.

---

## Platform Support

| Platform | Support |
| -------- | ------- |
| macOS | Full |
| Linux | Full |
| Windows via WSL2 | Full |
| Windows native + Git Bash | Supported (Bash tool, POSIX-ish syntax) |
| Windows native + PowerShell tool | Limited — security validation fails closed |

Notes for native Windows:

- Claude Code supports native Windows (10 1809+). Installing
  [Git for Windows](https://gitforwindows.org/) enables the Bash
  tool; without it, the PowerShell tool is used (opt-in via
  `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`).
- Under PowerShell, the security-validation hook applies a strict
  command allowlist and **fails closed**: commands it does not
  recognize are blocked rather than silently passed. Use Git Bash
  or WSL2 for the full experience.
- OS-level sandboxing is available on macOS/Linux/WSL2 only, not
  native Windows.

### Redis on Windows

Redis has no native Windows build. Docker is the recommended path:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Without a reachable Redis, cross-session memory degrades gracefully
to the local file backend —
`attune.memory.session_stash.backend_status()` reports
`fallback: true` so the degradation is visible, and no errors are
spammed to the session.

---

## API Mode

API mode is what the `attune` CLI and the MCP tools run on. **It is not
required to use Attune** — the Claude Code plugin runs on your
subscription and needs none of this (see
[What this costs](#what-this-costs)). Set these up only if you want the
CLI or MCP surfaces:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."     # Required *for API mode*
export REDIS_URL="redis://localhost:6379"  # Optional
```

The key must belong to an org with pay-as-you-go API credit. A Claude
Pro/Max subscription does not grant it — without credit the calls
return `credit balance is too low`.

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

One-flag cheap mode for pattern-matching workflows (forces every
inherit-default subagent onto Haiku; security/architect/plan/quality
keywords still get their pinned model):

```bash
attune workflow run bug-predict --cheap     # Haiku-default subagents
attune workflow run refactor-plan --cheap
```

See your spend live on the dashboard (`attune ops` → home) — today / 7-day
/ MTD / 30-day tiles fed from the Anthropic admin cost-report API.

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

## Privacy & Telemetry

Attune AI keeps usage data local-first. An **opt-in, anonymous usage
ping** is available to help the project understand which workflows
people actually use — it is **OFF by default** and sends nothing
unless you explicitly turn it on.

When enabled, each ping carries exactly this, and nothing more:

- the package (`attune-ai`) and its version
- the workflow name you ran (e.g. `workflow.security_audit`)
- your OS (`darwin` / `linux` / `windows`) and Python version
  (e.g. `3.12`)
- a rotating, anonymous install id (a random UUID you can reset)
- a timestamp

It **never** sends paths, code, prompts, arguments, filenames,
project names, cost, tokens, or model data — the payload is frozen in
source and guarded by a regression test. Transport is fire-and-forget
with a short timeout, so it can never block, slow, or crash the CLI,
and the collection endpoint stores no IP address and no request
headers.

```bash
attune telemetry status     # show exactly what would be sent
attune telemetry enable     # opt in (mints an anonymous install id)
attune telemetry disable    # opt out
```

`DO_NOT_TRACK=1` and `ATTUNE_USAGE_PING=0` force it off regardless of
config; `ATTUNE_USAGE_PING=1` forces it on. Full payload disclosure is
in [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md).

---

## Session continuity & cross-session memory

Lightweight hook surfaces keep long Claude Code sessions
oriented and recoverable — and carry what you learned into the
next one. All are opt-in via plugin install and silent until
they have something to say.

| Surface | Event | When it fires |
|---------|-------|---------------|
| `spec_orient.py` | `SessionStart` | On `startup` / `resume` / `clear`, prints up to 3 in-flight spec slugs. On `compact`, prints the most-recent spec body so the model keeps the spec in fresh post-compact context. |
| `compact_warning.py` | `Stop` | Once per session when transcript size crosses ~70% of the context window. Emits a copy-pasteable resume prompt and recommends starting a fresh session. |
| `/handoff` | slash command | On demand. Prints the same resume prompt as the auto-warning AND appends it to `~/.attune/last-handoff.md` so you can recover it later. |
| `session_stash.py` | `Stop` | Once per session past a utilization floor: extracts durable findings (decisions, bugs, references) and stashes them to the memory store (file by default, Redis AMS when installed). |
| `session_recall.py` | `SessionStart` | Surfaces the most recent cross-session findings for this project; warns when the configured memory backend is unreachable rather than degrading silently. |
| `lesson_recall.py` | `UserPromptSubmit` | Surfaces up to 3 relevant lessons from the project's lessons corpus when a prompt matches a known trap moment; silent otherwise, once per (session, lesson). |
| `jit_recall.py` | `PreToolUse` | Surfaces the curated rule governing a tool call at the decision point (e.g. release tagging), once per session. |
| `/recall <topic>` | slash command | On demand. Searches session findings and the lessons corpus, labels results by source, and names the answering backend. |

### Tunable defaults

- `ATTUNE_AI_COMPACT_WARNING_THRESHOLD` (default `0.70`) — fraction of context window before the warning fires.
- `ATTUNE_AI_CHARS_PER_TOKEN` (default `4.0`) — utilization estimator's chars-to-tokens factor.
- `ATTUNE_AI_CONTEXT_WINDOW_TOKENS` (default `200000`) — context window assumed by the estimator.
- `ATTUNE_AI_WORKSPACE_ROOTS` (`os.pathsep`-separated paths: `:` on POSIX, `;` on Windows) — override the workspace roots scanned for `specs/`.
- `ATTUNE_AI_SENTINEL_DIR` (default `~/.attune`) — directory for the once-per-session warning sentinel.
- `ATTUNE_LESSON_RECALL` / `ATTUNE_JIT_RECALL` (set `0` to disable) — off-switches for the prompt-time and tool-call recall hooks.
- `ATTUNE_LESSON_RECALL_FLOOR` (default `8.0`) — minimum retrieval score before a lesson surfaces at prompt time.

The transcript-size proxy is crude but monotonic: the warning
fires when the user's total content characters cross the
threshold once. If your real auto-compact triggers consistently
earlier or later than the warning, drop the threshold to `0.65`
or raise it to `0.75`.

---

## Migration

`attune-help` and `attune-author` now ship from the
`Smart-AI-Memory/attune-ai` marketplace alongside `attune-ai` itself.
The separate `Smart-AI-Memory/attune-docs` marketplace is retired.

New users:

```text
/plugin marketplace add Smart-AI-Memory/attune-ai
/plugin install attune-help@attune-ai
/plugin install attune-author@attune-ai
```

If you previously installed either from `attune-docs`:

1. ```text
   /plugin uninstall attune-help@attune-docs
   /plugin uninstall attune-author@attune-docs
   ```

2. ```text
   /plugin marketplace add Smart-AI-Memory/attune-ai
   /plugin install attune-help@attune-ai
   /plugin install attune-author@attune-ai
   ```

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
