# Telemetry / Models Layering — decisions

Running log of decisions and open questions. Newest first.

## Open questions (need Patrick before Phase 3)

- **OQ-1 — Facade vs. break.** Phase 3 assumes a thin back-compat facade
  per split module (NFR-1). Alternative: a hard break with a deprecation
  shim and a one-release migration window. Facade is lower-risk but
  carries a permanent indirection. **Default: facade** unless Patrick
  wants the clean break.
- **OQ-2 — Singleton removal scope.** FR-4.3 removes the `UsageTracker`
  and `get_auth_strategy` singletons. This touches `mcp/server.py`,
  `gates/meter.py`, `help/feedback.py`, `outline_stage.py`. Confirm we
  want DI threaded through all call sites vs. keeping a process-level
  default instance wired at the entry point only.
- **OQ-3 — Phase independence.** Can Phases 1, 2, 4.4 (the flush-race
  fix) ship as standalone PRs ahead of the big SRP splits? They are
  low-risk and independently valuable. **Proposed: yes** — Phase 1 and
  the flush-race fix don't need the splits.

## Decisions

- **D0 (2026-06-29) — Spec scope.** This spec owns ONLY the architectural
  items deferred from #1167 and #1168; the correctness/security/perf
  fixes already shipped in those PRs. Source of findings: the four
  step-2 `code_review` runs (auth_strategy 51, registry 58, feedback 63,
  usage_ping 71) + the usage_tracker review.
- **D1 (2026-06-29) — Phase 1 first.** Pricing single-source is the
  highest-leverage, lowest-blast-radius theme and retires the standing
  `project_model_pricing_three_sites` memory item, so it leads. The 1000×
  cost bug (#1168) is evidence the hand-maintained constants are a live
  hazard, not a theoretical one.
- **D2 (2026-06-29) — Splits land last, behind facades.** SRP splits
  (Phase 3) are the riskiest (they break callers); they start only after
  Phases 1–2 remove the upward coupling that makes the splits painful,
  and each lands behind a back-compat facade (NFR-1).

## Cross-references

- `project_model_pricing_three_sites` (memory) — the pricing-duplication
  item FR-1 retires.
- PR #1167 — usage_tracker correctness/security/perf fixes (flush-race
  bug flagged there, fixed here in FR-4.4).
- PR #1168 — auth_strategy/registry/usage_ping/feedback fixes (the 1000×
  cost-math Critical that motivates FR-1).
