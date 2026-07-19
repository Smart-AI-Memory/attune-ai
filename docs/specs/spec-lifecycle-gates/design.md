# Spec-Lifecycle Gates v1 — Design

**Status: design draft — awaiting chair review** (2026-07-19).
Grounded per RR-5's chair edit: every seam below was re-verified by
import in this session; probe receipts inline. Requirements:
`requirements.md` (thread `producing-spec-lifecycle-gates-20260719-3`,
8 approved items). Rulings G1–G3 bind this design.

## Verified seams (RR-5 receipts, probed 2026-07-19)

| Seam | Import probe | Result |
|---|---|---|
| Compiler lints | `attune.roundtable.compiler` (`lint_draft/critique/final`) | OK |
| Producing caps + taxonomy | `attune.roundtable.producing` (`DEFAULT_MAX_INVOCATIONS`, `FAILURE_CODES`) | OK |
| Curator extension contract | `attune.curator.sources.SourceReader` (Protocol: module-level `read(*, project_root, since) -> SourceSummary`, must-not-raise, stable `state_hash`) | OK |
| Solution materializer | `attune.roundtable.solutions` (`materialize`, `validate`) | OK |
| Corpus-readiness shape | `attune.pipeline_learner.corpus` (`assess_readiness`, `Readiness`) | **on queued PR #1475** — resolves once merged; the shape (refuse + exact shortfall) is the pattern gates reuse |

## Architecture — one small package, no daemons

New package `src/attune/gates/`:

- **`protocol.py`** — the RR-1 contract. `GateReceipt` dataclass:
  `receipt_id`, `gate_id`, `phase` (one of the five boundaries),
  `timestamp`, `target` (spec slug + artifact path), `state`
  (`PASS | REVISE | CHAIR_REQUIRED | BLOCKED` — a closed enum, like
  `FAILURE_CODES`), `findings: list[str]` (exact shortfalls, the
  corpus-readiness idiom), `evidence_refs: list[str]`,
  `proposed_disposition: str`, `decisions_ref: str | None`.
  Adding a state requires a spec amendment.
- **`ledger.py`** — G1's machine ledger:
  `<ATTUNE_HOME|~/.attune>/ops/gates/verdicts.jsonl`, append-only
  JSONL, same resolution + suite-isolation posture as the
  run-record corpus (the `_isolate_attune_home` fixture already
  redirects it). Chair rulings never write here; receipts never
  write decisions.md (RR-2). Read side: `latest_for(target)`,
  `unresolved_chair_required()`.
- **`activation.py`** — RR-3/RR-4 policy. Pure functions:
  `blast_radius(changed_paths) -> "isolated" | "chair"` and
  `active_gates(tier, radius) -> list[gate_id]`. Sub-spec-tier
  work maps to the mechanical baseline only (G3).
- **`baseline.py`** — RR-4's corrected enforcer inventory as thin
  adapters, each returning a `GateReceipt`: round-table compiler
  lints, symbol-reality resolution (imports + path existence — the
  gate this spec's own authoring run proved necessary),
  falsifiability lint (acceptance bullets name a receipt type or
  probe; "configured/registered/exits-0" phrasings flagged). CI
  enforcers (rules-residency budget, complexity ratchet, lessons
  golden-smoke, doc-import audit) stay where they are — the
  baseline CITES their results, never re-implements them.
- **`runner.py`** — `run_boundary(phase, spec_slug, *, tier,
  changed_paths) -> list[GateReceipt]`: selects via `activation`,
  runs gates serially, appends every receipt to the ledger,
  returns them. Never advances anything (RR-2): callers render
  receipts; a human moves the phase.

### Trigger surface (RR-1: event-driven, no background sweeps)

v1 events are the three places phase transitions already happen:

1. **The `/spec` skill** — its stage instructions call
   `attune gates check <phase> --spec <slug>` (a new thin CLI over
   `runner.py`) at each boundary and render the receipts;
   `CHAIR_REQUIRED`/`BLOCKED` items are presented for ruling
   before the skill proceeds.
2. **Producing runs** — after `compile_requirements`, the
   moderator runs the requirements-boundary gates over the
   compiled document (symbol-reality would have caught this
   spec's own confabulated paths mechanically).
3. **CI (mechanical baseline only)** — the already-shipped
   enforcers keep failing CI directly; the gate layer reads their
   outcomes, it does not wrap CI.

### Blast-radius surface map (RR-3's named design deliverable)

`chair` radius (always `CHAIR_REQUIRED`): `src/attune/security/`,
`src/attune/__init__.py` and any module's public re-exports,
`plugin/` (MCP tool surface + skills), record schemas
(`src/attune/models/telemetry/data_models.py` and peers),
`.github/workflows/`, `pyproject.toml`/packaging, deletions of any
registered capability, and DB/state migrations. `isolated` radius:
new not-yet-imported modules, `tests/`, `docs/` (except projected
outputs, which drift-guards own). Unclassifiable → `chair` (the
conservative default, ruled in RR-3).

### Drift gate (RR-6) — a curator source, not a daemon

`src/attune/curator/sources/spec_drift.py` implementing the
verified `SourceReader` protocol: compares each spec's
highest-phase status header against git/PR reality (the
starter-reconciler pattern, in-repo), returns candidates in its
`SourceSummary`; must-not-raise, stable `state_hash`. Runs when
the curator runs (event-armed by its callers) — never mutates,
never rules.

### Waiver lifecycle (RR-8, per G2)

A waiver is a decisions.md line the chair writes:
`WAIVER: <gate_id> <target> until <date|commit-count> — <reason>`
plus the receipt's `receipt_id`. `activation.py` reads unexpired
waivers (parse-only) and downgrades the matching gate to `PASS
(waived)` — the receipt still logs, tagged `waived=true`. On
expiry the gate simply fires again; no cron, no state machine.

### RR-7 re-admission input (measured, as the decline required)

159 `docs/specs/*/decisions.md` commits on main in the last 6
weeks ≈ **26.5/week** (upper-bound proxy: commits, not individual
rulings; some are evidence appends). The drafter's invented
"3.2/week" was ~10× low — the real volume makes batching MORE
justified, not less. Proposal for the chair at design review:
re-admit RR-7 with this measured baseline and a batching threshold
expressed as a multiple of it (e.g. gate-generated
`CHAIR_REQUIRED` items exceeding 20% of baseline weekly volume →
weekly batch summary).

## Test plan (RR-9)

`tests/unit/gates/test_lifecycle_gates.py`: per-gate positive and
negative probes (malformed receipts, out-of-scope diffs, unknown
states → conservative `BLOCKED`/`CHAIR_REQUIRED`); ledger
append/read round-trip under `ATTUNE_HOME` isolation with a drift
guard mirroring the run-record corpus's; waiver parse/expiry
boundary cases. One full-seam integration test: a fixture spec dir
→ `run_boundary` → real ledger write → a decisions.md fixture
citing the `receipt_id` → `latest_for` linkage asserted. Suite
receipts run serially per the delegation-receipts discipline.

## Dependencies and sequencing

1. PR #1475 (corpus-readiness seam) — merge before implementation
   imports it.
2. Phase 3 (tasks.md) decomposes: `protocol+ledger` →
   `activation+baseline` → `runner+CLI` → `/spec` skill wiring →
   `spec_drift` source → RR-9 suite. Implementation starts only
   after chair approval of this design.

## Open questions for the chair

1. RR-7 re-admission with the measured baseline (above) — now, or
   after v1 ships and real `CHAIR_REQUIRED` volume is observed?
2. Should the `/spec` skill HARD-block on `BLOCKED` receipts
   (cannot proceed) or soft-block (proceed with the receipt
   rendered and an explicit chair acknowledgment)? Design assumes
   hard-block for `BLOCKED`, soft for `CHAIR_REQUIRED`.
