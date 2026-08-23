# Design: Workflow Behavioral Validation

**Status**: draft (2026-08-23) — Phase 2. Direction approved by the
chair (all four Phase-1 open questions resolved via recommendations,
2026-08-23; see `decisions.md`). Mechanical gate/config changes remain
gated to execution and are NOT part of this design doc.

Builds on [requirements.md](./requirements.md).

---

## Architecture — two tracks, one program

The test-quality program now has two tracks that share posture but not
mechanism:

| | Coverage track | Behavioral track (this spec) |
|---|---|---|
| Owns | deterministic code | LLM workflow behavior |
| Unit of evidence | line/branch coverage | a passing planted-defect probe |
| Cost | free | LLM-billed |
| Cadence | every push (CI) | gated / on-change / weekly (never per-push) |
| Bar | 85% floor | probe surfaces the planted defect |

The behavioral track's moving parts:

```
fixtures (planted defects) ──> probe runner ──> run-record (JSON)
                                                     │
                              registry projector <───┤
                                     │               │
                              registry table    dispositions ledger
                              (derived)          (hand-authored gaps)
```

## 1. Registry — derived from run-records

**Decision (ruled):** a new tracked artifact under this spec dir,
DERIVED from probe run-records — not the R5 cross-review ledger.

- **Run-record** — one JSON per probe run, reusing the `ops/runs/`
  pattern. Schema: `workflow, fixture, receipt_type, verdict
  (pass|fail|crash), cost_usd, duration_s, ran_at, runner_version,
  evidence`. Written by `scripts/workflow_probe_runner.py`.
- **Registry table** — `registry.md` (or `.csv`), PROJECTED from the
  latest record per workflow by a small script. Verdict/cost/last-run
  cannot lie because they are the last real run (Principle 12: memory is
  derived, never authored in the serving layer).
- **Dispositions ledger** — the ONE hand-authored part, per the
  "derived status column is confidently wrong" lesson: which workflows
  intentionally have no probe, and why (e.g. "no meaningful planted
  defect exists for X"). Without it, "no record" reads as "clean"
  instead of "not yet probed".

Persistence dir: `~/.attune/` for records (machine-local, like
`ops/runs/`); the projected table + dispositions are tracked in-repo.

## 2. Carve — fleet-wide policy, per-workflow activation, probe-gated

**Decision (ruled):** the Principle 5 carve is a fleet-wide *policy*
that activates *per workflow*, and only once that workflow has a passing
probe. Mechanically implemented by seam-split (approach (a));
coverage-advisory is the named retreat if a clean split is impossible
for a given module.

The bright line:

> A workflow module's **LLM-execution driver** graduates to the probe
> bar. Its **deterministic seams** — arg parsing, path validation, the
> result adapter, error classification, budget allocation — keep the
> 85% coverage floor.

Rules that keep "replace the floor" from becoming "no floor":

1. **No probe → full floor.** A workflow module keeps the 85% floor in
   its entirety until it has a passing probe. The carve is *earned*, not
   granted.
2. **Probe → split, then carve.** When a workflow gets its probe, its
   deterministic seams move to a separately-covered helper module; the
   thin driver file is the carved behavioral surface. The split is
   amortized one workflow at a time — never a 20-module big bang.
3. **Reject pragma-no-cover** as the mechanism (it rots and invites
   "exclude the lines the probe happens to hit" — the path-validation
   exclusion lessons). Splitting is also better code.
4. **Retreat position:** if a module genuinely cannot be split cleanly,
   it goes coverage-*advisory* (measured, not gated) with the probe as
   its only gate — recorded per-module in `decisions.md`.

Enforcer implication (execution, gated on the chair ruling being
recorded): `codecov.yml` gains a per-path carve for carved driver files;
`test_coverage_threshold_is_at_least_80` stays as the deterministic-code
drift guard. No config lands before the ruling is in `decisions.md`.

## 3. Gate wiring — one runner, three triggers, release consumes the verdict

**Decision (ruled):** a standalone gated probe job, NOT folded into the
release-prep team; the release process consumes its verdict.

Reasons: billed probes need their own budget envelope; coupling to
`secure-release` (just found returning GO on a dead gate, #2208) is the
wrong dependency; one standalone job serves all three cadences.

| Trigger | Scope | Budget cap | Blocking? |
|---|---|---|---|
| Pre-release gate | affected + gate-critical probes | scaled to scope | yes — a fail blocks release |
| On workflow change | that workflow's probe | ~$1–5 (one probe) | advisory / labeled |
| Weekly scheduled audit | full fleet | **$25–30 hard cap** | advisory |
| On-demand (CLI) | any subset | `--budget` | n/a |

Budget basis: measured $6.70 for 5 probes (discovery-sweep alone $2.6 at
a $5 cap); naive scale to ~20 ≈ $15–25. The $25–30 full-fleet cap is
tied to the $50 API-spend budget — a full sweep is a deliberate budgeted
event. The runner already reports measured spend, so the cap is
validated against reality, not left a guess.

## 4. Rollout & fixture design

**Decision (ruled):** analytical-first, then the gate/fail-open group,
generative last.

**Order:**

1. **Analytical batch** (cheapest, pattern proven): code-review,
   deep-review, perf-audit, refactor-plan, simplify-code, test-audit,
   doc-audit, bug-predict. All plant-a-defect / assert-it's-named; all
   share ONE multi-defect fixture workdir (each probe asserts its own
   defect class). ~8 probes, one fixture pack.
2. **Gate / fail-open group**: secure-release, health-check,
   doc-orchestrator — coordinated with #2207–#2209. These probes ASSERT
   the DEGRADED / NO-GO behavior those PRs add; highest teeth (they
   catch GO-on-dead-gate directly), but blocked on those fixes landing.
3. **Generative last**: test-gen (#2213), doc-gen, rag-code-gen — fix
   first, then the probe (execute the emitted output) guards the fix.

**Fixture design by workflow type:**

| Type | Fixture | Receipt |
|---|---|---|
| Analytical | one shared multi-defect workdir | the planted defect is named, score non-perfect |
| Generative | per-workflow target + output-executor | emitted output actually runs (tests pass / code imports / cited sources resolve) |
| Gate/reporting | fixture that SHOULD fail the gate | verdict fails closed / tracks reality (planted breaking change surfaces) |
| Meta (sweep) | staged multi-defect workdir | no LLM lane $0-and-empty; no lane in failures (built) |

## Risks

1. **The seam-split refactor churns ~20 modules over time.** Mitigated
   by per-workflow amortization and by it being a genuine code
   improvement, but it is real work — the carve rolls out only as fast
   as splits + probes land.
2. **LLM non-determinism.** Assertions stay behavioral, never
   exact-match; today's findings-key near-miss is the cautionary tale.
   Fixture guards run free on every push to keep planted defects present.
3. **Registry projector drift.** The projector is itself code that can
   go stale; it needs its own free unit test (project a synthetic
   record → expected row).
4. **Budget creep.** Full-fleet caps must be re-validated against the
   runner's measured spend as probes are added; the $25–30 cap is a
   starting estimate, not a proof.

## Decisions to make at execution time

- Registry file format (`.md` table vs `.csv`) and the exact run-record
  schema fields.
- Per-workflow: split vs advisory-retreat, recorded as each is worked.
- The pre-release gate's "gate-critical" probe set (which subset always
  runs pre-release vs only-affected).
- Scheduler mechanism for the weekly audit (cron/scheduled-task).
