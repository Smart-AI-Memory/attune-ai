# Round table — next obvious multi-LLM win (q-multi-llm-obvious-win-001)

**Thread:** `q-multi-llm-obvious-win-001` · **Date:** 2026-07-22 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #3 #4 #7 (chair-approved).

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
  transport).
- **Amended same day:** `cross_review` is ALSO ratified — the
  second committed multi-LLM feature, not a merely-recorded
  candidate. Sequencing: handoff first, `cross_review` second; the
  07-27 usage-signal read (#5) now informs `cross_review`'s
  sequencing and design (frequency, advisory-vs-gate posture), it
  is no longer a commitment gate. The claude seat's own risk
  posture carries into the spec: board-only advisory first, never
  a merge gate until dogfooded finding-quality earns it.
- Remaining candidates (seat-executed worktree audits, provider
  router) stay recorded, not committed.
- **#6** left unruled on the board (TTL applies; re-raise if the
  audit idea advances to a spec).

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-multi-llm-obvious-win-001.md` and is
not distributed with the repository.*
