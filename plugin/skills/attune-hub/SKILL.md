---
name: attune-hub
description: "Developer workflow hub — routes to the right skill based on what you need. Triggers on: attune, what can attune do, what can you do, capabilities, where do I start, get started."
argument-hint: "<what you need help with>"
---

# Attune Hub

**IMPORTANT: Start your response by telling the user:**

> **Attune Hub** — Your starting point — discovers what you need and routes you to the right skill.

## Scoping

If no argument is provided, use `AskUserQuestion`:

```yaml
question: "What are you trying to accomplish?"
header: "attune-ai"
options:
  - label: "Run a workflow"
    description: "Security audit, code review, test gen, perf, release prep"
  - label: "Manage memory"
    description: "Store, retrieve, search, or forget patterns"
  - label: "Configure settings"
    description: "Check setup, update attune-ai, view telemetry"
  - label: "Learn what attune-ai does"
    description: "Overview of capabilities and skills"
```

## Execution

Based on the user's answer or arguments, describe the
intent so Claude matches the right skill:

| Input | Describe to Claude |
| ----- | ------------------ |
| "Run a workflow" or `security` | "Run a security audit on the code" |
| "Run a workflow" or `review` | "Review the code for quality issues" |
| "Run a workflow" or `tests` | "Generate tests for uncovered code" |
| "Run a workflow" or `perf` | "Analyze code for performance issues" |
| "Run a workflow" or `release` | "Prepare for a release" |
| "Run a workflow" or `bugs` | "Predict likely bug locations" |
| "Manage memory" or `memory` | "Store or retrieve from memory" |
| "Configure settings" or `setup` | Run `attune doctor` and `attune auth` |
| "Configure settings" or `update` | Run `pip install --upgrade attune-ai` |

## Natural Language Routing

| Pattern | Route to |
| ------- | -------- |
| "security", "vulnerability", "audit" | security-audit skill |
| "review", "quality", "code review" | code-quality skill |
| "test", "generate tests", "coverage" | smart-test skill |
| "performance", "bottleneck", "optimize" | workflow-orchestration skill |
| "release", "publish", "ship" | release-prep skill |
| "bug", "predict", "risk" | bug-predict skill |
| "run all audits", "full sweep", "what should I fix" | discovery-sweep skill |
| "memory", "store", "remember" | memory-and-context skill |
| "docs", "documentation" | doc-gen skill |
| "plan", "feature", "architecture" | planning skill |
| "refactor", "tech debt", "simplify" | refactor-plan skill |
| "spec", "brainstorm", "plan and execute" | spec skill |
| "scope this", "ask me everything at once", "discovery form" | elicit skill |

When the scoping turn has **2–4 independent, non-branching, genuinely
open dimensions** (e.g. goal + scope + focus), gather them as one form
via the `elicit` skill instead of sequential buttons — **preferring the
rich widget surface** (`elicitation_render_widget` → `show_widget`, so
free-text dimensions are textareas and concerns are multi-select
checkboxes), with the AskUserQuestion mapping as the fallback (see the
`elicit` skill's "Choosing a surface"). Stay single-question when only
one dimension is unknown or answers branch.

## Single-referent resolution

Before acting on a terse confirmation (`go`, `do it`, `y`, `1`),
make sure exactly **one** referent is obvious from the prior turn —
that you can fill in "go [doing **X**]" with a single, unambiguous X.

- If the prior turn left **multiple** proposals on the table, the
  referent is unresolved — ask which one before executing, don't
  guess the most likely.
- **Restate the referent as you act** ("Running the security audit
  on `src/` —") so the user can catch a mismatch immediately.

This is advisory guidance for the broader conversation; the one
*enforceable* foothold is the `AskUserQuestion` one-question-per-turn
rule (a single turn can't bundle multiple ambiguous decisions). See
`docs/specs/collaboration-gates/` (R9/R10).

## Skills Reference

| Skill | Triggers |
| ----- | -------- |
| security-audit | security, vulnerability, audit, scan |
| code-quality | review, quality, bugs, code smell |
| bug-predict | predict bugs, risky code, what might break |
| discovery-sweep | run all audits, full sweep, what should I fix, triage findings |
| doc-gen | generate docs, documentation, README |
| smart-test | generate tests, test gaps, coverage |
| fix | attune fix, scoped fix, fix with receipt |
| fix-test | fix test, broken test, debug test |
| planning | plan, feature, architecture, TDD |
| refactor-plan | refactor, tech debt, simplify |
| release-prep | release, publish, deploy |
| memory-and-context | memory, store, retrieve, empathy |
| workflow-orchestration | workflow, run, analyze |
| spec | spec-driven dev, brainstorm and execute |
| rag-code-gen | grounded code, cite sources, verify against attune (needs `[rag]` extra) |
| coach | coach, learn, explain, tell me more, deeper |
| recall | recall, remember, what did I learn, prior session, past findings |
| verify | verify docs, fact-check, did the model hallucinate, check generated content |
| bulk | batch, bulk process, 50% savings, overnight analysis |
| catalog | catalog, list capabilities, browse, what can attune do |
| personal-memory | remember this for me, capture this decision, save to personal memory, my saved topics, forget topic |
| image-analysis | analyze this image, look at this screenshot, what's in this diagram, read this mockup |
| elicit | scope this, discovery form, ask me everything at once, multi-select question |
| author-feature | author a feature page, single-source doc, new feature master, draft docs without an api |
| roundtable | roundtable, convene the table, ask the table, what do the other models think |
| cross-review | cross review, second opinion, ask another model to review, pre-merge check from codex |
| docs-outbox | docs outbox, outbox sweep, pending docs, approve digest |
| recap | recap, end of session review, session retro, wrap up the session |

## MCP Server Not Running

If the MCP server is not responding, run:

```bash
pip install attune-ai
attune doctor
```
