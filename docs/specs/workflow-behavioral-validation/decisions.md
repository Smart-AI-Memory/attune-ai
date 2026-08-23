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
once that workflow has a passing probe: no probe → full floor; probe →
seam-split so the driver is carved and the seams stay covered. Mechanism
is seam-split (design approach (a)); `# pragma: no cover` is rejected;
coverage-advisory is the named per-module retreat if a clean split is
impossible.

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
enforcers from finding 4 and the monotonic projector from finding 3.
