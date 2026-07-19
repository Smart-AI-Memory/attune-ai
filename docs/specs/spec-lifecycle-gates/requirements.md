# Spec-Lifecycle Gates v1 (table-authored) — Requirements

**Status: requirements chair-ruled per item** — authored by the
round table (thread `producing-spec-lifecycle-gates-20260719-3`); compiled deterministically by
`attune.roundtable.compiler` (V2-P2). Approved items only;
declined: none (RR-7 re-admitted amended, G4 2026-07-19);
unruled: none.

Chair rulings 2026-07-19 ('as recommended', this thread): RR-2/RR-8/RR-9 approved clean (RR-8/RR-9 restaged from deferred_over_cap per the TR-6 recourse path); RR-1/RR-3/RR-4/RR-5/RR-6 approved WITH chair edits — the drafter's cited module paths were confabulated (verified against the tree: every specific entry point it named was missing) and are corrected in place, marked '[chair edit]'; the verdict-ledger destination is corrected to the G1-ruled machine ledger. RR-7 DECLINED as written: its 'measured' chair-interaction baseline (~3.2 rulings/week) was invented by a text-only seat — re-admit once the count is actually measured. The confabulation itself is recorded as live evidence FOR the symbol-reality gate this spec mandates.

## Requirements

**RR-1 — Lifecycle Gate Boundaries and Shared Receipt Protocol**
To establish predictable quality controls across the spec-driven development lifecycle without mutating ruling surfaces, gates must operate at defined phase transitions using a standardized machine-readable receipt protocol.
- Gates must execute at all five phase boundaries (brainstorm → requirements → design → tasks → execution → verification) upon event-driven phase transition triggers rather than standing background sweeps.
- Every gate evaluation must emit a machine-readable JSON receipt containing `receipt_id`, `gate_id`, `phase`, `timestamp`, `target_artifact`, `evaluation_state` (`PASS`, `REVISE`, `CHAIR_REQUIRED`, `BLOCKED`), `findings`, `exact_shortfalls`, `evidence_refs`, `proposed_disposition`, and `decisions_ref`.
- Receipts must persist exclusively in the candidate verdict log at `~/.attune/ops/gates/verdicts.jsonl` (the G1-ruled machine ledger) [chair edit], leaving `decisions.md` strictly reserved for chair-authored rulings.
(table: agreed; chair: approved)

**RR-2 — Action and State Protocol Separation with Autonomy Split**
To enforce strict boundary discipline while enabling continuous progress, autonomous evaluation states must be cleanly decoupled from lifecycle promotion actions.
- Autonomous gates evaluate candidate states (`PASS`, `REVISE`, `CHAIR_REQUIRED`, `BLOCKED`) and execute actions restricted to `BLOCK`, `REVISE`, and `REPORT` with exact shortfalls attached.
- A `PASS` evaluation state indicates mechanical compliance but shall NEVER auto-promote or auto-advance lifecycle phases; phase advancement remains exclusively gated by chair sign-off.
- Scope approvals, architectural decisions, policy waivers, and lifecycle phase promotions unconditionally evaluate to `CHAIR_REQUIRED`.
(table: agreed; chair: approved)

**RR-3 — Mechanical Blast-Radius Classifier and Escalation Policy**
To prevent high-risk modifications from bypassing chair supervision while preventing decision bottlenecking on trivial edits, change impact radius must be mechanically classified.
- Additive, fully isolated changes with zero public API, schema, or security surface changes are eligible for autonomous `PASS` state evaluations when all mechanical baseline checks pass.
- Changes impacting public APIs, shared schemas/projections, security primitives (`src/attune/security/`), database migrations, [chair edit: the drafter's `src/attune/api/` and `src/attune/schemas/` do not exist; the concrete surface map is a design-phase deliverable] or ambiguous surface areas must automatically evaluate to `CHAIR_REQUIRED`.
- Ambiguous or unclassified blast-radius detections must conservatively default to `CHAIR_REQUIRED` rather than an autonomous pass.
(table: agreed; chair: approved)

**RR-4 — Risk-Tiered Gate Activation and Baseline Enforcer Inventory**
To avoid ceremony inflation and conform to the ruled fixed-vs-dynamic gate policy in `decisions.md`, gate enforcement must scale with work scope while grounding baseline checks in verified existing enforcers.
- Sub-spec-tier work activates only a mandatory mechanical baseline consisting of existing enforcers [chair edit — corrected to the real set]: the round-table compiler lints (`src/attune/roundtable/compiler.py`), rules-residency budget (`tests/unit/rules/test_rules_residency_budget.py`), the doc-import CI audit, the complexity ratchet (`tests/unit/quality/test_complexity_ratchet.py`), the lessons golden-smoke (`tests/unit/lessons/test_lessons.py`), and code formatting.
- Spec-tier and high-permanence work automatically activates the full multi-boundary gate ladder in conformance with the fixed-vs-dynamic policy ruled in `decisions.md`.
- Grepped enforcers (rules residency, doc-import audit, complexity ratchet, lessons golden-smoke) must be reused directly as baseline checks to prevent duplicate enforcement code.
(table: agreed; chair: approved)

**RR-5 — Integration with Verified Shipped Building Blocks and Verdict Ledger Seams**
To ensure architectural coherence, gate enforcers must integrate directly with verified shipped code paths while preserving `decisions.md` as the sole chair ruling ledger.
- Boundary gates must invoke verified entry points [chair edit — the drafter's list was confabulated; corrected to the shipped seams]: the round-table compiler lints (`src/attune/roundtable/compiler.py`), corpus-readiness refuse-with-shortfall (`src/attune/pipeline_learner/corpus.py`), the doc-import CI audit and its skip hatch, producing-run caps (`src/attune/roundtable/producing.py`), the delegation-receipts re-run discipline (decision-routine rule), curator sources (`src/attune/curator/sources/`), and the session-start starter-reconciler hook. Design must re-verify each seam by import before building on it.
- Gate evaluation receipts and evidence log to `~/.attune/ops/gates/verdicts.jsonl` (the G1-ruled machine ledger) [chair edit], whereas chair-authored rulings, overrides, and waivers write directly and exclusively to `decisions.md`.
(table: agreed; chair: approved)

**RR-6 — Event-Armed Drift Detection and Non-Mutating Reconciler**
To detect specification divergence without violating chair promotion authority or introducing un-armed background drift, drift checks must run on phase events using non-mutating reconcilers.
- The drift guard must run a starter-reconciler-style non-mutating comparison on lifecycle event transitions [chair edit: the reconciler is a session hook today, not an attune module; the gate wraps its pattern, not that path] and commit events to compare codebase implementation against spec assertions and enforcer budgets.
- Detected budget violations or specification drift must generate a machine-readable shortfall receipt evaluating to `REVISE` or `CHAIR_REQUIRED`, opening a candidate item without modifying existing rulings in `decisions.md` or reversing prior chair promotions.
(table: agreed; chair: approved)

**RR-8 — Flaky-Live-Fire Override Path and Chair Waiver Lifecycle**
To handle non-deterministic test failures without stalling pipelines, live-fire overrides and waivers must follow a strict chair-governed lifecycle.
- Conforming to the flaky-live-fire override ruling in `decisions.md`, non-deterministic test failures must evaluate to `CHAIR_REQUIRED` with a structured `flaky_candidate` tag and diagnostic trace attached.
- Chair waivers are requested via a `CHAIR_REQUIRED` receipt, recorded in `decisions.md` with explicit expiration bounds (timestamp or commit count), and automatically re-evaluated by baseline gates upon expiration.
(table: agreed; chair: approved)

**RR-9 — Mechanical Acceptance Criteria and Negative Probe Discipline**
To verify gate correctness and prevent regression, every gate boundary must be validated by automated probe test suites.
- Acceptance test suites (`tests/unit/gates/test_lifecycle_gates.py`) must probe each lifecycle boundary with both positive cases (valid inputs yielding expected candidate state) and negative cases (malformed receipts, out-of-bounds diffs, or unhandled exceptions triggering conservative `BLOCKED` or `CHAIR_REQUIRED` states).
- At least one live integration test must exercise the full seam from phase event trigger -> enforcer probe -> verdict-ledger write (`~/.attune/ops/gates/verdicts.jsonl` (the G1-ruled machine ledger) [chair edit]) -> `decisions.md` chair resolution linkage.
(table: agreed; chair: approved)

**RR-7 — Measured Chair-Interaction Cost and Decision Batching Policy (re-admitted amended, G4)**
[chair edit — re-admitted 2026-07-19 with a MEASURED baseline replacing the declined draft's invented figure]
To protect the chair from decision fatigue, gate escalation thresholds must be governed by measured decision volume.
- Baseline: ~26.5 `docs/specs/*/decisions.md` commits/week (159 commits over the 6 weeks to 2026-07-19; an upper-bound proxy — commits, not individual rulings). The baseline must be re-measured at implementation time and recorded in the verdict ledger's config.
- When gate-generated `CHAIR_REQUIRED` candidate volume exceeds 20% of the measured weekly baseline, the gate system activates batching mode: non-urgent `CHAIR_REQUIRED` candidates group into a single weekly review summary artifact for chair evaluation.
- Urgent classes (security surface, `BLOCKED` escalations) never batch.

## Non-goals

- **No secondary chair ruling surface**: Gate verdicts, candidate proposals, and evidence records persist in `~/.attune/ops/gates/verdicts.jsonl` (the G1-ruled machine ledger) [chair edit], while `decisions.md` remains the sole chair ruling surface.
- **No full gate ladder for sub-spec work**: Sub-spec-tier work will not activate gate ladder evaluations beyond the mandatory mechanical baseline (the corrected baseline inventory in RR-4) [chair edit].
- **No autonomous chair rulings or auto-advancement**: Autonomous gates are strictly prohibited from granting waivers, mutating `decisions.md`, or auto-promoting lifecycle phases.
- **Un-armed standing background sweeps**: Gates and drift checks execute on explicit phase transition events and commit hooks, avoiding un-armed continuous background polling.

## Dissent register

Empty — attested
