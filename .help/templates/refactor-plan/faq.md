---
type: faq
name: refactor-plan-faq
feature: refactor-plan
depth: faq
generated_at: 2026-07-14T15:58:58.399264+00:00
source_hash: 198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb
status: generated
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
