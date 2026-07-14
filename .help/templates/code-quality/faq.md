---
type: faq
name: code-quality-faq
feature: code-quality
depth: faq
generated_at: 2026-07-14T15:58:49.270997+00:00
source_hash: 1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679
status: generated
---

# Code Quality FAQ

## What is code quality review?

A one-call code review: the `CodeReviewWorkflow` delegates
to four specialized SDK subagents — security, quality, performance,
architecture — and synthesizes their findings into a single report
with an overall 0–100 health score, per-domain findings, and a
prioritized list of next steps.

## When should I run a code quality review?

Before opening pull requests, after large refactors, when
inheriting unfamiliar code, or any time you want a health read on a
codebase. It is the everyday breadth review.

## How do I start a review?

Four ways: the `/code-quality` skill in a Claude Code
conversation, the CLI (`attune workflow run code-review --path
src/` — note the slug), the `code_review` MCP tool, or the Python
API (`await CodeReviewWorkflow().execute(path="src/")`).

## What's the difference between quick, standard, and deep reviews?

`depth` sets the agent-turn budget — `quick` 10, `standard`
20 (the default), `deep` 40. All four passes run at every depth;
a bigger budget means more thorough passes, not different ones.
(One nuance: the `/code-quality` *skill* routes a "deep" request
to the separate deep-review workflow.)

## What do the health scores mean?

The Summary section opens with an overall 0–100 health
score synthesized from the four passes — higher is healthier. It
is an LLM judgment, not a measurement: treat it as a trend signal
and read the per-domain findings for the substance.

## Can I fix issues automatically?

The workflow reports; it never modifies files. In a Claude
Code session, ask the agent to apply specific fixes from the
report — mechanical ones (unused imports, style) are quick wins;
structural findings need manual judgment.

## How do I focus on specific types of issues?

There's no `focus` parameter — all four passes always run.
Narrow the `path`, use deep-review (which has `focus`), or drill
into the returned report conversationally ("just show me the
security findings").

## What if I want to compare different parts of my code?

Run the workflow once per path (e.g. `src/auth/` then
`src/api/`) and compare the health scores and finding counts —
the report is per-run, one path at a time.

## Where can I learn more?

Say "tell me more" (the coach skill goes progressively
deeper: concept → procedural → reference), or open this feature's
quickstart and task guides.

## Why does `attune workflow run code-quality` say "unknown workflow"?

The registered slug is `code-review`. The `code-quality`
name is the skill / help topic; run the workflow as
`attune workflow run code-review`.

## What's the difference between code-quality and deep-review?

Code-quality runs four passes — security, quality,
performance, architecture — and has no narrowing knob.
Deep-review swaps performance and architecture for a test-gap
pass and lets you narrow with `focus`. Use code-quality for the
everyday maintainability read, deep-review when test coverage is
the concern.

## How do I run only the security pass?

You can't — code-quality has no `focus`. Either narrow the
`path`, or use deep-review with `focus=["security"]`.

## Which calls are async?

`execute` is the only public method and it is a coroutine
— `await` it or use `asyncio.run`.

## Does a clean review mean the code is good?

No. Findings are LLM predictions, not proofs, and a clean
pass is not a guarantee — treat the review as one input.
