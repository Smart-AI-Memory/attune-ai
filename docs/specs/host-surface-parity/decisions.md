# Host Surface Parity — Decisions

## D1 — Three chair rulings at intake (2026-09-03, chair)

Recorded from the Cowork session that produced this spec. The Claude
seat proposed; the chair ruled. The options declined are recorded so
the table does not re-pitch them.

**D1a — Local models' first job is a `LOCAL` tier for low-stakes
roles.** Recall re-ranking, lesson classification, triage pre-sort,
skeptic/countersign at low stakes, fact-check probes. Seats
unchanged for now. *Declined:* a fourth round-table seat now;
"both, LOCAL first" (the chair chose the narrower ruling; a seat
remains a later, separate question).

**D1b — Extensions are the seam.** Providers, memory backends and
seats arrive through the trust-gated `attune.extensions` system
ruled in release-16-manifest D1/D2. This spec sequences behind
passenger 4 for R6 and never edits a roster tuple to add a vendor.
*Declined:* keeping roster and providers as in-tree tuples this
cycle.

**D1c — The deliverable is a spec under `docs/specs/`.** This
directory is the chair's R4 approval for these files and nothing
else; the round-table brief artifact stays the companion page.
*Declined:* a roadmap page only; both.

## D2 — `LOCAL` tier mechanics (PROPOSED 2026-09-03 — NOT RULED)

D1a names a `LOCAL` tier; the mechanics have two honest options.

- **(a) Enum member.** Add `LOCAL = "local"` below `CHEAP` in all
  four tier copies and the `attune-rag` mirror in one release, with
  `tests/unit/test_model_tiers_drift.py` as the receipt. Pricing
  zero; spend gate records tokens for volume. *Cost:* a coordinated
  attune-rag release. *Benefit:* routing, telemetry tiles and cost
  reports all understand the tier without special cases.
- **(b) Routing label.** Leave the enum alone; add a `role → target`
  table where a target is a tier or an enabled extension. *Cost:* a
  second routing vocabulary beside the tier; ops tiles need a case
  for "not a tier". *Benefit:* no cross-package release.

**Seat's recommendation: (a).** The drift guard exists precisely to
make this change safe, and a tier that ops can see is what lets a
power user be demanding about where a role runs.

## D3 — No third capability contract (PROPOSED 2026-09-03 — NOT RULED)

release-16-manifest D1 ruled exactly two capability contracts:
workflows and memory backends. A general "provider" contract — Ollama
as a model provider for every workflow — would be a third. This spec
does not propose it. Local models serve R6's roles as a
memory-backend extension (rerank) and workflow extensions (roles),
which fit the two ruled contracts and make the Ollama reranker the
first real second implementer D2 named as its falsifier.

If the chair later wants a provider-level contract, that is a
release-16-manifest amendment, not a host-surface-parity task.

## D4 — Parity is an enforcer, not a principle (PROPOSED 2026-09-03 — NOT RULED)

Collaboration-contract principle 1 ("the receipt beats the promise")
carries the *aspirational* label because no gate can check intent.
For surfaces the check is mechanical: a RICH renderer or host hook
either has its PORTABLE and HEADLESS twins receipted or it does not.
R2 proposes `tests/unit/gates/test_surface_parity.py` as the
enforcer for this case, and Task 1 lands it green before any new
renderer exists so it gates rather than chases.

## Open

- Convene `q-fable-51-surface-overlap-001` before ruling R1–R8?
- Coverage floor for this initiative (85% repository floor, or 90%
  as in shared-command-workspaces D4).
- D2 mechanics.
- Whether Task 7 waits for Phase B or ships alone on Phase A.
