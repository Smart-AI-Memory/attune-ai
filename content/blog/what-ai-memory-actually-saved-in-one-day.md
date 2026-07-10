---
title: "What an AI Memory System Actually Saved in One Day"
date: "2026-07-05"
author: "Patrick Roebuck"
excerpt: "I measured a full day of Claude Code sessions from their transcripts: 11 sessions, 694 million tokens of context re-read. A memory architecture change cut that by 8% — but the real savings never showed up in the token counts at all."
tags: ["token economics", "memory", "prompt caching", "Claude Code", "Redis"]
published: true
---
# What an AI Memory System Actually Saved in One Day

Yesterday I priced a single long Claude Code session from its
transcript and found that 94% of everything the model processed was
re-reading its own history. Today I want to answer the follow-up
question: we ship a cross-session memory suite in attune-ai — what
did it actually save us?

I picked a good day to measure. July 4th was a three-release day in
the attune-ai repo: a bug-fix release of a sibling package, a minor
release that made our Redis memory client a core dependency, and a
docs patch. Eleven Claude Code sessions, 2,262 assistant messages.
Here's the day, straight from the transcripts:

| What | Tokens |
|---|---|
| Fresh input (text the model had never seen) | 807,564 |
| Output (everything the model wrote) | 1,985,207 |
| Cache writes (context stored for reuse) | 17,263,230 |
| Cache reads (context re-read from cache) | 693,637,455 |
| **Total processed** | **~713 million** |

Same shape as the single session, scaled up: 97% of the day was the
model re-reading context it already had. Prompt caching makes that
affordable, but 694 million tokens of re-reading is the number any
savings claim has to be measured against.

## The multiplier that makes memory architecture matter

Here's the mechanic that took me embarrassingly long to internalize:
anything that sits in your session's baseline context — rules files,
instructions, memory indexes — is re-read on *every single turn*.
Not once per session. Every turn.

So a context file that costs 26,000 tokens doesn't cost 26,000
tokens. Across a 200-turn session it costs 5.2 million cache reads.
Across my 2,262-turn day, a 26,000-token baseline item costs about
59 million.

That's exactly the size of the change we shipped this week. Our
engineering-rules corpus had grown to 116KB of always-loaded
context. We cut it over to just-in-time recall: a 13KB index stays
resident, and the full rule bodies are retrieved only at the moment
a tool call or prompt actually needs them — a few hundred tokens per
hit, maybe a dozen hits a day.

Measured against the transcripts, that one change avoided roughly
**59 million cache reads — 8% of the entire day's context
throughput**. The same pattern covers our project memory: a 412KB
corpus of decisions and findings never enters context wholesale.
A 17KB index loads, Redis serves a few hundred exactly-relevant
tokens on demand, and our benchmarks put query-first recall at about
6× cheaper than the grep-and-read alternative.

## The savings that never show up in token counts

Here's the honest part, and the part I find more interesting: the
8% was saved by the recall *architecture*. The memory *loop* — the
part that stashes findings when a session ends and recalls them when
the next one starts — saved almost nothing in tokens. It saved
something better.

Four concrete moments from the same day, all reconstructable from
the transcripts:

**A silent API failure, avoided twice.** Approving a PyPI publish
gate through the GitHub API requires a typed array parameter; the
obvious string form silently does nothing and leaves your release
stuck at "waiting" with no error. We learned that the hard way weeks
ago and it became a memory entry. Yesterday it was retrieved
automatically at the exact tool call it governs — at both publish
gates. That's a known 30-minute debug cycle, avoided twice, by a few
hundred tokens of recall.

**Three tags, all from verified commits.** A past release shipped
from the wrong ref, and the lesson — verify the version and
changelog are actually *in* the commit you're about to tag — now
fires at tag time. It ran before all three of yesterday's tags.

**A mid-task takeover with zero re-derivation.** I stopped one
session partway through a release and another picked it up. The
incoming session started with the full task chain — what was merged,
what was pending, what the acceptance criteria were — from
session-start recall, instead of spending its first twenty minutes
reconstructing state.

**A release race, prevented.** The incoming session also knew from
memory that a parallel session existed and had been working the same
repo — so instead of duplicating the release, it stood down and
monitored. Two agents racing the same `git checkout` and PyPI
publish is a genuinely expensive mess to clean up.

## What it adds up to

On a subscription plan none of this shows up on a bill — the token
savings buy context headroom and speed, not dollars. Priced at the
API rates I used in yesterday's post, the day would have run about
a thousand dollars, and the architecture change trimmed roughly
sixty of that. Real, but not the headline.

The headline is the second category. The memory loop converted past
failures into a few hundred tokens of exactly-timed context, and
those firings saved over an hour of debugging and one potential
release collision — on a day we shipped three releases.

Measure your memory system both ways. The token math tells you
whether your architecture is honest. The rework math tells you
whether your memory is worth having.
