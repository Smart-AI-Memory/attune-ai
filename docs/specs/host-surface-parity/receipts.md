# Host surface parity — evidence ledger

**Status:** active — Task 1B increment 2; production parity incomplete.

This ledger explains the machine receipt IDs in `parity-registry.json`.
It is not parsed as authority by the gate. The registry names 35 discovered
producer roots, preserving their helper anchors, and two additional declared
transport owners. Its 158 derived obligations comprise three executed package
receipts and 155 explicitly owned local runtime gaps for increment 3.

Chair ruling, 2026-09-06: keep increment 2 focused on registry and gates;
record every missing runtime receipt for increment 3. Passing inventory
validation does not imply complete parity. Pending obligations and experiments
cannot make a route admissible. The runtime policy must use the evidence
precondition when it is implemented in increment 3.

Parity assertions cover only the subjects the registry names. Static discovery
bounds that scope; it cannot prove every indirect producer. The `targets` and
cold/warm lists on unreceipted subjects are obligations for implementation,
not proof that those fallbacks currently exist. No route is activated here.

## Reviewed producer-baseline binding (D13)

D13 was ruled by the chair on 2026-09-06: the registry records the fixture's
canonical path, schema version and SHA-256 of canonical JSON. The fixture
remains the discovery source. `validate_baseline_pin` rejects a changed path,
unsupported/mismatched schema or changed content before an inventory report
is issued. Its mismatch names the expected and actual digests and the
regenerate / re-derive / review command. Experiment validation consumes the
resolved, pin-validated fixture's shipped roots. The report's registry digest
therefore binds transitively to that fixture content.

The rebase includes the SessionStart memory-backend notice (#2446) and the
PreToolUse Bash worktree-add guard (#2447), each with its reaching `main`
helper preserved. Their qualified delivery routes add six pending evidence
keys; they are inventory entries, not new executed runtime receipts.
`test_new_hook_subjects_have_qualified_delivery_obligations` rejects either
missing subject. D13 mutations reject changed pin shape/path/schema/content,
stale reports after a pin refresh, and shipped experiment roots; a refreshed
pin still cannot hide a newly detected hook signature under an existing root.

## Package renderer receipts

| Machine receipt ID | Executed evidence | Limit |
| --- | --- | --- |
| `renderer.standalone-form.surface.RICH` | Released canonical form through RICH/PORTABLE/HEADLESS; common form collector; bound projection outputs | Serializer/common-collector evidence, not host paint or transport lifecycle |
| `renderer.standalone-form.host-native.form.askuserquestion` | Canonical specialized batches provide answer IDs/options; common collector consuming emitted PORTABLE reply IDs and HEADLESS schema controls | `compatibility_projection` only; not an active host route |
| `renderer.generic-workspace.surface.RICH` | Released canonical workspace through all three projections; response built from HEADLESS contract and passed to `collect_workspace_action` | Package boundary only; stateful attune-ai consumer round trip remains open |

Each row binds implementation, fixture, owning-target slice, normalization and
result digests. The fixtures execute from the installed 0.14.0 wheel. A later
artifact is not accepted merely because its version is compatible. The full
installed renderer description must still match and the evidence must replay.
Changing a declared receipt mode also invalidates the row.

Only the package's declared widget telemetry token is normalized in projection
text. The controls consume the emitted PORTABLE reply-contract field IDs and validate
the collected answers against the emitted HEADLESS schema. They establish
reply-contract compatibility for this fixture, not complete Markdown/HTML
semantic equivalence or native display. The form observation includes validated responses and template identity;
there is no independent cross-surface FormResponse comparison.
Collector-generated `timestamp` and `response_id` are the two omitted telemetry
paths. Workspace HEADLESS and PORTABLE replies are independently collected; action
nonce, revision, workspace/view/action IDs, contract hash, confirmation and
responses remain in their comparison. Local subject
normalization paths are empty until production evidence can justify them.

The attune-forms closure helper supplies package implementation digests.
Independently proving its behavior-affecting dynamic dependency closure and
route-active profile/adapter bindings remains part of Task 1B check 3; these
receipts do not claim that external package audit is complete.

## Outstanding runtime evidence

`pending_obligations` names every missing parity, lifecycle or qualified
informational-delivery key, its owner, reason and next increment. This list is
not an experiment or exemption. Deleting an entry without supplying evidence
fails inventory validation. Package-renderer obligations cannot be moved into
this list. The strict receipt validator still rejects this incomplete
inventory, and every declared live route reports missing evidence.

The two fixed compatibility endpoints additionally await their exact production
shape/provenance receipts (check 16): `form_to_ask_payload` and deprecated
`_handle_elicitation_render_form`. Their fixed contracts and route exclusion
are recorded now. They do not invent lifecycle states to fill the gap.

The chart widget and workflow report are classified as informational artifacts
because their returned HTML presents content rather than collecting a
`FormResponse`. They retain their enhanced-target obligations and missing
PORTABLE/HEADLESS implementation evidence; classification cannot hide them.
Resource registration and tool-list metadata are likewise informational
artifacts, not owners of interaction state transitions. Review these explicit
classifications with the producer anchors when adding runtime fixtures.

## R4b — Codex native-host observation

Source: [held observation](../../probes/host-surface-parity/codex-native-receipt-2026-09-06.md).
This is human/live-host evidence, **not** a replayable parity, lifecycle or
delivery receipt. It cannot activate a host profile in the machine registry.

- Forms version loaded by the Codex-launched server: **0.13.0**, per the
  original process-argv/dist-info probe (not the 0.14.0 used by this PR's tests).
- Form ID: `e1cfd8b31260`; title: `Codex receipt 4b`.
- Instance ID: `fb05442cfee34605b4bf2bbc34a7976c`.
- Collect receipt: `resp-20260905-214151-fe89fe82`; the Codex MCP app returned
  successful validated responses with `paint = Yes, rendered as a card`.
- Chair paint observation: **yes**. There is no machine paint trace.

| UTC timestamp, 2026-09-06 | Event | Instance ID |
| --- | --- | --- |
| 01:41:28.127872Z | `form_rendered` | `fb05442cfee34605b4bf2bbc34a7976c` |
| 01:41:51.111595Z | `form_submitted` | `fb05442cfee34605b4bf2bbc34a7976c` |

The two rows were independently reread from the local telemetry JSONL during
increment 2. The matching instance ID supports a widget post-back. Attribution
to the Codex-launched server remains **inferred from timing**, because the
telemetry has no process ID. The original local precompute `form_build` at
01:28:46Z is excluded. Observed render-to-submit time is approximately 23 seconds.
No Markdown fallback was observed or needed in this run. The observation used
the chair's Codex subscription and made no API-billed call. Task 4b's dependency
on completed Task 1B remains open; folding this observation does not close it.

## Task 1B validation coverage

Numbers below are the `<check>` entries in Task 1B, in source order. All tests
are in `tests/unit/gates/test_surface_parity.py` unless another path is named.
“Partial” means only the named property is tested, not the entire check.

| Checks | Status in increment 2 | Failure-sensitive tests / remaining work |
| --- | --- | --- |
| 1 | Existing prerequisite verified | Before edits, locked 0.14.0 had no editable `direct_url`, all seven canonical projections executed. D12 corrects the task's 0.13.0 wording. `test_installed_renderer_evidence_replays_deterministically` reruns the projections. |
| 2 | External AF-1 check remains open here | No claim to rerun the package's annotation/allowlist mutation suite. |
| 3 | Partial | `test_live_registry_matches_installed_renderer_records`, `test_changed_evidence_invalidates_existing_receipt`, `test_compatibility_answer_comes_from_emitted_questions`, `test_route_active_target_cannot_reuse_compatibility_evidence`; full projection semantic equivalence, dynamic closure/profile audit and advisory workflow remain open. |
| 4 | Open, increment 3 | Package HEADLESS collection is executed; the stateful attune-ai consumer round trip is not claimed. |
| 5 | Partial | `test_additional_host_native_target_creates_independent_obligation`, `test_changed_evidence_invalidates_existing_receipt`; local target execution remains pending. |
| 6 | Structural portion enforced | `test_form_transport_associations_fail_closed`, `test_host_profile_ref_requires_matching_profile_and_lifecycle`, `test_receipts_cannot_borrow_or_invent_evidence`, `test_route_evidence_requires_delegated_timeout_even_when_form_accept_passes`; live lifecycle receipts remain pending. |
| 7–12 | Discovery enforced (increment 1 + registry link) | Baseline tests and existing direct/alias/helper, manifest, wrong-event, same-file, new-command and attune_redis mutations; `test_root_subjects_preserve_shared_helpers_without_duplicate_interactions`, `test_live_inventory_mutations_fail_instead_of_becoming_exemptions`. |
| 13 | Open, increment 3 | Trusted accessibility constraints and runtime precedence. |
| 14 | Partial | Declared default orders checked; runtime selection/noninteractive branch remains open. |
| 15 | Open, increment 3 | Authenticated capability sources, negative precedence and cache rules. |
| 16 | Partial | `test_compatibility_endpoints_remain_exact_fixed_shape_anchors`; unified handler, exact production endpoint receipts (two explicit pending keys) and closed schema remain open. |
| 17–25 | Open, increment 3 | Runtime admissibility, context table, session/store lifecycle, submission/challenge semantics, transport provenance and attempt bounds. |
| 26 | Structural portion enforced | `test_deleting_one_receipt_fails_its_exact_obligation`, `test_changed_evidence_invalidates_existing_receipt`, `test_live_inventory_is_accounted_but_does_not_claim_complete_parity`; 155 real local receipts still absent. |
| 27 | Partial | `test_deleting_twin_names_exact_owner_and_shortfall`, installed renderer replay; local interactive/informational execution remains pending. |
| 28 | Partial | Active/expired/future/duration/history/cap/conflict/exception mutations; filesystem resolution and binding experimental artifacts/decision references to current execution remain open before any real experiment is activated. The live inventory rejects all experiment activation until that verification exists; only synthetic fixtures exercise the interval rules. |
| 29 | Enforced for declared local twins | `test_live_inventory_mutations_fail_instead_of_becoming_exemptions[delete_portable-chart-widget.*missing PORTABLE]` removes a real local subject's PORTABLE declaration; execution of that twin remains open. |
| 30 | Projected | `tests/unit/scripts/test_project_collaboration_contract.py` plus projector `--check`; generated blocks must equal the master. |
| 31 | Measured before push | Focused coverage command on both changed modules; final result recorded in PR. |

Full Task 1B is not complete. Increment 3 owns runtime and local evidence;
increment 4 owns the advisory cross-repository compatibility workflow.

## Increment-2 review corrections

Claude's read-only evidence-chain review identified four blocking gaps. Receipt
IDs now bind their obligation keys, discovered classifications and minimum target
footprints cannot shrink through registry edits, every route derives a separate
production-projection obligation, and package controls consume the emitted reply
contract instead of comparing identical collector calls. Tests mutate each property.
The 155 pending keys include 27 route projections and two compatibility endpoints.
A hook containing a registered renderer call cannot hide behind delivery
classification. Hook route IDs also bind event/matcher/signature/sink/destination, so swapping
registrations cannot reuse a future receipt.

Remaining limitations: non-hook delivery vocabulary and compatibility metadata
are declarations pending production adapters; their exact runtime schemas remain
open. Pending rows have an increment owner but no elapsed-time ratchet; they can
only be removed by changing the detected obligation footprint or adding verified
evidence, and cannot waive a route. Live experiments are explicitly refused,
including self-asserted decision references. Full visual/semantic equivalence of
package projections is not established by the reply-contract fixture.


## Claude review of 7c21c2863 — chair accepted 2026-09-06

The [published review](https://github.com/Smart-AI-Memory/attune-ai/pull/2444#issuecomment-5559744953)
covered all 15 files at `7c21c2863` with no omissions (Board run ending
`20260906-1109`). The earlier 7-file and 4-file Max-session reviews are
separate runs, not partitions of that review. The later `bf530993b` review
covered 16 files after the bug-log addition. Approval of the published review authorizes
corrections; it does not establish runtime parity or approve a merge.

| Finding | Disposition and evidence |
| --- | --- |
| F1 | Fixed: form controls use the owning renderer record and its fixture, never registry position zero. Reordering the installed registry preserves every receipt. |
| F2 | Fixed: every delivery route ID hashes event, matcher, signature, sink and destination. Mutating any field rejects the old ID; re-deriving it replaces the four artifact obligations. Existing pending keys were migrated, not marked verified. |
| F3 | Trust-boundary clarification: `InventoryReport` is an in-process value object supplied by a trusted caller, not an authenticated token. The helper now documents that it must come from `validate_inventory` over trusted executed evidence. A Python caller can still fabricate one; increment 3 must not accept deserialized reports as authorization. No runtime routing is implemented here. |
| F4 | Deferred to the experiment-activation increment: current rolling-cap checks guard windows intersecting the active experiment, not an audit of every historical window. Global history validation and retention of past bounded exceptions need a joint design. Live activation remains unconditionally refused by `validate_inventory`; this finding is not reported as fixed. |
| F5 | Fixed: artifact/root collisions union provenance instead of overwriting helpers. A collision mutation asserts all prior anchors remain. |
| F6 | Fixed: both provenance fields must be nonempty strings as well as equal to executed evidence. Missing, blank and wrong-typed pairs fail. Synthetic tests now declare their synthetic provenance explicitly. |
| F7 | Fixed for the reported collection boundary: inventory, obligation derivation and experiment validation reject absent/wrong-typed collections with the owning key. This is not a claim of exhaustive nested JSON schema validation. |
| F8 | Fixed: workspace subjects own their lifecycle and reject delegated transport references; unvalidated references cannot reach the route helper. |
| F9 | Fixed: the HEADLESS-only handler exemption matches the exact repository anchor. Relocation loses the exemption and fails the footprint test. |
| F10 | Fixed: malformed specialized question shapes and PORTABLE/HEADLESS reply contracts raise keyed `SurfaceRegistryError`; JSON/schema exceptions retain their causes. No broad exception swallowing was added. |
| F11 | Retained fail-closed: unknown historical obligation keys remain rejected so renames cannot erase waiver history. A legitimate rename needs an explicitly reviewed migration design before experiment activation; no automatic alias is introduced in this increment. |
| F12 | Retained dependency: `surface_evidence` is a shipped, importable evidence-replay module and directly imports `jsonschema`. Moving the dependency alone to a test extra would break that public module in a normal install. Separating the module into optional tooling would be a separate packaging change. |
| F13 | Fixed: the contract gate normalizes whitespace before asserting the same required sentences, so cosmetic line wrapping is harmless. |

F4 and F11 remain open experiment-activation work; F3 remains a documented
trusted-caller limitation for the future runtime boundary. The 155 pending
runtime obligations remain inadmissible. A registry digest and passing inventory
are not host paint, transport lifecycle, or production route evidence.


## Claude re-review of bf530993b — dispositions (2026-09-06)

Triage is against `1efa084062569de83e5e2a1d5b66458a96249dc8`, whose only
change after the reviewed head is the shared CONTRIBUTING CI fix. Review
source: `~/.attune/reviews/pr2444-bf530993b-result.json`, Board run ending
`20260906-1424`, 16 sent / 0 omitted. No new reviewer or paid API run was
launched. These dispositions are code/probe findings, not a clean-review receipt.

| Finding | Disposition and evidence |
| --- | --- |
| R1 | Confirmed overclaim; removed the redundant second form collection and unreachable inequality branch. `_validate_projected_answers` explicitly validates emitted PORTABLE IDs and HEADLESS schema compatibility. Existing mutations reject missing/changed IDs and invalid schemas; RICH output is digest-bound, not independently decoded into an answer. Full visual/semantic parity remains unproved. |
| R2 | Fixed: mixed hook-delivery and interactive package envelopes fail closed even without a registered renderer call. Both form and workspace envelope mutations exercise the guard. Supporting a mixed boundary requires a reviewed representation, not a precedence exemption. |
| R3 | Partly confirmed and fixed: the old package helper internally used HEADLESS, so the claim that it used no HEADLESS contract was too broad. It did bypass the record fixture and the emitted target output. Replay now uses the record fixture, builds a reply from the actual HEADLESS output, independently fills the PORTABLE reply, collects both, and compares their validated action/binding/response fields. Revision, field-ID and malformed-contract mutations fail; a renamed owning fixture succeeds. No RICH host paint claim. |
| R4 | Fixed conservatively: every route requires all package-renderer obligations, matching the staged inventory's existing package-evidence requirement. A waived renderer blocks RICH, PORTABLE and HEADLESS routes. Subject-to-renderer target bindings remain runtime design work; this stricter precondition does not invent or activate them. |
| R5 | Fixed: `validate_receipts` requires caller obligations to equal freshly derived registry obligations before validation. Narrowed maps and changed foreign keys fail; public call sites were searched and retain the current signature. |
| R6 | Fixed: path-aware containment rejects an exact shipped root as well as descendants. Tests include an exact file root and a trailing-slash spelling; existing parent-containment and unsafe-root tests remain. |
| R7 | Fixed at the reported row boundaries: subject, pending and receipt non-object rows raise keyed errors; a missing producer root names the subject. The receipt case was an adjacent instance of the same defect. Exhaustive nested schema validation is still not claimed. |
| R8 | Fixed: all installed targets are checked for route-active status before any projection runs. RICH, PORTABLE and HEADLESS mutations assert refusal before execution; the existing host-native regression remains. |
| R9 | Retained deliberately: whole-module source hashing invalidates receipts on cosmetic edits. This is exact-runner provenance, not semantic change detection. Selective source/AST hashing could miss behavior-affecting dependencies; conservative regeneration is preferable for this small fixture. No claim that comments preserve receipt identity. |
| R10 | Fixed by removing unused duplicate metadata: compatibility endpoints derive from subjects, signature classification lives in `surface_inventory`, and future capability/constraint/context schemas belong to the design and pending runtime work. The machine registry no longer carries these five unvalidated top-level fields. This does not implement increment 3. |
| R11 | Rejected as a review-identity conflation; clarified the paragraph. `git diff e884f599d 7c21c2863 --name-only` yields 15 files and the original complete manifest lists 15 with zero omitted. The 7/4-file rows describe earlier reviews. `git diff e884f599d bf530993b --name-only` yields 16 after the bug log was added; its separate row already says 16. |
| R12 | Historical receipts retained and labeled: the 141-test/25,638-test row describes its earlier review follow-up, not the branch tip. Current validation belongs to the latest handoff section and this triage receipt; historical counts are not rewritten as new executions. |

Runtime schemas remain pending; removed placeholder metadata must not be
interpreted as schema implementation. The scanner owns `ENVELOPE_SIGNATURES`
and `PACKAGE_SIGNATURES`; compatibility subjects own their fixed contracts.
The full runner source remains part of `fixture_digest`; regenerate only by
executing `replay_renderer_evidence` after the final formatting pass.


Triage validation: 656 gates/quality tests passed at 99.55% combined coverage;
40/41 changed executable lines covered. Whole configured tree: 25,903 passed,
241 skipped, 3 xfailed. Eighteen targeted defect probes fail against the
original `1efa08406` source and pass in the corrected gate run. Pinned hooks
pass. Commands, logs and environment limits are in the latest handoff section.
