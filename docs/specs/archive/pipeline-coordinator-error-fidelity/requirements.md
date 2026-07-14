# Spec: Pipeline Coordinator Error Fidelity

> When a pipeline coordinator (`discovery-sweep`, `secure-release`,
> future) fails, surface the typed cause — both the orchestrator's
> own failure mode and any sub-workflow SDK errors — instead of
> collapsing both layers into a generic prose string.

**Status:** killed (2026-07-14) — triage decision (matrix-2026-07-14): 6 weeks untouched; error-fidelity family largely shipped elsewhere
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

Today both coordinators handle errors with bare-except prose
(scope verified against source 2026-06-02):

- [`src/attune/workflows/discovery_sweep/workflow.py:376`](../../../src/attune/workflows/discovery_sweep/workflow.py)
  — `except Exception as exc:  # noqa: BLE001` in `_run_source`,
  wrapping `source.discover()`. Already captures
  `type(exc).__name__` into the `source_failed` event and returns
  `(source.name, exc)`.
- [`src/attune/workflows/secure_release.py:275`](../../../src/attune/workflows/secure_release.py)
  — `except Exception as e:  # noqa: BLE001` wrapping the *entire*
  four-stage pipeline (crew, security, code-review, release) in
  one block. Sets `NO_GO` + generic "Pipeline failed: {e}"; cannot
  attribute which stage failed without restructuring into per-stage
  `try` blocks.

A third bare-except at `discovery_sweep/workflow.py:74`
(`_safe_emit`) is **not** a fidelity site — it is best-effort
event-sink observability that must swallow so sink latency never
breaks the sweep. It belongs on the waived list, not the scope.

Plus per-source bare-excepts inside `discovery_sweep/sources/*.py`
— **six** sites, not four: `bug_predict`, `dependency_check`,
`doc_audit`, `perf_audit`, `security_audit`, `test_audit` — that
catch sub-workflow errors per path and emit findings at the source
layer.

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
- Bare-except cleanup at the six per-source sites inside
  `discovery_sweep/sources/*.py` (`bug_predict`,
  `dependency_check`, `doc_audit`, `perf_audit`, `security_audit`,
  `test_audit`) — flag for triage but defer; they catch
  *sub-workflow* errors which are handled by the layer-1
  propagation rule, so they don't need their own typed kind.
- The observability swallow at `discovery_sweep/workflow.py:74`
  (`_safe_emit`) — correctly best-effort by design; never type it.
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

**Adopt the Routes A + C *shape*, but ground the layer-C taxonomy
and confirm layer-A feasibility against source in Phase 2 before
naming anything.** Route B is what the closed parent already chose
("out of scope for that spec"); recommending it again would be a
non-answer. Single-route A or single-route C leaves half the
diagnostic gap unaddressed. The two-layer model (A = "what failed
below me", C = "what failed at my level") is the keeper.

The change from the original draft: do **not** ratify the five
`coordinator_error_kind` values in Phase 1. The 2026-06-02
grounding pass (below) shows the proposed taxonomy is partly
speculative and the layer-A mechanics are more nuanced than "read
the sub-result's kind." Per the project lesson "the code is the
contract, not the spec's named list," Phase 2 derives the taxonomy
from observed failure modes.

### Grounding pass (verified against source 2026-06-02)

Reading the actual coordinator code surfaced five constraints the
draft missed or left underspecified:

1. **Scope was off.** One real coordinator site in discovery-sweep
   (`:376`), not two — `:74` is an observability swallow (waived).
   Per-source sites are six, not four (see Problem statement).
2. **discovery-sweep is partial-failure-by-design.** Per NFR-1 a
   source failure becomes a "questions" entry and never aborts the
   sweep (`:376` returns `(name, exc)`, emits `source_failed`). So
   `partial_failure` is the *expected* path there, not an error
   kind — typing it as a failure would mislabel the common case.
3. **Route A is two cases, not one.** When a sub-workflow returns
   `success=False`, its `metadata["sdk_error_kind"]` is present and
   trivially propagable. When a sub-workflow *raises*, there is no
   kind — only an exception to classify. Route A as drafted covers
   only the first; the raise-path bleeds into layer C.
4. **secure-release needs restructuring for layer A.** Its single
   broad catch wraps all four stages, so attributing the failing
   sub-workflow requires per-stage `try` blocks — a real
   implementation cost, not a metadata read.
5. **`subworkflow_timeout` is speculative** — neither coordinator
   has timeout logic today. And **`WorkflowResult` needs no new
   field**: `metadata["sdk_error_kind"]` already exists
   (`base.py:410`) and flows end-to-end through `ops/runner.py`.

### Phase 2, task 1 (grounding deliverable)

Before any design: enumerate the real failure modes at the one
discovery-sweep coordinator site, the one secure-release site, and
the six per-source sites; derive the layer-C kinds from those;
record that secure-release requires per-stage `try`-block
restructuring for any sub-workflow attribution.

Phase 2 design.md still decides:

- The aggregation rule for layer A (first-failure vs severity-
  ranked vs all-listed)
- Partial-success semantics — noting discovery-sweep treats it as
  normal (see grounding #2)
- Dashboard chip surface: coordinator_kind only, sub_kind only, or
  both? If both, presentation order?
- Whether to define `subworkflow_timeout` speculatively or drop it
  until coordinator-side timeouts exist

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
6. The six per-source bare-excepts inside
   `discovery_sweep/sources/*.py` and the `_safe_emit` swallow at
   `workflow.py:74` are flagged in `decisions.md` as waived (per
   "out of scope" above) so a future audit doesn't re-open them.

---

## Open questions for Phase 2

Captured so design.md has a clean checklist. Several from the
original draft were resolved by the 2026-06-02 grounding pass
(see Recommendation) and are marked below.

- **Aggregation rule for layer A:** first-failure encountered,
  most-severe by a ranked list, or all-listed? Affects whether
  coordinator result carries a single `sdk_error_kind` or a list.
  *(Open.)*
- **Partial-success semantics:** *Partly resolved* —
  discovery-sweep treats partial failure as normal (NFR-1); the
  open part is whether secure-release's M-of-N stages should be
  success-with-warnings or failure.
- **Chip surface:** show coordinator kind, sub kind, or both? If
  both, which dominates the chip's color/icon? *(Open.)*
- **Timeout introduction:** *Resolved direction* — no coordinator
  has timeout logic today, so `subworkflow_timeout` is either
  defined speculatively for future use or dropped; it cannot fire
  now.
- **Layer C taxonomy completeness:** *Promoted to Phase 2 task 1*
  (grounding deliverable) rather than an open question — derive
  kinds from observed failure paths, don't ratify the five.
- **`release_prep.py` and `release.py` scope:** these are
  orchestration-shaped too. Roll into this spec, or address
  separately? *(Open.)*
- **Subworkflow propagation hook:** *Resolved* — no new
  `WorkflowResult` field needed; `metadata["sdk_error_kind"]`
  already exists at the workflow level and flows through
  `ops/runner.py`.
