# Decisions — Workflow Behavioral Validation

Append-only. See `requirements.md`, `design.md` for the framework.

---

## D1 — Adopt behavioral validation as a second track (2026-08-23)

**Ruled:** chair (Patrick), 2026-08-23.
**Decision:** the test-quality program adopts a second, standing track —
workflow behavioral validation — with the planted-defect probe harness
(`scripts/workflow_probe_runner.py`, `tests/fixtures/workflow_probes/`,
PRs #2210/#2211) as its seed. The coverage track is unchanged.
**Basis:** the fleet-health roundtable found 12/20 workflows marked
"working" on "exited 0" alone; the harness validated 3, caught 2 defects
(#2213, #2214) and a bug in itself. Line coverage on a mocked workflow
is a fictional quality signal.

## D2 — Principle 5 carve: probe replaces floor, per-workflow, probe-gated (2026-08-23)

**Ruled:** chair, 2026-08-23 (form answer "Probe replaces floor" +
"use recommendations").
**Decision:** for LLM workflow modules, a passing planted-defect probe
REPLACES the 85% mocked-coverage floor — but scoped to the
**LLM-execution driver surface only**, not the whole module. The
deterministic seams (arg parsing, path validation, result adapter, error
classification, budget allocation) KEEP the coverage floor.

The carve is a fleet-wide policy that ACTIVATES per-workflow and only
once that workflow has a FRESH passing probe: no probe → full floor;
probe → seam-split so the driver is carved and the seams stay covered.
Mechanism is seam-split (design approach (a)); `# pragma: no cover` is
rejected. **Retreat (corrected by D6): if a module cannot be split
cleanly it gets NO carve — full floor on the whole module plus the probe
as an additive gate.** Whole-module coverage-advisory is rejected (it
would drop the seams' floor). The carve is revocable — a failed, crashed,
or stale latest probe re-arms the full floor (see D6 + design.md).

**Governance note:** Principle 5 is a ratified contract principle with
mechanical enforcers (`codecov.yml`, the threshold drift guard). This
ruling approves the DIRECTION. The mechanical contract-text + enforcer
edits are gated to execution and land in a separate reviewed PR, each
recording the affected workflow — NO gate/config change lands ahead of
that. (Lead-conduct CHAIR-ARMS: the lead does not arm auto-merge on the
governance-text diff; the chair reads and rules it.)

## D3 — Registry is derived, not authored; its own artifact (2026-08-23)

**Ruled:** chair, 2026-08-23 (recommendation accepted).
**Decision:** the probe registry is a new tracked artifact under this
spec dir, PROJECTED from per-run JSON records (reusing the `ops/runs/`
pattern) — not the R5 cross-review ledger. The one hand-authored part is
a dispositions ledger of intentional probe gaps, so "no record" reads as
"not yet probed", never "clean". (Principle 12; "derived status column
is confidently wrong" lesson.)

## D4 — Standalone gated job; release consumes the verdict (2026-08-23)

**Ruled:** chair, 2026-08-23 (recommendation accepted).
**Decision:** one standalone probe job with three triggers — pre-release
gate (blocking), on-workflow-change (labeled), weekly scheduled audit
(advisory) — never in per-push CI (DEC-6). The release process consumes
the job's verdict rather than embedding it; it is NOT folded into the
release-prep team (billed-budget separation; avoids coupling to the
just-fixed secure-release gate, #2208). Budget by trigger; full-fleet
weekly cap ~$25–30, tied to the $50 API-spend budget; validated against
the runner's measured spend.

## D5 — Rollout order: analytical → gate group → generative (2026-08-23)

**Ruled:** chair, 2026-08-23 (recommendation accepted).
**Decision:** probe the analytical workflows first (share one
multi-defect fixture workdir), then the gate/fail-open group
(coordinated with #2207–#2209, asserting their new DEGRADED/NO-GO
behavior), generative workflows last (fix #2213 first, then probe by
executing the emitted output). Fixture design differs by type — see
design.md § Rollout & fixture design.

## D6 — Codex D11 governance cross-review of the carve; 4 findings accepted (2026-08-23)

**Lane:** the D2 carve is a governance-affecting change to a ratified
principle, so per the D11 rule it got a different-model review lane
BEFORE ratification. Codex, run on the spec branch diff; row in
`docs/specs/cross-review/receipts.md` (2026-08-23). All four findings
were Codex-independent — not the lead's prior echoed back.

**Accepted, all four, folded into design.md before ratification:**

1. **(high) Retreat contradicted D2.** "Coverage-advisory for an
   unsplittable module" would drop the floor from the deterministic
   seams too — contradicting "seams keep the floor". Fixed: the retreat
   is now *no carve* — full floor on the whole module + probe as an
   additive gate. Never advisory.
2. **(high) No revocation / freshness.** A one-time historical pass
   would permanently earn the carve. Fixed: the carve tracks the LATEST
   probe and is revocable — a failed/crashed/stale probe re-arms the
   full coverage floor until a fresh pass restores it.
3. **(medium) Registry not reproducible.** Projecting a *tracked* table
   from *machine-local* `~/.attune/` records lets machines disagree and
   stale runs overwrite newer verdicts. Fixed: records feeding the
   tracked table are themselves tracked with `git_sha`/`ran_at`
   provenance, and the projector is monotonic (refuses to regress a
   newer verdict).
4. **(high) Excluding the driver ≠ gating the seam.** A codecov
   per-path carve on the driver does not by itself require the extracted
   seam-helper to meet 85%. Fixed: two enforcers — carve the driver's
   lines AND a positive check that each seam-helper independently meets
   the floor.

**Disposition:** the carve DIRECTION (D2) stands; these are refinements
to how it is specified and will be enforced, not a reversal. Design.md
updated; the mechanical enforcer PR (still gated) must implement both
enforcers from finding 4 and the reproducible projector from finding 3.

## D7 — Second Codex lane (re-lane after D6): 3 findings accepted (2026-08-23)

**Lane:** chair re-invoked `/cross-review codex` on the amended spec to
verify the D6 fixes held before ratifying. Codex, spec branch diff; row
in `docs/specs/cross-review/receipts.md`. The re-lane caught that the
D6 round-1 fixes were STATED but not mechanically coherent — a useful
demonstration that "accepted and folded in" is not the same as "correct".

**Accepted, all three, folded into the spec:**

1. **(high) D2's own text still contradicted D6.** The design.md retreat
   was fixed in D6 but D2's decision text still named whole-module
   "coverage-advisory" as the retreat. Fixed: D2's retreat clause now
   reads "no carve — full floor + additive probe", matching D6.
2. **(high) "Monotonic projector by git_sha" is not implementable.**
   Two arbitrary Git SHAs have no older/newer relation without a history
   walk. Fixed: the projector rebuilds the whole table from the full
   append-only *tracked* record set, selecting the latest `ran_at` per
   workflow; `git_sha` is provenance only, never an ordering key. Because
   records are append-only and tracked, re-projection is idempotent with
   no regression path to guard.
3. **(high) Static coverage config cannot REVOKE a carve.** codecov.yml
   is static and cannot re-arm the floor when a latest probe
   fails/crashes/stales, leaving D2's revocability unenforced. Fixed:
   the carved-driver set is GENERATED from the registry each run (a
   driver is carved iff its latest probe is a fresh pass) and
   drift-guarded, so a workflow drops out of the carve set automatically
   when its probe stops passing — revocation is mechanical, not manual.

**Disposition:** direction still stands; D7 makes the D6 refinements
actually implementable. Two consecutive lanes both found real issues, so
the chair may reasonably want one more re-lane before ratifying, or may
judge the mechanics now sound.

## D8 — Chair answers to the Phase-2 open questions (2026-08-23)

**Ruled:** chair, 2026-08-23, answering requirements.md § Open questions.

1. **Registry format / persistence → new tracked file.** Confirms D3
   (derived, its own artifact, not the R5 ledger).
2. **Carve mechanics → fleet-wide.** The MECHANISM is chosen uniformly
   for the whole fleet — seam-split for every workflow, not a
   per-module menu of split-vs-pragma-vs-advisory. This refines D2:
   there is ONE carve mechanism fleet-wide.
   **Interpretation CONFIRMED by chair (2026-08-23):** "fleet-wide"
   means *uniform mechanism across the fleet*, NOT *carve all ~20
   modules at once*. Per-workflow, probe-gated ACTIVATION (D2,
   cross-review-hardened) stands: a module is carved only once it has a
   fresh passing probe; no probe → full floor. A module that cannot be
   split simply stays fully floored + additive probe (D6/D7).
3. **Pre-release gate wiring / budget → standalone job (D4), full-fleet
   cap uses the large cap but HARD $32 ceiling.** Sets D4's open number:
   the weekly/full-fleet run may use the large cap but must abort rather
   than exceed **$32**. Design.md updated.
4. **Rollout / fixture design → lead's best judgement.** Confirms D5
   (analytical-first, shared multi-defect fixture; gate group next;
   generative last). The lead owns the per-workflow specifics.

## D9 — Requirements RATIFIED; third Codex lane; design mechanics → Phase 3 (2026-08-23)

**Ruled:** chair, 2026-08-23 ("ratify requirements. ok do as you
recommend" — i.e. run the final lane, then ratify).

**Third Codex lane** on the amended spec returned 4 findings — and,
tellingly, ALL FOUR were in design.md's enforcement mechanics; NONE
touched requirements.md. Accepted and folded in:

1. **(high) `ran_at` ordering is skew-prone** — a future wall-clock
   stamp would win indefinitely. Fixed: the projector orders by **Git
   commit order** (authoritative, monotonic for an append-only tracked
   set); `ran_at`/`git_sha` are informational only.
2. **(high) Revocation had no write-back mechanism** — a blocking probe
   failure could leave the last passing record + stale carve checked in.
   Fixed: record-write + carve-config regen is an **always-runs step**
   (pass/fail/crash) that commits the record and opens an automated
   carve-config PR, drift-guarded — independent of the blocking verdict.
3. **(medium) Seam-helper "independent 85%" underspecified** against
   aggregated coverage. Fixed: per-file/per-flag codecov target per
   helper + an explicit source→helper ownership map.
4. **(medium) Stale "split vs advisory-retreat" line** contradicted
   D6/D8. Fixed: "split vs no-carve".

**Ruling:** **Requirements are RATIFIED.** The two-track model, the
Principle 5 carve direction, cadence, non-goals, and the definition of a
validating probe are stable — three consecutive lanes found zero issues
in them. The churn was entirely in design.md's *enforcement mechanics*
(ordering keys, write-back, per-file measurement) — the kind of detail a
prose spec can only gesture at and that real code + tests will pin down.
Per the lead's recommendation, those move to **Phase 3 execution**,
where each mechanic is implemented with its own review lane, rather than
continuing to re-lane a prose document with diminishing returns.

**Still gated:** the mechanical enforcer PR touching Principle 5's actual
gates (codecov config, contract text) is chair-armed only — the lead
does not arm auto-merge on it (CHAIR-ARMS).
