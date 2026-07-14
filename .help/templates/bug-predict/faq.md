---
type: faq
name: bug-predict-faq
feature: bug-predict
depth: faq
generated_at: 2026-07-14T15:58:47.681115+00:00
source_hash: 3c6441a981e2df351b5043ad522cb27f0fed3c7907db1157a7f65632cc74504d
status: generated
---

# Bug Predict FAQ

## Does bug-predict fix the bugs it finds?

No. It predicts and prioritizes likely-bug hotspots and
suggests prevention strategies; applying fixes is a separate
step you (or a refactor workflow) take.

## Is there an `attune bug-predict` command?

No dedicated subcommand — run it as
`attune workflow run bug-predict`, or use the `/bug-predict`
skill or the `bug_predict` MCP tool.

## Which calls are async?

`execute` is the only public method and it is a
coroutine — `await` it or use `asyncio.run`.

## What does `depth` change?

The agent-turn budget (quick 10, standard 20, deep 40)
and the per-run cost cap — deeper scans read more and cost
more.

## Why didn't my `./attune.config.yml` `bug_predict` settings change the results?

Those settings configure the internal static pattern
helpers, not the live SDK subagents. Steer the scan with
`system_prompt_suffix` or a deeper `depth` instead.
