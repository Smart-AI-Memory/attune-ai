# Launch article draft — 10.6.0, the multi-LLM release

**Written:** 2026-07-22 (launch plan item 1 —
`.claude/plans/launch-10-6-0-multi-llm.md`). **Fires:** Tuesday
2026-07-28, AFTER the lift + live receipts (chair-ratified timing).
**Venue:** LinkedIn article. **Status:** draft — `[RECEIPT: …]`
slots fill from Monday's real transcripts; publishing with an
unfilled slot is forbidden (no claim without a receipt).

Pre-publish checklist:

- [ ] All `[RECEIPT: …]` slots filled with real transcript excerpts
      — **3 of 4 filled 2026-07-28** (PII canary, round-table report
      link, Codex live canary) from the transport spec's receipts
      ledger. The 4th (handoff create→resume) is **BLOCKED on a chair
      ruling** — see the inline comment at that slot: the Codex leg
      was auto-cancelled, so no receiving-agent drift report exists.
- [x] Version/date claims re-checked against **live PyPI**
      (2026-07-28): latest = **10.6.1**; tags `v10.6.0` and `v10.6.1`
      both exist and both PyPI versions return 200. The body's
      "10.6.1 is on PyPI now" line is accurate as written. 10.6.0
      names the release; **10.6.1** is the same-day patch and is what
      `pip install` resolves to — it carries the README "Multi-LLM
      collaboration" section this article describes. **Re-verify with
      `curl -s https://pypi.org/pypi/attune-ai/json` immediately
      before firing** — a later patch moves this number again.
- [ ] Chair honesty-gate pass (same ruling session as Draft B).
      **Three items are queued for that ruling:** (1) the 4th receipt
      slot — close it with an interactive Codex run, or reword to
      per-agent truth; (2) the "third proposed the audit pattern"
      sentence — flagged inline as unsupported by the report it
      links, with a receipted replacement drafted; (3) the closing
      variant (a/b/c, noted at the draft's foot).
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

[RECEIPT: create-in-Claude → resume-in-Codex transcript, showing
the drift report on a real branch]

<!-- BLOCKING — CHAIR RULING REQUIRED (2026-07-28). This slot cannot
be filled honestly today. What IS receipted (handoff spec receipts.md,
2026-07-27):

  - Claude leg, LIVE PASS: handoff_create through the real MCP server
    (plugin 10.6.1) on branch claude/handoff-t4-docs — ok:true, packet
    written, git-derived head_sha 3fed725b7…, verification row stored
    as "not run" per R1.
  - Codex leg, REACHED BUT NOT EXECUTED: handoff_resume IS in Codex's
    tool list and dispatch started ("mcp: attune-ai/handoff_resume
    started") — distribution is PROVEN at 10.6.1 — but codex's headless
    approval policy auto-cancelled the call. Verbatim:
    [{"type":"text","text":"user cancelled MCP tool call"}]

  So the drift report itself has never been produced by the receiving
  agent. Two ways to clear this (chair picks):

  (a) CLOSE IT — one INTERACTIVE Codex run from the
      attune-ai-github-issues-0aeac3 worktree (the packet is sitting
      uncommitted at docs/handoffs/claude-handoff-t4-docs.md):
        codex "Call the attune-ai MCP tool handoff_resume with no
               arguments and show the raw JSON result"
      Expected: ok:true, verified.branch = claude/handoff-t4-docs,
      drift warnings listing the dirty tree. Fills this slot for real.
      Same real-terminal sitting as the clean-run re-fire.

  (b) REWORD TO PER-AGENT TRUTH — publish the section claiming only
      the Claude-side receipt plus proven cross-provider dispatch, and
      mark the receiving-agent drift report as an honest UNPROBED row.
      This is ON-message: the article already sells honest UNPROBED
      rows, and Draft B-v2's checklist pre-authorizes this exact
      reword ("if only the Claude-side receipt exists Tuesday, reword
      to per-agent truth or hold").

  Do NOT publish this section as written under either option without
  the chair's pick. -->


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
proposed the audit pattern that shaped our review discipline. I
chaired, ratified, and the specs were authored and built the same
evening — with the deliberation thread, every seat's position, and
my rulings promoted to a tracked report in the repo.

<!-- HONESTY FLAG (2026-07-28) — one sentence above is not supported
by the report it links. "The third proposed the audit pattern that
shaped our review discipline": the third seat (Antigravity) proposed
roundtable_audit_worktree, and the chair ruling records it as
"recorded, not committed" — it collides with R1 (members never touch
shell). Grep confirms zero linkage into docs/specs/cross-review/.
What IS true and receipted in the same report (#7 synthesis): all
three seats independently named the same risk — that every candidate
degrades into ceremony/noise/false precision unless receipts stay
real and outputs stay advisory-not-authoritative. THAT is what shaped
the review discipline, and it's a better line anyway (three-way
convergence on the risk, not just the feature).

Suggested replacement, chair to approve:
  "The third proposed a verification pattern I ruled out — it needed
  seats to run shell, which our contract forbids. But all three,
  unprompted, flagged the same risk: any of these features rots into
  ceremony unless the receipts stay real and the output stays
  advisory. That shaped the review discipline more than the feature
  picks did."

The two verified claims in this paragraph stand as written: 2-of-3
convergence on the handoff (report #7, verbatim), and specs authored
same-day (#1603 and #1604 both merged 2026-07-22). -->



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

---

*Draft note (not for publication): candidate closing variants —
(a) the install-line close above; (b) a question close inviting
readers to name which agent they'd hand off to first; (c) the
DEC-2-style ask ("what boundary kills your context?"). Chair picks
at the honesty-gate ruling.*
