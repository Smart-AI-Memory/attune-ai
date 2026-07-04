---
title: "What One Long AI Coding Session Actually Costs"
date: "2026-07-04"
author: "Patrick Roebuck"
excerpt: "I priced a full afternoon Claude Code session from its transcript: 14.1 million tokens processed, 94% of it the model re-reading its own history. Prompt caching cut the bill 5x — and the real lever is carrying less in the first place."
tags: ["token economics", "prompt caching", "Claude Code", "memory", "Redis"]
published: true
---

# What One Long AI Coding Session Actually Costs

I just ran a long Claude Code session in one of my repos. One afternoon, 135 assistant messages, and a conversation that ended at about 138,000 tokens of context. When I added up the token counts from the transcript, the totals surprised me — not the output, but the re-reading.

Here is what the model processed, straight from the transcript:

| What | Tokens |
|---|---|
| Fresh input (new text the model had never seen) | 89,160 |
| Output (everything the model wrote) | 124,901 |
| Cache writes (context stored for reuse) | 622,609 |
| Cache reads (context re-read from cache) | 13,266,884 |
| **Total processed** | **~14.1 million** |

Read that last big number again. About 94% of everything the model processed was the session re-reading its own history.

That sounds wasteful until you know how these models work. The API is stateless — it remembers nothing between messages. Every time the model responds, the entire conversation gets sent back through it: every file it read, every command it ran, every earlier answer. My session averaged about 98,000 tokens of history per message, times 135 messages. That's where the 13.3 million comes from. It's not a bug. It's the price of a session that stays coherent for a whole afternoon.

Prompt caching is what makes this survivable. Anthropic charges roughly one tenth the normal input price to re-read tokens it already has cached, and 1.25 times the normal price to write them into the cache the first time. So the session pays full freight once per chunk of context, then re-reads it at a steep discount hundreds of times.

My session ran on a Claude Code subscription, so none of this hit a per-token bill. But the transcript lets me price it as if it had run on the API. The session used Claude Fable 5, which lists at $10 per million input tokens and $50 per million output tokens.

**With caching, the session would have cost about $28.19:**

- Cache reads: $13.27
- Cache writes: $7.78
- Output: $6.25
- Fresh input: $0.89

**Without caching — every one of those 14.0 million input tokens at full price — it would have cost about $146.03.**

So caching cut the input cost roughly 6x, and the whole session about 5x. That's a real saving. It's also not the whole story, and I want to be straight about it: even with caching, one afternoon of serious agentic work would cost about $28 on the API. The biggest single line item is still the cache reads — the discounted re-reading of context is cheap per token and expensive in bulk, because there's so much of it.

This is why I care about memory architecture, and it's the thesis behind what I'm building at Smart AI Memory. My sessions run on a two-layer memory system: long-term memory is git-tracked markdown, and a hook hydrates it into a Redis index at session start. The small, stable orientation the session always needs gets front-loaded — exactly the kind of reusable text that caches well, written once at 1.25x and re-read all afternoon at 0.1x. Everything else stays OUT of the conversation until it's needed: the model queries the warm Redis index on demand — sub-millisecond lookups that return a few hundred tokens of exactly-relevant context instead of whole files re-read into history. Persistent memory decides *what* the model should carry. Redis-served recall keeps that carry small. Caching decides what carrying the rest *costs*. Get all three right and you can run a session that stays sharp for hours instead of starting over every twenty minutes — because the cheapest token in that 94% is the one you never carried at all.

The takeaway isn't "caching makes AI cheap." It's that long, coherent sessions have a specific economic shape: tiny amounts of new text, modest output, and a huge multiple of re-read context. Caching turns that multiple from ruinous into workable. If you're building agents — or budgeting for a team that uses them — that 94% is the number to plan around.

---
