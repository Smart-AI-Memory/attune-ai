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

- **Run-record** — one JSON per probe run. Schema: `workflow, fixture,
  receipt_type, verdict (pass|fail|crash), cost_usd, duration_s,
  ran_at, runner_version, git_sha, evidence`. Written by
  `scripts/workflow_probe_runner.py`.
- **Registry table** — `registry.md` (or `.csv`), PROJECTED from the
  records by a small script. Verdict/cost/last-run cannot lie because
  they are the last real run (Principle 12: memory is derived, never
  authored in the serving layer).
- **Dispositions ledger** — the ONE hand-authored part, per the
  "derived status column is confidently wrong" lesson: which workflows
  intentionally have no probe, and why (e.g. "no meaningful planted
  defect exists for X"). Without it, "no record" reads as "clean"
  instead of "not yet probed".

**Reproducibility (finding 3 from the D2 Codex cross-review, accepted).**
A tracked registry table cannot be projected from machine-local
`~/.attune/` records — different machines would produce different
"latest" rows, and a stale machine could overwrite a newer tracked
verdict. So:

- The run-records that feed the **tracked** registry are themselves
  **tracked** (committed under this spec dir / the reports corpus),
  append-only, each carrying `ran_at` + `git_sha` provenance. Ad-hoc
  local runs may still write to `~/.attune/` for scratch, but only
  committed records feed the tracked table.
- The projector selects, per workflow, the record with the **latest
  `ran_at`** across the full committed record set, and rebuilds the
  whole table from scratch each run — it does NOT diff against the
  existing table. Because the record set is append-only and tracked, a
  re-projection is deterministic and idempotent: there is no
  local-overwrite path to guard against, so no cross-record ordering
  comparison is needed. (`git_sha` is provenance only — NOT an ordering
  key; two arbitrary SHAs have no "older/newer" relation without a
  history walk, so ordering is by `ran_at`, a monotonic wall-clock
  stamp. Clock-skew across machines is bounded by records being
  committed in Git order, and ties break on the committing order.)
- The projector gets its own free unit test (synthetic records →
  expected table, including two records for one workflow → latest
  `ran_at` wins).

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

Rules that keep "replace the floor" from becoming "no floor"
(findings 1, 2, 4 from the D2 Codex cross-review, all accepted —
see `docs/specs/cross-review/receipts.md`, 2026-08-23):

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
4. **The carve tracks the LATEST probe, and is revocable (finding 2).**
   The carve is contingent on the workflow's *most recent* probe
   passing AND being fresh (within a staleness window — starting
   proposal: the probe must have passed on or after the workflow
   driver's last change, and no older than the last release). A
   subsequent failed, crashed, or stale probe **re-arms the full
   coverage floor** for that module until a fresh pass restores the
   carve. A one-time historical pass never permanently earns the carve.
5. **Retreat = no carve, NOT advisory (finding 1).** If a module
   genuinely cannot be split cleanly, it does **not** get the carve: it
   keeps the full 85% floor on the whole module AND runs its probe as an
   *additive* gate (both must hold). "Coverage-advisory for the whole
   module" is explicitly rejected — it would drop the floor from the
   deterministic seams too, contradicting the bright line. Recorded
   per-module in `decisions.md`.

Enforcer implication (execution, gated on the chair ruling being
recorded). The carve is **derived from the registry, not a static
hand-maintained path list** — this is what makes revocation (rule 4)
mechanical rather than aspirational (round-2 finding 3):

- The set of carved driver files is **generated** from the registry each
  run / pre-release: a workflow's driver is carved **iff** its latest
  probe is a fresh pass. A failed/crashed/stale latest probe drops the
  workflow from the generated carve set, so its full floor re-applies
  automatically — no human toggles a static list. The generated carve
  config is checked in and regenerated by the same job that runs probes;
  a drift guard fails CI if the committed carve set does not match what
  the registry would generate (so a stale carve can't linger).
- A **positive** enforcer requires each extracted seam-helper module to
  meet the 85% floor independently (finding 4) — excluding the driver is
  not enough; "seams keep the floor" must be a check that FAILS when a
  seam-helper drops below 85%, not merely the absence of a check on the
  driver.

So there are two static checks (driver carve-out + seam-helper floor)
PLUS the dynamic driver: coverage config is a projection of registry
state, regenerated and drift-guarded, never hand-edited.
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
| Weekly scheduled audit | full fleet | **$32 hard cap** (chair-set) | advisory |
| On-demand (CLI) | any subset | `--budget` | n/a |

Budget basis: measured $6.70 for 5 probes (discovery-sweep alone $2.6 at
a $5 cap); naive scale to ~20 ≈ $15–25. The full-fleet run uses the large
cap but a **hard $32 ceiling** (chair-set, 2026-08-23) — a full sweep is
a deliberate budgeted event within the $50 API-spend budget. The runner
enforces the cap via `ATTUNE_MAX_BUDGET_USD` and reports measured spend,
so the ceiling is validated against reality, not left a guess; the job
must abort rather than exceed $32.

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
