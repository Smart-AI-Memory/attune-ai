# Retro — the round-table integration (2026-07-18 → 2026-08-18)

**Date:** 2026-08-18 · **Provenance:** single-seat retrospective
(Claude, chair-requested in session), NOT a board thread — no
transcript exists; every claim below cites a tracked artifact.
**Chair:** Patrick (requested and promoted this report).
**Sources:** `docs/specs/agent-round-table/decisions.md`,
`docs/specs/roundtable-triage/`,
`docs/specs/roundtable-producing-team/`,
`docs/reports/roundtable/` (16 promoted reports at writing),
`.claude/lessons.md` (roundtable-derived entries),
`src/attune/roundtable/` + `tests/unit/roundtable/`.

## Verdict

The integration worked, and the record shows why: the wins came
from the governance structure — receipts, refute-first lanes,
chair-gated promotion, hard caps — not from the multi-model roster
itself. The models supplied perspective; the structure converted
perspective into decisions that survived contact with the real
system. The dominant cost center was never deliberation quality —
it was seat environment fragility.

## What worked (receipts inline)

- **Dogfood-first validation.** Probe-001 (day one) produced three
  distinguishable positions, and the chair overruled a UNANIMOUS
  member recommendation using context the members lacked (the
  plugin-manifest consent moment). The human-in-the-loop shape the
  design bet on, demonstrated before P0 hardened.
  (`agent-round-table/decisions.md`, Probe-001.)
- **The routine paid for itself on run one.** Clean-run #1 caught
  three real defects: seat env inheritance breaking auth, a SILENT
  synthesis failure, and genuine website-count drift from the 25th
  skill. (Decisions, "P3 manual proof runs".)
- **Prove-before-automate was vindicated exactly.** The skeptic
  merge was held for the first scheduled fire; the 2026-07-27 fire
  then failed on two environment faults invisible to CI — the one
  unproven surface was precisely where the failures lived. Green
  fire 2026-07-28 flipped the spec to shipped. (Decisions,
  2026-07-20 final-review clause + 2026-07-28 entries.)
- **Failure containment held under real failure.** All four
  2026-07-19 producing runs failed BEFORE staging (`staged: 0`, R8
  honored) — zero unruled content reached the chair; each failure
  carried a taxonomy code; salvage was archived and re-runs
  succeeded. (`producing-runs-20260719-failure-archive.md`.)
- **Anti-machinery instincts were consistently right.** P1
  specialist agents CUT unanimously; baseline numbers ruled a
  report line, not a ledger; stale digests get recorded zeros +
  TTL expiry, not archival accretion. Three separate moments where
  the boring shape beat the impressive one, each with recorded
  rationale. (Decisions: 2026-07-21 extensions, 2026-07-28
  baseline ruling, 2026-07-22 digest policy.)
- **The table's best exports are epistemics, not decisions.** The
  strongest durable outputs are judgment rules the deliberations
  generated: the census rule (a proposed src/-wide refactor shrank
  to 4 references via a 20-line AST count), checkability-over-
  confidence (the hedged claim was live; the confident one was
  refuted by one `ls`), reconcile-not-transcribe at promotion, and
  grep-checking causal prose in launch copy. The seats' role was
  often to produce the QUESTION that a cheap script then answered
  decisively. (`.claude/lessons.md`, 2026-07-28 cluster;
  `q-conftest-env-scrub-001.md`.)

## What it cost

- **Environment fragility dominated every failure class.**
  Child-CLI 401s in three distinguishable flavors; an exported
  API key silently shadowing subscription auth; a revoked OAuth
  token; a stale `claude login` instruction that no-ops on CLI
  2.1.220 (three diagnostic rounds lost); stale `REDIS_URL`;
  ambient `ATTUNE_*` poisoning a brief so seats reasoned correctly
  from a wrong premise. Nearly all hardened since (provider-clean
  scrub + guard, conftest env scrub + drift guard, fail-fast board
  check, streamed progress) — but that hardening was most of the
  integration's real labor, and none of it was visible to CI.
- **Shipping tax on plugin surfaces.** The 25th skill touched five
  surfaces; the website half only failed in the FULL suite
  (17,608 tests deep). (Lessons, 2026-07-18.)
- **The chair is the scarce resource, and remains unmeasured in
  practice.** Chair-latency telemetry was added presciently and
  rubber-stamp decay was named as a skeptic failure mode on day
  one — but no tracked artifact yet shows either being READ.
  ~16 promoted reports in three weeks is healthy output and also
  a load curve worth watching before it saturates.

## Transferable principle

Adversarial structure plus cheap verification beats model
quantity, and the human chair is where surprising information
enters the system. Every mechanism that worked — dissent-with-cite,
lesson-lane lint, R8, invocation caps — is a way of making an
agent's claim falsifiable before it costs anything. The principle
is now load-bearing beyond the table (cross-review lanes; the
removing-dead-code gate applied to the 2026-08-18
DocumentManagerWorkflow deletion).

## Open threads (state at promotion — unverified from this clone)

Recorded per the reconcile-not-transcribe rule: these were open as
of writing and live on the moderator's machine, not in the repo.

1. **Weekly fire health since 2026-07-28.** The record-zeros
   policy means quiet weeks leave no tracked trace by design;
   an occasional local check of the appendix ledger
   (`~/.attune/ops/triage_appendix.json`) and the launchd log is
   the verification path.
2. **P4 role telemetry readout.** Whether enough events have
   accumulated to read the skeptic dissent hit-rate and chair
   latency trend (aggregates are min-N gated by design).
3. **Chair-waived lessons.** Any entries still carrying
   `unverified — design rationale (chair-waived)` await their
   evidence upgrade.
