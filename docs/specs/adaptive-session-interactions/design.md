# Adaptive session interactions — Design

**Status:** draft (2026-09-05) — moderator design supporting approved
requirements; reconcile and review before execution.

[Requirements](requirements.md) are authoritative for approved scope.
[Tasks](tasks.md) are parked. [Evidence](evidence.md) names the inspected
source and its limits. This is a bounded consumer-policy extension of
[elicitation-form-surface](../elicitation-form-surface/design.md), not a
new renderer, selector service, or source of command authority.

## Problem and outcome

The system has expressive form controls and surface-selection guidance. The inspected MCP implementation observes the agent's surface choice after the tool is selected. That observation does not establish a consistent policy for when an interaction is useful, whether the current host can complete it, or whether the user wants it.

The intended outcome is predictable adaptation: a relevant interaction appears without the user having to name a control, remains stable while being answered, respects session preferences, and completes through the same validation and authority boundaries as its fallback.

## Proposed design

Choose the interaction's meaning before selecting its rendering surface. The host adapter provides capability evidence; attune-forms renders and validates; the owning command remains the authority for actions. Use the existing state and telemetry seams where they suffice.

The first integration point should be an existing schema-bounded command-workspace choice, with a fixed action set, an established conversational fallback, and canonical acceptance. A Spec review choice is the leading candidate; T1 selects the exact live consumer after reconciling active work. Before adding an API, T1 must demonstrate whether guidance plus the current selector is sufficient or a binding caller is missing. An autonomous model-based classification service is not presumed necessary.

A session default means the presentation selected when the user has given no applicable override. The initial treatment is explicit guidance at the chosen consumer; the baseline is that consumer's present agent-chosen presentation. Freeze both definitions before the comparison. Do not equate surface selection with deciding whether a question is needed.

Start with guidance and existing caller seams. Add a binding check only when a concrete probe demonstrates that those cannot honor the scoped preference or preserve semantics, and after its owner and tool-return contract are identified. If existing behavior satisfies the requirements, close the work with evidence and documentation; a routing implementation is not mandatory.

Selection order: identify the immediate need using conversation context; apply explicit interaction preference and existing authorization; choose a supported presentation; keep the pending interaction stable; validate the returned answer; let the owning command decide whether any action is authorized.

The complete interaction mapping lives in [requirements](requirements.md#interaction-mapping).

## Ownership and future reconciliation

T1 identifies the actual consumer and preference facilities from its own
execution checkout. Candidate paths are the existing elicitation guidance,
MCP handler, spec command adapter, canonical workspace host, and the
attune-forms dependency. Their presence is evidence of seams to reuse, not
proof that a code change is needed. Host readiness remains owned by
host-surface-parity. No edits to those implementations are included here.

A source diff from the planning snapshot
3588c5487e641925b9617035abb483b1b936d616 to the preservation base
be15968fa2259d9fdc15d8e5eb8af70261d866a0 showed no changes in the inspected elicitation, MCP,
spec, roundtable, elicit-skill, host-surface-parity, or parent spec paths.
This does not establish freshness of another agent's uncommitted work.

If T1 shows a load-bearing premise is false, revise the affected requirement
and return that change to the chair. Ordinary reconciliation does not
implicitly authorize another roundtable round or provider spend.

## Remaining execution choices

1. Select the exact existing consumer and host using T1 evidence; a Spec
   review choice is preferred only if it satisfies ASI-5's conditions.
2. Identify existing storage for one-interaction and session preferences;
   keyboard mode is not assumed to provide those semantics.
3. Establish a valid baseline and preregister the comparison before trials.
   Record missing visibility timing without converting it into a result.
4. Review the concrete file scope and task before any implementation go.

The retained counter-cases and their chair-approved dispositions are in
[requirements](requirements.md#dissent-register) and [decisions](decisions.md).
