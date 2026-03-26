# Spec-Driven Development with Claude Code: From Idea to Implementation in One Command

*How Attune AI's `/spec` command turns natural language ideas
into structured, reviewable, executable development plans
inside Claude Code.*

---

## The Problem with Ad-Hoc AI Coding

Most developers use AI coding assistants the same way:
describe what you want, get code back, manually verify it
works. This is fine for small changes, but it breaks down
for anything multi-file or multi-step.

The failure mode is predictable:

1. You describe a feature
2. The AI writes code across 5 files
3. Something is subtly wrong in file 3
4. You spend 20 minutes debugging AI-generated code you
   didn't fully review before it was written

The root cause: **there's no review step between "idea"
and "execution."**

---

## Spec-Driven Development

Attune AI v5.3 introduces `/spec` — a command that adds
a structured lifecycle to Claude Code sessions:

```
Brainstorm -> Plan -> Review -> Execute (with approval gates)
```

Each stage is explicit. You approve the plan before any code
is written. You approve each task after it's implemented.
And if you step away, the spec remembers where you left off.

### Quick Start

Install attune-ai and type one command:

```bash
pip install 'attune-ai[developer]'
attune setup
```

Then in Claude Code:

```
/spec add a rate limiter to the API endpoints
```

---

## Stage 1: Brainstorm

`/spec` starts by asking questions, not writing code.
This follows Anthropic's recommended pattern of using
Claude to scope work before executing it.

```
What problem are you solving?
> API endpoints have no rate limiting. A single client
> can overwhelm the server.

What does success look like?
> Per-client rate limits with configurable thresholds,
> 429 responses when exceeded, Redis-backed for
> distributed deployments.
```

The brainstorm stage captures **context**, **problem**,
**goals**, and **end state** — the same structure you'd
use in a design document, but gathered conversationally.

---

## Stage 2: Plan

From the brainstorm output, `/spec` decomposes the work
into discrete tasks using XML-structured specifications:

```xml
<task id="1" name="rate-limiter-core">
  <objective>
    Create a sliding-window rate limiter with Redis backend
  </objective>
  <files-to-create>
    <file path="src/api/rate_limiter.py">
      SlidingWindowLimiter class with check() and reset()
    </file>
  </files-to-create>
  <validation>
    <check>Unit tests pass for window expiry</check>
    <check>Redis connection failure degrades gracefully</check>
  </validation>
  <risks>
    <risk severity="medium">
      Clock skew in distributed Redis deployments
    </risk>
  </risks>
</task>
```

Each task specifies:

- **What to build** (objective)
- **Which files to create or modify** (with before/after
  context for modifications)
- **How to verify it works** (validation checks)
- **What could go wrong** (severity-tagged risks)

The plan is saved to `.claude/plans/` as a markdown file
with embedded XML tasks — human-readable and version
controllable.

---

## Stage 3: Review

Before any code is written, you review the full plan:

```
| Status | ID | Name              | Objective                    |
|--------|----|-------------------|------------------------------|
| ...    | 1  | rate-limiter-core | Sliding-window rate limiter  |
| ...    | 2  | middleware-hook   | FastAPI middleware integration|
| ...    | 3  | redis-backend     | Redis adapter for distributed|
| ...    | 4  | config-surface    | Environment variable config  |

Approve this plan? [Approve / Edit / Reject]
```

You can approve individual tasks, edit their scope, or
reject and re-brainstorm. Nothing executes until you say so.

---

## Stage 4: Execute with Approval Gates

Execution proceeds task by task. After each task:

1. The code is implemented
2. Quality gates run automatically (tests, linting,
   security scan via Attune's pipeline orchestrator)
3. Results are severity-gated:
   - **HIGH** (score < 50): must fix or explicitly
     acknowledge risk
   - **MEDIUM/LOW**: approve, redo, or enable auto-run
     for remaining tasks

```
Task 1/4: rate-limiter-core [done]
Task 2/4: middleware-hook   [>>>]

Quality gate: 87/100 (MEDIUM)
  - 1 ruff warning (unused import)
  - Tests: 4/4 passing

[Approve] [Redo] [Auto-run remaining]
```

If you choose "Auto-run remaining," the spec executes
the rest without pausing — but still enforces quality
gates and blocks on HIGH severity findings.

---

## Resume Support

State is persisted as an HTML comment inside the plan file:

```html
<!-- spec-state: {"completed":["1","2"],"current":"3"} -->
```

If you close Claude Code and come back later, `/spec`
detects the incomplete plan and offers to resume:

```
/spec resume
```

This works because the state lives in the plan file itself
— no external database, no session cookies, just a file
in your repo.

---

## How It Works Under the Hood

The `/spec` command orchestrates four components:

| Component | Role |
|-----------|------|
| **Brainstorm** | Socratic discovery via `AskUserQuestion` |
| **Decomposer** | XML task generation from approach description |
| **Presenter** | Markdown tables, progress bars, task detail views |
| **Runner** | Task execution with `PipelineOrchestrator` quality gates |

State management uses a `SpecState` dataclass serialized
to JSON inside an HTML comment. The comment is invisible
in rendered markdown and ignored by the XML task parser,
so the plan file stays clean and readable.

Quality gates are powered by Attune's pipeline orchestrator,
which runs the same checks available through `/code-quality`
and `/security` — ruff, bandit, and test execution.

---

## Design Decisions

**Why XML for task specs?** Claude's structured output
works well with XML. The `<task>`, `<files-to-create>`,
`<validation>`, and `<risks>` elements map directly to
how developers think about work decomposition. XML also
survives markdown rendering without corruption.

**Why persist state in the plan file?** External state
stores create sync problems. Embedding state in the plan
means `git diff` shows exactly what happened, the plan is
portable across machines, and there's no cleanup needed.

**Why severity-gated approval?** Unconditional auto-run
is dangerous — a security finding in task 3 shouldn't be
silently approved because you enabled auto-run after
task 1. The severity gate ensures high-risk findings
always require human judgment.

---

## Try It

```bash
pip install 'attune-ai[developer]'
attune setup
```

Then in Claude Code:

```
/spec <describe what you want to build>
```

The full source is at
[github.com/Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai).
Apache 2.0 licensed.
