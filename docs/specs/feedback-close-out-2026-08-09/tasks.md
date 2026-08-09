# Feedback Close-Out 2026-08-09 — Tasks

**Status:** active (2026-08-09) — chair-approved with lead
ordering authority; T1-T3 execute in one docs PR, T4 is
monitor-gated on the concurrent chip session.

Lead ordering rationale: ratifications and closures first (T1/T2
are merge-now decision entries with zero design content), the
cadence amendment next (small design call, chair-reviewable in
the same PR), and the CHANGELOG callout LAST because it is
already in flight in chip session task_0630d99f — duplicating the
edit recreates the both-append conflict class; verifying beats
racing.

| # | Task | From | Status | Notes |
|---|------|------|--------|-------|
| 1 | Record task-2 void ratification as memory-security-hardening D7 (form-selection receipt quoted) | F2/R1 | done | this PR |
| 2 | US-3 UNRESOLVED closure entry in usage-signals decisions.md + status-line note | F3/R2 | done | this PR |
| 3 | US-4 cadence amendment entry + launchd template `scripts/launchd/com.smartaimemory.attune.reach-snapshot.plist`; install chair-gated | F4/R3 | done | this PR; amendment is chair-reviewable at merge |
| 4 | Verify chip PR lands the 11.6.0 premium callout; direct-write ONLY on chip stall/miss | F1/R4 | monitor | chip task_0630d99f in flight |
