---
name: refactor-plan
source: content/features/refactor-plan.md
tags:
- refactor
- tech-debt
- complexity
type: faq
---

# Refactor Plan FAQ

## Does refactor-plan change my code?

No. It analyzes and produces a prioritized roadmap; its
subagents only read the codebase. To apply a cleanup, use
simplify-code.

## What's the difference between refactor-plan and code-quality?

Refactor-plan ranks tech debt and sequences the work;
code-quality reports health across security, quality,
performance, and architecture. Use refactor-plan to plan a
cleanup, code-quality for a broad review.

## How do I make a run cheaper?

Narrow the `path` and use a shallower `depth` (`quick`
uses the smallest agent-turn budget).

## Which calls are async?

`execute` is the only public method and it is a coroutine
— `await` it or use `asyncio.run`.

## Does a clean roadmap mean there's no debt?

No. Findings are LLM predictions, not proofs — treat the
roadmap as one informed input.
