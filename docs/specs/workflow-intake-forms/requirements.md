# Workflow Intake Forms — Requirements

**Status:** approved (2026-07-31) — requirements ratified by the
chair in-session ("I like your judgement calls and the
requirements.md — go"). Implementation authority is NOT yet
granted: each phase's task is authored and executed only behind
its own chair gate; the next gate is Phase 1 task authoring.
**Slug:** `workflow-intake-forms`
**Provenance:** chair brainstorm 2026-07-31, same-day as the fix
and spec intakes shipped (#1824, #1826). The chair named the core
idea (dynamic generation from a form template plus a stored
procedure, optimized for latency) and steered sequencing
schema-first in-session. Drafted by the lead from that brief plus
tree grounding; the interview was the conversation.

## Position against the existing stack

This spec is a CONSUMER of
[elicitation-form-surface](../elicitation-form-surface/requirements.md)
(which owns the `FormSchema` artifact, controls, validation, and
renderers) and a sibling of
[socratic-ambiguity-calibration](../socratic-ambiguity-calibration/requirements.md)
(which owns *when* to ask). It adds no controls and no renderer.
What it adds: WHICH form a given workflow or command should ask,
generated instead of hand-authored.

## Problem

Two intake forms exist (fix, spec — `attune/elicitation/
{fix,spec}_intake.py`) and each cost a hand-written module, skill
wiring, and its own candidate derivations. The pattern demonstrably
improves user↔AI communication (one batched form replaces N
question turns — the Socratic rule's headline case), and most
registered workflows would benefit (a security audit wants
path + focus + depth; a refactor plan wants target + goal;
release-prep wants version + checklist scope). Hand-authoring one
module per workflow does not scale, and re-implemented derivations
will drift.

**Grounded blocker (2026-07-31):** only 2 of the ~23 registered
workflows declare an `input_schema` (`llm_mixin.py`,
`validation.py` carry the machinery; `fix_workflow` declares one).
Dynamic generation has nothing to generate FROM until workflows
declare what they take. The ops runner's `PATH_ARG_REGISTRY` is a
partial, parallel encoding of the same knowledge — evidence the
need exists and that it belongs in ONE place.

## Hypotheses

- **H1 — schema-first (chair-sequenced).** Declaring an
  `input_schema` on every registered workflow is the load-bearing
  phase: it is the contract the generator consumes, it subsumes
  `PATH_ARG_REGISTRY`-style side registries over time, and it is
  independently valuable (better `workflow run` validation errors)
  even if generation never ships.
- **H2 — template + providers, not modules.** A small
  `FormTemplate` (typed field slots referencing named CANDIDATE
  PROVIDERS) can generate each workflow's intake `FormSchema` at
  ask-time. The derivations already shipped twice become the
  provider library: git-changed paths, test-shaped files, package
  areas, taken spec slugs. Providers are functions in a dict —
  not a plugin system, not a new registry beyond that (H3 of
  outcome-first-fix binds here too: no parallel framework).
- **H3 — latency is a derivation problem, and it is measurable
  today.** Baseline measured 2026-07-31 in this repo (large tree):
  ~100–145 ms end-to-end, of which form BUILD is 0.1 ms —
  candidate derivation (git status + rglob) is effectively 100%
  of the cost. Budget: **p50 ≤ 150 ms, p95 ≤ 500 ms** from ask to
  rendered form, cold. Escalation order, each step gated on the
  previous one measurably missing budget:
  1. bound provider work (caps and shallow scans — already in the
     shipped providers);
  2. cache derived candidates keyed on `(repo_root, HEAD,
     dirty-set hash)` — invalidation is cheap because the key IS
     the state;
  3. the chair's stored-procedure idea: a Redis Function
     (`FCALL`, the `recall_digest` precedent) assembling the form
     payload server-side from cached fragments, for surfaces that
     already hold a Redis connection (MCP, ops dashboard).
  Constraints on (3): read-side only — templates and providers
  live in the tracked tree, never authored in the serving layer
  (collaboration principle 12), and Redis absent degrades to
  inline derivation, never blocking (principle 15).
- **H4 — communication impact is measurable.** Before/after on:
  question-turns per scoped run, form completion vs abandonment,
  and the edit rate of prefilled fields (a high edit rate means
  the providers guess badly; near-zero means the field may not
  need asking — both actionable).

## Non-goals

- No new controls, renderer, or validation path — the elicitation
  spec owns those.
- No natural-language inference at intake. Prefill comes from the
  user's own invocation text and derived candidates only.
- No hand-maintained per-workflow YAML mapping (ratified in the
  fix intake: derived, never authored — a mapping file is the
  drift generator this design exists to avoid).
- No new telemetry store; H4 metrics come from existing surfaces.
- No form for workflows where one dimension suffices — the
  Socratic rule's ceremony warning is binding; a generated form
  with padded fields is a regression, not a feature.

## Phases (each behind its own chair gate)

- **Phase 1 — declare the contracts.** `input_schema` on every
  registered workflow; unify `PATH_ARG_REGISTRY` consumers onto
  it where cheap. Receipt: registry sweep test asserting coverage;
  `workflow run` rejects malformed input with named fields.
- **Phase 2 — the generalization, at the rule of three.** Build
  `FormTemplate` + the provider library when the THIRD intake is
  wanted (candidates: security-audit, refactor-plan, release-prep)
  and re-express the fix and spec intakes on it in the same
  change — three consumers or the abstraction waits. Receipt:
  the two shipped intakes render byte-identical forms through the
  template path.
- **Phase 3 — latency, measured then optimized.** Instrument
  ask-to-render; apply the H3 escalation only where the budget is
  actually missed. The Redis Function ships only with a measured
  before/after and a degrade test.
- **Phase 4 — coverage.** Roll intake forms across the workflows
  where a form genuinely batches ≥2 dimensions; wire the H4
  metrics.

## Counter-case

The strongest argument against: **two instances is not a
pattern.** The template layer could easily be more code than the
N hand modules it replaces, and a generated form tuned to a
schema can ask what the user already said or pad fields to fill
the template. The mitigations are structural — Phase 2 is gated
on a third real consumer, prefill-from-invocation is required
behavior, and the H4 edit-rate metric exists precisely to catch
bad guessing. If the third intake never gets asked for, the right
outcome is that this spec's Phase 2+ never executes and the two
hand modules stay — cheap, honest, and no framework was built.
