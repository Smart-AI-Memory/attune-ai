# Host Surface Parity — Tasks

**Status:** active, execution-reconciled (2026-09-04) — thirteen local
task blocks are authored: Task 0, Task 1B, and Tasks 2–12. AF-1 and
AF-2 are explicit external handoffs, not local runner tasks. Task 0 is
complete and locally committed but not yet pushed or merged. The
original Task 1 execution probe
falsified its registry and green-baseline premises and paused before
production. D10 rules the corrected context-routed Task 1 split. Each task
executes only behind its own chair go; a go on one task is not a
go on the next. The original Task 1 go covered the falsifying probe;
AF-1 has neither an implementation go nor a package-release go, and
Task 1B has no execution go.
D8 (2026-09-03) granted the 16.3 execution gos for
the ungated items: Task 2 (R1 tier 0), Task 4 (R4 receipt), Task
10 (R9 foundation) and Task 12 (D2 placement-label wiring). Task
shapes were reconciled under D10, whose sequencing correction expressly
preserved those four D8 gos while changing their earliest start. Task
12 remains immediately eligible; Tasks 2, 4, and 10 retain their gos
but execute on the critical path `AF-1 release → 1B → 4 → 10 → AF-2
release → 2`, while Task 1B waits for AF-1's separately authorized
package release; AF-2 likewise has neither an implementation go nor a
0.14.0 release go. Task 11 (R10, adopted in
D9) awaits its own execution go.
Tasks 3, 6, and 9 depend only on Task 0's relevant characterization and
are dependency-eligible independently of the attune-forms release chain. The
document-order runner has no task-ID selector and does not skip earlier blocks;
they execute only when the queue reaches them, so dependency eligibility is not
schedule independence. Task 5 remains
behind Task 1B because its generated templates become parity subjects.
Task 7 additionally waits for the release-16-manifest Phase A substrate
on disk; Task 8 waits for the shipped Phase B artifact. Because the
current spec runner has no enforced external-gate field, each condition
is a parser-visible human/agent STOP precondition and pre-mutation
receipt, not an unsupported XML tag or a claimed machine gate.

## Task 0 — Characterize the surfaces, roster and projector as they are

```xml
<task id="0" name="characterize-baseline">
  <objective>
    Pin current behavior before any change: which forms reach which
    Surface tier, the exact roster gates, and the projector's
    targets and refusal of hand edits.
  </objective>
  <files-to-create>
    <file path="tests/unit/elicitation/test_surface_tiers_characterization.py">
      One demo form rendered on RICH, PORTABLE, HEADLESS; identical
      validated output asserted.
    </file>
    <file path="tests/unit/roundtable/test_roster_characterization.py">
      CANONICAL_SEATS, SEAT_RECIPES, PLAN_ONLY_SEATS and the
      workspace round_complete roster check pinned byte-for-byte.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="tests/unit/scripts/test_project_collaboration_contract.py">
      Pin a hand edit inside a valid projected block as stale.
    </file>
  </files-to-modify>
  <validation>
    <check>Both suites green on main with no production change.</check>
    <check>The projector suite refuses a hand edit inside the marked block.</check>
  </validation>
</task>
```

## Task 12 — Placement-label wiring (D2)

*(Authored 2026-09-03 under D8's go, which names the D2
placement-label wiring an ungated 16.3 item with its execution go
granted. This is the label mechanics only — the field, its
resolution semantics, and the drift-guard receipt — landed ahead of
any local extension so Tasks 7 and 8 find the routing seam waiting.
Before Phase A/B ships an extension, every resolution falls back
hosted, so observable routing behavior is unchanged. The ops-tile
"not a tier" case stays with Task 8 per D2. The four existing in-tree
enum call-paths and canonical attune-rag model-resolution source do not
change — that is the ruling's whole point. The former mirror drift test
was retired by ccb4fe7bc, so Task 12 owns the current focused
assertion.)*

```xml
<task id="12" name="placement-label-wiring">
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <objective>
    Add the D2-ruled placement routing label to the role routing
    record: an optional placement field (default hosted) on
    UnifiedAgentConfig expressing "CHEAP, prefer local, fall back
    hosted". Resolution prefers an enabled local extension when one
    provides the role and falls back hosted when none does — which,
    pre-Phase-A, is always. No enum member anywhere.
  </objective>
  <files-to-modify>
    <file path="src/attune/config/agent_config.py">
      UnifiedAgentConfig gains placement: "local" | None (default
      None = hosted); get_model_id()/routing consults it; with no
      enabled local extension the resolved model is byte-identical
      to today's.
    </file>
    <file path="src/attune/gates/session_ledger.py">
      Invocation rows separate declared placement_preference from
      actual_placement and placement_reason, so fallback is visible rather
      than misreported as local execution.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/config/test_placement_label.py">
      Field default, validation (only "local" or absent), hosted
      fall-back with no extension enabled, an injected fake capability
      provider exercising the future local branch without Phase A production
      substrate, ledger rows separate preference/actual/reason, and all four existing in-tree
      tier enum call-paths remain exactly cheap/capable/premium with no LOCAL
      member.
    </file>
    <file path="docs/specs/host-surface-parity/task-12-receipt.md">
      Focused-test result plus an exact changed-file manifest proving the
      Task 12 diff contains no sibling attune-rag path.
    </file>
  </files-to-create>
  <validation>
    <check>test_placement_label asserts all four in-tree enum call-paths remain exactly cheap/capable/premium and attune.model_tiers remains a lazy canonical re-export.</check>
    <check>The task-12 receipt records the exact changed-file manifest and fails review if any sibling attune-rag path appears; the unit test does not claim to inspect a different repository's diff.</check>
    <check>With no local extension enabled, a role with placement local resolves to the same model id as the same role without the label.</check>
    <check>That pre-Phase-A fallback row records placement_preference local, actual_placement hosted, and placement_reason local_unavailable; an injected successful local provider records actual_placement local. No row treats declared preference as observed execution.</check>
    <check>An injected fake local-capability provider exercises the preference seam in tests; production remains on the empty provider until Phase A supplies the real extension mechanism.</check>
    <check>A placement value other than "local" fails validation with the field named; absent means hosted with no warning.</check>
    <check>No change to ModelProvider; no new routing store — the label lives on the existing record.</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```

## External prerequisite AF-1 — Renderer registry and HEADLESS projection

This work executes in a separate clean `attune-forms` worktree, not in
the attune-ai task runner. The portable implementation contract and
package-local receipts are in
[attune-forms-handoff.md](attune-forms-handoff.md#af-1--registry-and-production-headless-projection-0130).
Its 0.13.0 publication remains an explicit release action. Task 1B
stops before mutation until that released artifact is independently
verified.

## Task 1B — Context-routed surface parity gate (R2)

```xml
<task id="1B" name="context-routed-surface-parity-gate">
  <objective>
    STOP PRECONDITION — human/agent-enforced because the current spec
    runner has no cross-repository gate. Before any file mutation,
    verify a released attune-forms 0.13.0 artifact exposes AF-1's
    non-empty registry, production workspace_to_headless target, and public
    package-shipped canonical fixtures/normalization descriptors; a
    local editable checkout is not evidence. If false or unverifiable,
    report BLOCKED and leave this task incomplete. Against that released
    registry, select the first supported
    surface from each subject's cold/warm preference order and add the
    non-vacuous parity gate, receipts, and contract enforcer.
    attune-forms owns generic serializers; attune-ai owns the stateful
    adapters, receipt store, routing policy, and production round trip.
  </objective>
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <files-to-create>
    <file path="src/attune/elicitation/surface_policy.py">
      Resolve the deterministic precedence over one immutable capability
      snapshot; evaluate pure candidate admissibility; issue/rotate
      server-owned context receipts; define the route-neutral non-serializable
      PresentationChallenge, DeferredPresentationAdapter callback context, and
      submission-idempotency state; and emit
      reason-coded route/latency decisions without probing or trial renders.
    </file>
    <file path="tests/unit/elicitation/test_surface_policy.py">
      Cold/warm evidence, ordered fallback and unknown-is-cold tests.
    </file>
    <file path="tests/unit/gates/test_surface_parity.py">
      Registry, producer-discovery, lifecycle, experiment and mutation gates.
    </file>
    <file path="docs/specs/host-surface-parity/parity-registry.json">
      Machine-readable renderer receipts, detected surface subjects,
      host profiles, per-target obligations, envelope signatures,
      accessibility-constraint provenance, capability snapshots,
      context-receipt schema, cold/warm routes, normalization paths,
      event-qualified delivery routes, compatibility endpoints,
      producer_baseline, experiments/history, and experiment exceptions.
    </file>
    <file path="docs/specs/host-surface-parity/receipts.md">
      Human evidence ledger keyed to machine receipt IDs.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="pyproject.toml">Raise the attune-forms floor from 0.12.2 to 0.13.0; retain the existing exclusive 1.0 upper bound.</file>
    <file path="uv.lock">Lock released attune-forms 0.13.0.</file>
    <file path=".github/workflows/cross-repo-compat.yml">Add scheduled, dependency-update and manual advisory fresh-resolution jobs with version/digest/fixture/owner artifacts; never replace the locked gate.</file>
    <file path="src/attune/elicitation/__init__.py">Export the surface-policy API.</file>
    <file path="src/attune/elicitation/ask_payload.py">Preserve the fixed AskUserQuestion compatibility adapter; unified policy uses host-native only through a trusted in-process profile and route-active registry target.</file>
    <file path="src/attune/elicitation/command_workspace.py">Render only the selected route and expose the authoritative workspace binding captured by the receipt.</file>
    <file path="src/attune/mcp/server.py">Own the session ID and receipt store; add the unified context-routed form handler while retaining the fixed-shape deprecated render_form compatibility handler.</file>
    <file path="src/attune/mcp/tool_schemas.py">Define the closed success/error selected_route/payload_kind/receipt/submission union and exact four-field context_reason/selection_elapsed_ms/renderer_attempt_count/presentation_attempt_count summary whitelist, require echoed receipt/submission IDs plus host response for deferred collection, and preserve the compatibility schema.</file>
    <file path="tests/unit/elicitation/test_ask_payload.py">Trusted AskUserQuestion profile and untrusted-capability rejection.</file>
    <file path="tests/unit/mcp/test_server_elicitation.py">Receipt issue/echo, restart invalidation, unified discriminated routing, and fixed-shape compatibility behavior.</file>
    <file path="tests/unit/elicitation/test_command_workspace.py">Full workspace binding and event-sequence invalidation.</file>
    <file path="tests/unit/elicitation/test_command_workspace_contract.py">Selected-only rendering and receipt binding contract.</file>
    <file path="tests/unit/mcp/test_tool_schemas.py">Opaque receipt input/output schema.</file>
    <file path="tests/unit/mcp/handlers/test_elicitation_render_widget.py">Production widget handler policy routing.</file>
    <file path="content/collaboration/contract.md">
      Add the surfaces enforcer, then run the contract projector.
    </file>
    <file path="AGENTS.md">Projector-owned contract block.</file>
    <file path=".claude/CLAUDE.md">Projector-owned contract block.</file>
    <file path=".agents/AGENTS.md">Projector-owned root mirror.</file>
  </files-to-modify>
  <validation>
    <check>A pre-implementation clean-wheel receipt proves the installed released artifact is attune-forms 0.13.0, exposes AF-1's non-empty registry, closed projection_output_types vocabulary and production HEADLESS target, imports/executes every registry-referenced canonical fixture without test modules, and is not a local editable override; absence fails the task.</check>
    <check>The AF-1 scanner strips only None from Optional[T]/T|None and requires one declared projection type; other unions fail closed while prefix-named callables remain covered independently. Adding, removing or editing an allowlisted FQN/rationale—or attempting to hide a renderer there—fails the package gate.</check>
    <check>A later artifact stays green only when its obligation set and per-target implementation/fixture/normalization/owning-record-slice digests are unchanged and its canonical fixtures pass. Route-active host-native evidence uses route_roundtrip and binds the installed profile facet and adapter/collector closure. AF-1's compatibility-only target instead requires compatibility_projection: its fixed contract ID/shape and status/mode are digest-bound; its canonical specialized output alone supplies question IDs/options for a raw answer passed through common collect_form_response; and its normalized FormResponse equals PORTABLE/HEADLESS controls without claiming route, presentation, lifecycle, or tier. The consuming compatibility endpoints separately bind their two exact legacy shapes. Changing status/mode, contract ID/shape, emitted questions/options, or a helper invalidates the exact target; an unrelated symbol does not. Unresolved behavior-affecting dynamic dependencies require explicit package-relative artifact refs or fail closed, and uv.lock pins the gating artifact set. The advisory fresh-resolution workflow runs on schedule, dependency update and manual dispatch and publishes resolved version/digests/fixture result/owner without replacing or failing the locked gate.</check>
    <check>A response constructed from the released workspace_to_headless output reaches attune-ai's stateful command-workspace adapter and ultimately attune-forms collect_workspace_action, matching widget/Markdown normalization; an action-ID-only or empty mapping fails closed. R4 separately receipts the public fix_workspace_collect_action seam.</check>
    <check>Every enhanced renderer/subject target derives a unique obligation key and digest-bound parity receipt; adding a second host-native target, changing route-active/compatibility-only status or its required evidence mode, or replacing a callable/normalizer under an existing key without fresh evidence fails with that exact key.</check>
    <check>Parity, lifecycle and delivery receipts use their closed discriminated foreign keys. For each interactive form, route_transport_refs keys equal the union of declared cold/warm route tokens; MCP-native keys name their matching interaction_transport, host-native keys name their matching host profile, and direct RICH/PORTABLE/HEADLESS keys name interaction transports. A missing/extra/wrong-kind route key, a complete interaction_transport whose form_subject_ids omit the current form, an orphan/one-way association, or one missing timeout or validation-feedback-delivery receipt fails referential integrity and makes that route inadmissible.</check>
    <check>Every mechanically detected host-exposed producer root has exactly one subject record. Python module-body output uses repo/path.py:&lt;module&gt;. Discovery traverses statically resolvable repo-local helper calls cycle-safe; helpers retain file:qualname plus every reaching root as implementation/provenance nodes and become subjects only when independently exported/invoked at a host boundary. Adding a registered projection call or positive host-envelope signature in a root or helper fails as root-anchor -&gt; helper-anchor, shared helpers may serve different root routes, and unresolved relevant dispatch fails closed. A same-file unrelated function cannot transfer positive-signature credit.</check>
    <check>Before mutation Task 1B creates a reviewed producer_baseline fixture from its execution base with separate renderer_call_anchors, package_host_envelope_anchors, manifest registrations/raw commands/resolved paths/events, and helper-reachability edges. D6's calibration found six renderer-call anchors/seven sites and 26 registrations/24 unique paths; Task 0 is not claimed as the owner of those facts. Direct, attune.elicitation re-export, qualified-module alias, and helper-indirection mutations are discovered against the fixture.</check>
    <check>The path-aware producer_baseline preserves distinct same-basename files, while plugin/commands/handoff.md remains artifact-anchored and resolves _handoff_cli.py as its implementation. Registration order is permuted in a test; event union schedules one scan but emitted obligations remain keyed by event/matcher/signature/sink/destination, so one event cannot transfer credit.</check>
    <check>The closed shell resolver accepts every current wrapper without execution; an unknown variable, extra token/operator, path escape, missing file, or genuinely inline/non-Python manifest program fails with its registration identity and manifest JSON-pointer.</check>
    <check>The cycle-safe AST scanner covers supported literal/dict/single-assignment mappings through statically resolvable helpers at the closed print/sys.stdout.write/buffer.write and return sinks and fails closed on a recognized key or dynamic sink it cannot resolve. Event-aware non-empty stdout from SessionStart/UserPromptSubmit, PreToolUse deny+permissionDecisionReason, Stop/SubagentStop block+reason, and declared SystemExit(2)/exit-2 stderr sinks classify to their exact subject kind and destination; wrong event/exit/stream plus bare reason/control fields remain control-plane. The refreshed producer_baseline, not a permanent literal count, owns the evidence.</check>
    <check>A new plugin/commands/new.md is discovered as artifact:plugin/commands/new.md; shipped Python roots are derived from packaging/entry-point metadata (including attune_redis), an attune_redis renderer-call mutation is caught, and unreferenced tests/development scripts stay excluded.</check>
    <check>A hard PORTABLE accessibility constraint beats a warm receipt and RICH-capable profile; an unavailable hard constraint returns no_supported_surface, and neither a tool argument nor model response can assert the constraint.</check>
    <check>Default orders are pinned: cold form discovery prefers the negotiated mcp-native transport backed by the HEADLESS elicitation-schema projection, then trusted route-active in-process host profiles, then PORTABLE/HEADLESS; warm forms prefer RICH, negotiated mcp-native, trusted host-native, PORTABLE, HEADLESS; warm workspaces prefer RICH before portable fallbacks; cold workspaces prefer PORTABLE; noninteractive execution prefers bare HEADLESS. Informational subjects have event-qualified delivery_routes instead of surface cold/warm lists and do not cycle surfaces.</check>
    <check>MCP native elicitation/apps use only the authenticated initialize/session capability object, where omission from a completed closed-vocabulary negotiation is observed false rather than unknown; AskUserQuestion uses only a trusted immutable in-process adapter profile. Capability cells are typed session_negotiated or host_static; request/tool/model fields cannot populate either channel, a current negative beats cache, doctor cache fills only unknown host_static cells, and absent current negotiation never selects cached MCP native/apps.</check>
    <check>Producer route ownership is exact: _handle_elicitation_ask applies trusted capability/accessibility admissibility then resolves only mcp-native through session.elicit_form, preserving its unsupported shape; form_to_ask_payload and deprecated _handle_elicitation_render_form are the exact derived compatibility_endpoint anchors over the specialized target and own no policy route. The new _handle_elicitation_route_form returns the closed success/no_supported_surface/render_failed/session_ended/challenge_invalidated/challenge_consumed union with exact route/receipt/submission invariants. A deferred-payload success alone carries a server-issued submission_id; same-call completion and errors carry none. Its exact server-output-only decision-summary keys are context_reason, selection_elapsed_ms, renderer_attempt_count, and presentation_attempt_count with the closed types in the design; candidate/provenance/binding details and unknown keys fail schema validation, and echoed/modified summary data has no authority, while the full route receipt stays server-side. It invokes session.elicit_form itself for mcp-native and uses host-native only through a trusted profile plus route-active target. A third compatibility anchor or another direct/policy caller fails.</check>
    <check>A candidate missing one semantic/lifecycle requirement is rejected by pure admissibility metadata and the next declared candidate wins without invoking the rejected renderer; if the one selected renderer then fails or unexpectedly reports unsupported, the route ends render_failed and no second renderer runs.</check>
    <check>Every ordered context predicate is table-tested, including empty+missing, ended+superseded, terminal+expired, age 0, just below 3600, exactly 3600, future time, and the same explicit form_id with changed canonical schema digest; the first-match reason is exact.</check>
    <check>Session close atomically marks the registry ended and tombstones every active receipt before a late action can commit. Active age uses observed_at and returns expired only after earlier mismatches; tombstone age uses tombstoned_at and returns its stored reason below 7200 seconds. At exact age 7200 either is logically foreign regardless of physical GC; 7199.999/7200 and delayed-cleanup cases are pinned under the same lock.</check>
    <check>The installation-scoped receipt-auth key survives a process restart while the default store does not, producing foreign_receipt for an old well-formed ID and invalid_receipt for a bad MAC; an injected cross-instance record exercises server_instance_mismatch.</check>
    <check>subject_id is bound to immutable subject_kind. Empty string is valid only as a cold anonymous-form subject ID. Form receipts forbid workspace fields; workspace receipts require all seven binding fields; missing/invalid/forbidden fields—including CommandWorkspaceHost.get returning None—return record_shape_mismatch; workspace_mismatch compares workspace IDs only after valid workspace shape, and workspace-only reasons never run for a form.</check>
    <check>An unchanged pure re-render returns the same active receipt but atomically registers a fresh authenticated pending submission token for that presentation; changed state/binding issues or rotates the receipt. The token is bound in the receipt-chain store to server/store instance, session/chain, receipt, route, payload and collection/validator digests. A deferred-payload success returns it for the public collector to echo; same-call transports mint/consume it internally. The one store lookup rejects malformed/unauthentic/unissued as invalid_submission and authentic cross-binding use as submission_mismatch before validator/side effects. Commit stores canonical-response digest plus exact result: a delivery-loss retry with the same ID/digest returns that byte-identical result after tombstoning, while same ID/different digest fails submission_conflict. Two issued IDs on one unchanged receipt race normally; after one winner the other gets superseded_receipt/terminal. Unused tokens die on supersede/terminal/expiry/session close. Validation feedback CASes active receipt plus revision/schema, tombstones the predecessor and activates the same-state successor; non-terminal returns a warm successor plus its next-attempt token; terminal atomically creates a tombstone and no active receipt.</check>
    <check>Deferred collection uses a route-neutral frozen SurfaceInteractionRecord slot containing canonical validator input, payload digest, selected route, expected authenticated collection transport and opaque adapter-owned correlation data. Public collection accepts only active receipt, submission ID and host response; only a server-registered DeferredPresentationAdapter callback can supply non-serializable CollectionTransportContext. Missing context validates as unverified_transport; adapter/correlation mismatch or callback replay fails without rotation. Caller-supplied form/bindings/profile/tier is rejected. Task 1B defines no AF-2 QuestionAnswerBinding dependency.</check>
    <check>The mcp-native route_form arm serializes the HEADLESS schema once, creates a non-serializable PresentationChallenge from authoritative state, invokes authenticated session.elicit_form itself, and accepts only the server-observed completion for that challenge rather than returning a caller-presentable request. Completion creates/advances the interaction receipt atomically; transport failure records render_failed, creates no new receipt and preserves any predecessor. A second completion returns the public challenge_consumed error arm with the required already-selected route, null receipt/payload/completion/submission, no exposed winner receipt, and no mutation; session close/explicit invalidation returns session_ended/challenge_invalidated under the same invariants. These are challenge dispositions, not new interaction-lifecycle evidence tokens. Task 1B records trusted transport provenance separately from bare schema consumption but does not stamp rendered_tier; Task 11 owns that mapping.</check>
    <check>Selection performs no network/capability probe, at most one receipt-store lookup, one authoritative session-registry read and one current-workspace read, and at most one projection-renderer invocation—one for a selected route, including the schema serializer behind mcp-native transport, and zero for no_supported_surface. Feedback-capable same-route retries reuse that projection; they increment a separate presentation_attempt_count without changing renderer_attempt_count or cycling. The receipt records candidate dispositions, both attempt counts, selection_elapsed_ms and a non-gating comparison with failed-rich-then-fallback.</check>
    <check>Required and receipted sets are exactly equal for parity, every owned/delegated lifecycle state, artifact content/render/destination/delivery, and event-qualified hook content/destination/delivery; all kinds bind and execute current implementation/fixture/evidence digests, and every normalized parity/lifecycle fixture binds its normalization digest. Deleting one direct accept, artifact render, delivery receipt, or form validation-content evidence—or changing normalization only—fails the exact existing key.</check>
    <check>Every RICH or host-native renderer/subject target has PORTABLE and HEADLESS twins. Interactive fixtures prove schema-identical validated payloads after declared normalization and lifecycle; informational fixtures prove their exact per-kind closed evidence set.</check>
    <check>Experiments declare id, exact obligation_key, package-excluded root_anchor, valid UTC dates, owner and reason; 13/31-day, future-start, expired and shipped-artifact entries fail while an active 14/30-day entry subtracts only its named obligation. One reviewed registry mutation atomically adds the active experiment, removes its machine receipt, and appends machine history; expiry requires fresh execution. Active experiment plus receipt fails experiment_receipt_conflict. Overlapping/touching records or more than 30 waiver days per stable obligation in 180 days fail; an experiment_exceptions record binds one experiment/key/current implementation/decision/bounded interval and relaxes only the rolling cap, never the obligation/conflict/sibling checks. Target rename cannot erase history.</check>
    <check>Deleting one real local subject's PORTABLE target from a scratch parity-registry copy makes the Task 1B gate fail with the exact subject and shortfall; renderer-target deletion is AF-1's package receipt.</check>
    <check>python scripts/project_collaboration_contract.py --check exits 0, proving the marked AGENTS.md and .claude/CLAUDE.md blocks equal the canonical rendering from content/collaboration/contract.md; .agents/AGENTS.md is byte-identical to AGENTS.md.</check>
    <check>Changed code carries at least 90% coverage.</check>
  </validation>
  <risks>
    <risk severity="high">Static discovery cannot prove every indirect wrapper; direct-call/envelope mutations and Task 11 tier provenance bound the residual.</risk>
  </risks>
</task>
```

## Task 4 — MCP Apps round-trip receipt (R4)

```xml
<task id="4" name="mcp-apps-roundtrip-receipt">
  <dependencies>
    <dep>1B</dep>
  </dependencies>
  <objective>
    Record both R4 paths independently: a live Cowork capture identifies
    its actually advertised state, and a controlled keyless fixture proves
    whichever advertised-profile or absent-profile branch was not live.
    The advertised transcript bootstraps cold through PORTABLE, echoes the
    server receipt, and reopens the unchanged workspace warm before any RICH
    widget claim. Both receipts preserve exact Fix render/action or Markdown-fallback
    evidence and label simulated evidence as simulated. No production change
    unless either receipt fails.
  </objective>
  <files-to-modify>
    <file path="docs/specs/host-surface-parity/receipts.md">
      R4 blocks: advertised-profile render/action response and absent-profile Markdown fallback, each with provenance; replay, stale revision and wrong hash refused.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="docs/specs/host-surface-parity/r4-receipts.json">Machine authority for exactly the advertised-profile and absent-profile host-capture records, with live/simulated provenance, capability-snapshot digest, render/binding fields and fail-closed outcomes; separate from parity-registry.json.</file>
  </files-to-create>
  <validation>
    <check>The advertised-profile transcript first captures the intentional cold PORTABLE preview and server receipt, echoes that receipt, then reopens the unchanged workspace warm and captures the RICH Fix widget plus a bound response from the public fix_workspace_collect_action tool with exact revision/nonce/hash. It traces delegation through the shared command-workspace host to the underlying attune-forms collector; it is live when advertised and otherwise comes from the controlled keyless fixture labeled simulated.</check>
    <check>Replay, stale revision, and wrong contract hash each fail closed with the exact existing fix_workspace reason.</check>
    <check>The independent absent-profile receipt proves the Markdown preview matches the terminal preview argv exactly; it is live when the host lacks ui:// and otherwise comes from the controlled keyless snapshot labeled simulated.</check>
    <check>r4-receipts.json contains exactly one record per path and the Markdown ledger references both IDs; no R4 host capture is misclassified as a replayable parity-registry receipt.</check>
  </validation>
</task>
```

## Task 10 — Capability descriptor and conformance foundation (R9)

*(Authored 2026-09-03 under D8's go; D9 records the motivation.
Motivation receipt: the 2026-09-03 guard-intervention audit ("The
Prose Gap", `~/.attune/reports/guard-intervention-record-2026-09-03.md`,
ledger entry 2) logged a live instance of the exact failure this
task kills — a widget emitted to a host that does not render
MCP-app content, with the render claimed successful unverified.
The chair ruled R9/R10 the one mechanical enforcer to adopt from
that audit, declining all other new gates. Sequencing per D5:
after Task 4's R4 receipt, before Task 2. D6 probe 2 verified that
installed attune-forms already exports `HostCapabilities`,
`InteractionProfile`, and the `attune_forms.conformance` types
`ConformanceReceipt`, `ConformanceReport`, `ConformanceStatus`, and
`ConformanceFinding` — this task wires against them, it does not
reinvent them. The deferred round-2 questions (attestation schema for
host-UI resolutions; the single no-privileged-host receipt producible
in CI) became concrete in this task and were settled by D8/D9; Task 10
retains that execution go under D10's dependency correction.)*

```xml
<task id="10" name="capability-descriptor-foundation">
  <dependencies>
    <dep>4</dep>
  </dependencies>
  <objective>
    Give every host adapter and extension a machine-readable
    capability descriptor, an `attune surfaces doctor` probe that
    writes capability receipts, a generated hosts × capabilities
    matrix, and a conformance suite — all assertable in CI with no
    host present. Register the doctor-backed CapabilityProvider through
    Task 1B's policy seam so the policy consumes one immutable snapshot
    and passes only the selected route's profile to one renderer, never
    probing/sniffing per call; host-capability absence becomes a
    recorded fact, not an assumption.
  </objective>
  <files-to-create>
    <file path="src/attune/surfaces/__init__.py">Export descriptor, doctor, matrix and conformance public APIs.</file>
    <file path="src/attune/surfaces/descriptor.py">
      Capability descriptor record per host adapter and extension:
      structured-question shape, memory surfaces, ui:// profiles,
      scheduling/monitoring support, action round-trip guarantees,
      receipt schema versions. Reuses attune-forms
      HostCapabilities/InteractionProfile where they fit. Derive the
      authoritative ID inventory from production CapabilityProvider
      registrations plus shipped/enabled attune.* extension entry points;
      require exact equality with descriptor IDs. Before Phase A ships, the
      extension-derived half is expected to be empty and is not itself a
      mismatch.
    </file>
    <file path="src/attune/surfaces/doctor.py">
      Probe + `attune surfaces doctor` CLI: records which
      contracts the current host actually advertises and writes a
      capability receipt with each cell typed session_negotiated or
      host_static; with no host present it writes the
      all-fallback receipt and exits 0.
    </file>
    <file path="src/attune/surfaces/matrix.py">
      Generates the hosts × capabilities matrix (each cell
      native / fallback-receipted / absent) from accumulated
      receipts.
    </file>
    <file path="docs/specs/host-surface-parity/capability-matrix.md">
      Generated; header states it is generated and names the
      generator; drift-guarded.
    </file>
    <file path="tests/unit/surfaces/test_descriptor.py">Descriptor schema, authoritative-ID equality and invalid-claim receipts.</file>
    <file path="tests/unit/surfaces/test_surfaces_doctor.py">Hostless, advertised-capability, expiry and replay receipts.</file>
    <file path="tests/unit/cli_commands/test_surfaces_commands.py">
      Parser/dispatch, hostless receipt and exit-code coverage for
      `attune surfaces doctor`.
    </file>
    <file path="tests/unit/surfaces/test_conformance_suite.py">
      Canonical transcripts against each adapter: unsupported
      capabilities degrade deliberately; semantic outputs stay
      equivalent; receipts keep provenance and replay protection;
      removing any host adapter leaves PORTABLE and HEADLESS
      usable; no workflow silently selects a privileged host.
    </file>
    <file path="tests/unit/gates/test_capability_matrix_drift.py">Deterministic generation, hand-edit refusal and descriptor/provider drift receipts.</file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/cli_minimal.py">Register and dispatch the `surfaces doctor` command group.</file>
    <file path="src/attune/elicitation/surface_policy.py">Register and merge the persistent doctor-backed provider behind the existing CapabilitySnapshot seam.</file>
    <file path="src/attune/mcp/server.py">Compose the provider without adding a render-path probe; fresh negotiated evidence wins over cached evidence.</file>
    <file path="tests/unit/elicitation/test_surface_policy.py">Provider precedence, stale evidence, and no-probe request-path receipts.</file>
    <file path="tests/unit/mcp/test_server_elicitation.py">Composition-root wiring and current-negative-over-cached-positive behavior.</file>
  </files-to-modify>
  <validation>
    <check>The doctor with no host present writes the all-fallback receipt and the matrix's fallback column is green — the whole suite passes keyless and hostless in CI.</check>
    <check>A descriptor advertising a capability its adapter cannot demonstrate fails the conformance suite with the cell named.</check>
    <check>The production CapabilityProvider registration set is non-empty and its IDs plus attune.* extension-entry-point IDs equal descriptor IDs exactly; before Phase A the extension-derived set is explicitly receipted empty rather than used as the non-vacuity witness. Adding an unregistered adapter/extension or orphan descriptor fails with its ID.</check>
    <check>A hand edit inside the generated matrix fails the drift guard; regeneration is deterministic.</check>
    <check>With any single host adapter removed, PORTABLE and HEADLESS conformance stays green and no privileged host is silently selected.</check>
    <check>The policy reads one provider snapshot with no request-path network probe; observed live cells beat persisted cells, a host-bound cache fills only unobserved host_static cells during [observed_at, expires_at), exact-expiry is stale, a future observed_at or interval outside (0,3600] seconds is rejected rather than clamped, and a current negative is never elevated. MCP-native elicitation/apps are session_negotiated and require current authenticated negotiation; absent negotiation never selects a cached native value.</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```

## External prerequisite AF-2 — Host-profile renderer

After local Task 10, this package work executes in a fresh clean
`attune-forms` worktree under
[attune-forms-handoff.md](attune-forms-handoff.md#af-2--host-profile-structured-question-renderer-0140).
Its 0.14.0 publication is a separate release action. Local Task 2
consumes only the verified released artifact.

## Task 2 — Consume the host tier 0 renderer (R1)

```xml
<task id="2" name="host-tier-zero-consumer">
  <dependencies>
    <dep>10</dep>
  </dependencies>
  <objective>
    STOP PRECONDITION — human/agent-enforced because the current spec
    runner has no cross-repository gate. Before any file mutation,
    verify a released attune-forms 0.14.0 artifact exports AF-2's
    HostQuestionProfile, QuestionAnswerBinding, HostQuestionBatch,
    host_question_admissibility, form_to_host_question,
    and its host-profile registry target; verify that target resolves to the
    matching facet of one installed InteractionProfile. A local
    editable checkout is not evidence. If false or unverifiable, report
    BLOCKED and leave this task incomplete. Lock and consume that
    renderer on the actual attune-ai routing seam through a concrete trusted
    in-process HostQuestionAdapter used only by the unified route_form tool;
    leave form_to_ask_payload and deprecated render_form compatibility unchanged.
    Pure admissibility metadata
    selects PORTABLE intact whenever the active profile cannot represent the
    form; the policy never invokes the host renderer to discover that fallback.
    Validate every returned answer on the common path.
  </objective>
  <files-to-create>
    <file path="src/attune/elicitation/host_question_adapter.py">Immutable HostQuestionAdapter protocol, server-owned ValidationFeedbackEnvelope, and HostQuestionCompletion over Task 1B's route-neutral PresentationChallenge; same-call present_and_collect is the only trusted non-MCP presentation boundary.</file>
    <file path="tests/unit/elicitation/test_host_question_adapter.py">Profile/target identity binding, Task 1B challenge use, same-call collection, completion compare-and-consume, session-close race, absent-adapter fallback and fake-adapter interface receipts.</file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/elicitation/surface_policy.py">Register the released profile target as host-native only when a live matching HostQuestionAdapter object is installed; preserve selected-only rendering.</file>
    <file path="src/attune/elicitation/ask_payload.py">Add the raw host codec/correlation and Other/cancellation decoder from immutable QuestionAnswerBinding records into the common validator bridge for a same-call trusted HostQuestionCompletion; invoke the released renderer only with the trusted profile and preserve form_to_ask_payload unchanged.</file>
    <file path="src/attune/mcp/server.py">Register the immutable adapter outside request data; for the unified host-question arm call present_and_collect with an in-memory challenge and collect its completion without returning a relay payload.</file>
    <file path="src/attune/mcp/tool_schemas.py">Define host-question-completion as the unified response arm; expose no caller input for bindings, profile, tier, presentation challenge or completion attestation.</file>
    <file path="tests/unit/elicitation/test_surface_policy.py">Released-registry integration, pure profile admissibility, selected-only rendering, terminal render-failure and capability-change receipts.</file>
    <file path="tests/unit/elicitation/test_ask_payload.py">Generic-adapter malformed answer, Other, cancellation and common-validation receipts plus the unchanged fixed-shape compatibility regression.</file>
    <file path="tests/unit/mcp/test_server_elicitation.py">Same-call AF-2 completion, caller-forgery refusal, absent/mismatched-adapter fallback and superseded/terminal receipt refusal.</file>
    <file path="scripts/render_demo_forms.py">
      Add the tier-0 render and profile-change fallback of the existing audit demo form.
    </file>
    <file path="pyproject.toml">
      Raise the attune-forms floor to 0.14.0; retain the existing exclusive 1.0 upper bound.
    </file>
    <file path="uv.lock">Lock that released package artifact.</file>
    <file path="docs/specs/host-surface-parity/parity-registry.json">Add the new profile target's machine receipt foreign keys.</file>
    <file path="docs/specs/host-surface-parity/receipts.md">Record the human evidence keyed to those receipt IDs.</file>
  </files-to-modify>
  <validation>
    <check>A pre-implementation receipt proves the installed released artifact is attune-forms 0.14.0, exports HostQuestionProfile, QuestionAnswerBinding, HostQuestionBatch, host_question_admissibility, form_to_host_question, and its registry target; that target's profile_id resolves to exactly one installed InteractionProfile host-question facet; the artifact is not an editable checkout. Absence fails the task.</check>
    <check>A direct defensive call outside the active profile returns None from form_to_host_question, while the routed policy rejects that candidate through host_question_admissibility without invoking it and renders PORTABLE unchanged with one renderer attempt total.</check>
    <check>If a profile-admissible selected host renderer raises or unexpectedly returns None, the receipt is render_failed and PORTABLE is not attempted on that request.</check>
    <check>The demo proves a profile capability change changes admissibility without changing form data; malformed host answers re-enter common validation and are never accepted. If the profile supports feedback, the server derives an immutable ValidationFeedbackEnvelope from canonical errors, binds its digest into a fresh challenge, and passes it as a separate argument while reusing the original HostQuestionBatch and original non-resetting deadline. The positive max_validation_attempts includes the initial call. Each present_and_collect call increments presentation_attempt_count, renderer_attempt_count remains one, and rejection rotates/re-presents only that route. Caller/host-authored or mutated feedback is rejected. A cap-3 fixture with reject/reject/accept records one route decision, renderer count 1, presentation count 3, and zero fallback calls. Exhaustion aborts; adapter exception/None/wrong challenge/deadline failure is render_failed and preserves the receipt active when that attempt began; trusted user timeout remains timeout. No case selects another surface.</check>
    <check>Recommended options use a stable partition; the suffixed emitted label is included in per-question length/collision admissibility after profile normalization and cannot collide with the profile's reserved Other label/token. HostQuestionBatch.answer_bindings is an immutable tuple of QuestionAnswerBinding records carrying stable question_id, emitted ordinal, exact emitted question text, and that question's ordered emitted_label/response_atom/option_id triples; repeated Yes/No labels across questions remain unambiguous. The renderer retains no hidden state; only the trusted adapter sends the batch payload, while the same server call retains the bindings/profile mode and collects the completion without stripping text or accepting a caller-supplied map.</check>
    <check>HostQuestionProfile declares closed question/option normalization, response_correlation question_id/emitted_text/ordinal, raw multi-select atom kind/codec, finite attempt cap and deadline. A characterization receipt from installed Claude Code 2.1.260 pins the current AskUserQuestion profile: header max 12; emitted-text answer keys; canonical comma-space-delimited emitted-label atoms; JSON-string quoting for labels containing the delimiter or a quote; canonical re-encoding required; and freeform in a separate global response. The server maps atoms through retained bindings to option IDs. Empty/unknown/duplicate/noncanonical atoms, duplicate normalized questions, structured-plus-freeform conflict, zero/multiple unanswered-question freeform ambiguity, malformed correlation/encoding, and profile-digest changes are covered. A future token-returning profile must declare response_token atoms and bind them distinctly.</check>
    <check>A live HostQuestionAdapter is immutable and registered by the server outside request/tool/model data; its adapter/profile identity must match the installed InteractionProfile and route-active target. The unified arm calls present_and_collect once per bounded presentation attempt with a non-serializable PresentationChallenge and optional server-owned validation-feedback envelope and accepts only a completion returning that challenge object. Trusted completion atomically creates/advances the record; failure creates no new receipt and preserves a predecessor. Second completion returns challenge_consumed; close/invalidation wins as session_ended/challenge_invalidated without mutation. No/mismatched adapter makes the candidate inadmissible before rendering and selects PORTABLE; a fake proves only the interface.</check>
    <check>The released registry gives the pre-existing AskUserQuestion target and new generic profile target distinct target IDs; for their overlapping profile the old target is compatibility-only and the new target is the sole route-active choice, while each keeps its own parity obligation.</check>
    <check>Task 1B's two compatibility regressions remain byte-for-byte green after AF-2 consumption: form_to_ask_payload retains its list of tool-ready `{questions,metadata}` batch payloads, while deprecated elicitation_render_form separately retains `{success,title,description,batches}` over the specialized target. Only the unified elicitation_route_form path calls the trusted adapter and emits the selected_route/payload_kind union with a host-question-completion arm.</check>
    <check>Parity gate green with the new receipt line.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs anywhere in the task.</check>
  </validation>
</task>
```

## Task 11 — Tier provenance on validated answers (R10)

*(Authored 2026-09-03 under D8's go; requirement adopted in D9 from
the same guard-intervention audit — the audit's ledger entry 2 is
the failure made visible: with provenance stamped from the response
envelope, a render claimed on a surface that never displayed it
becomes a recorded fall-through instead of an unverifiable prose
claim. Executes only behind its own chair go. Pairs with Task 10 as
H1's falsifier: the doctor says which tiers the host offers;
provenance says which tier each answer actually used.)*

```xml
<task id="11" name="tier-provenance">
  <dependencies>
    <dep>2</dep>
  </dependencies>
  <objective>
    Give every validated answer an exhaustive provenance disposition. Stamp a
    surface tier (tier 0 host-native / RICH / PORTABLE / HEADLESS) only from a
    server-observed completion or authenticated adapter callback, never the
    render request; mark model-mediated transport and the legacy compatibility
    collector explicitly unverified instead of inventing a tier. Surface
    verified tier-0 fall-through/Other counts and raw unverified counts through
    the existing telemetry stores.
  </objective>
  <files-to-modify>
    <file path="src/attune/elicitation/ask_payload.py">
      Validated-answer envelope gains a rendered_tier field,
      stamped where the response is collected.
    </file>
    <file path="src/attune/mcp/server.py">
      Unified elicitation_collect_response and both native MCP handlers record
      actual tier and whether the host "Other" free-text escape was used, but
      only from a server-observed MCP completion, authenticated deferred
      callback bound to the active receipt, or same-call HostQuestionAdapter
      completion bound to Task 1B's PresentationChallenge. The legacy form-plus-answers branch
      records unverified_compatibility and no tier.
    </file>
    <file path="src/attune/gates/session_ledger.py">
      Independent raw fall-through, Other, unverified-transport and
      unverified-compatibility counters, never ratios;
      Task 9 later reads the same ledger beside its ask/outcome fields.
    </file>
    <file path="scripts/render_demo_forms.py">Regenerate the canonical five-surface fixture/projections and bare HEADLESS control without claiming to simulate host display.</file>
    <file path="docs/specs/host-surface-parity/receipts.md">Human live-host transcript keyed to the tier-provenance machine receipt IDs.</file>
    <file path="tests/unit/mcp/handlers/test_elicitation_ask.py">Existing native handler and unified native arm stamp only from server-observed session.elicit_form completion; unsupported/error paths do not.</file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/elicitation/test_tier_provenance.py">Actual-tier stamping, fallback, Other, HEADLESS and answer-privacy receipts.</file>
    <file path="docs/specs/host-surface-parity/tier-provenance-receipts.json">Machine records for server-observed/authenticated host completions plus the identical bare HEADLESS control; no answer contents.</file>
  </files-to-create>
  <validation>
    <check>A form exceeding the current host profile records rendered_tier portable and increments the verified fall-through counter only when its PORTABLE answer returns through an authenticated adapter callback; a model-mediated answer records unverified_transport and no tier.</check>
    <check>A render requested RICH whose authenticated response arrives on a fallback surface records the fallback, never the request — the audit's ledger-2 case is a recorded fall-through. The same response without authenticated presentation evidence is unverified_transport.</check>
    <check>An authenticated answer via the host "Other" escape increments the Other counter; verified rates are computable from the existing JSONL with no new runtime/telemetry store. The spec-owned tier-provenance-receipts.json is evidence, not a counter source.</check>
    <check>A headless run records rendered_tier headless; Task 11 neither depends on nor duplicates Task 9's later ask/outcome counters and friction display.</check>
    <check>Two responses built from the same elicitation-schema projection are distinguished by trusted transport evidence: the unified mcp-native handler's server-observed session.elicit_form completion records rendered_tier host_native plus its selected_route, while bare programmatic consumption records rendered_tier headless. Caller input, requested route and the render receipt alone cannot assert presentation or tier; transport provenance is not collapsed into the tier field.</check>
    <check>The pre-existing _handle_elicitation_ask path also records host_native only after its own server-observed session.elicit_form completion. Its unsupported/error branches never stamp a tier.</check>
    <check>The deprecated elicitation_render_form followed by legacy form-plus-answers collection records provenance_status unverified_compatibility, no rendered_tier, and one separate raw counter; it is excluded from verified tier/Other denominators and cannot claim host-native from caller input.</check>
    <check>A keyless, non-mocked live receipt uses a production host's negotiated session.elicit_form to display the canonical demo, returns a server-observed completion, and stamps host_native; the same canonical schema's bare control stamps headless with identical validated output. The separate five-surface projection receipt pre-feeds one canonical answer through each projection's common validator; it does not claim five host interactions. A RICH, PORTABLE, or non-MCP host-native row without its authenticated callback is unverified_transport and projection-only. If negotiated native host is unavailable, Task 11 remains incomplete.</check>
    <check>Answer contents are never recorded in the counters (D5's R8 privacy rule).</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```

## Task 3 — Memory index projection (R3)

```xml
<task id="3" name="lesson-index-projection">
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <objective>
    Generate a promoted-lesson index from the store and project it
    to the configured Cowork project-memory path plus
    .claude/CLAUDE.md, AGENTS.md and .agents/AGENTS.md through the
    existing projector; regenerate a hit-frequency-prioritized bounded
    digest on promote between the separate literal sentinel comments
    &lt;!-- ATTUNE:MEMORY:START --&gt; and
    &lt;!-- ATTUNE:MEMORY:END --&gt;.
  </objective>
  <files-to-create>
    <file path="scripts/project_lesson_index.py">Generate the globally capacity-bounded deterministic digest, target-relative validated links, source/render digests, check/repair modes, and project each configured target.</file>
    <file path="content/collaboration/lesson-index.md">
      Generated; header states it is generated and names the script.
    </file>
    <file path="tests/unit/memory/test_lesson_index_projection.py">Top-K/new-promotion priority, per-target line+byte budgets, stale removal, sentinel ownership, projector-failure semantics, scratch Cowork-path coverage, and proof that recall never reads the generated index.</file>
  </files-to-create>
  <files-to-modify>
    <file path="scripts/project_collaboration_contract.py">
      Generated lesson-index source + tracked target set plus a configured scratch Cowork project-memory target; no bare repository MEMORY.md target, and the promoted store remains the sole authority.
    </file>
    <file path="src/attune/memory/promotion.py">
      promote() triggers regeneration; after the authoritative store commit, a
      regeneration failure raises typed ProjectionSyncError, leaves the
      promotion durable/retryable, and marks the projection stale rather than
      pretending to roll the store back. New records initialize nullable
      first_projected_at; legacy records missing it read as null.
    </file>
    <file path="AGENTS.md">Projector-owned ATTUNE:MEMORY block.</file>
    <file path=".claude/CLAUDE.md">Projector-owned ATTUNE:MEMORY block.</file>
    <file path=".agents/AGENTS.md">Root mirror regenerated after the canonical AGENTS.md projection.</file>
  </files-to-modify>
  <validation>
    <check>A promotion in a scratch store produces the same canonical lesson IDs/order/hooks in the three tracked targets and a configured scratch Cowork MEMORY.md target; each target-relative link resolves to the same path-validated store record, and raw link text need not match. No bare repository MEMORY.md path is assumed.</check>
    <check>Exceeding any target's declared line/byte budget or the residual 20,000-byte eager-load headroom fails the drift guard with the target and count.</check>
    <check>K is the minimum of 25 and every configured target's rendered capacity and must be at least 1. If active promotions have null first_projected_at, the newest occupies slot 1 and hit frequency orders K-1 others; otherwise all K use normal ranking. After every target write, one atomic metadata transaction timestamps every previously-null emitted promotion. Target or metadata failure leaves all null for idempotent retry and removes no stale marker.</check>
    <check>A legacy curated record without first_projected_at reads as null and projects without migration; its first all-target success atomically adds a valid timestamp while preserving all existing and unknown frontmatter fields. New records serialize the nullable field, and recall fixtures remain byte-identical in behavior.</check>
    <check>The provenance header carries canonical source/render digests. Check/project refuses a hand edit between literal sentinels while explicit --repair replaces only that owned block; an outside edit remains legal and is never overwritten.</check>
    <check>A forced target-write or metadata-transaction failure leaves the promoted store record durable and affected first_projected_at fields null, raises ProjectionSyncError, stores LessonProjectionStatus(stale, observed_at, reason, target IDs) in the existing promotion store, and clears it only after an explicit all-target+metadata success.</check>
    <check>Frozen recall-digest fixtures are byte-identical before/after projection and a read spy proves recall never opens the generated index.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```

## Task 5 — Scheduled and monitored delivery, twinned (R5)

```xml
<task id="5" name="scheduled-delivery-twinned">
  <dependencies>
    <dep>1B</dep>
  </dependencies>
  <objective>
    Define sweep, bug-predict, release-prep and the context_fit.jsonl
    watch once, then generate host bindings and cron + attune CLI twins.
    File events only triage/enqueue; debounce, hourly cap, acknowledgment,
    self-origin suppression and the spend gate bound every execution.
  </objective>
  <files-to-create>
    <file path="content/automations/discovery-sweep.yaml">Canonical schedule, invocation, spend cap and acknowledgment policy.</file>
    <file path="content/automations/bug-predict.yaml">Canonical schedule, invocation, spend cap and acknowledgment policy.</file>
    <file path="content/automations/release-prep.yaml">Canonical schedule, invocation, spend cap and acknowledgment policy.</file>
    <file path="content/automations/context-fit-monitor.yaml">Canonical watched path, host-event binding, cron poll interval/cursor, triage/outbox action, debounce, hourly cap and self-origin rule.</file>
    <file path="scripts/project_scheduled_templates.py">Validate masters and deterministically generate every host/cron binding plus its informational-artifact parity record.</file>
    <file path="src/attune/scheduled_delivery.py">Normalize host file events and cursor-bounded cron polls through deterministic triage, debounce, hourly-cap, acknowledgment and self-origin guards.</file>
    <file path="src/attune/security/operator_confirmation.py">AckChallenge, owner-only SQLite transactional store, trusted HostAcknowledgmentAdapter, CSPRNG digest handling, local IPC peer verification, and platform OperatorConfirmationProvider.</file>
    <file path="docs/specs/host-surface-parity/operator-confirmation-receipts.json">Machine support matrix and per-platform live/fail-closed receipt authority.</file>
    <file path="plugin/templates/scheduled/README.md">Generated provenance and installation guidance.</file>
    <file path="plugin/templates/scheduled/discovery-sweep.md">Generated host scheduled-task binding.</file>
    <file path="plugin/templates/scheduled/bug-predict.md">Generated host scheduled-task binding.</file>
    <file path="plugin/templates/scheduled/release-prep.md">Generated host scheduled-task binding.</file>
    <file path="plugin/templates/scheduled/context-fit-monitor.md">Generated host monitor binding.</file>
    <file path="plugin/templates/scheduled/crontab.example">Generated portable bindings.</file>
    <file path="tests/unit/scripts/test_project_scheduled_templates.py">Master/output equality and drift refusal.</file>
    <file path="tests/unit/test_scheduled_delivery.py">Guard and live-file-event receipts.</file>
    <file path="tests/unit/cli_commands/test_automation_commands.py">Interactive single-use acknowledgment, operator/event binding, replay, non-TTY and cron/headless refusal.</file>
    <file path="tests/unit/security/test_operator_confirmation.py">Entropy/digest non-disclosure, half-open TTL, owner peer credentials, OS-auth refusal, PTY-only rejection, restart invalidation and durable replay refusal.</file>
    <file path="tests/integration/security/test_operator_confirmation_boundary.py">Keyless production CLI→owner-only UDS/named-pipe→real peer credential→platform confirmation round trip, with explicit production fail-closed coverage on unsupported platforms.</file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/workflows/base.py">
      Run receipts carry automation_kind: scheduled | monitor | interactive
      separately from delivery_adapter: host | cron | interactive.
    </file>
    <file path="src/attune/cli_minimal.py">Register the interactive automation acknowledge command and reject non-TTY/headless invocation.</file>
    <file path="docs/specs/host-surface-parity/parity-registry.json">Project one informational_artifact subject and closed evidence foreign keys per generated host/cron binding.</file>
    <file path="docs/specs/host-surface-parity/receipts.md">Human content-schema, render, destination and delivery evidence keyed to the generated registry IDs.</file>
    <file path="TASKS.md">Close the fit_source clock item with the verified writer/monitor receipt.</file>
  </files-to-modify>
  <validation>
    <check>Changing one master and regenerating changes its host and cron twins together; interactive is rejected in masters, a hand edit to either generated output fails the drift guard, and max_runs_per_hour is a positive integer.</check>
    <check>Keyless dry-run adapters execute one deterministic stub workflow through the host schedule and cron twin and produce .attune/workflow_runs.jsonl receipts with identical normalized semantic fields/automation_kind and only delivery_adapter differing; adapter cursor/event config may differ under its own binding. No discovery, prediction, or release model call runs.</check>
    <check>The spend gate refuses a scheduled run whose prompt omits a cap.</check>
    <check>A raw file event performs deterministic triage or enqueues an outbox item and cannot launch a token-intensive audit before an authenticated host action or local `attune automation acknowledge &lt;event-receipt-id&gt;`. The portable command uses owner-only local IPC, verifies peer UID/SID, and requires the injectable OS-authenticated OperatorConfirmationProvider; a TTY/PTY alone is insufficient. AckChallenge binds server instance/event/operator to a digest-only 256-bit CSPRNG nonce, issued/expires in a half-open interval no longer than five minutes, and durable consumed state. Raw nonce disclosure to argv/cron/log/store, expiry, mismatch, OS-auth refusal/unavailability, PTY-only automation, cron, and headless attempts fail while leaving the item pending.</check>
    <check>Challenge and pending-event consumption uses owner-only SQLite BEGIN IMMEDIATE plus conditional update. Exactly one of two independent processes launches. Completed replay fails after acknowledgment-server restart; an uncompleted raw challenge is invalid after server restart while the event stays pending and may receive a fresh challenge; client/CLI restart alone has no effect.</check>
    <check>A keyless, non-mocked live receipt on at least one declared supported platform runs the production command through production IPC, matches real peer UID/SID, obtains real platform confirmation, consumes one event, then refuses replay. The trusted host adapter consumes the same challenge and cannot be synthesized from request/model data. operator-confirmation-receipts.json declares every platform and records explicit production provider failure for unsupported ones; Markdown references every ID.</check>
    <check>Events inside 60 seconds debounce, the first event beyond each definition's max_runs_per_hour in the half-open UTC hour emits hourly_cap_exceeded without launch/consumption and remains pending, and a row carrying the monitor's own origin never retriggers it.</check>
    <check>A host file event and a cron poll of the next unseen row normalize to the same guarded monitor receipt; repeated polling at the saved cursor emits nothing.</check>
    <check>Parity gate green: every host template has its twin, and each generated informational_artifact subject has exactly content_schema/render/destination/delivery evidence with no fabricated interaction lifecycle.</check>
    <check>A scratch configured context_fit.jsonl row proves one monitor receipt without claiming a production path; TASKS.md closes only after a separate repository probe names the real writer path and repeats the receipt there.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```

## Task 6 — Roster as data (R7)

```xml
<task id="6" name="roster-as-data">
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <objective>
    Move the roster to validated typed role slots carrying a unique stable
    slot_id, execution mode, trust boundary, required capabilities, receipt obligations and typed
    brief transport (argv placeholder or stdin),
    with exactly one reserved moderator, plan_reviewer and code_proposer role.
    Plan-only legacy views derive from execution mode. Preserve the current three as the embedded
    default; load one immutable ActiveRosterSnapshot at the composition root;
    derive CANONICAL_SEATS, SEAT_RECIPES and PLAN_ONLY_SEATS from it; gate
    workspace checks on its length; and template the preamble. A non-default
    roster can come only from the fixed operator-owned path outside the
    worktree and requires a digest-bound chair-approved override receipt.
  </objective>
  <files-to-create>
    <file path="src/attune/roundtable/roster.py">Typed loader, immutable expiry-aware ActiveRosterSnapshot, unique slot/seat validation, OS-account-rooted trusted paths, reserved-role classifiers, mutually exclusive brief transports, extension validation, and override/activation receipt verification.</file>
    <file path="src/attune/roundtable/roster.default.yaml">Golden three-slot default with explicit moderator/plan_reviewer/code_proposer slot IDs, all typed fields, argv brief transport for Claude/Antigravity and stdin for Codex.</file>
    <file path="tests/unit/roundtable/test_roster.py">Golden behavior, invalid shape/cardinality, trusted override path/ownership/symlink/digest checks, process-wide snapshot behavior, and fourth-slot receipts through an injected fake extension catalog; production remains three-slot before Phase A.</file>
    <file path="src/attune/security/roster_confirmation.py">Task-6-owned OS-authenticated RosterOperatorConfirmationProvider; TTY is presentation only.</file>
    <file path="tests/unit/cli_commands/test_roster_commands.py">Interactive override approval/activation, kernel operator/chair-decision binding, OS confirmation, replay and non-TTY refusal.</file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/roundtable/rotation.py">Derive CANONICAL_SEATS from the validated roster.</file>
    <file path="src/attune/roundtable/routine.py">Derive recipes/plan-only views and template the brief preamble.</file>
    <file path="src/attune/roundtable/workspace.py">Use the validated roster length and receipt obligations.</file>
    <file path="src/attune/roundtable/skeptic.py">Consume role/capability data without literal vendor assumptions.</file>
    <file path="src/attune/roundtable/countersign.py">Consume role/capability data without literal vendor assumptions.</file>
    <file path="src/attune/cli_minimal.py">Register interactive `attune roster approve` and `attune roster activate &lt;slot-id&gt;` for fixed operator-owned paths.</file>
    <file path="pyproject.toml">Ship src/attune/roundtable/roster.default.yaml as package data.</file>
  </files-to-modify>
  <validation>
    <check>Task 0's roster characterization suite passes unchanged against legacy views derived from the same ActiveRosterSnapshot.</check>
    <check>Missing typed fields, duplicate/invalid slot or seat ID, duplicate/missing reserved roles, a moderator lacking receipts, an argv transport without exactly one whole-token {brief} or with stdin delivery, or a stdin transport with any placeholder/not exactly one piped brief fails exactly. An extension may be plan_only and joins PLAN_ONLY_SEATS without satisfying reserved plan_reviewer cardinality.</check>
    <check>The embedded default loads automatically. A non-default roster/receipt loads only below the profile directory derived from effective UID/token SID—poisoned HOME/USERPROFILE/XDG values have no effect—and both files are owner-only/non-symlink. Approval binds digest/path/kernel operator/chair decision, requires the Task-6 OS confirmation provider, treats TTY as presentation, stamps server UTC, rejects caller/future time, and refuses duplicate live issuance.</check>
    <check>The composition root loads ActiveRosterSnapshot once before any seat invocation; all legacy constants/gates read it. The snapshot stores the earliest receipt expiry and refuses a new seat launch at/after valid_until without rereading files; an invocation already started may finish. External file edits appear only in a new process.</check>
    <check>A fourth slot whose role is not extension:&lt;role&gt;, whose named extension is not enabled, whose roster-wide override receipt is absent, or whose separate RosterActivationReceipt is absent fails to load.</check>
    <check>RosterOverrideReceipt carries roster_digest, trusted_path, operator_id, decisions_ref, issued_at and expires_at; its interval is half-open and bounded to (0,30 days], future issue fails, and the chair-decision reference must resolve. The embedded-default digest is rejected as an override receipt.</check>
    <check>`attune roster activate &lt;slot-id&gt;` is the sole activation issuance path, applies the same operator/confirmation/chair/time rules, records operator_id, and refuses an identical live authorization. Its receipt loads only from the owner-only direct-child activations path; explicit slot_id is never derived from extension:&lt;role&gt;, and traversal/symlink/mismatch/future/interval/expiry failures are exact.</check>
    <check>The fourth-slot path uses an injected fake extension catalog in tests; without Phase A production substrate the default catalog is empty and the embedded three-slot roster still loads.</check>
    <check>A built wheel includes roster.default.yaml and loads the embedded roster without a source checkout.</check>
    <check>A chair-approved, digest-bound override swapping the plan_reviewer's vendor changes the recipe and nothing else.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```

## Task 7 — Local reranker extension (R6a) — waits for Phase A substrate; completes A's example (D5, unanimous)

```xml
<task id="7" name="local-rerank-extension">
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <objective>
    STOP PRECONDITION — human/agent-enforced because the current spec
    runner has no external-gate field. Before any file mutation, verify
    the current authoritative base contains a committed Phase A substrate on
    this same branch lineage (not an uncommitted sibling checkout): the public
    attune.extensions API and entry-point
    group, live `attune extension enable` CLI, public memory-backend
    capability contract, and attune.testing memory-backend contract kit.
    If any probe is false or unverifiable, report BLOCKED and leave this
    task incomplete. Once verified, ship the Phase A example
    extension as an Ollama-backed reranker
    under the memory-backend contract's optional rerank capability,
    with fail-open fallback to store ranking.
  </objective>
  <files-to-create>
    <file path="extensions/attune-ext-local-rerank/pyproject.toml">Standalone package metadata and attune.extensions entry point.</file>
    <file path="extensions/attune-ext-local-rerank/src/attune_ext_local_rerank/__init__.py">Public extension export.</file>
    <file path="extensions/attune-ext-local-rerank/src/attune_ext_local_rerank/extension.py">Extension manifest, memory-backend capability registration and machine-readable surface capability descriptor.</file>
    <file path="extensions/attune-ext-local-rerank/src/attune_ext_local_rerank/backend.py">Ollama rerank implementation with store-order fail-open behavior.</file>
    <file path="extensions/attune-ext-local-rerank/tests/test_contract.py">Standalone attune.testing contract-kit receipt.</file>
    <file path="tests/unit/extensions/test_local_rerank.py">In-tree enablement, degradation and recall-eval integration receipts.</file>
    <file path="docs/specs/host-surface-parity/local-rerank-receipts.md">Task-local with/without-reranker P@3, fail-open and descriptor receipts; independent of Task 1B.</file>
  </files-to-create>
  <files-to-modify>
    <file path="pyproject.toml">Add the local-rerank package as a uv workspace member/test dependency so the in-tree suite imports the real extension.</file>
    <file path="uv.lock">Lock the workspace package and its test environment.</file>
  </files-to-modify>
  <validation>
    <check>A pre-implementation receipt records the committed base SHA and exact probes proving the public Extension manifest and memory-backend contract import, the attune.extensions group exists, `attune extension enable --help` exits 0, and the attune.testing memory-backend contract kit passes against a bundled backend before any changed file; absence or an uncommitted-only substrate fails the task. This same-repository Phase A completion intentionally differs from external released-artifact gates.</check>
    <check>attune extension enable local-rerank loads and constructs the backend in-process (D1 receipt 2 wording).</check>
    <check>Connection/DNS timeout, HTTP error, protocol/version mismatch, malformed response, duplicate/unknown/missing IDs and partial/non-permutation ranking each emit a closed health reason and atomically return the complete original store order; no partial ranking leaks.</check>
    <check>memory-recall-eval reports raw hits/queries, successful-rerank count and P@3 with/without on the frozen benchmark. A healthy reranker must actually run and P@3_reranked must be at least P@3_store, so fail-open cannot vacuously tie.</check>
    <check>The package contract proves the extension entry-point ID and published descriptor ID are exactly equal and schema-valid without a central registration edit.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```

## Task 9 — Asks-per-outcome (R8)

```xml
<task id="9" name="asks-per-outcome">
  <dependencies>
    <dep>0</dep>
  </dependencies>
  <objective>
    Store raw structured-ask, terminal work-unit-outcome, session and
    fallback counts without answer contents. A work unit is one declared
    session/workflow objective and emits at most one terminal outcome, not one
    per ask. Keep asks-per-session secondary; let friction_gate derive
    asks-per-terminal-outcome, zero-outcome rate and fallback frequency over a
    trailing 30-day project/workflow aggregate only above the ten-outcome floor.
  </objective>
  <files-to-modify>
    <file path="src/attune/gates/session_ledger.py">Raw ask, terminal-outcome, zero-outcome-session and fallback counters; no answers or stored ratio.</file>
    <file path="plugin/hooks/friction_gate.py">Floor-gated derived display with asks/session, zero-outcome rate and fallback frequency.</file>
    <file path="tests/unit/gates/test_session_ledger.py">Terminal partitions, privacy, raw-count and floor-boundary receipts.</file>
  </files-to-modify>
  <validation>
    <check>Every ask/outcome carries session_id and work_unit_id. Accepted, cancelled, aborted (including observed abandonment), timed_out and blocked each terminate that work unit at most once regardless of ask count; blocked need not terminate the whole session. Only session close increments zero_terminal_outcome_sessions, and only when no work unit terminated.</check>
    <check>For one project/workflow key in the half-open trailing 30-day JSONL aggregate, nine terminal work units render insufficient_evidence and ten render the ratio from asks attributed to those terminal units without persistence. Asks on open/zero-outcome units are reported as unattributed_open_asks; out-of-window/other-key rows do not leak.</check>
    <check>Asks-per-session remains visible beside zero-outcome rate and fallback frequency; a headless zero-ask/zero-outcome run is recorded without division or a false 0.0 claim.</check>
    <check>No serialized ledger row contains form answers, free text, or validated payload values.</check>
    <check>No new file or store; fields live in the existing ledger JSONL.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```

## Task 8 — Local role workflows via placement label (R6b) — gated on shipped Phase B

*(Amended 2026-09-02 per the D2 ruling: routing label, not enum
member. The in-tree tier enums and canonical attune-rag model-resolution
source do not change; the original enum-edit mechanics are superseded.
Amended 2026-09-03: the label field and its resolution semantics
land earlier as Task 12 under D8's 16.3 go; this task consumes the
label, it no longer introduces it.)*

```xml
<task id="8" name="local-role-workflows">
  <dependencies>
    <dep>6</dep>
    <dep>7</dep>
    <dep>12</dep>
  </dependencies>
  <objective>
    STOP PRECONDITION — human/agent-enforced because the current spec
    runner has no external-gate field. Before any file mutation, verify
    the released artifact has shipped the release-16-manifest Phase B
    workflow contract: public WorkflowRequest, WorkflowContext, and
    WorkflowResult types plus the built-in-public-path ratchet receipt.
    If any probe is false or unverifiable, report BLOCKED and leave this
    task incomplete. Once verified, consume Task 12's placement routing
    label (`placement: local`) and ship workflow extensions
    for classification, triage pre-sort, low-stakes
    skeptic/countersign and fact-check probes, each advisory-labeled
    with a PREMIUM fallback above a chair-set stakes threshold
    (fact-check probes additionally hosted-model countersigned per
    D5's H4 ruling). Render placement separately from quality tier on
    the existing ops Workflows surface, so "local" is observable without
    becoming a fourth tier.
  </objective>
  <files-to-modify>
    <file path="src/attune/config/agent_config.py">
      Consumes the placement label landed by Task 12; local roles
      route to the enabled workflow extension. Tier enum untouched.
    </file>
    <file path="src/attune/workflows/__init__.py">Expose each workflow role's declared placement preference separately from tier_map.</file>
    <file path="src/attune/ops/data.py">Preserve declared placement separately from tier in the Workflows view model; never add local to TIER_LABEL.</file>
    <file path="src/attune/ops/routes/dashboard.py">Pass placement labels and tooltips to the existing Workflows surface.</file>
    <file path="src/attune/ops/templates/workflows.html">Render a distinct Local preferred chip; its label is declared placement, never actual execution or a quality tier.</file>
    <file path="tests/unit/ops/test_workflows_route_concerns.py">Pin separate declared-placement and tier chips, accessible labels, unchanged no-placement rows, and no local TIER_LABEL member.</file>
    <file path="src/attune/cost_tracker.py">Record actual placement orthogonally to model tier, local_no_api_charge with zero API-billed cost for local execution, actual hosted fallback pricing, and a separate BY PLACEMENT aggregate.</file>
    <file path="tests/unit/test_cost_tracker.py">Pin cheap+local as one cheap quality-tier event, one local placement event and zero API-billed cost—never a local tier or hosted-price estimate.</file>
    <file path="pyproject.toml">Add the local-roles package as a uv workspace member/test dependency so the in-tree suite imports the released-contract consumer.</file>
    <file path="uv.lock">Lock the workspace package and its test environment.</file>
  </files-to-modify>
  <files-to-create>
    <file path="extensions/attune-ext-local-roles/pyproject.toml">Standalone package metadata and attune.extensions entry point.</file>
    <file path="extensions/attune-ext-local-roles/src/attune_ext_local_roles/__init__.py">Public extension export.</file>
    <file path="extensions/attune-ext-local-roles/src/attune_ext_local_roles/extension.py">Workflow capability manifest, role registrations and machine-readable surface capability descriptor.</file>
    <file path="extensions/attune-ext-local-roles/src/attune_ext_local_roles/workflows.py">Classification, triage, skeptic/countersign and fact-check adapters.</file>
    <file path="extensions/attune-ext-local-roles/tests/test_contract.py">Standalone workflow contract-kit and advisory-label receipts.</file>
    <file path="tests/unit/extensions/test_local_roles.py">Placement, stakes fallback, countersign and ledger integration receipts.</file>
  </files-to-create>
  <validation>
    <check>A pre-implementation receipt records the exact released-artifact probes/results proving the three public workflow types import and the Phase-B built-in-public-path ratchet receipt exists before any changed file; absence fails the task.</check>
    <check>Task 12's focused placement test stays green with all in-tree enums unchanged and no LOCAL member anywhere.</check>
    <check>A role routed "CHEAP, prefer local" runs on the local extension when present and falls back to its existing hosted tier when absent; the ledger shows local_unavailable, actual placement, and actual pricing source.</check>
    <check>Only placement: local records enter this stakes rule. A low-stakes skeptic tries local and, if unavailable, falls back to its originally declared hosted tier; above threshold it routes directly to the existing hosted PREMIUM enum member with stakes_fallback even when local is available. A non-local record retains existing routing and no enum changes.</check>
    <check>The package contract proves the extension entry-point ID and published descriptor ID are exactly equal and schema-valid without a central registration edit.</check>
    <check>The ops Workflows surface renders Local preferred as a declared-placement chip beside the unchanged quality-tier chip; its aria-label never calls local a tier or claims where execution ran, no-placement rows retain the old render, and local is absent from TIER_LABEL.</check>
    <check>An actual local execution remains in by_tier.cheap, separately increments by_placement.local, and records pricing_source local_no_api_charge with API-billed cost 0; hosted fallbacks use the actual hosted model price. The report renders BY MODEL TIER and BY PLACEMENT, with no local tier bucket.</check>
    <check>No change to ModelProvider.</check>
    <check>Changed code carries at least 90% coverage; no API-billed call occurs.</check>
  </validation>
</task>
```
