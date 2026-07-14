# Requirements — Opus 4.8 Platform-Fit

**Status:** superseded (2026-07-10) — by fable-premium-tier; reconciled at 2026-07-14 triage
Phase 0 to follow in a focused session (parked as a draft PR)
**Owner:** Patrick
**Target:** attune-ai, ships in an 8.x minor (NOT gated on 9.0.0 —
additive/quality, not breaking)

---

## Problem

PR #674 migrated the PREMIUM tier to Claude Opus 4.8, but did only the
**mechanical** half: model id, corrected pricing, and stripping the
sampling params Opus 4.7+ reject. The **quality** half — calibrating
attune to Opus 4.8's *behavior* — is untouched. Opus 4.8's documented
behavioral shifts (Anthropic migration guide, "Migrating to Opus 4.8")
land squarely on attune's core surface, multi-subagent orchestration:

- **Narrates more** between tool calls and writes longer end-of-task
  wrap-ups by default → attune's subagent prompts likely now over-talk.
- **Under-reaches** for subagents, file-based memory, and custom tools
  unless explicitly told when to use them → directly weakens attune's
  delegation-heavy workflows.
- **More deliberate / asks more** on minor decisions → higher ask-rate
  in otherwise-autonomous runs.
- **Effort sweet-spot moved** (sweep `medium`/`high`/`xhigh`; `high` is
  the new default, not a reflexive `xhigh`).

attune already has the control surface wired in
`src/attune/workflows/agent_sdk_adapter.py`
(`get_thinking_config`, `get_task_budget`, `_cli_supports_task_budget`,
`effort="high"`), so this is **calibration, not new infrastructure** —
tune the depth→effort/thinking/task_budget mapping and add explicit
delegation/tool/memory triggering to subagent prompts.

## Why measure first (non-negotiable)

The retired `agent-surface-parallelism-evaluation` spec is the cautionary
template: its Phase 0 probe found the proposed orchestrator already
shipped, and the spec was retired before any code. The same risk applies
here — attune's current settings may already be fine for 4.8 on some
axes. We do **not** tune blind. Phase 0 instruments and measures real
4.8 behavior, a decision matrix is **pre-committed before** seeing the
data (per the "pre-committed decision matrices survive contact with
data" discipline), and later phases tune **only** where the data
justifies it. If Phase 0 shows attune is already well-calibrated, the
spec retires with a measurement artifact and no churn — a valid outcome.

## Goals

1. A repeatable measurement harness that runs representative attune
   multi-subagent workflows on Opus 4.8 and captures the behavioral axes
   above plus token cost, retained in-tree.
2. A **pre-committed decision matrix** (in `decisions.md`) mapping each
   measured axis to a tune / leave-alone threshold.
3. Where the data crosses a threshold: calibrated `effort`/thinking/
   `task_budget` depth mappings and subagent-prompt triggering changes,
   with before/after measurements showing the improvement.
4. No regression to non-premium tiers or the SDK-native path.

## Non-goals

- Not a model change (4.8 already shipped in #674).
- Not the direct-provider / batch / langchain-adapter sampling-param
  fixes (those are PR #674 + the open `task_e5f204ca` follow-up).
- Not pool-aware billing visibility (that extends the separate
  `anthropic-cost-integration` spec).
- Not breaking; not part of the 9.0.0 redis-facade removal.

## Phase 0 — measure (the only phase fully specified now)

**0.1 Harness.** A script (e.g. `scripts/phase0/opus48_behavior.py`,
reusing the `scripts/phase0/` pattern from prior specs) that runs a fixed
corpus of inputs through `security-audit`, `deep-review`, and
`code-review` on Opus 4.8 and records, per run:

| Axis | Metric (from the SDK message stream / run record) |
|---|---|
| Narration volume | assistant TextBlock chars between tool-use blocks; end-of-task wrap-up length |
| Subagent under-use | subagent (Task) spawn count vs the workflow's historical baseline |
| Tool/memory under-use | tool-call count by type; any file-memory use |
| Ask-rate | count of clarifying/question turns the orchestrator emits |
| Effort fit | wall-clock + total tokens at `medium`/`high`/`xhigh` for the same input |
| Cost | input/output/cache tokens + $ per run vs the old premium baseline |

Each run is real API (Opus 4.8), budget-capped; the harness lives in-tree
for re-runs. Output: a `phase0-data/` dir + a `phase0-findings.md`
summary.

**0.2 Pre-committed decision matrix** (`decisions.md`, written and
committed BEFORE 0.1 runs): for each axis, the threshold that triggers a
tune and the specific knob it maps to. Example shape (numbers TBD at
authoring): "if mean inter-tool narration > N chars → add a
silence-default clause to subagent prompts"; "if subagent spawn count
drops > X% vs baseline → add explicit delegation-trigger guidance"; "if
`xhigh` shows < Y% quality gain over `high` at Z% more tokens → default
the premium depth map to `high`."

**0.3 Decision** (`phase0-findings.md` + a `decisions.md` verdict):
route each axis to TUNE or LEAVE per the pre-committed matrix. If every
axis says LEAVE, retire the spec with the artifact.

## Later phases (decision-gated — designed after Phase 0)

Deliberately under-specified; their existence and scope depend on Phase 0:

- **Phase 1 — effort/thinking/task_budget calibration:** adjust the
  depth→knob mapping in `agent_sdk_adapter.py` per the matrix, with
  before/after numbers.
- **Phase 2 — subagent-prompt triggering:** add explicit
  delegation/tool/memory "when to use" guidance + a narration
  silence-default to the workflows' subagent prompts, only where 0.3
  flagged TUNE. Re-measure to confirm the gain.

## Done when

- Phase 0 harness is in-tree and has produced `phase0-findings.md`.
- `decisions.md` has the pre-committed matrix (timestamped before the
  data) and a per-axis TUNE/LEAVE verdict.
- Either: the flagged tunings are merged with before/after measurements,
  OR the spec is retired with the measurement artifact (a valid outcome).
- No regression to non-premium tiers or the SDK-native path.

## Open questions (for design phase)

1. Fixed input corpus — reuse an existing fixture set, or curate 2–3
   representative repos/paths per workflow?
2. "Historical baseline" for subagent/tool counts — pull from
   `~/.attune/telemetry/usage.jsonl`, or capture a one-off Opus-4.6 run
   for a clean A/B? (4.6 is still an active model, so an A/B is feasible.)
3. Budget ceiling for the Phase 0 measurement run (multi-subagent on 4.8
   at high effort is the expensive case — `ATTUNE_MAX_BUDGET_USD`).
