# Pipeline Learner v1 (table-refreshed) — Requirements

**Status: requirements chair-ruled per item** — authored by the
round table (thread `producing-pipeline-learner-v1-20260719-2`); compiled deterministically by
`attune.roundtable.compiler` (V2-P2). Approved items only;
declined: none;
unruled: none.

Chair rulings 2026-07-19: all eight items approved, including the deferred-over-cap RR-8 restaged in the same chair-initiated session (TR-6 recourse path); RR-4 2-1 upheld as tabled (bulletin deferred, antigravity dissent preserved in the thread register). Authored by a HEADLESS producing run (V2-P4 dogfood #2); replaces the 2026-05-17 draft, whose stale premises the live probes in the grounding pack falsified. Prior draft preserved in git history.

> **Amendment 2026-07-19 (chair-ruled edit per
> `docs/specs/run-record-corpus/decisions.md` D2).** The RR-1
> external dependency resolved with a different corpus than RR-4
> pinned: the ops-runs store works as designed but is
> dashboard-only + 30-day pruned (its ceiling can never satisfy
> RR-1), while the telemetry seam already persists one
> `WorkflowRunRecord` per workflow execution. v1's single mining
> source is therefore the canonical run stream
> `~/.attune/telemetry/workflow_runs.jsonl` (rotated archives in
> `~/.attune/telemetry/archive/`), NOT `~/.attune/ops/runs/`.
> Records carry `trigger` ("manual" | "attune-rec"; absent =
> unknown, weighted as auto per RR-3) and `project` (repo-root
> identifier; worktrees resolve to the parent repo) — the two
> fields RR-3/RR-4 required. Historical backfill is ruled OUT
> (D3: start clean at cutover; the pre-cutover archive is
> pytest-polluted with no verifiable purity filter). Source pins
> below are amended in place and marked; everything else in the
> table-authored text stands.

## Requirements

**RR-1 — Gate v1 on a working run-persistence prerequisite**
The "thousands of runs going back months" premise is false today: `~/.attune/ops/runs/` has 15 workflow dirs but exactly 1 run JSON total (PACK-3), and the bulletin archive is 3 stale files (2026-05-27 → 2026-06-06). Mining is worthless without a corpus, and the 15-dirs-1-file signature strongly implies run persistence itself is broken or disabled. v1 must not ship a miner on top of a dry pipe; it must first establish and verify that runs accumulate.

- A prerequisite check inspects `~/.attune/telemetry/workflow_runs.jsonl` (+ rotated archives; amended 2026-07-19) and reports: total eligible records (schema-valid, timestamp-parseable), distinct workflows, distinct active days, and date span before any mining runs. Eligibility excludes records predating the 2026-07-19 cutover (D3: start clean).
- Readiness is operationally defined, not proxied by a single number: the corpus is "viable" only when it holds ≥ (2 × min-support) eligible records across ≥ 7 distinct active days AND at least one candidate pair clears min-support; otherwise the learner emits an explicit "insufficient corpus — not yet viable" status, prints the shortfall, and exits without proposing anything.
- Persistence diagnosis is scoped OUT of the learner's own code: the spec names, as a hard external dependency with a named owner in `decisions.md`, the confirmation that `src/attune/ops/runner.py` persists one JSON per run. The learner's acceptance probe is "the readiness check runs and reports"; fixing the 15-dir/1-file anomaly is a separate spec's responsibility, not a circular self-dependency.
(table: agreed; chair: approved)

**RR-2 — Pair-mining algorithm testable against a fixture corpus with a declared record schema**
The mining design (pair-mining, 30-min window, min-support ~5 / ratio ~0.5) is sound and does not depend on live-corpus size to be correct (PACK-4). Its correctness must be provable on committed fixtures so the algorithm can land and be trusted even while the live corpus is thin — but only if the fixture record shape and the pair semantics are pinned.

- The spec declares the canonical fixture record schema mirroring `WorkflowRunRecord` JSONL rows in `~/.attune/telemetry/workflow_runs.jsonl` (amended 2026-07-19): the exact fields consumed (`workflow_name`, `started_at`, `trigger`, `project`). One schema, one source (bulletin deferred per RR-4); no dual-format fixture.
- Pair semantics are fully specified so a fixture cannot pass two incompatible algorithms: ordering is by start timestamp; the ratio denominator is "count of A occurrences"; intervening unrelated workflows do not break an A→B pair within the window; A→A self-sequences are excluded; duplicate records and malformed/timezone-naive timestamps are normalized to UTC or dropped (and the drop is counted).
- A fixture corpus containing a known 7-occurrence A→B sequence surfaces exactly that pair above the support/ratio thresholds; noise sequences below min-support (2–3 occurrences) are filtered; and an off-by-window case (two steps > 30 min apart) is asserted excluded.
(table: agreed; chair: approved)

**RR-3 — Rank candidates with a reproducible, manual-over-auto weighted formula**
`ATTUNE_REC` is real and referenced in `code_review.py`, `curator/sources/recommendations.py`, and `ops/runner.py` (PACK-3), so the manual-vs-auto distinction remains meaningful: a sequence a human ran deliberately is stronger evidence than one an auto-recommendation triggered. But the ranking must be a deterministic function, not a prose "combines".

- The score is a stated formula over frequency, ratio, recency, and manual-fraction, with named normalization, a fixed recency decay constant (half-life in days), and a deterministic tie-breaker (e.g. higher support, then lexical member order). Two runs of the ranker over the same corpus produce identical ordering.
- Provenance is read from a named persisted field: the requirement names the exact attribute `src/attune/ops/runner.py` writes to distinguish an `ATTUNE_REC`-triggered run from a manual one, and RR-1's readiness check verifies that field is present in eligible records. If historical records lack it, they count as unknown-provenance (weighted as auto), and this is stated — the mere existence of `ATTUNE_REC` in source does not prove records preserve attribution.
- Given two sequences with identical frequency/ratio, the `ATTUNE_REC`-triggered one ranks strictly below the manual one (asserted); recency decay is asserted so a months-old burst does not outrank a smaller recent pattern of equal support.
(table: agreed; chair: approved)

**RR-4 — Single input contract (ops-runs), single-project scope, bulletin explicitly deferred**
The draft simultaneously described ops runs as the corpus, left bulletin open, and assumed a nested `YYYY-MM-DD/` archive layout that PACK-3 contradicts (archives are flat `archive/2026-05-27.jsonl`). A commit-or-kill spec cannot carry an ambiguous input contract.

- v1 mines exactly one source: `~/.attune/telemetry/workflow_runs.jsonl` + its rotated archives (amended 2026-07-19 per run-record-corpus D1/D2). The bulletin archive is DEFERRED (Non-goal), and the spec deletes the stale nested-directory assumption, recording the observed flat shape as the reason deferral is cheap to reverse later.
- Single-project scope is enforced, not assumed: the host-global canonical stream mixes repositories by design, so the learner filters on the `project` field each record now carries (amended 2026-07-19 — the dependency RR-4 named is DELIVERED by run-record-corpus RC-3). RR-1's readiness check validates that field is present; records without it are ineligible, not silently mined across mixed projects.
- The spec cites `src/attune/ops/runner.py` as the record producer and pins the record fields the learner depends on, so a schema change surfaces as a failing readiness check rather than silent mis-mining.
(table: 2-1 antigravity would fold bulletin in as a second v1 input; drafter + codex defer it to keep the contract commit-or-kill; chair: approved)

**RR-5 — Surface candidates through the SHIPPED curator via its real extension contract**
The draft cited `docs/specs/multi-actor-bulletin/` and `docs/specs/bulletin-curator/`, both now absent (PACK-3). A curator SHIPPED in code at `src/attune/curator/` with a `sources/` surface (`bulletin.py`, `recommendations.py`, `specs.py`, `sweep.py`). Integration must target that live surface by its actual contract, not by placing a parallel file and assuming it is discovered.

- The requirement names the exact callable/protocol and aggregation path a curator source implements (as `curator/sources/recommendations.py` does) and the execution lifecycle it must honor (synchronous sweep vs. background evaluation, per `sweep.py`). The learner conforms to that contract.
- An integration test proves a mined candidate actually reaches the chair-facing curator output — not merely that a module exists in `sources/`. The spec removes all references to the deleted sibling specs.
- A candidate item carries enough evidence (support, ratio, member workflows, sample run IDs, provenance mix) to let the chair decide without re-mining.
(table: agreed; chair: approved)

**RR-6 — Strictly opt-in with durable decision state; learner proposes, chair disposes**
The core safety property: the learner never materializes a pipeline without explicit acceptance, and re-runs are idempotent — which requires decision state to live somewhere concrete, resolving the draft's self-contradiction (idempotency with "only acceptance writes").

- Candidate identity is a stated fingerprint (ordered member workflows + window class); accept/decline decisions are persisted to a named ledger (e.g. `~/.attune/ops/pipeline_learner/decisions.jsonl`) that is itself an authorized, non-artifact write — distinct from the pipeline-artifact write and explicitly permitted.
- Running the learner with no acceptance produces zero writes under the pipeline-artifact path `docs/specs/pipelines/` (asserted). Only an explicit accept writes the YAML + evidence. Already-accepted or already-declined fingerprints are not re-proposed; a declined candidate reopens only when its evidence materially changes (support crosses a stated delta) — stated behavior, not implicit.
(table: agreed; chair: approved)

**RR-7 — Acceptance scaffolds a safe, drift-guard-clean artifact that VALIDATES (not mutates) the registry**
On acceptance the learner scaffolds a YAML pipeline + `evidence.json` under `docs/specs/pipelines/`. The prior draft required wiring the scaffold into `_DEFAULT_WORKFLOW_NAMES` (`src/attune/workflows/__init__.py`), which would mutate core Python during curator acceptance — contradicting opt-in-only writes and the mines-and-scaffolds Non-goal. Reframed: the pipeline is a composition of EXISTING workflows and must never register a new workflow name.

- Acceptance writes `<name>.yaml` and `<name>.evidence.json` atomically (both or neither; rollback on partial failure; create the destination dir if absent). The evidence file cites mined support, ratio, contributing run IDs, and provenance mix.
- The scaffolded YAML's member workflow names are VALIDATED against `_DEFAULT_WORKFLOW_NAMES` — a pipeline referencing an unknown workflow fails a test. No pipeline name is ever added to `src/attune/workflows/__init__.py`; the registry drift-guard stays green because nothing was registered.
- Name sanitization and path containment under `docs/specs/pipelines/` are enforced (chair-supplied names cannot escape the directory), collision behavior is defined, and malformed scaffolds fail a schema test rather than landing silently.
(table: contested — antigravity + codex both flag that wiring into `_DEFAULT_WORKFLOW_NAMES` conflicts with RR-6 and the "mines and scaffolds only" Non-goal; drafter concedes and reframes to validation-only; chair: approved)

**RR-8 — Honest viability statement and lifecycle stated in the spec now**
Per the chair's commit-or-kill framing (PACK-1) and the moderator read (PACK-4), the requirements must not restate the stale "months of rich history" premise, and must not be left incomplete pending an external ruling (the prior draft's `decisions.md` circularity).

- The requirements document states plainly: the algorithm (RR-2/RR-3) and safety/scaffold surfaces (RR-6/RR-7) are buildable and testable NOW on fixtures with production surfacing disabled; the live VALUE premise is unmet until RR-1's readiness gate passes.
- The spec states the proposed lifecycle up front rather than deferring to a chair ruling to be complete: fixture-only components MAY land now with live curator surfacing gated behind RR-1's readiness check; kill/park is the alternative. The chair's actual choice is recorded in `docs/specs/pipeline-learner/decisions.md` — a named, existing artifact target — but the requirements are complete without it.
- No requirement asserts a live-corpus size or history depth that the 2026-07-19 probes contradict.
(table: agreed; chair: approved)

## Non-goals

- Executing or scheduling pipelines — v1 mines, ranks, and scaffolds only.
- Registering new workflow names or mutating `_DEFAULT_WORKFLOW_NAMES` / `src/attune/workflows/__init__.py` — scaffolds validate against the registry, never write to it (RR-7).
- Mining the bulletin archive (`~/.attune/bulletin/archive/*.jsonl`) — DEFERRED to a later version; v1 is ops-runs only (RR-4).
- Semantic understanding of what a sequence *means*; ranking is frequency/recency/provenance-based, not intent-based.
- Real-time next-workflow prediction or in-session suggestion.
- Cross-project mining — v1 filters to a single project identifier within the canonical run stream (RR-4, amended 2026-07-19).
- Sequences longer than pairs (triples/n-grams) — v1 is pair-mining only.
- Fixing or redesigning the ops run-record schema — RR-1 confirms persistence works and names an owner; the fix itself is a separate spec.

## Dissent register

- **RR-4 (bulletin as a v1 input) — antigravity dissents (2-1).** Antigravity holds that the bulletin archive is available data and excluding it needlessly narrows v1's corpus, especially given how thin ops-runs is. Drafter and codex prevail: adding a second source with a different record shape (flat `.jsonl` lines vs. run JSON) widens the input contract exactly when commit-or-kill demands it be pinned, and the ops-runs corpus must be proven first. Bulletin is deferred, not rejected — RR-4 records the flat-directory reality so re-inclusion is cheap. Revisit once RR-1's readiness gate passes on ops-runs alone.
- **RR-7 (registry wiring) — resolved, no standing dissent.** Both reviewers flagged the `_DEFAULT_WORKFLOW_NAMES` mutation as contradicting opt-in-only writes and the mines-and-scaffolds Non-goal; drafter conceded and reframed to validation-only. Recorded as contested→resolved rather than open dissent.
