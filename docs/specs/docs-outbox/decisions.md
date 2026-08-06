# docs-outbox — decisions

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
