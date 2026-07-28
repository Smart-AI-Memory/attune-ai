# Launch article draft — 10.6.0, the multi-LLM release

**Written:** 2026-07-22 (launch plan item 1 —
`.claude/plans/launch-10-6-0-multi-llm.md`). **Fires:** Tuesday
2026-07-28, AFTER the lift + live receipts (chair-ratified timing).
**Venue:** LinkedIn article. **Status: PUBLISHED 2026-07-28** —
<https://www.linkedin.com/posts/patrick-roebuck-attune-ai_this-article-talk-about-the-multi-llm-memory-activity-7487899197329993729-pGPN>

All four `[RECEIPT: …]` slots were filled from real transcripts before
firing; the no-claim-without-a-receipt rule held end to end. This file
is now the archival source for a shipped article — the published copy
differs only in that its one JSON block was reflowed to prose for
LinkedIn's editor, which has no code-block primitive. Every value in
that reflow was fact-checked against the raw receipt.

Pre-publish checklist:

- [x] All `[RECEIPT: …]` slots filled with real transcript excerpts
      — **4 of 4 filled 2026-07-28.** PII canary, round-table report
      link, and Codex live canary from the transport spec's receipts
      ledger; the handoff create→resume slot closed live at 09:47 EDT
      from an **Antigravity** session (not Codex — codex's headless
      approval policy auto-cancels, so the receiving agent was
      switched to the seat already proven at 10.6.1 by transport
      receipt 6). Returned `ok:true` with `head_moved` +
      `files_diverged`. Transcript appended to the handoff spec's
      `receipts.md`, closing R6.
- [x] Version/date claims re-checked against **live PyPI**
      (2026-07-28): latest = **10.6.1**; tags `v10.6.0` and `v10.6.1`
      both exist and both PyPI versions return 200. The body's
      "10.6.1 is on PyPI now" line is accurate as written. 10.6.0
      names the release; **10.6.1** is the same-day patch and is what
      `pip install` resolves to — it carries the README "Multi-LLM
      collaboration" section this article describes. **Re-verify with
      `curl -s https://pypi.org/pypi/attune-ai/json` immediately
      before firing** — a later patch moves this number again.
- [x] Chair honesty-gate pass — **RULED 2026-07-28, all 3 applied.**
      (1) 4th receipt slot → path (a), closed for real; the reword
      fallback was NOT needed. (2) "third proposed the audit pattern"
      sentence → replacement APPLIED; every claim in that paragraph
      now traces to the linked report. (3) Closing variant → **(c)**
      APPLIED, layered after the install line.
- [x] **PUBLISHED 2026-07-28** —
      https://www.linkedin.com/posts/patrick-roebuck-attune-ai_this-article-talk-about-the-multi-llm-memory-activity-7487899197329993729-pGPN
      URL carried into Draft B-v2's `[LINK: launch article]`.
      Pre-publish checklist fully discharged; this draft is now
      the archival source for a shipped article.
- [x] Counts re-verified against the merged registries (2026-07-28):
      "five `session_memory_*` tools" = 5, names match
      (`attune_redis.mcp_tools.SESSION_MEMORY_TOOL_DEFINITIONS`).
      No other capability count appears in the body — the earlier
      "26 skills" item checked a claim this draft does not make.

---

## Your AI coding agents don't talk to each other. This release makes them.

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

### Shared memory, any agent

The core of the release is a set of five `session_memory_*` MCP
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
2026-07-22. A canary carrying a real-looking address went in; recall
returned the stored representation:

```text
T2-LIVE-CANARY-e5f1: contact [EMAIL] re parser deadlock
```

Redacted at rest, not just in the response. Forget deleted 1,
re-recall found nothing — the canary cleaned up after itself.
(Transport spec, receipt 3.)

### Handoffs that verify instead of trust

`handoff_create` writes a handoff packet for the current branch —
but the git-derived facts (branch, changed files, HEAD) come from
git at call time, never from what the model *says* it did. Claims
without receipts are recorded as exactly that: `not run`.

`handoff_resume`, on the receiving agent, re-checks the packet
against the actual tree and reports drift — head moved, files
diverged, branch missing — before any work continues. The
receiving agent gets context clearly separated from claims. Our
collaboration contract has said "a handoff is context, not
authority" for months; now it's mechanical.

**Receipt** — live Antigravity session, 2026-07-28, plugin 10.6.1.
The packet was created in Claude Code on branch
`claude/handoff-t4-docs`; `handoff_resume` then ran in a *different
vendor's* agent, which re-checked it against the real tree and
reported what had moved:

```json
"warnings": [
  {"code": "head_moved",
   "detail": "packet 3fed725b7 vs current afd3040f2"},
  {"code": "files_diverged",
   "detail": {"packet": [],
              "current": ["tests/unit/telemetry/test_memory_events.py"]}}
]
```

The world had shifted under that packet, and the receiving agent said
so before touching anything. Note what it did *not* do: the packet's
own verification row still reads `not run`, and it stays quarantined
in the `asserted` block — the sending agent's prose, kept strictly
apart from the git-rechecked facts in `verified`. Context, not
authority, mechanically enforced.

### Second opinions from a different vendor

`/cross-review` sends your actual diff — not a summary of it — to
one seat from a different provider for an adversarial pass.
Different model, different blind spots. Findings come back
anchored (`file:line`, severity), the run is recorded, and the
whole thing is *advisory by spec*: it cannot gate a merge, fail a
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
independently: *given everything attune has, what's the obvious
next win?*

Two of three converged, unprompted, on the same feature with
nearly identical designs: the cross-provider handoff. The third
proposed a verification pattern I ruled out — it needed seats to
run shell, which our contract forbids. But all three flagged the
same risk, still without seeing each other's answers: any of these
features rots into ceremony unless the receipts stay real and the
output stays advisory. That shaped the review discipline more than
the feature picks did.

I chaired, ratified, and the specs were authored and built the same
evening — with the deliberation thread, every seat's position, and
my rulings promoted to a tracked report in the repo.

<!-- RULED 2026-07-28 (chair). The prior sentence — "the third
proposed the audit pattern that shaped our review discipline" — was
NOT supported by the report it links: that seat proposed
roundtable_audit_worktree, which the ruling records as "recorded, not
committed" (collides with R1, members never touch shell), and grep
confirmed zero linkage into docs/specs/cross-review/. Replaced above
with the receipted version: report #7's synthesis records all three
seats independently naming the ceremony/noise/false-precision risk.
Every claim in this paragraph now traces to the linked report:
2-of-3 convergence on the handoff (#7 verbatim), the third seat's
proposal ruled out on R1 (chair ruling), the three-way risk
convergence (#7), and specs authored same-day (#1603 + #1604, both
merged 2026-07-22). -->



The tooling deliberated its own roadmap. I just held the gavel.

**Receipt** — the whole deliberation is public: every seat's
position, the moderator synthesis, my rulings, and the two questions
I left unruled.
[q-multi-llm-obvious-win-001](https://github.com/Smart-AI-Memory/attune-ai/blob/main/docs/reports/roundtable/q-multi-llm-obvious-win-001.md),
merged to main 2026-07-22.

### Receipts or it didn't happen

One discipline runs through all of this: no feature is "done"
because its tests pass. Mocked tests prove your assumptions agree
with themselves — the PII bug taught us that. So every boundary
claim in this release carries a dated receipt from the real
system, and the ledger keeps honest `UNPROBED` rows for anything
we haven't proven yet.

We even discovered a receipts lesson about our own distribution:
an agent like Codex installs the plugin from its marketplace
pinned to our main branch — so until a feature *merges and
publishes*, no live probe from that agent can pass, no matter how
finished the code looks. The honest ledger row for that day reads
"probed — blocked pre-release." Today, post-release, it reads:

**Receipt** — live Codex session, 2026-07-27, plugin 10.6.0. Four
legs, all green: capture returned `ok:true`
(id `a1c7b6e0-2668-42c5-b14a-02e8770cbf36`); recall returned the
stored representation

```text
R4-LIVE-CANARY-20260727: codex post-lift probe, contact [EMAIL] re transport receipt
```

— the same redaction gate, enforced from a different vendor's agent;
forget reported `requested:1 deleted:1`; the final re-recall found
neither the token nor the id. (Transport spec, receipt 4.)

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
same loop the round table does — the last set of answers is part of
why these features got built and not others.

---

*Draft note (not for publication): closing variant RULED 2026-07-28
(chair) — variant (c), the DEC-2-style ask, layered AFTER the
install-line close rather than replacing it. Variant (b) (which
agent would you hand off to first) is not used. Rationale: the
DEC-2 ask is the pattern that earned replies on 07-17, and replies
feed the US-3 slots; the install line still does the conversion
work above it. The "I read the replies … feed the same loop" claim
is true and cheap to keep true — log the replies (N1) as they
arrive.*
