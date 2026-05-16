# Spec Execution Sequencing

Working order for approved specs as of 2026-05-16. Update
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

- Status: Phases 1–5 shipped; Phase 6 pending. Phase 5 infra
  on `main` (PR #413); Phase 5.4 code-review-emits-recs in
  flight (PR #415, single-flake CI issue not related to the
  change — re-run pending).
- Why after security-hardening: 6 phases, each shippable.
  Phase 1 is pure inspection so it can start anytime. Phases
  3 and 4 shipped together (2026-05-14) for the chaining UX.
- Tasks
  - [x] Phase 1 — workflow registry verification (2026-05-13)
  - [x] Phase 2 — scope picker (dropdown + custom path) (2026-05-14)
  - [x] Phase 3 — persist recent runs (2026-05-14, with Phase 4)
  - [x] Phase 4 — clickable workflow-name pills (2026-05-14, with Phase 3)
  - [x] Phase 5 — structured recommendation channel (2026-05-16,
        infra via #413; 5.4 demo integration in PR #415)
  - [ ] Phase 6 — telemetry + close
- Phase 2 unblocks the discovery-sweep-ops-integration spec
  (per its design dependency on the scope picker) — that spec
  shipped 2026-05-16, see Done.
- Spec: [ops-runner-tier2](ops-runner-tier2/)

### discovery-sweep — done 2026-05-13

- Status: **feature-complete on `main`**. Phase 1, 1.5, 2A, 2B
  (P2.1–P2.6), 3, P2.7 all shipped. Phase 4 (CLI deprecation)
  closes empty — P2.7 surface-evaluation returned zero
  deprecation candidates (KEEP all six standalone audit
  workflows). Phase 3.2 (severity-colored badges) shipped as a
  polish follow-up.
- Tasks
  - [x] Phase 1 — Engine + PatternScanSource (non-LLM floor)
  - [x] Phase 1.5 — Second-pass design landings
  - [x] Phase 2A — Shared LLM adapter base
  - [x] Phase 2B — Six adapters (P2.1 bug-predict, P2.2
        security-audit, P2.3 dependency-check, P2.4 perf-audit,
        P2.5 doc-audit, P2.6 test-audit)
  - [x] P2.7 — Surface evaluation (KEEP all)
  - [x] Phase 3 — Output polish + JSON mode
  - [x] Phase 3.2 — Severity-colored badges
  - [⊘] Phase 4 — CLI deprecation (closes empty)
  - [→] Ops dashboard integration → carved out as
        `discovery-sweep-ops-integration` follow-up spec
- Spec: [discovery-sweep](discovery-sweep/)
- Surface evaluation: [surface-evaluation.md](discovery-sweep/surface-evaluation.md)
- Plan: [.claude/plans/discovery-sweep.md](../../.claude/plans/discovery-sweep.md)

### discovery-sweep-ops-integration — done 2026-05-16

(See Done section for full retrospective.)

### website-update-dashboard-and-fold (Phase 1)

- Status: approved 2026-05-16 (status flip pending via PR #407)
  — 41 tasks, 0% done
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

### workflow-path-arg-unification

- Status: 3 of 5 PRs merged; PR-2 + PR-5 pending. Gates v7.0
  release per [PR #412](https://github.com/Smart-AI-Memory/attune-ai/pull/412)
  changelog rewrite (CHANGELOG-only, all-green CI, awaiting
  scope decision before merge).
- Why here: Follow-up to ops-runner-tier2 Phase 1's bridge
  registry (PR #294). Migrates 5 workflows from
  `project_root` / `src_path` / `cwd` → `path`. After all 5
  land, `PATH_ARG_REGISTRY` collapses to a flat
  `frozenset[str]`.
- Tasks
  - [x] PR-1 — health-check + orchestrated-health-check
        (merged via PR #297)
  - [ ] PR-2 — doc-orchestrator (pending)
  - [x] PR-3 — test-audit (with required-flag handling)
        (merged via PR #298)
  - [x] PR-4 — rag-code-gen (semantic clarification)
        (merged via PR #300)
  - [ ] PR-5 — registry simplification (gated on PR-2)
- Spec: [workflow-path-arg-unification](workflow-path-arg-unification/)

### sibling-subscription-auth — draft (Phase 0 in flight)

- Status: draft 2026-05-15. Phase 0 probe + findings open in
  [PR #406](https://github.com/Smart-AI-Memory/attune-ai/pull/406).
- Why here: Decision gate before any sibling-package auth work.
  Phase 0 result drives PROCEED / DEFER / RETIRE.
- Spec: [sibling-subscription-auth](sibling-subscription-auth/)

### sibling-package-pre-commit — approved

- Status: approved — no tasks tracked here yet
- Why here: Cross-sibling-package pre-commit alignment. Low
  user-visible risk, high developer-experience win.
- Spec: [sibling-package-pre-commit](sibling-package-pre-commit/)

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

### agent-surface-parallelism-evaluation — draft

- Status: draft 2026-05-16. Phase 0 (telemetry + A/B
  measurement) is the gate. Pre-committed decision matrix in
  `decisions.md` routes PROCEED / DEFER / RETIRE based on
  multi-workflow session frequency, wall-clock delta, and
  qualitative synthesis value.
- Why standing: Distinct from the retired `agent-surface-
  rebalance` spec (byte-savings premise was wrong). This is
  the parallelism angle. Phase 0 budget cap $20.
- Cadence: Phase 0 only. Auto-retires if 90 days pass without
  starting OR if matrix routes to RETIRE.
- Spec: [agent-surface-parallelism-evaluation](agent-surface-parallelism-evaluation/)

### doc-stack-reference-subtypes — draft

- Status: draft 2026-05-16. Phase 0 (inventory + hand-crafted
  samples) gates whether the subtype hypothesis is real. Owner
  package is `attune-author` (sibling) — spec lives here per
  the spec-viewer-ia precedent for cross-package work.
- Why standing: Reference template is tabular-only today;
  procedural and free-form variants would improve RAG retrieval
  + readability for skills, commands, and concept docs. Phase 0
  budget cap $10.
- Cadence: Phase 0 only. Auto-retires if 90 days pass without
  starting OR if matrix routes to RETIRE.
- Spec: [doc-stack-reference-subtypes](doc-stack-reference-subtypes/)

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

**Close the open-PR cluster from the 2026-05-16 daily briefing
session** — 5 PRs at the head of the queue all gated on
review/merge decisions rather than additional code:

- [#412](https://github.com/Smart-AI-Memory/attune-ai/pull/412)
  CHANGELOG v7.0 rewrite (docs-only, all CI green, scope-
  decision call).
- [#415](https://github.com/Smart-AI-Memory/attune-ai/pull/415)
  ops-runner-tier2 Phase 5.4 — code-review emits ATTUNE_REC.
  Single CI flake (`test_tracks_retries_in_metrics`); re-run
  the failed Ubuntu lanes.
- [#417](https://github.com/Smart-AI-Memory/attune-ai/pull/417)
  spec-viewer-ia proposal salvage (docs-only).
- [#418](https://github.com/Smart-AI-Memory/attune-ai/pull/418)
  help-IA code-quality triage flow salvage (docs-only).
- [#420](https://github.com/Smart-AI-Memory/attune-ai/pull/420)
  2 new spec drafts: agent-surface-parallelism-evaluation +
  doc-stack-reference-subtypes (docs-only).

Alternatives if you'd rather start fresh work than close out:

- **ops-runner-tier2 Phase 6** — telemetry + close. Smallest
  unit of work that retires a whole spec.
- **agent-surface-parallelism-evaluation Phase 0** — telemetry
  pull (~30 min, no LLM cost) routes a decision matrix that's
  already pre-committed in `decisions.md`.
- **doc-stack-reference-subtypes Phase 0** — inventory pass
  (~30 min) tells us how many features fall into each subtype
  before any generator work.
- **test-quality-program** — opportunistic filler.

Recently shipped:
- 2026-05-16 — `.help` regen (PR #402) — 9 stale features
  refreshed + project docs added.
- 2026-05-16 — ops-runner-tier2 Phase 5 infra (PR #413) —
  structured recommendation channel for run-view.
- 2026-05-16 — discovery-sweep-ops-integration (PR #411) —
  dashboard chips, live progress, drill-in. Spec done.
- 2026-05-16 — ops-security-hardening closeout (PR #409).
- 2026-05-16 — ops-scope-picker-ia AC-6 (PR #410) — scope
  picker renders in read-only mode.
- 2026-05-14 — v6.8.0 PyPI release.

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
  + subscriber queue binding + structured logging. Closeout
  Phase 5 smoke + 6 close tasks via PR #409 (2026-05-16).
- [docs/specs/discovery-sweep-ops-integration](discovery-sweep-ops-integration/) —
  complete 2026-05-16. All four phases shipped: engine
  telemetry hooks, `ATTUNE_DS` stdout emission, sweep-results
  storage primitives, daemon wiring + HTTP route, dashboard UI
  (chips + live progress + drill-in), docs. Carved out from
  the parent `discovery-sweep` spec so the parent could ship
  feature-complete without stalling on its ops-dashboard
  consumer. Feature flag `ATTUNE_OPS_SWEEP_RESULTS=1` gates
  persistence; chips render zero until a sweep has been
  recorded for the current scope.

---

## Proposals (lightweight, not full specs)

These are proposal docs that landed in PRs but don't have the
full spec structure (no requirements / decisions / tasks
breakdown). Tracked here so they don't get lost.

- [docs/specs/spec-viewer-ia/proposal.md](spec-viewer-ia/proposal.md) —
  salvaged 2026-05-16 (PR #417). Approved-status proposal for
  grouping the attune-gui specs page. Cross-package: targets
  `sidecar/attune_gui/templates/specs.html` but hosted here.
  Implementation will land in attune-gui when sequenced.
- [docs/specs/help-ia-code-quality/proposal.md](help-ia-code-quality/proposal.md) —
  salvaged 2026-05-16 (PR #418). Approved audit doc for the
  `.help/templates/code-quality/` 11-kind set; documents the
  triage-flow gap. Artifact (hand-authored `task.md` + how-to)
  landed in the same PR.
