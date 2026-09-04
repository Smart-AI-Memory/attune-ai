# Host Surface Parity — attune-forms Handoff

**Status:** external prerequisites; execute in the `attune-forms`
repository, never through the attune-ai task runner.

This document replaces the old `attune-forms:...` pseudo-paths. The
attune-ai runner treats every parsed task path as local, so cross-package
implementation must use a separate clean `attune-forms` worktree and
branch. Verify the package's current default branch and version before
editing; a stale saved checkout is not authority. Publishing either
package remains a separate chair-authorized release action.

## AF-1 — Registry and production HEADLESS projection (0.13.0)

**Depends on:** host-surface-parity Task 0 characterization.

In a clean `attune-forms` worktree:

- Create `src/attune_forms/headless.py` with the production
  `workspace_to_headless` serializer. Its deterministic JSON-safe output
  preserves the complete view, form, actions, binding, and response
  contract; an action-ID-only or empty mapping is not a valid twin.
- Create `src/attune_forms/renderer_registry.py` with a public, iterable,
  non-empty registry of stable standalone-form and generic-workspace
  projection records plus the finite public `projection_output_types`
  vocabulary consumed by the no-escape sweep. Optional host-native targets are
  keyed by stable target ID and discriminated by status: a route-active target
  names its installed host-profile ID, while a compatibility-only target names
  a package-shipped immutable compatibility-contract ID and exact shape digest
  and cannot require a live adapter. Each also declares `evidence_mode`:
  `route_roundtrip` for route-active or `compatibility_projection` for
  compatibility-only; status and mode are part of the owning-record digest.
  There is at most one route-active target
  per family and profile.
- Create `src/attune_forms/canonical_fixtures.py` with deterministic public
  fixture factories/payloads and normalization descriptors referenced by each
  registry record. They ship in the wheel; test modules are not the fixture
  distribution boundary.
- Create `tests/test_renderer_registry.py` for registry uniqueness,
  callable targets, canonical fixtures, and the no-escape sweep.
- Modify `src/attune_forms/__init__.py` to export the registry and every
  registry target, including `workspace_to_headless`.
- Advance the package version/floor from the verified 0.12.x baseline to
  0.13.0.

Acceptance receipts:

- The no-escape candidate set is the union of: semantically typed production
  callables accepting `Form` or `WorkspaceView` and returning a declared
  projection-output type from the registry's closed vocabulary when
  public/exported/registry-referenced or called
  across a production module/package boundary; every registry target; and
  every `form_to_*` / `workspace_to_*` callable used outside its defining
  module as a naming guardrail. Private helpers used only inside one registered
  renderer remain implementation, not extra targets. Unresolved relevant annotations fail
  closed. `Optional[T]`/`T | None` strips only `None` and must leave one
  declared projection type; other unions fail. Any explicit non-renderer
  allowlist is small, fully qualified, rationale-bearing, and mutation-tested
  for add/remove/rationale edits and attempted renderer hiding. Every candidate appears exactly
  once; an unregistered or unexported symbol fails with its exact name.
- Standalone form records inventory the already-shipped specialized
  `form_to_askuserquestion` renderer beside widget, Markdown, and
  `form_to_elicitation_schema`. The specialized target is compatibility-only
  for the fixed-shape legacy tool and binds that fixed contract ID/shape digest;
  its evidence mode is compatibility_projection and it has no installed
  profile-facet or live-adapter precondition. AF-1 exposes no route-active host-native
  target. The last is the single HEADLESS data
  projection used both by bare programmatic HEADLESS execution and, through a
  separate negotiated transport, native MCP elicitation. AF-1 does not create
  a new AskUserQuestion renderer. Workspace records cover widget HTML,
  Markdown, and production HEADLESS projection.
- Canonical package-local fixtures prove recursive schema/value parity after
  only closed, rationale-bearing nonsemantic volatile-path normalization;
  revision, event sequence, contract hash, and subject/schema/action IDs may
  not be normalized away. A clean-wheel probe
  imports and executes every registry-referenced fixture.
- The specialized compatibility fixture executes its canonical form through
  `form_to_askuserquestion`, PORTABLE, and HEADLESS; derives a canonical raw
  answer only from the specialized batches' emitted question IDs/options; and
  passes it through common `collect_form_response` to obtain the same normalized
  `FormResponse` as both controls. This evidence claims projection/validation
  only, never routing, presentation, lifecycle, or tier. Contract ID/shape,
  emitted-question/option, and status/evidence-mode mutations fail the exact
  obligation.
- Each target implementation digest is the deterministic cycle-safe transitive
  closure of statically resolvable package-local functions, classes, constants,
  defaults, and decorators. An unresolved behavior-affecting dynamic dependency
  requires an explicit package-relative artifact reference or fails closed; a
  helper-only change invalidates its target while an unrelated symbol does not.
- Removing a real PORTABLE or HEADLESS target fails with the record and
  target named. Changed code carries at least 90% coverage.

After a separately authorized 0.13.0 release, attune-ai Task 1B locks the
released artifact and sends the serialized response through its stateful
command-workspace adapter, which ultimately invokes this package's real
`collect_workspace_action` at the consuming boundary. The public MCP
`fix_workspace_collect_action` handler is separately receipted by attune-ai R4
and delegates through that shared host.

## AF-2 — Host-profile structured-question renderer (0.14.0)

**Depends on:** released AF-1 and completed attune-ai Task 10 capability
descriptor/conformance foundation.

In a fresh clean `attune-forms` worktree:

- Create `src/attune_forms/host_question.py` with public pure pre-render
  `host_question_admissibility(form, profile)` and
  `form_to_host_question(form, profile)`. The profile—not a vendor name
  or universal constant—declares question/option limits, multi-select,
  free-text Other with its exact reserved label/token, cancellation,
  question/option text normalization, validation-error behavior, finite
  validation-attempt cap and response deadline, raw multi-select response encoding,
  and response correlation by question ID, exact emitted text, or ordinal. The
  first AskUserQuestion profile has a 12-character header limit and uses
  emitted-text question keys plus the verified canonical codec
  `{kind: comma_delimited, delimiter: ", ", atom: emitted_label,
  escaping: json_quote_when_delimiter_or_quote, canonical_reencode: required}`.
  Labels containing the delimiter or a quote are JSON-string encoded; other
  labels are bare. Freeform is the host's separate global `response`, not an
  option token. The routed
  path uses admissibility metadata to select PORTABLE before renderer
  invocation. A defensive direct renderer call outside the profile returns
  `None`; an unexpected `None` or exception after routed selection is terminal
  `render_failed` in the later consumer, never a signal to invoke a fallback
  renderer. AF-2 only declares feedback support, cap, and deadline as immutable
  profile metadata and returns the pure frozen projection/bindings. It does not
  implement the host presentation loop, feedback envelope, challenge, receipt,
  deadline enforcement, or attempt counters; attune-ai Task 2 owns those seams.
  `HostQuestionBatch` is the frozen return type: it contains the host-visible
  payload plus immutable `answer_bindings: tuple[QuestionAnswerBinding, ...]`.
  Each binding carries stable question ID, emitted ordinal, exact emitted
  question text, and that question's ordered
  `(emitted_label, response_atom, option_id)` triples. For this profile the
  response atom equals the exact emitted label; a future token host must bind a
  distinct declared atom rather than guess. The package keeps no hidden
  state: it returns the composite to the attune-ai server adapter, which retains
  bindings plus profile/correlation metadata inside the same-call
  HostQuestionAdapter boundary and its non-serializable PresentationChallenge.
  Only the adapter sends the payload across the host boundary; after its trusted
  completion, attune-ai atomically creates/advances the interaction receipt.
- Create `tests/test_host_question.py` covering single- and multi-question
  profiles, more-than-four-option fallback, stable multi-select ordering,
  recommended-first suffixing, repeated Yes/No labels across questions,
  duplicate-question-text fallback/correlation modes, reserved-Other collision,
  profile serialization of cancellation/freeform/feedback capability,
  cap/deadline and the exact comma-delimited codec, response-atom construction
  for delimiter/quote labels, and
  a capability/profile change between renders.
- Modify `src/attune_forms/conformance.py` to define the public immutable
  `HostQuestionProfile` facet and add its optional field to
  `InteractionProfile`. The containing `InteractionProfile.id` is the sole
  profile identity; the facet has no independent ID. Profile validation rejects
  duplicate/empty interaction-profile IDs and inconsistent limits; the shipped
  profile used by the registry is an actual installed `InteractionProfile`, not
  a test-local mapping.
- Modify `tests/test_conformance.py` to cover the new facet, validation, and
  profile serialization/equality contract.
- Modify `src/attune_forms/renderer_registry.py` to register the new
  per-profile host-native target beside its PORTABLE and HEADLESS twins. It
  has its own target ID; for an overlapping AskUserQuestion profile, the old
  specialized target remains compatibility-only and the generic target is the
  sole route-active choice. Both retain separate parity obligations.
- Modify `src/attune_forms/__init__.py` to export `HostQuestionProfile`,
  `QuestionAnswerBinding`, `HostQuestionBatch`,
  `host_question_admissibility`, and `form_to_host_question`; the no-escape
  sweep must see the renderer.
- Advance the verified 0.13.x package to 0.14.0.

Acceptance receipts:

- The same form may be admissible for a multi-question profile and
  inadmissible for a single-question profile; the pure predicate agrees with
  the renderer and no renderer truncates it.
- The current emitted-text AskUserQuestion profile rejects two normalized
  identical question strings before rendering. ID- and ordinal-correlated test
  profiles admit the same texts only when their host response contracts return
  unique IDs or exact ordered cardinality, and their immutable emitted bindings
  remain sufficient for the later server bridge to resolve each question
  without guessing.
- Profile serialization includes the closed normalization algorithms,
  raw atom kind/codec, attempt cap, and deadline; changing any facet changes
  the profile digest and invalidates consuming parity/lifecycle evidence.
- A clean-wheel probe imports public `HostQuestionProfile`,
  `QuestionAnswerBinding`, `HostQuestionBatch`, `InteractionProfile`,
  `host_question_admissibility`, and `form_to_host_question`, executes the
  predicate/renderer, and loads the shipped `InteractionProfile` whose sole ID
  equals the registry target's `profile_id` and whose host-question facet is
  present. Every route-active host-native target resolves to exactly one
  installed interaction profile; absence fails AF-2 before release.
- Recommended and option order are a stable partition; admissibility checks
  the suffixed emitted label against profile bounds and per-question collision
  rules after profile normalization, including collision with the reserved
  Other label/token. The pure renderer returns one immutable
  `QuestionAnswerBinding` per question with stable ID, emitted ordinal, exact emitted question
  text, and exact ordered emitted-label/response-atom/option-ID triples.
  Repeated labels across questions are legal, the recommended suffix remains
  part of the bound response atom, and no hidden renderer state is permitted.
  Package-local evidence stops at pure projection, immutable bindings/profile
  metadata, and canonical fixture construction. AF-2 exports no raw-host decoder
  and claims no host-response correlation, Other/cancellation decoding, common-
  validator result, feedback delivery, challenge, retry, deadline enforcement,
  receipt rotation, or presentation-attempt count; attune-ai Task 2 owns those.
- AF-2 produces fresh package-local transitive implementation, fixture, normalization,
  and owning-record-slice digests and its package-local gate is green before
  release. The consuming attune-ai obligation is absent and ineligible—not
  red—until Task 2 locks the released artifact and derives its machine/human
  receipt foreign keys; main never intentionally lands a red parity gate.
- Changed code carries at least 90% coverage; no API-billed call occurs.

After a separately authorized 0.14.0 release, the local Task 2 locks the
artifact, adds a trusted in-process `HostQuestionAdapter.present_and_collect`
boundary with an optional server-owned validation-feedback envelope for the
unified `elicitation_route_form` path, implements raw codec/correlation and
Other/cancellation decoding from the immutable bindings into the common
validator, updates the demo/parity
evidence, and proves fallback when that adapter is absent or mismatched on the
actual attune-ai routing seam. The package supplies the pure projection, not
the host transport. Task 2 never returns its batch for model-mediated relay and does not replace
`form_to_ask_payload` or the deprecated fixed-shape `elicitation_render_form`
compatibility contract.
