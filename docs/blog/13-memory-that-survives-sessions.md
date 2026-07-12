---
description: "Long-form product lead: Claude Code forgets everything between sessions. attune-ai's memory suite makes what you learned durable — files as truth, Redis as speed, a 3K-token budget cap as the contract — with every claim tied to a published benchmark."
---

# Your AI Assistant Forgets Everything. Here's the Fix — With the Receipts.

**Date:** July 6, 2026
**Author:** Patrick Roebuck

---

## TL;DR

Every Claude Code session starts from zero: yesterday's debugging
session, the dead end you burned an hour on, the decision your team
already litigated — gone. The obvious fix (stuff history into
context) doesn't scale: our own memory corpus is past 300K tokens.

attune-ai's memory suite makes memory durable AND cheap: git-tracked
files as the source of truth, Redis as the serving layer, and a hard
~3K-token budget on what any moment injects. 67x fewer tokens per
recall than corpus-loading, 96% precision-at-3 on a frozen
benchmark, ~5 MB of Redis at current scale, local-first. Every one
of those numbers has a published, re-runnable benchmark behind it —
including the one where our own marketing hope lost.

## The forgetting tax

You pay it in three currencies:

- **Repeated dead ends.** The trap you debugged two weeks ago is
  re-debugged, because the lesson lived in a session that's gone.
- **Re-derivation.** "How does our release automation work again?"
  gets re-explored from scratch, tokens and minutes each time.
- **Re-litigated decisions.** The AI proposes the approach your team
  already rejected, persuasively, because it never heard the verdict.

The naive fix — load your notes into every prompt — trades the
forgetting tax for a context tax that grows forever. At 300K tokens
of accumulated memory, corpus-loading isn't a strategy, it's a bill.

## The architecture: files are truth, Redis is speed, the cap is the contract

**Files as the store.** Every memory is a markdown file in git —
reviewable, diffable, portable, yours. No vendor database owns what
your team learned. Delete a file, the memory is gone. Multi-machine
sync is a git pull.

**Redis as the serving layer.** A SessionStart hook hydrates the
corpus into Redis (about 5 MB at our current scale of ~875 keys
including the search index). Recall is one warm function call —
sub-millisecond, measured at 0.6ms against 4.6ms for re-reading the
corpus files.

**The budget cap as the contract.** No moment injects more than
~3K tokens, no matter how large the store grows. This is the number
that makes memory scale: your corpus can grow 10x and your
per-session context cost doesn't move. Measured on our dogfood
store: 67x fewer tokens per recall than loading the corpus.

**Local-first, degradable.** No Redis? Everything falls back to the
file backend with clear guidance. Nothing leaves your machine.

## Recall at the trap moment, not in bulk

The suite's sharpest edge is WHEN it recalls. A UserPromptSubmit
hook matches what you're about to do against known traps — the
command shape, the file, the failure pattern — and injects only the
relevant lesson, only then.

On a frozen benchmark built from real trap moments in our own
sessions, the right lesson is in the top 3 results 96% of the time,
and 100% on the high-severity subset. Recall precision is the whole
game: memory that surfaces the wrong lesson is noise with
confidence.

## Memory that can be wrong — and fixed

Two disciplines most memory systems skip:

**Provenance.** We caught our own extractor promoting things a
session merely READ into "findings" — file contents restated as
decisions nobody made. We built a replay harness, measured the
failure class (5% of findings), fixed it, re-measured (0%), and
regression-tested the distinction. Memory that can't tell "I read
it" from "I concluded it" isn't memory, it's contamination.

**One-call correction.** Any record that search can surface, one
tool call can delete — by ID, in seconds. Corrections are part of
the loop, not an admin chore.

## The receipt you didn't expect

This week we also published the benchmark where memory LOSES.

We wanted to claim session-level cost savings. So we built an A/B
harness — same tasks, memory on vs off, real headless sessions —
and measured: on one-shot analysis tasks, memory ON costs 28% MORE
per task. No trap to avoid, no work to resume, nothing for recall
to save. The table is committed to the repo next to the harness.

Why lead a product post with the losing number? Because it's the
only thing that makes the winning numbers credible. The 67x and the
96% come from the same discipline, the same repo, the same
willingness to publish whatever the benchmark says. A savings
percentage will only ever appear in our marketing after the
continuity-task benchmark produces one.

## Try it

```bash
pip install attune-ai
```

Works with plain files out of the box; add Redis when you want the
speed. The benchmarks are in `benchmarks/` — `memory_savings.py`
for the recall economics, `session_savings.py` for the on/off A/B.
Run them on your own corpus. Publish what you find, either way.

Your team is already generating the lessons. The only question is
whether anything remembers them.
