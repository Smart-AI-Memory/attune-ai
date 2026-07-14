---
description: "We wanted to claim our AI memory saves 8% on costs. We built the benchmark to prove it — and measured +28% instead. Published the table anyway. Here's why that's the feature."
---

# We Benchmarked Our Own Marketing Claim. It Lost.

**Date:** July 6, 2026
**Author:** Patrick Roebuck

---

## TL;DR

I wanted to write "our memory features lower your Anthropic costs by
8%" in a LinkedIn post. Before publishing, we built an A/B benchmark
to back the number: same tasks, real headless Claude Code sessions,
memory suite toggled on and off.

The result: on that task set, memory ON cost **28% more** per task,
not less. The table is committed to our repo, next to the harness
that produced it, next to a bug the run itself flushed out.

We still think the memory suite is the best thing we've built. This
post is about why publishing the losing number makes that claim
stronger, not weaker.

## The claim I almost shipped

Every AI-memory pitch eventually writes the same sentence: "saves you
N% on tokens." I had the sentence half-drafted. The N was 8.

The problem: nothing we had measured produced that number. What we
HAD measured was per-recall economics — our recall injects a
budget-capped ~3,000-token slice instead of a 300K-token store (67x
fewer tokens per recall, precision-at-3 of 96% on a frozen
benchmark). Real numbers, but they answer "what does one recall
cost?" — not "what does memory do to your bill?"

Converting one into the other without measuring is how marketing
debt gets created. So we measured.

## The experiment

`benchmarks/session_savings.py` — about 400 lines, in the repo:

- 5 read-only analysis tasks against our own codebase
- each task runs twice via headless `claude -p` (read-only tools,
  turn-capped)
- ONE difference between arms: the memory suite's injection hooks,
  toggled by their env kill-switches
- compare medians: uncached input tokens, cache reads, output,
  turns, wall-clock, dollars

Total spend for the run: $6.59. Ten sessions, ten clean results.

## The result

| Metric (median/task) | Memory on | Memory off | Delta |
|---|--:|--:|--:|
| Uncached input tokens | 56,552 | 51,921 | +8.9% |
| Turns | 6 | 4 | +50% |
| Wall-clock | 52.0s | 38.6s | +34.8% |
| Cost | $0.654 | $0.510 | **+28.4%** |

The 8% I wanted to claim as savings showed up as +8.9% OVERHEAD.
Every metric pointed the same direction.

## Why (and what the number actually means)

The harness docstring predicted this outcome before the first run:

> Savings only appear on tasks where recall actually prevents
> re-derivation. A task set that never hits a trap moment will show
> memory as pure overhead — that is a true and useful result, not a
> benchmark failure.

These were one-shot analysis tasks. No prior session to resume, no
known trap for a recalled lesson to prevent. On that profile, memory
injects context and gets nothing back — and the memory-on sessions
explored more (6 vs 4 turns), which may mean better answers or just
more expensive ones; we didn't score quality. n=1 per task per arm:
directional, not gospel.

Where memory is DESIGNED to pay — "we solved this exact failure two
weeks ago, don't repeat the dead end" — is exactly what this task
set doesn't exercise. That benchmark is next, and until it exists,
we don't get to claim a savings percentage. Neither does anyone
else, by the way: if a memory product quotes you a % without
publishing the task profile, ask which profile.

## The bonus bug

The first run returned all zeros and claimed 10/10 success. Turns
out the CLI can emit `subtype: "success"` WITH `is_error: true`
(an auth failure), and our parser trusted the first field. Ten auth
failures aggregated into a beautiful all-zero "result."

A benchmark that can silently count failures as data is worse than
no benchmark. The fix and its regression test shipped the same
morning. That's the second thing the run paid for.

## What we can honestly say

- Recall injects <=3K tokens from a 300K+ token store: **67x fewer
  tokens per recall**, and the cap holds as memory grows.
- The right lesson is in the top-3 results **96%** of the time
  (100% on high-severity traps).
- On one-shot tasks, the suite costs ~9% extra uncached input.
  Turn it down for that profile; that's why the kill-switches exist.
- The session-level savings claim is UNPROVEN, and we published the
  benchmark that will prove or kill it.

## Why this is the lead

"Trust our memory system" is a claim every vendor makes. "Here's the
benchmark where our marketing lost, in the repo, re-runnable" is a
claim almost nobody makes — and it's the only kind that makes the
67x and the 96% believable.

Storage was never the hard part of AI memory. Truth is. That
includes truth in the marketing.

---

*The harness, the raw JSON, and the unflattering table:
`benchmarks/session_savings*` in the attune-ai repo (PR #1276).
Run it on your own setup — and if your task set makes our memory
suite look good, publish that too. We'll take it.*
