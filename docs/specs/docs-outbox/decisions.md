# docs-outbox — decisions

**Status:** active (2026-08-07) — Phase 1 built, reviewed, and
dogfooded; R3 memory lint and the R4 chip carried open; R5
deferred to Phase 2. (File-level line added at the 2026-08-08
triage so the lifecycle detector stops reading D1's inline status.)

## D1 — ACTIVATED: the outbox is the ruled fix for lessons-append conflicts

**Date:** 2026-08-06 · **Status:** ACTIVATED (chair: Patrick, via
decision form; validated receipt `resp-20260806-073002`)

The chair activated this parked candidate as the fix for the
slow-PR lessons-append conflict class, choosing it OVER the lead's
recommendation ("re-commit to EOD batching + a `merge=union`
seatbelt") and over a lessons-fragments restructure. Both rejected
options and the lead's rationale (discipline hadn't failed while
followed) are preserved per the pushback-shape record; the chair
weighed the growing multi-session pattern — parallel worktrees,
chip sessions, multiple same-day writers — and picked the
mechanism that removes in-session docs PRs entirely.

**Fresh motivating evidence (2026-08-06):** two lessons.md DIRTY
cycles in one session — #1963's lessons append conflicted #1964
(cut minutes earlier), then a second append re-conflicted it after
its own rebase window. Both were bundling violations of the
EOD-batch rule, and the day ALSO had a parallel chip session
(#1966) — the multi-writer condition the outbox is designed for.

**Effect:** the requirements interview (the four questions in
`requirements.md`) proceeds now; the candidate design (C1–C4)
remains the input hypothesis, not the contract. Build follows
ratified requirements, per the spec lifecycle. Until the outbox
ships, the EOD-batch rule stays binding for lessons appends.

## D2 — Interview answered; Phase-1 requirements RATIFIED

**Date:** 2026-08-06 · **Status:** approved (chair: Patrick, via
the four-question interview form; validated receipt
`resp-20260806-073859` — all four lead recommendations accepted)

- **Sweep cadence:** end-of-workday launchd + on-demand skill;
  stale-outbox warning at 2 days.
- **Pending-recall layer (C3): DEFERRED to Phase 2** — earns in on
  demonstrated need (reopen trigger: a session demonstrably missing
  a same-day lesson). The phasing concern was raised by the lead at
  activation (D1 discussion) and adopted by the chair here.
- **Write discipline:** per-artifact files, flat directory,
  timestamped names — concurrent writers conflict-free by
  construction.
- **Digest approval:** chip — one click spawns the
  approve-and-PR session; the ops inbox row is monitoring only.

`requirements.md` rewritten from candidate (C1–C4 hypotheses) to
Phase-1 ratified form (R1–R5, AC-1–AC-4, build tasks). Build may
proceed from the ratified requirements in a fresh session.

## D3 — Phase 1 BUILT; receipts AC-1/AC-3/AC-4 recorded, AC-2 pending chip

**Date:** 2026-08-06 · **Status:** built (lead: Claude; dogfooded
live against the real `~/.attune/docs-outbox/`)

Shipped (one PR): `attune.docs_outbox` package (store R1, routing
R2, sweep+digest R3, CLI), Stop-hook lessons reminder rerouted to
the outbox writer (drift-guarded in
`tests/unit/test_coverage_batch12.py`), `/docs-outbox` plugin
skill (+ `.agents/` sync), launchd TEMPLATE at
`scripts/launchd/com.smartaimemory.attune.docs-outbox-sweep.plist`
(daily 17:30, digest-compose only — NOT installed; chair's
machine, chair installs), ops Collaboration inbox "N docs pending,
oldest Nd" row (monitoring-only; stale is the only state that
counts toward the action badge). 56 new tests; package coverage
92% (worktree-coverage workaround). R5 not built (deferred, D2).

Build interpretations worth naming:

- **Memory lint** runs best-effort via
  `~/.claude/hooks/memory_lint.py` ONLY for artifacts targeting a
  `/memory/` directory (no Phase-1 kind does by default); absence
  or failure of the home linter degrades silently. In-repo there is
  no memory linter to call (verified).
- **Chip mechanics:** the sweep composes the digest; the chip is
  spawned by the in-session skill flow via `spawn_task` (a launchd
  run composes the digest and the next session's skill run spawns
  the chip). Surfaces without `spawn_task` fall back to asking
  directly — same approval contract.
- **Dedupe** is mechanical: exact-body duplicates dropped (keep
  earliest), same-slug kin flagged `related-slug` for the chair;
  no LLM judgment in the sweep.

**Receipts:**

- **AC-4 (no-rot) — PASS, live:** backdated artifact
  (`20260803-0900-lesson-ac4-stale-probe.md`, 3.0d) →
  `status` printed `1 pending, oldest 3.0d  STALE — sweep overdue`
  and the live collab provider returned
  `OutboxRow(count=1, oldest_days=3.0, stale=True)`. Probe removed
  after the receipt (synthetic backdate — a real 2-day wait is not
  dogfoodable same-day; the trigger math is also unit-tested).
- **AC-1 (conflict-class) — conflict-free half PASS, live:** two
  real lessons from this session written by two separate CLI
  processes in the same minute
  (`20260806-0958-lesson-website-skill-count-guard.md`,
  `20260806-0958-lesson-hermetic-home-reads.md`) — two distinct
  files, zero conflict by construction (no branch, no armed PR
  exists to go DIRTY), one digest listing both. The
  lands-in-one-PR half completes when the chip-spawned session
  applies and opens the swept PR (bundled with AC-2 by design —
  one approval, one PR).
- **AC-3 (routing) — PASS, live:** THIS D3 ruling was written the
  same day and ships merge-now in the feature PR, not via the
  outbox — R2's split exercised for real; the outbox CLI also
  refuses `--kind decision` outright (unit-tested).
- **AC-2 (sweep round-trip) — PASS, live (2026-08-07):** 11 real
  lessons written across the session by three separate writers
  (two CLI processes plus the Stop-hook-prompted route) swept in
  one pass: all 11 lint-clean, zero duplicates dropped, applied to
  `.claude/lessons.md` in timestamp order (+289 lines, one file),
  outbox drained to empty, all 11 archived to
  `~/.attune/docs-outbox/swept/`. Verified post-apply: zero CRLF in
  the diff, trailing-whitespace / end-of-file / mixed-line-ending
  hooks pass, `tests/unit/lessons` 26/26 green. Shipped as ONE PR.
  **Approval path — recorded as it happened, not as designed:** the
  chair approved by DIRECT INSTRUCTION in-session ("run the sweep
  and apply the 11 lessons"), not by clicking the digest chip. The
  chip had been spawned and started, but stood down on its
  precondition (#1970 unmerged) and did nothing; it was checked for
  concurrent work before this run (no open PR, no `swept/`, all 11
  still pending) precisely because a duplicate sweep would
  manufacture the lessons.md conflict this spec exists to prevent.
  The R4 contract — *no auto-shipping; the chair approves the
  digest before the PR opens* — was satisfied: a digest was composed
  and shown, and the chair authorized the apply. The chip
  specifically remains the untested surface; a future sweep should
  exercise it to close that gap.

## AC-1 completion note

AC-1's second half ("the sweep lands both in one PR") is closed by
the AC-2 run above: the two same-day writers' lessons from 09:58
are in the same swept PR as the other nine, with zero DIRTY cycles
at any point — no branch existed to conflict until apply time.

## D4 — Review lane found 3 data-loss defects; all fixed before merge

**Date:** 2026-08-06 · **Status:** fixed (lead: Claude; adversarial
review lane per D11 — persistence is a named risk class)

The Phase-1 build was reviewed adversarially before the chair read
the recommendation. The lane found **nine real defects**, three of
them capable of silently losing or corrupting data. Every one is
fixed with a named regression test in
`tests/unit/docs_outbox/test_sweep.py::TestReviewRegressions`.
Recording them because the first three all shared one root cause:
**the sweep parses `kind` and `target` off DISK, so nothing that
`write_artifact` validates is guaranteed at apply time** — a
hand-authored or post-edited artifact bypasses the routing gate
entirely.

| # | Defect | Was | Now |
|---|---|---|---|
| 1 | Unknown `kind` (e.g. the typo `lessons`) fell through to the file-REPLACING branch | Replaced the entire 380-lesson corpus with a one-line body | `_lint` rejects any kind not in `OUTBOX_TARGETS` |
| 2 | Mid-loop failure skipped archiving for the WHOLE batch | Already-applied artifacts stayed pending and re-applied (duplicate lessons) next run | Archive per artifact inside the loop; failures recorded in `apply_failures` and left pending |
| 3 | Two artifacts claiming one new target both linted clean | Second silently overwrote the first; both archived as applied | Intra-sweep `claimed` set collides the second at lint |
| 4 | Repo writes were truncate-then-write | A crash mid-write could empty `lessons.md` | `_atomic_write` (temp + `os.replace`) |
| 5 | Dedupe keyed on body alone | Identical prose bound for DIFFERENT files silently dropped one | Key is `(kind, target, body)` |
| 6 | `while path.exists()` check-then-act | Same-minute collision could overwrite a sibling session's artifact | `os.open(O_CREAT\|O_EXCL)` with a zero-padded serial |
| 7 | Lesson `target` unconstrained | A lesson could append prose into `src/app.py` | Target must be `.md` AND equal the kind's default |
| 8 | `--repo-root` defaulted to `.` unchecked | `apply` from the wrong cwd created `~/.claude/lessons.md` and swept the outbox | Refuses a root without `.git` |
| 9 | `digest.md` lingered after a drain | The chip could render an already-applied batch | Removed once the outbox drains |

Plus: serial-collision files sorted BEFORE their base name
(`-002.md` < `.md`), so `list_artifacts` now sorts by
`(created, serial)` rather than filename; an unparseable name gets
`datetime.min` rather than "now", so a hand-dropped file ages into
the stale warning instead of looking forever fresh; and `|` in a
target is escaped so it cannot break the digest table.

**Correction to D3 — the memory-lint claim was false.** D3 said the
sweep runs the home memory linter "best-effort". It could never
have fired: `~/.claude/hooks/memory_lint.py` takes
`--check-all DIR` or stdin-JSON hook input, so a per-artifact file
argument falls through to `run_hook()`, which blocks on stdin (30s
timeout, then a swallowed `TimeoutExpired`) or reads EOF and exits
0. It reported PASS unconditionally — false coverage. The call is
REMOVED rather than repaired: no ratified Phase-1 kind targets a
memory directory, and the linter would have been checking the
outbox wrapper's frontmatter rather than the payload that lands at
the target. Wire it when a memory-targeting kind lands. R3's
"run the memory lint" is therefore **not satisfied in Phase 1** and
is carried as known-open, not quietly claimed.

Coverage after fixes: **95%** on `attune.docs_outbox` (was 92%).
