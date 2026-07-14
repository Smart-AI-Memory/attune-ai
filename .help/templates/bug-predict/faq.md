---
type: faq
name: bug-predict-faq
feature: bug-predict
depth: faq
generated_at: 2026-07-14T22:05:25.786099+00:00
source_hash: 6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208
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
