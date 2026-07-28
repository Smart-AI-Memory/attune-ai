# Routine digest — weekly clean-run, 2026-07-28

**Thread:** `routine-clean-run-20260728-1020` · **Roster:** claude,
antigravity, codex · **Rounds:** 1 · **Invocations:** 8 ·
**Promoted:** #5 #7 #9 #10 (chair-approved 2026-07-28).

This is the FIRST green fire of the weekly routine. The 07-27
scheduled fire failed with the claude seat ABSENT; the cause was seat
auth, not the routine (see `docs/specs/agent-round-table/decisions.md`,
2026-07-28). A routine never promotes itself (R8) — this file exists
because the chair promoted the thread.

## Health verdict — HEALTHY (3/3 unanimous)

19,001 passed / 63 skipped / 7 xfailed; governance 76/76; projections
in sync; tree clean. No failure-axis signal.

**One drift, and only one:** local `main` was 0 ahead / 2 behind cached
`origin/main`.

**Lesson candidate: NONE.** All three seats declined to file one. The
claude seat additionally killed its own tempting second candidate ("a
green run at a stale SHA is a receipt for the wrong SHA") on the
grounds that nothing actually failed from it — hypothesis, not receipt.

**Self-flagged bias (claude seat):** it ranked the 2-commit lag as
trivial-but-first *without inspecting the commits' contents* —
asserting severity from the warning's shape, not its body, which is the
pattern the verify-first-on-infra lesson warns against.

### Split

| Axis | claude | codex | antigravity |
|---|---|---|---|
| Staleness severity | do it FIRST — the receipt certifies `15e568f54`, not the tip | low priority, but re-run after pulling | routine git tracking; no re-fire named |
| Hydrate coupling | ONLY seat to name it — the freshness WARN and the session's `STALE SOURCE` are the same fact | — | — |
| Scope hygiene | flags that "clean run: PASS" ≠ "tree is green" (no coverage / mkdocs / lint / Windows / keyed lanes) | — | — |

### Ranked actions and their disposition

| # | Action | Support | Disposition (2026-07-28) |
|---|---|---|---|
| 1 | Pull + re-hydrate | 3/3 | **DONE** — pulled to `11af1dc32`, re-hydrated (851 lessons); freshness WARN and stale-recall corpus cleared |
| 2 | Re-fire at the new tip, or scope the ledger entry to the SHA — *mandatory if either unpulled commit touches `src/` or `tests/`* | 2/3 | **RESOLVED AS OPTIONAL** — inspecting the two commits showed both docs-only (`d522d0c02`, `11af1dc32`); the condition is unmet, so the `-1020` receipt stands for the tip it certified |
| 3 | Record the four numbers weekly for a baseline diff | 1.5/3 | **UNRULED — chair.** The claude seat pre-committed to withdrawing it rather than let it grow machinery |
| 4 | Reporting hygiene — name the slice when quoting the result | 1/3 | Recorded; no action item |

Action 2's resolution is the inspection the claude seat flagged itself
for skipping — it cost one `git diff --stat` and settled the split.

## Appendix — briefing triage (4 items)

**Table shape:** claude and codex converge item-for-item on all four.
Antigravity diverges on all four — its positions derive from
lifecycle-bucket labels and declared-status strings rather than
PR/receipt state, and the recorded evidence resolves it the same way
each time. That is a seat-level bias worth carrying into any
default-reviewer-seat decision (input to cross-review OPEN-1).

| Item | Moderator recommendation | State as of promotion |
|---|---|---|
| 1 — cross-provider-memory-transport | CLOSE as shipped (2/3) | **STILL OPEN** — the five phase files still read `APPROVED … in execution; T1–T3`, the stale label the appendix identified. Receipts are 6/6 PASS and #1593/#1594/#1596/#1598 all merged 07-27 |
| 2 — cross-provider-session-handoff | HOLD OPEN, narrowed to ONE interactive `handoff_resume` probe; fix the stale recipe in the same pass | **SATISFIED SINCE — both halves.** R6 closed live 07-28 09:47 EDT from an Antigravity seat (`ok:true`, `head_moved` + `files_diverged`), and the stale recipe the claude seat uniquely caught was corrected in the same edit |
| 3 — cross-review | PARK with a dependency-milestone resume-trigger (chair usage-signal read), NOT a date | **PARK STANDS — gate verifiably unmet.** `docs/specs/usage-signals/snapshots/` still ends at `2026-07-26.json`; no 07-27 or 07-28 snapshot exists |
| 4 — feature-lead-governance | PARK behind Item 3; treat the bucket-vs-status mismatch as a label fix, not a re-approval | **PARK STANDS** — downstream of Item 3 |

**Compression the chair can act on:** one decision — run or kill the
deferred usage-signal read — resolves Items 3 and 4. Item 1 is a
status flip. Item 2 is now closed.

### Item 2's unique find, and why it mattered

The claude seat was the only one to notice the reproduction recipe in
`receipts.md` was stale: it named the `attune-ai-github-issues-0aeac3`
worktree expecting `verified.branch = claude/handoff-t4-docs`, but that
worktree had moved to `qa/memory-events`. Acting on the recipe verbatim
would have returned `packet_not_found` — which reads like a broken
feature rather than a stale instruction. Fixed the same day.

### Recorded risks of this synthesis (moderator, unprompted)

- Items 3 and 4 rest on a shared inference: that the deferred chair
  read is ONE read serving both. The unmet gate is receipt-tier (no
  07-27 snapshot); FLG's P1 inheriting cross-review's gate is recorded.
  What is NOT independently verified is chair *intent* that one sitting
  serve both — the starter asserts it, which is strong but claim-tier.
  If the chair wants a cross-review-specific read separate from FLG
  activation, "one decision unlocks three" becomes two decisions.
- Item 1's close assumes R8 receipts 4 and 6 were written from real
  07-27 runs, not back-filled at the lift. Verbatim Codex session ids
  and D7 no-simulation discipline make that unlikely, but freshness is
  receipt-tier only as far as the ledger's own honesty.
- **Claim-drift surface flagged while parked:** the PROVISIONAL knobs
  `DEFAULT_SEAT="codex"` and `DIFF_CAP_CHARS=60_000` are live in
  shipped 10.6.1, not branch-resident. Parking is safe; describing them
  as settled in docs would be drift.

## Still owed by the chair

- **Item 1** — flip the transport spec's five phase files to `shipped`;
  that flip discharges its `CHAIR_REQUIRED` receipt.
- **Item 3 / Item 4** — run or kill the deferred usage-signal read.
- **Action 3** — the four-numbers baseline ledger: green-light or drop.
