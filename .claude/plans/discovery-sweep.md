# Discovery Sweep — Plan Tracker

**Status:** Phase 1 in review (draft PR) — Phase 2A not started
**Spec:** [docs/specs/discovery-sweep/](../../docs/specs/discovery-sweep/)

A meta-workflow that fans out across audit-family workflows (bug-predict, security-audit, dependency-check, perf-audit, doc-audit) and triages findings into three buckets: `queue` (act on), `questions` (need human judgment), `rejected` (filtered noise).

---

## Quick links

- [decisions.md](../../docs/specs/discovery-sweep/decisions.md) — why this exists, design decisions
- [requirements.md](../../docs/specs/discovery-sweep/requirements.md) — user stories + acceptance
- [design.md](../../docs/specs/discovery-sweep/design.md) — architecture, dataclasses, Protocol
- [tasks.md](../../docs/specs/discovery-sweep/tasks.md) — phased plan

---

## Open DECIDE callouts

These need resolution before the dependent phase starts. Search the spec for `**DECIDE:**` to find context.

| Callout | Where | Resolve before | Status |
|---|---|---|---|
| Severity threshold for queue | `decisions.md` § Output contract | P1.4 | **resolved 2026-05-13** (medium+) |
| Exact JSON schema for structured emit | `decisions.md` § Why structured-emit | P2.1 | open |
| Five LLM adapters list | `decisions.md` § Why this isn't code-review | P2.1 | open |
| Default total budget without `--budget` flag | `decisions.md` § Cost discipline | P1.5 | $10.00 (in code) |
| Parallel vs serial fan-out | `design.md` § Architecture | P1.5 | **resolved 2026-05-13** (asyncio.gather) |
| Threshold values (severity, confidence) | `design.md` § Verification rules | P1.4 | **resolved 2026-05-13** (medium / 0.5) |
| `--source <name>` filter | `design.md` § Default sources list | P3.5 | open |
| P1.7: `discovery-sweep` in `PATH_ARG_REGISTRY` | `design.md` § CLI integration | P1.7 | **resolved 2026-05-13** (Category A) |
| Order of P2.1–P2.6 | `tasks.md` § Phase 2 | P2.1 | open |
| Phase 4 in-spec or split | `tasks.md` § Phase 4 | After Phase 3 ships | open |

---

## Status

- [x] Spec approved (2026-05-13)
- [ ] Phase 1 — Engine + PatternScanSource (**in review** 2026-05-13)
- [ ] Phase 2A — Shared LLM adapter infrastructure
- [ ] P2.1 — BugPredictSource
- [ ] P2.2 — SecurityAuditSource
- [ ] P2.3 — DependencyCheckSource
- [ ] P2.4 — Retirement evaluation (empirical, no code)
- [ ] P2.5 — PerfAuditSource
- [ ] P2.6 — DocAuditSource
- [ ] Phase 3 — Output polish + JSON mode
- [ ] Phase 4 — Ops dashboard integration (or split to follow-up spec)
- [ ] Phase 5 — Retirement execution (conditional on P2.4)

---

## Notes for next session

This plan + spec was drafted 2026-05-13 from two queued user prompts that assumed Phase 1 + Phase 2A had shipped. Neither had — nothing existed in any repo. The drafted spec captures the design implied by the prompts, with `DECIDE` callouts on every guess.

**Recommended next action:** read [decisions.md](../../docs/specs/discovery-sweep/decisions.md) and resolve the DECIDE callouts that block P1.4 and P1.5. Then execute Phase 1.
