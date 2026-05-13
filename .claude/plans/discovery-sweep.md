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

## DECIDE callouts — Phase 1 resolutions

Search the spec for `**DECIDE:**` to find unresolved context.

| Callout | Where | Resolution |
|---|---|---|
| Severity threshold for queue | `decisions.md` § Output contract | **Resolved 2026-05-13:** severity ≥ medium → queue, low/info → rejected, location-missing → questions |
| Default total budget without `--budget` flag | `decisions.md` § Cost discipline | **Resolved (per `_sequencing.md` note):** $10.00 default |
| Parallel vs serial fan-out | `design.md` § Architecture | **Resolved 2026-05-13:** `asyncio.gather(..., return_exceptions=True)`; crashed source → questions entry |
| Threshold values (severity, confidence) | `design.md` § Verification rules | **Resolved 2026-05-13:** severity rank `critical > high > medium > low > info`; queue threshold = `medium`; confidence threshold = `0.5` |
| `discovery-sweep` in `PATH_ARG_REGISTRY` | `design.md` § CLI integration | **Resolved 2026-05-13:** Category A (`path` kwarg), wired in task P1.7 |
| Exact JSON schema for structured emit | `decisions.md` § Why structured-emit | Open — resolve before P2.1 |
| Five LLM adapters list | `decisions.md` § Why this isn't code-review | Open — resolve before P2.1 |
| `--source <name>` filter | `design.md` § Default sources list | Open — resolve before P3.5 |
| Order of P2.1–P2.6 | `tasks.md` § Phase 2 | Open — resolve before P2.1 |
| Phase 4 in-spec or split | `tasks.md` § Phase 4 | Open — resolve after Phase 3 ships |

---

## Status

- [x] Spec approved (2026-05-13)
- [x] Phase 1 — Engine + PatternScanSource (draft PR open)
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
