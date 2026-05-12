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

## Track A — Test signal (sequential, critical path)

These specs feed each other; run in order.

### windows-memory-detection (NEW priority — replaces probes)

- Status: approved — 4-phase plan, Phase 1.1 done; Phase 3.1
  partially done in this worktree (encoding fix to
  `_run_hook` in test_session_continuity_io.py).
- Why first: The 4 actual Windows-only CI failures on main
  fit this spec exactly. One of them (the hook subprocess
  bug) is named in Phase 1.3 by test ID and the encoding
  fix matches Phase 3.1's proposed solution.
- Tasks
  - [x] Phase 1.1 — push diagnostic run (done via PR #245)
  - [ ] Phase 1.2 — promote hypotheses to root-cause notes
  - [ ] Phase 1.3 — diagnose hook subprocess failure
        (this worktree's fix may close it; verify on Windows CI)
  - [ ] Phase 2 — fix memory-feature worker-crash cluster
        (3 tests: redis_auto_detect, memory_features × 2)
  - [ ] Phase 3 — fix hook subprocess wrapper + add guard
        test (encoding fix shipped here; add guard test)
  - [ ] Phase 4 — unblock PR #242 (rebase, ready, merge)
- Spec: [windows-memory-detection](windows-memory-detection/)

### coverage-canonical-pattern — PAUSED 2026-05-12

- Status: paused — premise invalidated. Recent main CI
  failures are Windows-only individual test bugs, NOT the
  `[100%] PASSED → shutdown` OOM pattern the spec was
  designed to fix. See spec's `decisions.md`.
- Re-open only if the OOM/shutdown pattern recurs. Probes
  0a/0b are NOT to be executed — Probe 0a's change is
  already in `tests.yml` and Probe 0b's hypothesis no
  longer matches reality.
- Spec: [coverage-canonical-pattern](coverage-canonical-pattern/)

### coverage-exclusion-policy (Phases 3B–3D)

- Status: approved — 12 tasks, ~17% done (Phase 3A landed)
- Why here: Small. Slot between canonical-pattern phases as a
  context-switch break. Touches the same pytest config.
- Tasks
  - [ ] Phase 3B — audit 3 undocumented exclusions
  - [ ] Phase 3C — document or remove each
  - [ ] Phase 3D — enforcement script + CI gate
- Spec: [coverage-exclusion-policy](coverage-exclusion-policy/)

### windows-xdist-honor

- Status: draft — 4-phase plan, 0% done
- Why deferred: Adjacent concern (is `-n 1` honored on
  Windows). Address only if windows-memory-detection fixes
  alone don't yield 11+/12 green matrix jobs. Strict
  3-iteration cap per the tar-pit trip-wire rule.
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

**windows-memory-detection Phase 2.** Three Windows worker
crashes (`test_redis_auto_detect`, `test_memory_features`
×2) likely share one root cause — a Unix-only probe in
`MemoryFeatures.list_all_features()` or `is_redis_enabled()`.
One fix probably closes all three tests. The hook subprocess
fix (Phase 3.1) shipped in this worktree, so verifying it on
Windows CI is the natural next step alongside Phase 2.

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
