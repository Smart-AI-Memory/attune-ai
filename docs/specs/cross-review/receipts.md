# Cross Review — Receipts

## R5 dogfood ledger (T3 — five real runs, 2026-07-28/29 session)

D5/D7-honest: every row below is a real run executed 2026-07-29 UTC
(2026-07-28 ET evening session); no synthetic entries. Board thread
ids recorded per T3's live-fire check. Dispositions ruled by Patrick
(chair) in-session, 2026-07-28 ET.

| Date | Seat | Target | Files | Findings | Disposition |
|---|---|---|---|---|---|
| 2026-07-29 | codex | branch vs merge-base 94e8459c5 (origin/main) — #1559 skeptic diff | 3 sent / 0 omitted | 5 (findings) | carry-to-#1559 |
| 2026-07-29 | antigravity | branch vs merge-base 94e8459c5 (origin/main) — #1559 skeptic diff | 3 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-29 | codex | branch vs merge-base cd55f3839 (origin/main) — lessons docs diff | 1 sent / 0 omitted | 1 (findings) | dismissed — dated context by design |
| 2026-07-29 | antigravity | branch vs merge-base cd55f3839 (origin/main) — lessons docs diff | 1 sent / 0 omitted | 0 (clean) | clean |
| 2026-07-29 | codex | branch vs merge-base e7fa7e088 (origin/main) — feature-page docs branch | 23 sent / 7 omitted | 3 (findings) | stale-branch — carry only if revived |

Board threads (live-fire check): `review-detached-20260729-0036`,
`review-detached-20260729-0037`,
`review-claude-test-11-0-0-release-08e6c3-20260729-0037`,
`review-claude-test-11-0-0-release-08e6c3-20260729-0038`,
`review-detached-20260729-0039`. All five posted (`board: posted`);
zero absent seats; all replies format-compliant (no
`format_noncompliant` rows).

## Carried findings — #1559 (run 1, codex, all carry-to-#1559)

For the #1559 lift review; anchors are the draft's
`src/attune/roundtable/skeptic.py`:

1. [high] :193 — detached worktree is created from committed HEAD,
   so staged closure changes are absent from what receipts validate.
2. [medium] :186 — caller-provided `scratch_root` is not created
   before `git worktree add`; nonexistent roots fail.
3. [medium] :267 — COUNTERSIGN accepted with no CITE despite the
   every-verdict-cites contract (uncited rubber stamp).
4. [medium] :267 — CITEs never validated against executed receipt
   labels/argv; an invented CITE records as valid.
5. [low] :151 — nonzero git exit in `staged_closure_text` silently
   returns empty closure ("nothing to review" masks failures).

## Evidence notes for T4 (OPEN-1 / OPEN-3 re-rule)

- **Seat behavior (OPEN-1):** codex produced findings on all three
  diffs (5, 1, 3); antigravity returned NO FINDINGS on both diffs it
  reviewed, including the 821-line skeptic diff where codex found
  five. Consistent with the appendix-triage divergence recorded on
  #1602 (2026-07-28). Supports keeping the fixed `codex` default.
- **Diff-size distribution (OPEN-3):** 3 files / 821 insertions
  (fit, 0 omitted); 1 file / 44 insertions (fit); 30 files / 3,679
  insertions (truncated: 23 sent / 7 omitted). The 60,000-char cap
  fit both code-review targets whole and degraded visibly (manifest
  named every omitted file) on the bulk docs target. No run needed a
  larger cap for its code content.
- **Finding quality:** run 1's findings 3–5 are substantive contract
  gaps a same-model review missed; run 3's single finding was
  pedantic (dismissed); run 5 correctly flagged a stale doc claim.
  Quality supports continuing advisory posture; no gate-upgrade
  claim from five runs.

## Carried findings — #1559 dispositions (lift, 2026-07-29)

Ruled at the #1559 lift (branch rebased onto main; fixes land in
the lift commit on the PR):

1. [high] worktree-from-HEAD — FIXED by surfacing, not re-design:
   receipts still validate committed state (isolation is the
   point), but `uncommitted_paths()` now records the blind spot
   and the brief + chair digest name every uncommitted path the
   receipts could not see (TAC-4 honesty over silent omission).
2. [medium] scratch_root not created — DISMISSED, false positive:
   `git worktree add` creates missing parents (probed live with a
   3-level-deep nonexistent root, exit 0), and
   `test_isolated_pass_and_fail_receipts` already passes a
   nonexistent root — it stays as the regression guard.
3. [medium] uncited COUNTERSIGN — FIXED: every verdict now
   requires a CITE; an uncited countersign parses as malformed
   (rubber-stamp decay is the ruling's named failure mode #1).
4. [medium] CITE never validated — FIXED: `parse_skeptic_verdict`
   accepts `valid_labels`; a CITE whose label names no executed
   receipt records as malformed, never as a valid verdict.
5. [low] silent git failure — FIXED: `staged_closure_text` and
   `uncommitted_paths` raise `SkepticError` on nonzero git exit;
   an empty result can only mean "no staged closure".

Regression tests for all four fixes in
`tests/unit/roundtable/test_skeptic.py` (41 tests, serial pass).
