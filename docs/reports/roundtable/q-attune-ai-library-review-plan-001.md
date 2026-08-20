# Round table — attune-ai library-wide review plan (ratified)

**Thread:** `q-attune-ai-library-review-plan-001` · 2026-08-20 ·
3/3 seats (Claude, Antigravity, Codex), 1 round, unprompted
convergence. Chair-promoted sections only; full transcript is
machine-local (`~/.attune/reports/roundtable/`).

Adapts the attune-forms process-v2
([q-forms-review-process-v2-001](q-forms-review-process-v2-001.md),
outcome: 23 confirmed act-now defects fixed across 13 modules) to
attune-ai scale: 741 Python files, ~192k LOC, ~70 packages, plus
`attune_redis`. Scale-independent parts of process-v2 carry over
unchanged (sweep-first, single reviewer per target on a templated
brief, leave-intact-is-success, empirical confirmation bar, two
roundtable checkpoints, chair-only batch rulings, frozen ledgers).

## Ratified plan

### 1. Review unit: the seam

The review unit is a **cohesive exposure surface** (an untrusted
ingress plus its direct contract sink) or a coherent package slice
— never a file, never a whole package. Package size alone never
qualifies a target. Projected cost: ~12–20 briefed targets ≈
2.5–4x the forms spend (vs 50x naive extrapolation).

A **seam census** joins the discovery sweep at Checkpoint 0:
enumerate every point where untrusted bytes enter — stdin JSON
parse, argv, file read of user content, Redis read, LLM output
consumed as data, subprocess construction, path join. Census
recall is the plan's known weak point (grep misses dynamic
dispatch — entry points, `getattr` routing); the calibration run
(§5) exists to measure it.

### 2. Tiers

- **Tier 1 — deep review (full brief; completion mandatory,
  yield-independent):** `mcp` (60+ tools parsing caller-supplied
  args), `hooks` (session-ambient, runs unprompted every session),
  CLI ingress cluster (`cli_minimal.py`, `cli_router.py`,
  `cli_commands`, `commands`), elicitation/forms rendering,
  `memory` + `attune_redis` persistence boundary (stored data
  replays untrusted-later), `models`/`llm` auth + credential +
  provider boundaries, markdown/doc ingestion seams.
- **Tier 2 — sweep + targeted skim:** shared contracts and large
  behavioral packages (`workflows` engine, `orchestration`,
  `agents`, `agent_factory`, `meta_workflows`, `telemetry`, …).
  Skim = contract note + dismissed-list; evidence promotes seams
  to tier 1.
- **Tier 3 — accepted-untouched (sweep-gated):** support packages
  with no census hit and no sweep flag. Always with a **stated
  acceptance reason**, never silence.
- **Census decides (chair ruling, split A/B):** no whole-package
  tier promotion — the plugin-loading / subprocess /
  dynamic-import / ingestion seams *inside* `orchestration`,
  `agent_factory`, `authoring`, `ops` are tier-1 by the census
  rule; the remainder of those packages is tier-2/3.

### 3. Ordering

Session-**ambient** boundaries (hooks + MCP) → **invoked**
boundaries (CLI + elicitation + ingestion) → **stored-data**
boundaries (memory/Redis, path seams) → shared high-fan-in
**contracts** → sweep-gated **tail**. (The forms
"boundaries → contracts → render", generalized.)

### 4. Coverage honesty: two-artifact ledger

1. **Generated manifest** (~75 rows): every shipped Python file
   inherits a disposition (deep-reviewed / sweep-cleared-recorded
   / accepted-untouched) through an exact, frozen selector
   expansion. Checkpoint reconciliation must prove manifest =
   union of selectors, no overlaps or omissions.
2. **Dense act-now ledger** (finding-only): target seam, defect
   class, confirmed repro, PR link, dismissed-after-inspection
   list.

Sweep clearances carry a receipt: pinned sweep-suite version + run
ID + commit SHA. A **drift-guard CI test** fails when a package
under `src/attune` lacks a manifest row — nothing is born
un-dispositioned. "Library covered" = inventory-complete +
disposition-complete, explicitly **not** deep-read-complete; the
final report states that residual risk plainly.

Generated/projection-owned files (chair ruling, question E):
substantive review on the **source/template only**; generated
paths dispositioned `projection-owned → see source` in the
manifest so reconciliation stays exact.

### 5. Sweep-tooling discipline (chair ruling, questions C+D)

- **Calibration first:** run the sweep tooling against
  attune-forms' pre-fix commit — known ground truth of 23
  confirmed defects — and record its hit rate BEFORE its verdicts
  may clear tier-3 packages.
- **Frozen suite:** the standardized mechanized sweep-script suite
  (e.g. missing subprocess timeouts, unvalidated Redis key
  formatting, fail-open violations) is frozen at Checkpoint 1;
  additive extensions only, at chair sittings.

### 6. Budget and stop rule (per tier / per stratum)

- Tier-1 targets capped ~3–8k LOC or one coherent seam; batches of
  3–6 related targets sharing a defect hypothesis; ~150k token
  ceiling per seam-target, abort-and-report.
- **Tier 1:** finish the enumerated list — zero-yield never cancels
  it.
- **Tier 2:** two consecutive zero-yield batches end deepening
  **within a package family/stratum** (a zero-yield presentation
  batch cannot stop persistence review).
- **Tier 3:** stops at sweep clearance + inventory reconciliation.
- Final stop additionally requires: every manifest entry
  dispositioned, every ledger flag fixed / dismissed-with-reason /
  chipped, same-class widening complete, ledgers frozen and
  reconciled.

### 7. Reviewer-brief deltas (vs the forms brief)

- **Negative priors:** do not re-flag what the gates mechanically
  enforce (eval/exec, broad-except ratchet, path-validation
  presence, brand drift). Instead review the gate **allowlist
  entries** — the escape hatch is the actual attack surface — and
  classify findings *gate-covered / gate-gap /
  semantic-despite-gate*.
- **Positive priors:** the forms-23 classes (malformed/partial
  payloads, validation-order, truthiness-vs-presence, type
  coercion, default/fallback divergence, serialization round
  trips, unvalidated defaults) **plus** attune-ai-specific: MCP
  stdio transport crash on unhandled exception, schema-type
  mismatch on tool args, hanging coroutines / un-timeouted
  subprocess+LLM calls, Principle-15 fail-open compliance at Redis
  seams, token/payload truncation at model boundaries.
- **Receipts:** non-mocked round trips REQUIRED at
  hooks/MCP/Redis/subprocess/CLI seams — 85% mocked coverage is
  not evidence there ("registered ≠ working").
- **Boundary repro template:** the mandated malformed-payload
  template, keyed to each MCP tool's input schema.

### Checkpoints

Full roundtable exactly twice: **Checkpoint 1** — post-census+sweep
ledger ratification (+ calibration result + frozen sweep suite);
**Checkpoint 2** — end-of-review sign-off. Per-batch sittings are
chair-only rulings.

## Provenance

Board thread `q-attune-ai-library-review-plan-001`, messages 8
(synthesis) and 9 (chair ruling) promoted 2026-08-20. Seat
receipts: Codex 19,465 tokens (~55s, gpt-5.6-sol); Antigravity
~2m (plan mode); Claude 83,026 tokens (47s, agent seat).
