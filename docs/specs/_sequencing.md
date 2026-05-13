# Spec Execution Sequencing

Working order for approved specs as of 2026-05-12. Update
checkboxes as phases land. When a spec completes, move its
entry to the "Done" section at the bottom rather than
deleting it — the history is useful for retros.

---

## Ordering principles

1. Unblock test/coverage signal first — without trustworthy
   CI, every other spec ships on faith.
2. Audit before action — inspection-only phases reshape later
   work and may shrink scope significantly.
3. Parallelize independent tracks — test infra, ops surface,
   and website copy don't contend.
4. Defer release-day work — keep fold/cutover PRs single-
   purpose so they're trivial to review under pressure.

---

## Track A — Test signal (closed)

All Track A specs are now done:
windows-memory-detection (2026-05-12), ignored-tests
(2026-05-12), and coverage-exclusion-policy (2026-05-12).
Two specs remain on the track only as paused/conditional
guardrails — no active work.

### coverage-canonical-pattern — PAUSED 2026-05-12

- Status: paused — premise invalidated. Recent main CI
  failures were Windows-only individual test bugs, NOT the
  `[100%] PASSED → shutdown` OOM pattern the spec was
  designed to fix. See spec's `decisions.md`.
- Re-open only if the OOM/shutdown pattern recurs.

### windows-xdist-honor — CONDITIONAL

- Status: draft — 4-phase plan, 0% done
- Do not pre-schedule. Open only if Windows CI regresses
  with `-n auto` not honored. Strict 3-iteration cap per
  the tar-pit trip-wire rule.
- Spec: [windows-xdist-honor](windows-xdist-honor/)

---

## Track B — Audit work (parallel, low risk)

Inspection only. Output is a decision doc, not code. Safe to
run alongside Track A.

### ops-specs-features (Phase 0 unblock)

- Status: approved & prioritized 2026-05-11; gate condition
  0.1b now satisfied (main green as of `bb0d8aec`,
  2026-05-12). Phase 0.5 re-check still pending.
- Why here: Pure verification step (re-check usage and
  scope) gates the port-of-features implementation work.
  Cheap to close.
- Tasks
  - [ ] Phase 0.1b — confirm CI condition
  - [ ] Phase 0.5 — re-check porting scope vs current usage
  - [ ] Phase 1+ — implementation (after gate)
- Spec: [ops-specs-features](ops-specs-features/)

---

## Track C — Product surface (parallel, independent)

No coupling to Track A or B. Pick up whenever Track A hits a
natural pause.

### ops-security-hardening

- Status: approved — 27 tasks, 0% done
- Why early in Track C: Smallest spec, single phase, highest
  user-visible safety win. Good "ship a thing today" pick.
- Tasks
  - [ ] TrustedHostMiddleware + allowlist
  - [ ] Subscriber queue binding
  - [ ] Structured logging on run-view
  - [ ] Verification — output survives refresh
- Spec: [ops-security-hardening](ops-security-hardening/)

### ops-runner-tier2

- Status: approved — 37 tasks, 0% done (largest spec)
- Why after security-hardening: 5 phases, each shippable.
  Phase 1 is pure inspection so it can start anytime. Phases
  3 and 4 ship together for the chaining UX.
- Tasks
  - [ ] Phase 1 — workflow registry verification
  - [ ] Phase 2 — scope picker (dropdown + custom path)
  - [ ] Phase 3 — persist recent runs
  - [ ] Phase 4 — clickable workflow-name pills
  - [ ] Phase 5 — structured recommendations
- Spec: [ops-runner-tier2](ops-runner-tier2/)

### discovery-sweep — Phase 1 in review

- Status: spec approved 2026-05-13. Phase 1 (engine, FindingSource
  Protocol, verification rules, PatternScanSource adapter, CLI
  registration) submitted as a draft PR 2026-05-13. Phase 1 DECIDE
  callouts resolved (severity threshold = medium+, confidence
  threshold = 0.5, asyncio.gather fan-out, Category A in
  PATH_ARG_REGISTRY, default budget $10.00). Phase 2 callouts
  still open.
- Why on Track C: New user-facing capability — a meta-workflow
  that fans out across audit-family workflows (bug-predict,
  security-audit, dependency-check, perf-audit, doc-audit) and
  triages findings into queue / questions / rejected buckets.
  Independent of test-signal and audit tracks.
- Coordination note: P2.4 retirement evaluation may shrink the
  audit-family workflow surface — coordinate with ops-runner-
  tier2 if any retired workflow appears in `PATH_ARG_REGISTRY`.
- Tasks
  - [ ] Phase 1 — Engine + PatternScanSource (non-LLM floor) — **in review** 2026-05-13
  - [ ] Phase 2A — Shared LLM adapter base
  - [ ] Phase 2B — Per-source adapters (P2.1–P2.6, includes
        retirement eval P2.4)
  - [ ] Phase 3 — Output polish + JSON mode
  - [ ] Phase 4 — Ops dashboard integration (may split out)
  - [ ] Phase 5 — Retirement execution (conditional on P2.4)
- Spec: [discovery-sweep](discovery-sweep/)
- Plan: [.claude/plans/discovery-sweep.md](../../.claude/plans/discovery-sweep.md)

### website-update-dashboard-and-fold (Phase 1)

- Status: approved — 41 tasks, 0% done
- Why split: Phase 1 is pre-fold copy/page work. Phase 2 is a
  one-line PR on v7.0 tag day — do not pre-schedule it.
- Tasks (Phase 1)
  - [ ] Dashboard feature page
  - [ ] Homepage + install copy refresh
  - [ ] FAQ additions
  - [ ] Migration banner
- Tasks (Phase 2 — gated on v7.0 release)
  - [ ] Swap install command constants
  - [ ] Retire pre-fold banner
  - [ ] Add redirects
  - [ ] Enable automated screenshots
- Spec: [website-update-dashboard-and-fold](website-update-dashboard-and-fold/)

---

## Track D — Standing umbrella (opportunistic)

No start/end date. Slot a module whenever there's spare
context between bigger work. Use the rubric to pick.

### test-quality-program

- Status: approved — 8 phases, 0% done; umbrella spec
  codifying the COVERAGE_BUG_LOG playbook (~22% bug-find
  rate across 80 prior modules).
- Why standing: Module-by-module, not a single deliverable.
  Re-orients prior 100%-coverage chase to "meaningful
  coverage on customer-facing paths + test-reliability
  hardening."
- Cadence: One module per session, picked by rubric.
- Spec: [test-quality-program](test-quality-program/)

### integration-coverage — draft

- Status: draft 2026-05-13; complement to
  test-quality-program. Phase 0 audit gates whether a
  framework gets built at all.
- Why standing: Per-module coverage has known structural
  blind spots (cross-module integration, real LLM
  behavior, concurrency, process-shaped bugs). Phase 0
  classifies the last 30 days of bugs to test whether
  any mechanism justifies its cost.
- Cadence: Phase 0 is a one-shot audit (~3 hours); Phase
  1+ designed only after the audit data lands.
- Spec: [integration-coverage](integration-coverage/)

---

## Track E — Conditional / contingent (do not pre-schedule)

Open only if a trigger condition fires.

### larger-runners — draft

- Status: draft, post-Probe-C revision. Originally rescue
  for OOM; now about *headroom and speed*, not rescue.
- Trigger: CI duration becomes a constraint, or a workflow
  consistently hits worker-memory ceilings on default
  runners.
- Spec: [larger-runners](larger-runners/)

---

## Sequencing rationale (positive reasons)

- Track A first means every later spec lands against green,
  trusted CI. We stop fighting test infrastructure mid-
  feature.
- Audit-then-decide on redis-decoupling protects against
  scope creep — Phase 3A may halve the remaining work.
- Parallel tracks B + C mean the day doesn't bottleneck on a
  single thread. If coverage-canonical-pattern probes stall,
  ops-security-hardening is a clean checkpoint.
- Skipping fold-day work keeps the v7.0 release PR pristine.

---

## Today's recommended pick

**ops-runner-tier2 Phase 1.3** — implement the
`PATH_ARG_REGISTRY` dict per PR #285's audit. The audit
proved hypothesis H2 right (workflow `--path` support is
uneven) and proposed a three-way registry (Option 2) instead
of the spec's literal binary. ~50 LoC: registry dict in
`src/attune/ops/data.py` + drift-guard test in
`tests/unit/ops/test_path_support_registry.py`. Once landed,
Phases 2–5 of ops-runner-tier2 can read the registry and
ship the scope picker.

Alternative: **test-quality-program** — continuous module-
by-module work via the rubric. Slot whenever there's spare
context between bigger work.

---

## Done

- [docs/specs/ci-debt](ci-debt/) — complete 2026-05-10
- [docs/specs/telemetry](telemetry/) — complete
- [docs/specs/test-infrastructure](test-infrastructure/) —
  core work complete 2026-05-09 (follow-up: `ignored-tests`)
- [docs/specs/ignored-tests](ignored-tests/) — complete
  2026-05-09; 3 files retired, 1 reconciled (single-fixture
  fix), pytest.ini clean, +35 tests recovered. Docs closed
  2026-05-12.
- [docs/specs/windows-memory-detection](windows-memory-detection/) —
  complete 2026-05-12. Four Windows-only test failures
  resolved (PRs #260, #261). `-n auto` restored across the
  matrix (PR #242).
- [docs/specs/probe-c-memory-investigation](probe-c-memory-investigation/) —
  ✓ resolved 2026-05-11; threading-patch fix in PR #212
  commit `bcc6bdec` closed the OOM concern.
- [docs/specs/coverage-exclusion-policy](coverage-exclusion-policy/) —
  complete 2026-05-12 (PR #272). Inline-comment policy + audit
  resolution + enforcement script (`scripts/check_coverage_omits.py`)
  + pre-commit hook. 60/60 production-code `omit` entries
  documented (100% compliance).
- [docs/specs/redis-decoupling](redis-decoupling/) — **partial**
  2026-05-12. P1 (PR #279) deleted `attune.coordination/` with
  deprecation shim. P2 (PR #281) dropped `[memory]` extra,
  slimmed `[developer]`. P3 audited as mostly no-op (P1 already
  covered the test deletions necessary for green CI). Full
  decoupling deferred per Phase A audit (would require a
  memory-subsystem rewrite, not a delta).
- [docs/specs/ops-specs-features](ops-specs-features/) —
  Phases 1–3 complete (PRs #236, #239, #249); Phase 4
  reflection cycle awaiting 2 weeks of usage data (target:
  2026-05-25). Phase 0 audit verified 2026-05-12 (PR #290).
- [docs/specs/ops-security-hardening](ops-security-hardening/) —
  complete 2026-05-12 (PR #280). DNS-rebinding fix cluster
  + subscriber queue binding + structured logging.
