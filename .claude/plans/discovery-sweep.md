# Discovery Sweep — Plan Tracker

**Status:** approved 2026-05-13 — no code shipped
**Spec:** [docs/specs/discovery-sweep/](../../docs/specs/discovery-sweep/)

A meta-workflow that fans out across audit-family workflows (bug-predict, security-audit, dependency-check, perf-audit, doc-audit) and triages findings into three buckets: `queue` (act on), `questions` (need human judgment), `rejected` (filtered noise).

---

## Quick links

- [decisions.md](../../docs/specs/discovery-sweep/decisions.md) — why this exists, design decisions
- [requirements.md](../../docs/specs/discovery-sweep/requirements.md) — user stories + acceptance
- [design.md](../../docs/specs/discovery-sweep/design.md) — architecture, dataclasses, Protocol
- [tasks.md](../../docs/specs/discovery-sweep/tasks.md) — phased plan

---

## Resolved DECIDE callouts (2026-05-13)

| Callout | Resolution |
|---|---|
| Severity threshold for queue | `medium+` → queue, `low/info` → rejected, missing-location → questions |
| Verification thresholds (severity, confidence) | `severity ≥ medium` AND `confidence ≥ 0.5` → queue. Low-severity → rejected; low-confidence → questions (asymmetric by design) |
| `discovery-sweep` in `PATH_ARG_REGISTRY` | Yes — Category A, `kwarg="path"`, `required=False`. Added in P1.7 |
| Default total budget without `--budget` flag | `$10.00`, allocated proportionally via per-source `budget_multiplier` |
| Per-source budget multipliers | bug-predict=1.0, security-audit=4.0, dependency-check=0.5, perf-audit=1.5, doc-audit=1.0, test-audit=1.5. See decisions.md cost discipline |
| Parallel vs serial fan-out | `asyncio.gather` with `return_exceptions=True` |
| Exact JSON schema for structured emit | Sketch in design.md accepted; finalize during P2.1 |
| `--source <name>` filter | Yes — add in Phase 3 CLI flags |
| LLM adapters list (5 vs 6) | **Wrap all six.** Each lens is distinct (test-quality scoring ≠ bug patterns ≠ CVE feed). Retirement framing shifts to **CLI surface deprecation** rather than workflow redundancy |
| Surface evaluation framing | DEPRECATE CLI / KEEP CLI / DEFER per workflow. Workflows stay; CLI entries may deprecate |
| Order of P2.1–P2.7 | bug-predict → security-audit → dependency-check → perf-audit → doc-audit → test-audit → surface eval. Eval runs LAST for full-coverage signal |
| Globs in `--path` | Engine-level expansion. Protocol takes `paths: list[str]`. Sources never see globs |
| Ops dashboard integration (was Phase 4) | Deferred to follow-up spec `discovery-sweep-ops-integration`, triggered when ops-runner-tier2 Phase 2 (scope picker) ships |
| Adapter class mutation | Adapters construct workflow INSTANCES with augmented prompts at call time, never mutate the workflow class |
| Integration test marking | `@pytest.mark.integration` (default-excluded), not `pytest.mark.skipif(not HAS_API_KEY)` — per CLAUDE.md lesson |

## Open DECIDE callouts

**None.** All resolved 2026-05-13.

---

## Status

- [x] Spec approved (2026-05-13)
- [x] All DECIDE callouts resolved (2026-05-13)
- [ ] Phase 1 — Engine + PatternScanSource
- [ ] Phase 2A — Shared LLM adapter infrastructure
- [ ] P2.1 — BugPredictSource
- [ ] P2.2 — SecurityAuditSource
- [ ] P2.3 — DependencyCheckSource
- [ ] P2.4 — PerfAuditSource
- [ ] P2.5 — DocAuditSource
- [ ] P2.6 — TestAuditSource
- [ ] P2.7 — Surface evaluation (empirical, no code)
- [ ] Phase 3 — Output polish + JSON mode
- [ ] Phase 4 — CLI surface deprecation (conditional on P2.7)

---

## Notes for next session

This plan + spec was drafted 2026-05-13 from two queued user prompts that assumed Phase 1 + Phase 2A had shipped. Neither had — nothing existed in any repo. The drafted spec captures the design implied by the prompts, with `DECIDE` callouts on every guess.

**Recommended next action:** read [decisions.md](../../docs/specs/discovery-sweep/decisions.md) and resolve the DECIDE callouts that block P1.4 and P1.5. Then execute Phase 1.
