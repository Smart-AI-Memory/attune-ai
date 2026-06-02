# Spec: Pipeline Coordinator Error Fidelity

> When a pipeline coordinator (`discovery-sweep`, `secure-release`,
> future) fails, surface the typed cause — both the orchestrator's
> own failure mode and any sub-workflow SDK errors — instead of
> collapsing both layers into a generic prose string.

**Status:** draft (2026-06-02)
**Created:** 2026-06-02
**Owner:** TBD
**Related:** [`sdk-error-message-fidelity`](../sdk-error-message-fidelity/)
(parent — direct-SDK error fidelity; this spec is the deferred
pipeline-coordinator follow-up flagged in its 2026-06-02 close-out);
[`workflow-failure-exit-propagation`](../workflow-failure-exit-propagation/)
(sibling — exit-code side of the same surface)

---

## Problem statement

The `sdk-error-message-fidelity` spec (closed Phase 6, 2026-06-02)
established typed `sdk_error_kind` for direct SDK calls: when a
workflow's `claude_agent_sdk.query()` fails, the cause flows from
SDK → workflow result → CLI side-channel → run record → dashboard
chip classifier with a typed label (`api_quota`, `rate_limit`,
`auth_error`, etc.). 14 of 16 SDK-callable surfaces are covered.

Two SDK-callable surfaces were explicitly deferred:
`discovery-sweep` and `secure-release`. These are **pipeline
coordinators** — they don't call the SDK directly; they orchestrate
other workflows that do. The Phase 6 mechanical pattern (wrap the
SDK call, classify the exception, attach a kind) doesn't fit
because there's no SDK call at the coordinator's own level.

Today both coordinators handle errors with bare-except prose:

- [`src/attune/workflows/discovery_sweep/workflow.py:376`](../../../src/attune/workflows/discovery_sweep/workflow.py)
  — `except Exception as exc:  # noqa: BLE001` wrapping
  source-discovery failures.
- [`src/attune/workflows/secure_release.py:275`](../../../src/attune/workflows/secure_release.py)
  — `except Exception as e:  # noqa: BLE001` wrapping pipeline-run
  failures.

Plus per-source bare-excepts inside `discovery_sweep/sources/*.py`
(dependency_check, doc_audit, security_audit, perf_audit) that catch
sub-workflow errors and emit prose at the source layer.

### Concrete trigger

When a sub-workflow's SDK call hits `api_quota` (the original
trigger for the closed parent spec), running discovery-sweep
produces a dashboard chip showing generic failure — the typed
`api_quota` signal that exists *inside* the sub-workflow's result
is lost at the coordinator layer. The user sees "discovery-sweep
failed" instead of "discovery-sweep failed: bug-predict source hit
api quota — regains 2026-07-01". The coordinator strictly
*degrades* the diagnostic the closed spec just shipped.

### Two failure layers, not one

The diagnostic gap has two distinct sources:

1. **Below the coordinator** — a sub-workflow's SDK error
   (`api_quota`, `rate_limit`, `auth_error`, etc.) flows into the
   coordinator's result but isn't surfaced upward.
2. **At the coordinator itself** — orchestration logic fails in
   ways the SDK never raised (source discovery returned zero
   sources; sub-workflow timed out; partial failure with M-of-N
   sub-workflows succeeded).

A complete answer needs both layers typed.

---

## Scope

### In scope

- Define a `coordinator_error_kind` taxonomy for orchestrator-
  level failures (the second layer above).
- Propagate sub-workflow `sdk_error_kind` upward into the
  coordinator's result (the first layer above).
- Update `discovery-sweep` and `secure-release` to emit both
  fields on failure.
- Update the dashboard chip classifier to surface coordinator
  failures meaningfully (showing coordinator kind, sub-workflow
  kind, or both per design decision).
- Drift-guard test preventing regression to bare-except prose at
  the two named coordinator sites.

### Out of scope

- Workflow-level routing/recovery (failed sub-workflow does NOT
  auto-retry — that's a separate spec on resilience).
- Changing the existing `sdk_error_kind` taxonomy from the closed
  parent spec.
- Bare-except cleanup at the four per-source sites inside
  `discovery_sweep/sources/*.py` — flag for triage but defer; they
  catch *sub-workflow* errors which are handled by the layer-1
  propagation rule, so they don't need their own typed kind.
- Net-new sub-workflow error types.
- Cross-coordinator standardization (e.g. pulling
  `release_prep.py`, `release.py` into the same model) — covered
  only if the design naturally generalizes; otherwise its own
  spec.

---

## Design alternatives

The 2026-06-02 conversation surfaced three routes. Recording all
three so the design phase can reason from the same base.

### Route A — Propagate sub-workflow `sdk_error_kind` upward

Add an aggregation step that walks sub-workflow results in the
coordinator and surfaces the most-severe SDK error (rule TBD —
first-failure? severity-ranked? all-listed?) on the coordinator's
result.

- **Answers:** "what failed *below* the coordinator?"
- **Solves:** the trigger case (sub-workflow api_quota lost at
  coordinator).
- **Doesn't solve:** orchestration logic failures that aren't SDK
  errors (no sources discovered; coordinator-internal exception).

### Route B — Mark Phase 7 explicitly out of scope, close the question

Accept the closed-parent's "out of scope" stance permanently.
Pipeline coordinators stay with bare-except prose; dashboard chip
shows generic failure for coordinator runs.

- **Answers:** nothing — explicit non-design.
- **Solves:** the spec-decision-overhead problem; closes the
  question.
- **Doesn't solve:** the diagnostic gap. Coordinators continue to
  silently degrade the typed-kind UX the parent spec shipped.

### Route C — Define `coordinator_error_kind` for orchestrator-level failures

Add a new typed vocabulary parallel to but distinct from
`sdk_error_kind`:

- `source_discovery_failed` — no work found
- `subworkflow_timeout` — sub ran but didn't return
- `partial_failure` — M-of-N sub-workflows succeeded
- `all_subworkflows_failed` — total orchestration failure
- `internal_error` — coordinator-side exception unrelated to subs

- **Answers:** "what failed *at* the coordinator's level?"
- **Solves:** typing the bare-except sites at the two named
  coordinator lines.
- **Doesn't solve:** propagating sub-workflow SDK errors.

### Route A + C combined (recommended)

A and C answer different questions and are not alternatives —
they're layers. A handles "what failed below me"; C handles "what
failed at my level." Together they form the complete typed-fidelity
story for coordinators. Dashboard chip can show either or both per
design decision.

---

## Recommendation

**Adopt Routes A + C together.** Route B is technically what the
closed parent spec already chose ("out of scope for that spec");
opening this spec to recommend B again would be a non-answer.
Single-route A or single-route C leaves half the diagnostic gap
unaddressed. The combined design is the complete picture.

Phase 2 design.md will need to decide:

- The aggregation rule for layer A (first-failure vs severity-
  ranked vs all-listed)
- Partial-success semantics: M-of-N sub-workflows succeed →
  coordinator returns success-with-warnings or failure?
- Dashboard chip surface: coordinator_kind only, sub_kind only, or
  both? If both, presentation order?
- Whether `subworkflow_timeout` requires the coordinator to
  introduce timeouts it doesn't currently have (vs. defining the
  kind for future use only)
- Layer C taxonomy completeness — are the five proposed kinds
  enough, or are there orchestration failures the discovery-sweep
  and secure-release code paths produce that don't fit them?

---

## Acceptance criteria

For Phase 4 implementation to be considered complete:

1. `coordinator_error_kind` defined as a typed enum or string-
   literal type in a shared location (likely
   `src/attune/workflows/_errors.py` or sibling).
2. `discovery-sweep` and `secure-release` workflow results carry
   both `coordinator_error_kind` (when applicable) and propagated
   `sdk_error_kind` (when sub-workflows failed with one).
3. The two named bare-except sites
   ([`discovery_sweep/workflow.py:376`](../../../src/attune/workflows/discovery_sweep/workflow.py),
   [`secure_release.py:275`](../../../src/attune/workflows/secure_release.py))
   no longer emit untyped prose for the categories the taxonomy
   covers.
4. Dashboard chip classifier (`src/attune/ops/runner.py` log-scan +
   classifier) handles coordinator failures per the Phase 2
   surface decision.
5. Drift-guard test prevents reintroducing bare-except at the two
   named sites.
6. Existing per-source bare-excepts inside
   `discovery_sweep/sources/*.py` are flagged in `decisions.md` as
   waived (per "out of scope" above) so a future audit doesn't
   re-open them.

---

## Open questions for Phase 2

Captured so design.md has a clean checklist:

- **Aggregation rule for layer A:** first-failure encountered,
  most-severe by a ranked list, or all-listed? Affects whether
  coordinator result carries a single `sdk_error_kind` or a list.
- **Partial-success semantics:** when 3 of 5 sub-workflows
  succeed, is coordinator success? Affects discovery-sweep's UX
  (it's *expected* for some sources to find nothing).
- **Chip surface:** show coordinator kind, sub kind, or both? If
  both, which dominates the chip's color/icon?
- **Timeout introduction:** does adding `subworkflow_timeout` as a
  kind require introducing coordinator-side timeouts? Or do we
  define the kind speculatively for future use?
- **Layer C taxonomy completeness:** review actual failure paths
  in both coordinators to confirm the five proposed kinds cover
  what the code can produce.
- **`release_prep.py` and `release.py` scope:** these are
  orchestration-shaped too. Roll into this spec, or address
  separately?
- **Subworkflow propagation hook:** does the WorkflowResult
  contract need a new field, or can we layer the propagation onto
  existing fields (e.g. `metadata.sdk_error_kind` already exists
  at the workflow level)?
