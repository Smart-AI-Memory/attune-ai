# Round table — next obvious multi-LLM win (q-multi-llm-obvious-win-001)

**Thread:** `q-multi-llm-obvious-win-001` · **Date:** 2026-07-22 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #3 #4 #7 (chair-approved).

## #1 — question (chair)

Review the attune-ai multi-LLM feature inventory (2026-07-22) and
suggest the one or two features that would be the most obvious "win"
to add next — highest user-visible value relative to effort,
building on what exists. (Seats were briefed with the inventory:
shipped = roundtable core + producing runs + solution loop,
collaboration contract/projector, Antigravity adapter, shared Redis
memory index + Ollama stash extraction, Codex marketplace
distribution; merging 07-27 = `session_memory_*` MCP transport,
truthful backend status, transport telemetry.)

## #2 — position (claude, 36s)

POSITION: two features, both compositions of shipped parts.
(1) `cross_review` — one-shot second-opinion MCP tool (lead pick):
before merging, a different provider reviews the real diff
adversarially, findings posted to the board. A roundtable-lite: one
seat, one round, no chair ceremony, reusing adapters, board posting,
and the solution-loop receipt discipline. The full roundtable is an
occasional instrument; a pre-merge cross-model check is a
daily-frequency action — converts ceremony into habit.
(2) `session_handoff` — tool-mediated cross-provider resume: create
validates against actual git state, resume verifies before
continuing; makes "parity by adapters" legible — providers become
interchangeable seats on one task. Both beat: more seats, a board
GUI, auto-Ollama for non-Claude (07-27 capture must accrue usage
signal first).
RISK: a headless one-shot review without full repo context may
produce shallow or confabulated findings — a noisy reviewer erodes
trust in the whole multi-LLM story. Mitigation: reviewer sees real
artifacts via the solution-loop path; if dogfooding shows low
quality, keep it board-only advisory, never a merge gate. Secondary:
the ranking assumes frequency — if handoffs are common and reviews
rare, the ordering flips.

## #3 — position (antigravity, 43s)

POSITION: (1) `roundtable_audit_worktree` — non-proposing seats
check out the materialized worktree, execute the verification
probes, and attach independent signed receipts to the board before
chair approval; turns the solution loop into a true multi-model
consensus gate without new execution environments.
(2) `session_memory_harvest` (`attune session wrapup`) — an explicit
wrap-up action for MCP-backed environments (Codex/Antigravity) that
feeds the session transcript through the existing local Ollama
extraction pipeline into the shared Redis index; closes the
remaining parity gap since MCP hosts do not reliably emit lifecycle
termination events.
RISK: board over-saturation with redundant verification noise —
chair alert fatigue; requires strict formatting/summarization rules
for audit receipts.

## #4 — position (codex, 14s, 13.7k tokens)

POSITION: (1) Cross-provider session handoff — `handoff_create` /
`handoff_resume` as a thin MCP workflow over the existing contract,
handoff template, Redis recall, git inspection, and provider
telemetry; the receiving model gets outcome, acceptance criteria,
changed files, decisions, receipts, risks, and relevant memory, then
checks the packet against the current worktree before proceeding
(freshness/drift warnings, provider attribution). Clearest win
because users experience multi-LLM value at the provider boundary,
where context currently degrades.
(2) Provider-aware task router — recommendation-only: suggest
Claude/Codex/Antigravity/roundtable from task type, telemetry, and
tool availability; user approves before execution.
RISK: the handoff could become ceremonial context duplication; the
router could project false precision from sparse telemetry. Both
need terse defaults, explicit freshness checks, and
recommendations-not-authority framing.

## #5 — question (claude, R9 triage)

Before committing to `cross_review`: what do board/telemetry records
say about how often a FULL roundtable was convened when a
single-seat one-shot check would have sufficed — observed demand or
invented? (The 07-27 usage-signal read is the natural place to
answer.)

## #6 — question (antigravity, R9 triage)

When a non-proposing seat fails a worktree audit, should the system
auto-trigger a targeted retry loop between those two seats, or
immediately yield to the human chair with the failed receipt
attached? (Unruled; note R1 — members never touch shell — means any
seat-executed probe design needs a ruling first.)

## #7 — synthesis (moderator)

STRONG CONVERGENCE on one feature: tool-mediated CROSS-PROVIDER
SESSION HANDOFF (`handoff_create` / `handoff_resume`). Named
independently by 2 of 3 seats with nearly identical shapes: a thin
MCP workflow over the existing contract handoff template + the
07-27 `session_memory_*` transport + git-state verification on
resume ("handoff is context, not authority," made mechanical).
SPLIT on the second pick — one candidate per seat: `cross_review`
(strongest: no new subsystem, honest advisory fallback),
seat-executed worktree audits (collides with R1 — receipts must flow
through the moderator; needs a ruling), provider-aware router
(weakest today: telemetry only starts accruing 07-27; sparse-data
false precision is Codex's own named risk).
SHARED RISK THEME (all three seats, unprompted): every candidate
degrades into ceremony/noise/false precision unless receipts stay
real and outputs stay advisory-not-authoritative — matches the
repo's dogfood-or-remove discipline.
MODERATOR READ: handoff is the obvious win; `cross_review` the
strongest second, sequenced AFTER the 07-27 usage-signal read
(per #5). Defer the router and seat-executed audits.

## Chair ruling (2026-07-22)

- **Promoted:** this report (items #2 #3 #4 #7), and
  `handoff_create` / `handoff_resume` is RATIFIED as the next
  multi-LLM feature — spec to be authored AFTER the 2026-07-27
  sitting (post-lift, so it builds on the merged `session_memory_*`
  transport). Second-pick candidates are recorded, not committed.
- **#5** defers to the 07-27 usage-signal read.
- **#6** left unruled on the board (TTL applies; re-raise if the
  audit idea advances to a spec).
