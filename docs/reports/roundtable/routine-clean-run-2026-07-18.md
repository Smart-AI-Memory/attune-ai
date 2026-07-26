# Round table — clean-run digest 2026-07-18 (archival promotion)

**Thread:** `routine-clean-run-2026-07-18` · **Fired:** 2026-07-18
(weekly clean-run routine) · **Promoted:** 2026-07-22 (chair ruling:
archival — all findings verified stale-resolved at promotion time)
· **Rulings:** 0 action items (the archive is the ruling).
`record_rulings(thread, 0)` returned False — the appendix state
file (`~/.attune/ops/triage_appendix.json`) does not exist yet; it
is first created by a live routine fire, so this digest predates
the ledger and cannot feed the T4 auto-demote counter. Recorded
here instead as the honest paper trail.

## Why archival

The digest sat unruled for four days; by promotion time every
finding had been independently resolved. The chair chose a durable
record over deliberate expiry. Each item below carries its
status-as-of-2026-07-22.

## #1 — question (moderator): check battery

Keyless check results of 2026-07-18: collaboration-preflight PASS
with warnings (6 working-tree changes preserved; main 1 behind
cached origin/main), branch `claude/multi-llm-round-table-53f0b2`;
keyless unit suite FAILING at the time (per seat positions below).

## #2 — position (claude): ABSENT

`ABSENT — exit 1: Failed to authenticate. API Error: 401 Invalid
authentication credentials.`
**Status 2026-07-22:** resolved by the backlog (c) ruling — the
claude seat runs the API-key path (launchd plist sources
`anthropic.env`); the 07-27 06:00 fire is the live verification.
The 07-22 dry-run rehearsal (plist-exact env) exited 0.

## #3 — position (antigravity)

Ranked: (1) capabilities drift — site advertised 24 skills, 25
shipped (CRITICAL); (2) asyncio teardown `Event loop is closed`
noise; (3) main 1 behind; (4) 6 uncommitted changes.
**Status 2026-07-22:** (1) fixed on main (25) and moving to 26 in
the staged 10.7.0 website branch; (2) known-cosmetic, documented in
the session starter with an explicit don't-misread note (exit code
unaffected); (3)/(4) transient states, long since moved.

## #4 — position (codex)

"The tree is not clean-run healthy because the keyless unit gate
fails" + the same capability-count drift and teardown noise.
**Status 2026-07-22:** the keyless unit suite ran 18,260-green in
the 07-22 rehearsal; drift fixed as above.

## Chair ruling (2026-07-22)

Promote the whole thread as an archival record (items #1–#4); zero
action items ruled — everything already resolved through other
work. The rulings-count recording was attempted and is a no-op
until the appendix ledger exists (see header note); the Monday
06:00 fire creates it, and digests from then on feed the
two-zero-ruling auto-demote counter (T4). No follow-up work items
originate here.
