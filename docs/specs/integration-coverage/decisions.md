# Per-phase decisions — Integration Coverage Program

**Status:** parked (2026-07-13; re-affirmed 2026-07-19, chair
ruling T1 of `q-briefing-triage-001`) · Resume-Trigger: evergreen
(no external clock)


Append-only log. One section per phase as it lands. See
`requirements.md` and `tasks.md` for the framework.

Format per entry:

```text
## Phase N — <title>

**Date:** YYYY-MM-DD
**Outcome:** <one-line summary>
**Decision-doc:** <one-line summary of what got decided>

[Body: data summary, rationale, and what the next phase
(if any) needs to know.]
```

---

## Phases 0–1 — audit + revival (record backfilled 2026-07-21)

**Date:** 2026-06-09 → 2026-06-11 (executed; this entry backfilled
2026-07-21 — the receipts had lived only in sibling docs)
**Outcome:** Phase 0 flipped the premise — a 351-test integration
suite already existed, dormant; revive, don't build.
**Decision-doc:** GO reframed as revival; see
[phase0-findings.md](phase0-findings.md) §0.3.

Phase 0 findings landed in
[phase0-findings.md](phase0-findings.md) (§0.1 inventory, §0.2
catchability, §0.3 decision) instead of the `inventory.md` /
`bug_catchability.csv` artifacts the task table named. Phase 1
triage in [phase1-triage.md](phase1-triage.md); revival + CI job
shipped in #703/#704/#727; surface inventory (task 7) in
[surface-inventory.md](surface-inventory.md) (#768); auth nightly
live weekly (#952, triage in
[auth-run-triage.md](auth-run-triage.md)). Remaining on resume:
tasks 8–10 + no-auth required-check promotion.
