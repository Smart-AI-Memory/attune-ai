---
description: "LinkedIn Article — the 10.6.x multi-LLM release: shared memory across Claude Code/Codex/Antigravity, handoffs that verify instead of trust, cross-provider review, and roundtable-picked features. Canonical source reconstructed 2026-08-02."
---

# LinkedIn Article — Multi-LLM release (agents talk to each other)

*Format: LinkedIn Article. Title: "Your AI coding agents don't talk
to each other. This release makes them." Published 2026-07-28
(pulse slug -olxte). This file became the canonical source on
2026-08-02: the published copy was reconstructed here (the original
had no tracked source), given real paragraphs and code blocks (the
July paste carried hard-wrapped line-per-paragraph spacing and
literal fence markers LinkedIn never rendered), and extended with
the team-structure and worked-example paragraphs. The published
article was updated in place from this source the same day.*

---

**Your AI coding agents don't talk to each other. This release makes them.**

I run three AI coding agents on the same repository: Claude Code,
OpenAI's Codex, and Google's Antigravity. Each one is good at
different things. And until this week, each one was an island.

Start a task in Claude Code, hit a session limit or want a
different model's strengths, open Codex — and everything the first
session knew is gone. The goal, the decisions, the half-finished
state, the "don't touch that file, it's load-bearing" — all of it
evaporates at the provider boundary. You paste fragments and hope.

attune-ai 10.6.0 is about deleting that boundary. One plugin, three
agents, and the interesting part isn't any single feature — it's
that the features had to be *provable* across vendors before we'd
call them shipped.

A word on how this team is structured, because it shapes everything
below: the three agents are not interchangeable peers. Codex and
Antigravity hold advisory seats — their findings route through
review before anything lands — and I've chosen Claude for the lead
programmer role, a choice written into the repo's collaboration
contract. Running multi-model isn't hedging; it's an evaluated
division of labor, and the evaluation is a year of receipts.

### Shared memory, any agent

The core of the release is a set of five session_memory_* MCP
tools: capture, recall, recent, forget, status. Claude Code gets
them automatically — its lifecycle hooks stash session findings as
you work. Codex and Antigravity get the *same surface* through
their MCP configuration: no sidecar, no second memory system, no
"lite" version. A finding captured in one agent is recallable in
the next, with PII scrubbed on the way in.

That PII gate has a story. Our mocked unit tests — over a thousand
of them — said the sanitizer was on. A live canary said otherwise:
the constructor's defaults silently disabled both scrubbers.
Nothing mocked would ever have caught it, because the mocks
faithfully reproduced our wrong assumption. One live round-trip
caught it in minutes. It's now enabled, and the fix ships in this
release.

**Receipt** — live round-trip against the real memory backend,
2026-07-22. A canary carrying a real-looking address went in;
recall returned the stored representation:

```text
T2-LIVE-CANARY-e5f1: contact [EMAIL] re parser deadlock
```

Redacted at rest, not just in the response. Forget deleted 1,
re-recall found nothing — the canary cleaned up after itself.
(Transport spec, receipt 3.)

### Handoffs that verify instead of trust

handoff_create writes a handoff packet for the current branch —
but the git-derived facts (branch, changed files, HEAD) come from
git at call time, never from what the model *says* it did. Claims
without receipts are recorded as exactly that: not run.

handoff_resume, on the receiving agent, re-checks the packet
against the actual tree and reports drift — head moved, files
diverged, branch missing — before any work continues. The
receiving agent gets context clearly separated from claims. Our
collaboration contract has said "a handoff is context, not
authority" for months; now it's mechanical.

**Receipt** — live Antigravity session, 2026-07-28, plugin 10.6.1.
The packet was created in Claude Code on branch
claude/handoff-t4-docs; handoff_resume then ran in a *different
vendor's* agent, which re-checked it against the real tree and
reported what had moved. It returned two warnings. The first,
"head_moved", read: packet 3fed725b7 vs current afd3040f2. The
second, "files_diverged", was more specific still — the packet
recorded no changed files, while the tree it was resuming into had
one: tests/unit/telemetry/test_memory_events.py.

The world had shifted under that packet, and the receiving agent
said so before touching anything. Note what it did *not* do: the
packet's own verification row still reads not run, and it stays
quarantined in the asserted block — the sending agent's prose,
kept strictly apart from the git-rechecked facts in verified.
Context, not authority, mechanically enforced.

### Second opinions from a different vendor

/cross-review sends your actual diff — not a summary of it — to
one seat from a different provider for an adversarial pass.
Different model, different blind spots. Findings come back
anchored (file:line, severity), the run is recorded, and the whole
thing is *advisory by spec*: it cannot gate a merge, fail a
command, or block CI. If the reviewer's CLI is missing, you get an
honest ABSENT — never a fabricated review.

Whether it ever becomes more than advisory is not a roadmap
decision. Every run appends a row to a public dogfood ledger —
date, seat, findings, and whether a human judged them real or
noise. That ledger is the only evidence that can upgrade it.

### The features picked themselves

Here's my favorite part. We didn't choose this release's headline
features in a planning meeting. We asked the round table — the
multi-LLM deliberation loop that shipped in a previous release.
Three seats (Claude, Codex, Antigravity's Gemini) answered
independently: given everything attune has, what's the obvious
next win?

Two of three converged, unprompted, on the same feature with
nearly identical designs: the cross-provider handoff. The third
proposed a verification pattern I ruled out — it needed seats to
run shell, which our contract forbids. But all three flagged the
same risk, still without seeing each other's answers: any of these
features rots into ceremony unless the receipts stay real and the
output stays advisory. That shaped the review discipline more than
the feature picks did.

Working across vendors also taught me a small, humbling lesson
about specifications themselves. A format contract described in
prose — clear prose, I thought — failed repeatedly for one seat,
even through a repair round that quoted the exact failures back to
it. What fixed it was putting a worked example in the brief. Two
models read the same paragraph and produced different shapes; the
example converged them where the prose could not. If a contract
matters, ship an example with it.

I chaired, ratified, and the specs were authored and built the
same evening — with the deliberation thread, every seat's
position, and my rulings promoted to a tracked report in the repo.
The tooling deliberated its own roadmap. I just held the gavel.

**Receipt** — the whole deliberation is public: every seat's
position, the moderator synthesis, my rulings, and the two
questions I left unruled.
[q-multi-llm-obvious-win-001](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/reports/roundtable/q-multi-llm-obvious-win-001.md),
merged to main 2026-07-22.

### Receipts or it didn't happen

One discipline runs through all of this: no feature is "done"
because its tests pass. Mocked tests prove your assumptions agree
with themselves — the PII bug taught us that. So every boundary
claim in this release carries a dated receipt from the real
system, and the ledger keeps honest UNPROBED rows for anything we
haven't proven yet.

We even discovered a receipts lesson about our own distribution:
an agent like Codex installs the plugin from its marketplace
pinned to our main branch — so until a feature merges and
publishes, no live probe from that agent can pass, no matter how
finished the code looks. The honest ledger row for that day reads
"probed — blocked pre-release." Today, post-release, it reads:

**Receipt** — live Codex session, 2026-07-27, plugin 10.6.0. Four
legs, all green: capture returned ok:true
(id a1c7b6e0-2668-42c5-b14a-02e8770cbf36); recall returned the
stored representation

```text
R4-LIVE-CANARY-20260727: codex post-lift probe, contact [EMAIL] re transport receipt
```

— the same redaction gate, enforced from a different vendor's
agent; forget reported requested:1 deleted:1; the final re-recall
found neither the token nor the id. (Transport spec, receipt 4.)

### The design principle

Claude Code gets automatic lifecycle hooks. Every other agent gets
the same memory and the same contract through adapters — never a
parallel subsystem, never a degraded copy. Cross-provider parity
by adapters is the growth surface: when the next agent CLI ships,
it gets a seat at the table and a key to the memory, not a fork.

```bash
pip install attune-ai
```

10.6.1 is on PyPI now — 10.6.0 plus a same-day patch. The round
table is open.

One question before you go: **what boundary kills your context?**
Mine was the provider boundary — that's the one this release
attacks. Yours might be somewhere else entirely: the gap between
sessions, between you and the teammate picking up your branch,
between staging and prod. I read the replies, and they feed the
same loop the round table does — the last set of answers is part
of why these features got built and not others.
