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

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/routine-clean-run-20260728-1020.md` and is
not distributed with the repository.*
