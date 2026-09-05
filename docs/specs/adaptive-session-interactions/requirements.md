# Adaptive session interactions — Requirements

**Status:** approved (2026-09-05) — ASI-1 through ASI-7 individually
chair-approved; implementation is not authorized.

Extension of [elicitation-form-surface](../elicitation-form-surface/requirements.md),
using [host-surface-parity](../host-surface-parity/requirements.md) and
[shared-command-workspaces](../shared-command-workspaces/requirements.md).
This package has its own parked task ladder; it does not replace those owners.

Roundtable thread: `q-adaptive-session-interactions-001`. Candidate IDs
12–18 were approved by chair rulings 19–21. One of three seat replies
passed the compiler; no full-roster consensus is claimed. See
[decisions](decisions.md) for exact disposition and authority boundaries.

Editorial status reconciliation (2026-09-05): the requirement bodies below
preserve the approved text. ASI-5's phrase “not a ratified sequencing
decision” describes its pre-approval provenance; subsequent approval of
board item 16 ratified that requirement. The exact consumer remains
conditional on T1. Patrick later authorized repository preservation and a
spec commit only; ASI-7's freeze clause continues to prohibit implementation
and interference with Claude's work. This status correction adds no feature
scope or execution authorization.

## Interaction mapping

The original mapping is restored here so ASI-1's “mapping above” is
self-contained. It was present in the reviewed draft before compilation.

| Immediate need | Proposed interaction | Boundary |
| --- | --- | --- |
| Missing information | Short clarification | Only unresolved information needed for progress; no repeated intake |
| Genuine alternatives | Decision with recommendation and tradeoffs | Do not invent alternatives or manufacture disagreement |
| Several findings needing dispositions | Per-item triage | Informational findings need not become votes |
| Ongoing work | Progress display | A report does not require an answer; a real blocker may need a decision |
| Action requiring new authorization | Explicit confirmation | Existing applicable authorization is retained |
| Joint exploration | Conversation | A control appears when a concrete need emerges |

## Requirements

**ASI-1 — Select by immediate need with session context**
Apply the mapping above at a meaningful interaction boundary. Session phase is supporting context, not a command to display a particular control. If the need is ambiguous and progress is possible, continue the conversation. If ambiguity blocks the next step, ask the smallest clarifying question. Batch only independent unknowns of one decision; dependent questions remain sequential.

- Hold session phase constant while varying the immediate need; the selected interaction follows the need.
- An exploratory request with a nonblocking missing detail continues as conversation.
- Previously supplied facts and previously settled choices are not asked again.
- A plain single choice is not inflated into a multi-field form; a decision with real tradeoffs preserves those tradeoffs.
- The pilot's trigger is explicit: an unresolved choice with real alternatives whose answer is needed for the next step. A session phase may be conversational context; adding a phase field or classifier is not required.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-2 — Honor scoped preferences without losing meaning**
Allow a one-interaction override and a session-wide preference such as “just talk to me.” Use existing preference/state facilities if they can express the scope. A preference changes presentation, never validation or action authority. Do not silently omit fields that the selected surface cannot represent.

- A session-wide conversation preference survives subsequent phase changes until the user changes it.
- A one-time override expires only for the stated interaction; it does not rewrite the session preference.
- Switching presentation preserves the pending question and compatible entered data where the host exposes it. Where it cannot, disclose the limitation and request only missing data.
- A text fallback for a typed field retains its validation, or reports that it cannot complete the interaction; it never drops that field.
- Preference precedence is an explicit override for this interaction, then an explicit session preference, then the supported default. Missing preference means no inferred opt-out or consent. Capability constrains presentation without discarding meaning.
- T1 names the actual state facility for both scopes; keyboard mode is not assumed equivalent to a session-wide conversational preference. If no existing facility fits, propose its minimal owner and lifetime before implementation.
- Canonical answers already received are preserved. Unsubmitted client input is promised only when the host exposes a verified recovery mechanism; otherwise disclose that limit and ask only for required missing data.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-3 — Scope readiness evidence to host, runtime, and interaction**
Use the existing host capability/conformance design to distinguish advertised support, a verified round trip, and usefulness as an automatic default. Receipt provenance names the host, relevant runtime/package versions, interaction, actual surface, and result. Unknown support uses a supported equivalent presentation; a runtime change makes affected evidence due for rechecking, not automatically failed.

- Tool availability and generated HTML alone never mark a control operationally proven.
- A named-host receipt observes a usable presentation, actual submission, validation, and acceptance for the correct pending decision.
- An unsupported or auto-declined host path is distinguished from an observed user rejection and falls back without silently discarding the question.
- A capability change cannot confer new action authorization or silently overwrite active user input.
- Operational verification may use a named human observer's attestation that the correct control was visible and usable, or an instrumented host observation. Neither attestation nor receipt timestamps are passed off as precise paint timing.
- Receipt host/runtime and proposed-default host/runtime are recorded separately and must match for eligibility. A working fallback proves only that fallback, not an unseen rich widget.
- The fallback itself needs a demonstrated completion path. If neither presentation can complete the interaction, report the specific limitation rather than inventing support.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-4 — Preserve pending decisions and existing authority boundaries**
Keep a pending interaction stable until it is answered, cancelled, or its underlying decision changes. Use canonical command workspace revision/nonce/contract checks for state-changing actions where applicable. A telemetry instance token is correlation data, not an authorization credential. Plain data collection need not acquire a new security subsystem.

- Unrelated progress updates do not replace a pending control or invalidate an otherwise valid answer.
- A material change to the decision invalidates old action authority; compatible input is retained only where still valid.
- Stale, altered, or repeated action delivery cannot produce an unauthorized action or a second execution.
- Displaying, dismissing, or reading progress creates no approval. A valid form answer grants only the authority explicitly conveyed by that answer.
- A conversational answer authorizing an action passes through the same canonical collector as the widget answer. It does not authorize a direct implementation shortcut. In the inspected host the Python method is CommandWorkspaceHost.collect; the MCP tool is command_workspace_collect_action.
- A plain clarification uses the existing form validator. It does not acquire command-action nonce machinery merely because it is presented in a form.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-5 — Begin with one bounded automatic-default trial**
First apply the proposed default to one existing schema-bounded workspace choice containing real alternatives. Prefer a Spec review choice if T1 confirms it has an established fallback, typed validation, and observable canonical acceptance. Keep its existing action contract; do not create consequential work solely to test an approval. Other constructs retain their established behavior. This scope is a moderator proposal informed by Antigravity #6, not a ratified sequencing decision.

- The same task can be completed through the automatic decision control and through conversation, with equivalent validated meaning.
- A case with an already chosen alternative proceeds without presenting a new decision control.
- Include preference override, unavailable surface, invalid answer, material decision change, and repeated delivery scenarios.
- The initial host and consumer are named before measurement; do not imply other hosts are proven by that result.
- Separate readiness from usefulness: complete the chosen consumer's host/fallback behavioral checks first, then compare presentations on equivalent choices. A simpler smoke probe may help setup but does not prove the richer pilot's semantics.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-6 — Measure usefulness separately from system latency**
Record completed decisions/outcomes, extra clarification turns, user overrides, and failures using existing stores where possible. For timing, distinguish request-to-usable-visibility, submit-to-canonical-acceptance, and overall request-to-acceptance. Keep user deliberation separate. Mark visibility unmeasured if the host provides no valid observation boundary.

- Before trials, record the matched scenarios, order/counterbalancing, host/runtime, sample count, and intended comparison; freeze the protocol for that trial.
- Report raw samples/counts and limitations. A small within-user trial supports a local default decision, not a population performance claim.
- Observed misbinding, duplicate execution, lost required fields, or broken override blocks promotion for the affected path.
- A proposed default needs complete behavioral receipts and chair-reviewed evidence of usefulness. Quantitative targets are set before collection; unknown baselines do not become invented numeric promises.
- Renderer optimization is proposed only if measurements attribute a material delay to rendering and a controlled change improves it without semantic loss.
- Initial default promotion rests on complete behavioral receipts and preregistered usefulness criteria; latency is descriptive and does not block the first trial merely because paint timing is unavailable. Preserve any valid timing evidence rather than requiring a paid telemetry service.
- Usefulness includes completion, corrections/clarification, overrides, and validation failures. A low override count alone is not success. Record selection reason, preference source/scope, and actual fallback using existing receipts where possible, without raw answers or action nonces in counters.
- Any semantic/authority failure suspends the affected automatic default pending review, returning to a verified fallback if available. It does not label unrelated hosts or controls broken.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

**ASI-7 — Extend existing owners and promote only reviewed scope**
Reconcile the draft against current code and in-flight work before implementation. Agent-facing need selection belongs with the existing elicitation guidance/consumer; shared rendering and validation belong in attune-forms; host readiness belongs with host-surface-parity; canonical actions stay with the owning command adapter. Reuse current stores, projection scripts, and tests rather than introducing parallel mechanisms.

- T1 identifies actual call sites, owning sources, dependent specs, and existing tests from the execution checkout; each claimed gap has a failing behavioral probe or is labelled unverified.
- A skill change edits its master and reprojects the mirror. A sibling-package behavior change updates dependency floors and owned mirrors through their existing mechanisms.
- Roundtable refinements carry requirement IDs, evidence citations, dissent, and per-item chair dispositions. Unruled or declined proposals are not implemented.
- Repo promotion and implementation remain paused while the no-repo-change instruction remains active.
- If current code invalidates a load-bearing premise, revise the local proposal and return the changed requirement to the chair before implementation. Do not automatically spend another roundtable round for ordinary reconciliation.
- Source-level surface agreement is not evidence of host visibility or user benefit. The inspected selector computes _route(form, widget_capable, keyboard_mode) before logging chosen; passing chosen does not bias its recommendation, so no repair of that alleged confound is justified.
(table: contested — moderator refinement; one compiler-clean seat, no full-roster consensus; chair: approved)

## Non-goals

- No renderer rewrite, speculative caching, new telemetry store, or autonomous learned selector.
- No approval merely to choose presentation, and no repeated permission for previously authorized work.
- No automatic promotion of roundtable proposals or expansion to every interaction after the first trial.
- No claim that Codex and Claude have equivalent visibility instrumentation or that a successful generated widget was displayed.
- No interference with Claude's active repository work.

## Dissent register

Only Antigravity's critique (#6) passed the compiler. This is not full-roster consensus. The chair subsequently approved ASI-1 through ASI-7; the counter-cases below remain part of the decision record.

- Antigravity recommends prohibiting new server-side routing altogether. Moderator: start with guidance, but retain a narrowly evidenced binding check if guidance cannot honor explicit preference; an absolute prohibition would prejudge T1. Strongest counter-case: such a check can become the duplicate selector this spec is intended to avoid.
- Antigravity would allow submission/validation/acceptance to establish readiness while visibility remains wholly unobserved. Moderator: that proves the accepted path but not an unseen rich control. Permit human attestation of usability, keep exact paint timing optional, and keep host/surface attribution explicit.
- Antigravity recommends sequential collection for every multi-field text fallback. Moderator: retain existing batching for independent unknowns; sequence only dependent questions or host-imposed limits. Blanket sequencing would recreate the extra-turn problem.
- Antigravity asserts fine-grained rendering measurement requires paid services or client modification. The supplied evidence does not establish that. Existing stage telemetry is present, though its timing excludes paint and includes dwell. The spec retains descriptive measurements and makes no visibility-timing claim.
- Claude's and Codex's raw replies are retained separately as compiler-rejected material. They are not promoted, counted as votes, or represented as agreement. A substantive Claude claim about chosen biasing the router was independently checked and rejected against the implementation.
