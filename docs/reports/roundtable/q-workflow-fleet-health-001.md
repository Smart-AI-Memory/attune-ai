# Round table — workflow fleet health (2026-08-23)

Thread: `q-workflow-fleet-health-001` (Redis board, TTL 7d). Full
transcript (moderator development data, untracked):
`~/.attune/reports/roundtable/q-workflow-fleet-health-001.md`.

All 20 dashboard workflows (bug-predict excluded — fixed that morning)
were probed with real dashboard-shaped runs (`attune workflow run
<name> [--path]`, LLM-real, ~$18 API). Seats: claude, codex,
antigravity — one round, converged.

## Chair-promoted findings (2026-08-23)

1. **secure-release fails open** (Sev1, unanimous): both sub-workflows
   died (SDK subprocess), zero checks executed, yet the pipeline
   returned `success=True, go_no_go='GO', "All checks passed"`.
   Violates contract P7 (a failed gatekeeper fails the gate).
   → chip `task_df481436` (fail-closed sentinel, mirroring
   #2204/#2205).
2. **health-check fabricates perfection / doc-orchestrator reports "no
   gaps" when its scout never loaded** (Sev2/5): 100/100 grade A in
   9s/$0 with `coverage_percent=100.0` on an ~85-90% repo. Fix per the
   table's bifurcation: gates fail closed; advisory surfaces show
   DEGRADED / N-A, never fabricated numbers.
   → chip `task_ca1c3c49`.
3. **Trust probes for "working" verdicts**: on a clean small target,
   "found nothing" cannot distinguish clean from blind — planted-defect
   fixtures promoted into the test-quality program.
   → chip `task_a37e52f7`.
4. **Containment now**: dashboard reliability badges on secure-release
   and health-check until the fixes land (this PR;
   `RELIABILITY_NOTICES` in `src/attune/ops/data.py` — the fixing PR
   removes the entry).

## Recorded, not promoted

- doc-gen + research-synthesis fail deterministically (same
  `claude_agent_sdk.query()` transport as 12 working workflows — the
  discriminator is per-call options, not transport; SDK env drift
  0.2.116 vs lockfile 0.2.105 is real but explains neither break).
- fix / rag-code-gen are dashboard-unrunnable (required `goal`/`query`
  the Run button cannot supply).
- release-prep's $0 rule-based degrade is the fleet's counterexample:
  it degraded, said so, and still produced a real FAIL verdict.
