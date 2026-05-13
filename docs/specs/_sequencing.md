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

### redis-decoupling (Phase 3A only for now)

- Status: approved — 12 tasks, ~17% done
- Why parallel: Phase 3A is pure audit; findings may shrink
  the spec if internal callers are fewer than feared.
- Tasks
  - [ ] Phase 3A — audit internal Redis usage
  - [ ] Decision gate — re-scope based on findings
  - [ ] (Later) Phase B+ — implementation
- Spec: [redis-decoupling](redis-decoupling/)

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

**redis-decoupling Phase 3A** — pure audit, no code. Walk
internal callers of the Redis facade (`RedisShortTermMemory`
and its 15 submodules, plus `RedisAutoDetector`) and produce
a count + categorization. Output is a decision-doc update.
Findings likely shrink the spec — if internal callers are
fewer than feared, Phase B's implementation budget drops.

Why this over a Track C pick: Track A's just-closed Phase 3C
script gives us a clean enforcement loop on coverage debt, so
audit-mode work is the next-cheapest lever. Track C starts
shipping real product surface — better to start that *after*
the Redis scope is known.

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
