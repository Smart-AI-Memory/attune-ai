# Host Surface Parity — Design

**Status:** draft (2026-09-04) — execution reconciliation: Task 0 is
complete; Task 1 stopped before production when its baseline probe
falsified the proposed registry and host-artifact assumptions. D10
rules the replacement mechanism.
**Last updated:** 2026-09-04

## Verified baseline

Every anchor below was read from the tree on 2026-09-03 or reverified and
corrected on 2026-09-04, not carried from spec text.

- **Roster is literal.** `CANONICAL_SEATS: tuple[str, ...] =
  ("claude", "antigravity", "codex")` at
  [rotation.py:25](../../../src/attune/roundtable/rotation.py);
  `SEAT_RECIPES` (fixed argv: `claude -p`, `agy --mode plan`,
  `codex exec`) and `PLAN_ONLY_SEATS = {"antigravity"}` at
  [routine.py:92–106](../../../src/attune/roundtable/routine.py);
  `workspace.py` refuses `round_complete` unless the roster is
  exactly the fixed three
  ([workspace.py:258, 341](../../../src/attune/roundtable/workspace.py));
  the brief preamble hard-codes "three-model round table".
  `skeptic.py` and `countersign.py` import `CANONICAL_SEATS` for the
  different-model rule.
- **Provider registry is Claude-native.** `ModelProvider` has one
  member, `ANTHROPIC`
  ([registry.py:33](../../../src/attune/models/registry.py)).
  `ModelTier` is `CHEAP / CAPABLE / PREMIUM`
  ([registry.py:20](../../../src/attune/models/registry.py)) with
  duplicates in `config/agent_config.py:25`,
  `workflows/compat.py:50`, and `workflows/progressive/core.py:24`.
  Those four enums remain. Only the model-resolution-default mirror was
  retired: ccb4fe7bc removed
  `tests/unit/test_model_tiers_drift.py`, and `attune.model_tiers` now
  lazily re-exports canonical `attune_rag.model_tiers`. Ollama appears only in
  workflow config docstrings and comments; there is no Ollama client.
- **Surfaces exist, but are not registered.** `attune-forms` exposes
  `ProjectionSurface.RICH / PORTABLE / HEADLESS`. Its frozen
  `ProjectionRenderers` dataclass holds one injected workspace
  rich/portable/headless callable bundle plus an optional retained
  callable; it is not an iterable registry and has no exported
  instances. Standalone form renderers
  (`form_to_widget_html`, `form_to_markdown`,
  `form_to_askuserquestion`, `form_to_elicitation_schema`) sit outside
  that bundle. The host authority seam is
  `src/attune/elicitation/command_workspace.py` with Fix as the witness
  (`src/attune/elicitation/fix_workspace.py`, `src/attune/mcp/server.py`).
- **Projection has one master and three targets.**
  `MASTER_PATH = content/collaboration/contract.md`,
  `CONTRACT_TARGETS = (AGENTS.md, .claude/CLAUDE.md)`,
  `IDE_MIRROR_TARGET = .agents/AGENTS.md`
  ([scripts/project_collaboration_contract.py:19–29](../../../scripts/project_collaboration_contract.py)).
  The projector rejects symlinked targets and hand edits inside the
  marked block.
- **Memory promotion is a function.** `promote()` at
  [promotion.py:142](../../../src/attune/memory/promotion.py);
  `resolve_backend()` at
  [session_stash.py:120](../../../src/attune/memory/session_stash.py)
  resolves `attune.memory_backends` with two live implementations
  (`file`, `redis`). Recall hooks: `plugin/hooks/jit_recall.py`,
  `lesson_recall.py`, `session_recall.py`.
  `.attune/next_session_starter.md` is already a per-session
  projection of memory.
- **Spend and friction exist.** `src/attune/gates/spend_gate.py`,
  `src/attune/gates/session_ledger.py`, `plugin/hooks/friction_gate.py`.
- **Context-fit telemetry has a writer and no data.**
  [allocator.py:30](../../../src/attune/context/allocator.py) writes
  `~/.attune/telemetry/context_fit.jsonl`; the file does not exist on
  the chair's machine (TASKS.md, 2026-08-28).
- **Host contracts observed 2026-09-03** (Cowork session tool
  surface, described from the tool contracts):
  `AskUserQuestion` — 1–4 questions, each 2–4 options with `label`
  and `description`, `multiSelect`, an automatic "Other", and the
  convention of putting the recommended option first with a
  "(Recommended)" suffix. Project memory — `MEMORY.md` as an index of
  one-line links (about 150 characters each) to topic files carrying
  `name / description / type` frontmatter with `type` in
  `user | feedback | project | reference`. Scheduled tasks — cron or
  one-shot, each firing a fresh session with a standalone prompt.
  Monitor — wake on file or process change.

## Layer boundary

```text
host (Cowork / Claude Code / Codex / Antigravity / headless)
          |
          v
attune-forms  Projection registry + pure serializers
          |     RICH | PORTABLE | HEADLESS + host-native question (R1)
          |
          v
attune-ai   Surface policy/selection + receipts + CommandWorkspaceHost (R2)
          | host adapters and capability providers
          | roster.yaml -> role slots -> harness recipes   (R7)
          | projector: contract master + derived lesson-index source (R3)
          | ledger: asks-per-outcome                       (R8)
          |
          v
attune.extensions (release-16-manifest D3)
          | Phase A  memory-backend contract  -> local reranker   (R6a)
          | Phase B  workflow contract        -> local role workflows (R6b)
          | later    roster slot supplier     -> fourth seat (non-goal here)
          |
          v
parity gate (R2): every subject has cold/warm routes; every host-native
or RICH target / capable subject has PORTABLE + HEADLESS twins
```

The gate sits under everything on purpose: it is the enforcer that
lets the layers above adopt host features without the host becoming
privileged.

## R1 — Host tier 0 renderer

`attune-forms` adds a pure pre-render
`host_question_admissibility(form, profile) -> Admissibility` predicate and
`form_to_host_question(form, profile) -> HostQuestionBatch | None`.
`HostQuestionBatch` is a frozen composite with the host-visible question
`payload` and server-side immutable
`answer_bindings: tuple[QuestionAnswerBinding, ...]`; only `payload` is
serialized to the host. The pure renderer returns both values to its server
adapter; for a policy-owned host-native route the server retains the
composite's bindings/profile state in its PresentationChallenge and passes only
`batch.payload` to the trusted in-process `HostQuestionAdapter` described
below. The adapter emits that payload, while bindings remain server-side until
the same call returns a trusted completion.
Each frozen `QuestionAnswerBinding` carries the stable `question_id`, emitted
ordinal, exact emitted question text, and that question's ordered
`option_bindings: tuple[tuple[str, str, str], ...]`, ordered as emitted label,
response atom, then option ID.
The response atom equals the label only when the profile says so; a future
token-returning host supplies distinct atoms in the retained binding. Repeated labels such as
"Yes" and "No" are therefore legal across questions but never ambiguous
within one question.
`HostQuestionProfile` is the structured-question facet embedded in the
installed `InteractionProfile`. The containing `InteractionProfile.id` is the
sole stable profile identity; the facet has no second ID namespace. It declares
maximum question and per-question option/header counts, multi-select support,
the exact reserved Other label/token and free-text behavior, cancellation,
validation-feedback delivery, closed `question_text_normalization` and
`option_label_normalization` algorithms, a finite positive
`max_validation_attempts`, a finite positive `response_deadline_seconds`, and
one response-correlation mode: `question_id`, `emitted_text`, or `ordinal`.
It also declares the raw host multi-select response encoding: list or scalar,
the atom kind (`emitted_label` or `response_token`), and any delimiter,
escaping, and canonical-reencode rules. The server maps atoms through the
retained per-question bindings to canonical option IDs before validation and
never guesses label/token equivalence. The first
record models current Claude AskUserQuestion with
`{kind: comma_delimited, delimiter: ", ", atom: emitted_label,
escaping: json_quote_when_delimiter_or_quote, canonical_reencode: required}`.
An atom containing `", "` or `"` is JSON-string encoded with JSON backslash
escaping; every other atom is bare, atoms join with `", "`, and decoding is
accepted only when re-encoding equals the raw string. Other hosts may declare
larger or smaller shapes without changing this renderer. The function
defensively returns `None` when an unsupported direct call bypasses the
predicate. The routed path evaluates admissibility as metadata, selects
PORTABLE with the original form intact when false, and never calls the
host renderer merely to discover support.
Mapping for every admitted question:

| Form construct        | Host field                                      |
| --------------------- | ----------------------------------------------- |
| question text         | `question`                                      |
| short heading         | `header` (profile-bounded; no silent truncation) |
| option label / detail | `options[].label` / `options[].description`     |
| multi-select control  | `multiSelect: true`                             |
| recommendation        | stable-partitioned first, emitted label suffixed " (Recommended)" |
| free-text escape      | profile-declared separate response arm; never an option ID or guessed token |

Question and selected multi-value order are stable. Options use a stable
partition: the earliest recommended option moves first while relative order in
both partitions remains unchanged. Admissibility includes the suffixed label in
the profile length bound and rejects any within-question emitted-label
collision after profile normalization, including a user option colliding with
the profile's reserved Other label/token; it never truncates. The response path
also proves unambiguous question correlation before rendering: an
`emitted_text` profile rejects duplicate normalized emitted question text; a
`question_id` profile requires the host payload/response contract to carry the
stable ID; and an `ordinal` profile requires an ordered response with the exact
question count. The current AskUserQuestion profile is `emitted_text`, has
`header` bounded to 12 characters, and returns an `answers` mapping from exact
emitted question text to one canonical comma-delimited string. Decoded atom
order is preserved; empty, duplicate, unknown, or non-canonical atoms fail.
The recommended suffix is part of the exact emitted label/response atom and is
resolved through the retained binding, never stripped. Its freeform input is a
separate global `response`, not an answer token: it maps to Other only when
exactly one question lacks a structured answer. Zero or multiple missing
questions, or a structured answer plus freeform for the same question, is
malformed. The profile therefore falls back intact when two questions normalize
to the same text.
The response path
reuses the existing validator: the pure renderer stores each question's exact
ordered emitted-label/response-atom/option-ID triples in the frozen batch's immutable
`answer_bindings`; it retains no hidden mutable state. The trusted adapter
returns the host response directly to the server's same-call collector, which
already owns those immutable bindings plus the profile-declared correlation
mode; neither bindings, profile identity, nor a claimed presentation are
accepted from a later caller. It correlates the host response without
text/ordinal guessing, suffix stripping, or label guessing for chosen labels
or free text. It hands the answer to the
same validation the widget and headless tiers use. Other, cancellation,
malformed answers, and validation feedback follow the profile-declared
lifecycle; anything the profile cannot deliver falls back before
rendering. After rendering, a malformed answer is never interpreted as a route
failure: the common validator records the rejection and, when the already-
selected route declares validation-feedback delivery, commits that event,
rotates the receipt, constructs an immutable `ValidationFeedbackEnvelope` from
canonical validator errors, and calls `present_and_collect` for the next
presentation attempt on the same route. The envelope is a separate argument,
its digest is bound into that attempt's fresh single-use challenge, and no
caller- or host-supplied feedback is accepted. The server reuses the original
frozen batch and does not invoke the projection renderer again. Each adapter
call increments `presentation_attempt_count`; `renderer_attempt_count` remains
one for the selected interaction. Attempts stop at the profile's
finite cap or server-owned deadline; exhaustion records `abort`, invalidates
the challenge, and never cycles to a second surface. Adapter exception, `None`,
wrong challenge, or failure to complete before the deadline records terminal
`render_failed`, creates no new receipt, and likewise never changes surface.
A trusted user timeout returned by the adapter remains the distinct `timeout`
lifecycle result. A new immutable capability/profile snapshot may change the
next decision, but never rewrites an already-rendered form.

Rich constructs project only when the active profile explicitly names
their semantics; otherwise they stay on PORTABLE/RICH renderers. No
hardcoded construct denylist substitutes for profile fitness.

## R2 — Surface parity gate

Task 1 is now two ordered phases. First, `attune-forms` must expose a
public, non-empty renderer-record registry covering standalone forms
and workspaces, plus a package-local sweep proving that no production
renderer escapes it. A record names its PORTABLE and HEADLESS targets,
optional RICH target, and optional host-native targets keyed by stable target
ID. A route-active target names an installed `InteractionProfile.id`; a
compatibility-only target instead names a package-shipped immutable
`compatibility_contract_id` and exact `compatibility_shape_digest` and cannot
name or require a live adapter. Every host-native target also declares
`evidence_mode`: route-active requires `route_roundtrip`, and
compatibility-only requires `compatibility_projection`. Status and evidence
mode are included in the owning-record-slice digest. At most one target per renderer-family /
profile pair may be route-active; zero is valid until a separately released
route-active target exists. The standalone-form record maps RICH to `form_to_widget_html`,
PORTABLE to `form_to_markdown`, HEADLESS to
`form_to_elicitation_schema`, and the AskUserQuestion profile to
`form_to_askuserquestion`, marked compatibility-only with a fixed contract ID
and shape digest plus `compatibility_projection` evidence mode for the legacy
tool; AF-1 ships no route-active host-native
target. Host-native is not a `ProjectionSurface`
enum member. The workspace record maps RICH to
`workspace_to_widget_html`, PORTABLE to `workspace_to_markdown`, and
HEADLESS to the new production `workspace_to_headless` serializer; the
test-only conformance action-ID stub is not that target.

AF-2 adds `form_to_host_question(form, profile)` as a second,
profile-driven host-native target on the same standalone-form renderer
family. It does not rename or remove the pre-existing specialized
`form_to_askuserquestion` API: for an overlapping profile AF-2 leaves that old
target compatibility-only and makes the generic profile-driven target the one
route-active choice. Both retain distinct target IDs and parity obligations.
The package no-escape sweep sees both
public `form_to_*` callables and derives a separate obligation for each
host-profile target.

`workspace_to_headless(view, binding=None)` returns one deterministic,
JSON-safe mapping with `schema_version`, the complete `WorkspaceView`
projection (`id`, `title`, `summary`, ordered sections/actions, and full
form schema when present), the optional
`WorkspaceActionBinding.to_payload()`, and the response contract
(`__elicitation_response__`, title, view, action, confirmed, responses,
and binding fields). It may not collapse to action IDs. A canonical
package-local fixture chooses an action, constructs the declared
response-shaped mapping, and matches the widget/Markdown normalization
contract. After 0.13.0 is released, Task 1B sends that mapping through
attune-ai's stateful command-workspace adapter, which ultimately invokes
the attune-forms `collect_workspace_action` validator; the normalized
`WorkspaceActionResponse` must match. The public MCP
`fix_workspace_collect_action` handler is the later R4 seam and delegates
through that shared host rather than naming a different validator. The package does
not import its consumer or create a circular test dependency.

The package-local candidate predicate is closed and semantic. The registry
exports the finite `projection_output_types` vocabulary used by the sweep;
adding or removing a type is itself registry drift. Scan every production
Python module under `src/attune_forms/` for callables whose resolved inspected
annotations or bounded AST signature accept `Form` or `WorkspaceView` and
return one of those declared projection-output types when they are public,
exported, registry-referenced, or called across a production module/package
boundary.
For candidate typing, `Optional[T]` and `T | None` strip only the `None` arm
and must leave exactly one declared projection-output type; every other union
is unresolved and fails closed. A `form_to_*` / `workspace_to_*` function is
still caught by the independent naming guardrail even when its annotation is
not a candidate type.
Then union every registry target and every `form_to_*` / `workspace_to_*`
callable as a naming guardrail, including private names if production calls
them outside their defining module. A private helper used only within one
registered renderer is implementation, not a second target. Every candidate
must be a public package export and occur in exactly one
renderer record. An unresolved relevant annotation fails closed. A small
explicit non-renderer allowlist may contain only fully qualified symbols with a
rationale; its exact contents are mutation-tested and a prefix cannot be an
allowlist entry. Mutations add a semantically typed unregistered renderer, an
unregistered callable under each prefix, an unexported registry target, and
add/remove/edit one allowlisted FQN or rationale; all must fail with the exact
symbol. A mutation that attempts to place a detected renderer on the allowlist
also fails. New production renderers therefore cannot
escape by choosing a different verb. That
prerequisite releases as `attune-forms` 0.13.0 before `attune-ai` raises
its current `attune-forms>=0.12.2,<1.0` floor to
`attune-forms>=0.13.0,<1.0`.

After that release, `tests/unit/gates/test_surface_parity.py` walks
three inventories:

1. **Renderers** — every record exported by the released
   `attune-forms` registry. The gate derives one stable obligation key
   for each enhanced target:
   `renderer:<renderer-id>:surface:RICH` or
   `renderer:<renderer-id>:host-native:<target-id>`. The target separately
   carries its profile ID. Renderer record
   IDs, target identities, obligation keys, and receipt IDs are unique;
   a parity receipt carries exactly one `obligation_key` foreign key,
   and the receipted-key set must equal the derived obligated-key set.
   No orphan receipt, empty registry, or unreceipted enhanced target can
   pass. Adding a host-native target to an existing record creates a new
   obligation and cannot reuse that record's RICH or earlier host-profile
   receipt. Every registry record exposes a public, package-shipped canonical
   fixture factory/payload and normalization descriptor; tests are not the
   fixture distribution mechanism. The gate evaluates the registry exported by the actually
   installed artifact within the existing pre-1.0 compatibility range:
   a later release remains green only when its obligation and bound
   implementation/fixture/normalization/owning-record-slice digests are unchanged
   and its canonical fixtures pass; any new or changed obligation fails
   until its receipt lands. `uv.lock` remains
   one reproducible locked receipt and the gating execution base.
   `.github/workflows/cross-repo-compat.yml` runs scheduled,
   dependency-update, and manual fresh-resolution lanes across the allowed
   range as advisory compatibility probes. Each job summary and retained
   artifact names the resolved version, artifact and registry digests,
   canonical-fixture result, and surface-parity owner; these lanes never
   replace or turn red the verified locked gate merely
   because the resolver selected a different compatible artifact. Semver
   admissibility is deliberately not evidence
   equivalence: a compatible patch may install, but a changed bound
   implementation must be re-receipted before the parity gate turns
   green.

   The attune-ai surface-parity owner handles that failure in the dependency-
   update change: the gate names the exact obligation key, the owner executes
   the installed canonical fixture, and refreshed machine/human receipts land
   with the lock update. An unrelated upstream edit leaves target-specific
   digests unchanged; until a behavior-changing release is receipted, the lock
   retains the last verified artifact rather than making main permanently red.

   An obligation key identifies the target, but it is not proof that an
   old receipt still describes current behavior. Each parity receipt is
   also bound to the installed target implementation digest, canonical
   fixture digest, normalization-rules digest, and the canonical digest of
   that target's owning registry-record slice. The full registry hash belongs
   to route-decision versioning and does not invalidate unrelated target
   evidence. The
   gate executes the canonical fixture and compares those current
   digests. The implementation digest is the cycle-safe, deterministic
   transitive closure of statically resolvable package-local functions,
   classes, constants, default values, and decorators reachable from the
   target. An unresolved behavior-affecting dynamic dependency must be named by
   an explicit package-relative artifact reference or fails closed. A helper-
   only behavior change therefore invalidates the receipt, while an unrelated
   package symbol does not. Changing implementation or normalization invalidates the
   receipt even when the stable target/obligation ID is unchanged.
   For a route-active host-native target, the bound implementation identity
   additionally includes the installed `InteractionProfile` host-question
   facet digest and the adapter/collector implementation closure. Changing
   limits, normalization, response encoding, correlation, lifecycle behavior,
   or adapter collection under a stable profile ID therefore invalidates the
   target and lifecycle evidence. A compatibility-only target instead binds its
   fixed package compatibility-contract ID and shape digest. It has no route,
   profile-facet, or live-adapter precondition; the consuming
   `compatibility_endpoint` evidence separately binds each authorized anchor's
   exact response shape and provenance. Its package parity fixture executes the
   frozen canonical form through the specialized renderer plus its PORTABLE and
   HEADLESS twins, derives the canonical raw answer only from the specialized
   batches' emitted question IDs/options, feeds that answer through the package
   common `collect_form_response`, and requires one normalized `FormResponse`
   across all three paths. This `compatibility_projection` evidence proves no
   route, live presentation, lifecycle, or rendered tier. A status/evidence-mode
   flip, contract-ID/shape change, or changed emitted question/option invalidates
   the exact obligation and cannot reuse the old receipt.
2. **Attune adapters** — derive every shipped Python package root and
   entry-point module from `pyproject.toml` packaging metadata, currently
   including both `src/attune/` and top-level `attune_redis/`. Scan each
   package-root producer when
   they call a projection target from the registry or construct a
   recognized host-presented content envelope. `tests/` and the
   development-only `scripts/` root are outside this production
   inventory unless packaging metadata or a package/manifest/console
   entry point references a file there; this is derived scope, not a
   file-authored opt-out.
   Every detected producer must be named by exactly one local
   surface-subject record. Adding a projection call to an unregistered
   eligible producer anchor is the mutation receipt. A Python producer
   anchor is `file:qualname`; executable module-body output uses the reserved
   canonical anchor `repo/path.py:<module>`, so one module may own several
   distinct subjects. The exact current renderer-call anchor fixture is:

   - `src/attune/memory/recall_digest.py:render_digest_html`;
   - `src/attune/elicitation/command_workspace.py:CommandWorkspaceHost._render`
     (two renderer targets);
   - `src/attune/elicitation/ask_payload.py:form_to_ask_payload`;
   - `src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_form`;
   - `src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_widget`;
   - `src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_ask`.

   Imports, re-exports, type-only references, and response parsers are
   not producers by themselves. Alias resolution must cover direct
   imports, re-exports through `attune.elicitation`, and qualified module
   aliases; a per-syntax mutation adds an unregistered resolved call for
   each form and must fail with its anchor. Discovery also traverses
   statically resolvable repo-local helper calls from each host-exposed producer
   root, cycle-safe. Reachable helpers are implementation/provenance nodes, not
   standalone surface subjects: each retains its `file:qualname` and every root
   that reached it, so a mutation reports
   `<root-anchor> -> <helper-anchor>`. A helper becomes its own subject only if
   it is independently exported/invoked across a host boundary. This lets one
   shared helper serve roots with different routes without inventing an
   unreachable helper interaction. Unresolved dynamic dispatch at a relevant
   helper boundary fails closed unless the registry names the package-relative
   implementation artifact explicitly.

   Host-exposed producer-root records also own an exact route/target mapping.
   The initial MCP ask handler maps `_handle_elicitation_ask` to
   `mcp-native:native-elicitation` through authenticated
   `session.elicit_form`. `form_to_ask_payload` remains the fixed-shape
   compatibility adapter and owns no policy route; a unified host-native route
   may use only the registry's route-active target with a trusted installed
   adapter profile. Task 1B adds
   `_handle_elicitation_route_form` as the unified policy endpoint. Its closed
   discriminated response carries `schema_version`, `selected_route`,
   `payload_kind`, opaque nullable `receipt_id`, nullable `submission_id`, and a
   non-authoritative `route_decision_summary`. The summary's exact closed keys
   are `context_reason` (the exact closed `RouteContextReason` from the 23-row
   first-match table below), finite non-negative `selection_elapsed_ms`,
   `renderer_attempt_count: Literal[0, 1]`, and non-negative integer
   `presentation_attempt_count`; additional properties fail. The summary is
   server output only, and echoing or modifying it cannot affect routing or
   collection. It forbids candidate order/dispositions,
   capability or accessibility-constraint IDs/provenance,
   receipt/store/workspace/schema IDs, timestamps, and every unknown key. The
   full route receipt remains server-side, while the opaque active `receipt_id`
   is the only client-carried authority. A payload-return success requiring
   deferred collection has a non-null server-issued `submission_id`; a trusted
   same-call completion and every error arm have it null. Success arms are
   a route-specific presentation payload or a trusted completion. Error arms
   are `no_supported_surface` (null route/receipt), `render_failed` (selected
   route and no newly issued receipt), `session_ended`,
   `challenge_invalidated`, and `challenge_consumed`. `challenge_consumed`
   requires the already-selected route and null payload/completion, receipt, and
   submission ID; it exposes no winner receipt and performs no mutation.
   `session_ended` and `challenge_invalidated` carry no active receipt and only
   the route when one had already been selected. These three are challenge
   dispositions, not additions to the closed R2 interaction-lifecycle token
   set. Any
   other field combination fails
   response-schema validation. Task 1B's
   initial payload kinds are native-elicitation completion, rich HTML,
   portable Markdown, and headless schema. For
   `mcp-native:native-elicitation`, the handler serializes the registered
   HEADLESS schema, invokes authenticated `session.elicit_form` itself, and
   returns the server-observed completion envelope; it never returns a native
   request for the caller to present. After AF-2, Task 2 adds the closed
   trusted-host-question-completion arm: a selected host-native question route
   invokes the registered `HostQuestionAdapter.present_and_collect` and returns
   its trusted completion, never a host-question batch for the model to relay.
   Server-side bindings never cross in a host payload.

   The pre-existing `_handle_elicitation_ask` keeps its published response
   shape. Before calling `session.elicit_form`, it applies the same trusted
   capability and accessibility admissibility filters for that fixed native
   route. A rejected route returns that contract's explicit unsupported arm;
   it never selects another surface or returns a new payload shape.

   The existing `_handle_elicitation_render_form` retains its published
   AskUserQuestion `{success,title,description,batches}` response and calls only
   the specialized compatibility target under its trusted fixed profile. It is
   deprecated but is not routed through the unrestricted resolver, so old
   callers never receive a different payload shape. It keeps its own parity
   obligation but is never a policy candidate. Together with the existing
   fixed-shape `form_to_ask_payload` adapter, it forms the closed two-anchor
   compatibility allowlist for that target. The machine inventory represents
   those exact anchors as one derived `compatibility_endpoint` subject kind
   with fixed target, response shape, and `unverified_compatibility`
   provenance, and with no cold/warm route lists; a third anchor or a changed
   response shape fails. No policy producer may select a
   compatibility-only renderer. Any other direct caller, a policy bypass, an
   unmapped producer route, or a mapping to the wrong route-active target fails
   with the producer anchor and target ID.
3. **Host artifacts** — the union of every script resolved from
   `plugin/hooks/hooks.json` and `.claude/settings.json` regardless of
   directory, every command under `plugin/commands/` (currently only
   `handoff.md`), and the templates R5 adds. The manifest files are
   inventory sources, not surface subjects. Every resolved Python hook or
   command implementation is fed once to the same scanner used by item 2 and
   deduplicated by canonical producer anchor; item 2 does not rescan this
   manifest-derived set. Every registered hook is scanned for the same renderer-call/host-envelope indicators;
   non-rendering lifecycle hooks do not fabricate UI records.
   A Python entrypoint uses a `file:qualname` anchor. A filesystem
   command or template uses `artifact:<repo-relative-path>`. A manifest
   entry that does not resolve to a file uses
   `manifest:<manifest-path>#<JSON-pointer>` and fails closed as an
   unsupported discovery kind until the same change adds a
   language-specific scanner, canonical fixture, and mutation receipt.
   Markdown commands/templates are informational subjects by
   construction and use their artifact anchor plus a canonical render
   fixture; they do not need a Python AST.

   Manifest commands are parsed as data and never executed during
   discovery. For hooks, the initial resolver requires the exact shipped
   launcher prefix `PY=$(command -v python3 || command -v python) && "$PY"`,
   tokenizes only its remaining tail, and requires exactly one
   `.py` path token. `${CLAUDE_PLUGIN_ROOT}` / `$CLAUDE_PLUGIN_ROOT`
   resolve beneath `plugin/`; `${CLAUDE_PROJECT_DIR}` /
   `$CLAUDE_PROJECT_DIR` resolve beneath the repository root. Absolute
   remainders, `..`, unknown variables, arguments, redirects, extra shell
   operators, missing files, and resolved path escapes fail with the
   manifest registration identity. The `handoff.md` Markdown scanner
   separately accepts its one direct
   `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_handoff_cli.py"` fenced command. A
   genuinely inline or non-Python hook remains unsupported until its
   scanner/fixture lands; the current shell wrapper is not itself grounds
   to misclassify a resolvable Python entrypoint.

   Before resolution, registration identity is
   `(manifest_path, event, matcher, ordinal, raw_command)` and failures use
   `manifest:<manifest-path>#<JSON-pointer>`. After success it gains
   `resolved_repo_path`; no failure message relies on an undefined path.
   Subjects reached through multiple registrations deduplicate only by
   their canonical path/producer anchor, never by basename. The scanner groups
   registrations by resolved path and unions the event set only to schedule one
   AST scan. It emits event-qualified results and obligations keyed by producer,
   event, matcher, signature, sink/destination, and registration provenance;
   evidence from one event can never satisfy another. Manifest order cannot
   change the result. Each
   manifest must yield at least one registration or the inventory fails.

The host-envelope vocabulary is closed and machine-readable. Every signature
record declares its qualifying event predicate, `subject_kind`, exact
destination, and supported sink set. Its initial signatures are: a native MCP
`session.elicit_form` call; a
host-question batch returned from `form_to_host_question`,
`form_to_askuserquestion`, or `form_to_ask_payload`; an MCP handler
response carrying `html` or
`panel_html`; a bound `CommandWorkspaceRender` carrying both `html` and
`markdown`; MCP Apps metadata whose `ui.resourceUri` uses `ui://`; a
top-level Claude hook `systemMessage`; and
`hookSpecificOutput.additionalContext` paired with `hookEventName`; and
non-empty plain stdout from event types whose host contract injects it into
model context, initially `SessionStart` and `UserPromptSubmit`. The closed
stdout sinks are `print(...)`, `sys.stdout.write(...)`, and
`sys.stdout.buffer.write(...)`; a dynamic or aliased write the scanner cannot
resolve fails closed. `systemMessage` maps to `user_notice`;
`hookSpecificOutput.additionalContext` and the declared context-injecting
stdout events map to `model_context`. Event-qualified
positive control signatures are also closed: `PreToolUse` with
`permissionDecision: deny` and non-empty `permissionDecisionReason`, and
`Stop`/`SubagentStop` with `decision: block` and non-empty `reason`, are
`model_context`; host-visible allow/ask permission reasons or stop reasons are
`user_notice` only when the event contract declares that destination. An
explicit exit-2 stderr path is positive only for an event whose host contract
feeds blocking stderr back to the model. Its closed sinks are
`print(..., file=sys.stderr)`, `sys.stderr.write(...)`, and
`sys.stderr.buffer.write(...)`, paired in the same qualified reachable graph
with `sys.exit(2)`, `raise SystemExit(2)`, or a declared entrypoint return-code
2. Wrong event, wrong exit code, stdout/stderr swap, or unresolved dynamic sink
is a negative mutation. The same key on any other event remains control-plane
output. The signature registry maps native/form envelopes to
`interactive_form`, workspace/App envelopes to `interactive_workspace`, and
event-qualified notice/context envelopes to `informational_delivery` with
destination `user_notice` or `model_context`; no destination is inferred from
a bare field name.
The gate matches the qualified producer plus its required field set,
not a bare JSON key. For manifest-resolved Python entrypoints it uses a
bounded, cycle-safe interprocedural AST normalization over the reachable
repo-local helper graph, covering mapping literals,
`dict(...)`, constant-key subscript writes/updates, and a normalized
mapping passed to JSON serialization or returned. Imports build only
the alias table; a resolved call establishes producer membership and retains
its root-registration provenance. A
candidate containing a recognized key whose construction cannot be
normalized fails closed with its anchor instead of disappearing from
the inventory. Claude control-plane output — `continue`,
`stopReason`, `suppressOutput`, `decision`, `reason`,
`permissionDecision`, `permissionDecisionReason`, `updatedInput`, a
bare `hookEventName`, stderr, and stdout on non-context-injecting events — is
explicitly excluded unless the same qualified producer root or its reachable
helper graph also matches one of the positive signatures or calls a registered
projection target. Another function in the same file cannot transfer that
credit. The earlier structured-
envelope-only probe found `jit_recall.py`, `lesson_recall.py`, and
`session_stash.py`; that is characterization evidence, not the complete Task
1B obligation set. Task 1B creates a reviewed `producer_baseline` fixture from
its execution base before mutation. The fixture stores separate
`renderer_call_anchors`, `package_host_envelope_anchors`, manifest
registrations with raw commands/resolved paths/events, and helper-reachability
edges; those sets must not be collapsed into one count. D6's calibration found
26 manifest
registration rows resolving to 24 unique repository-relative Python
entrypoint paths (15 unique under `plugin/hooks/hooks.json`, nine under
`.claude/settings.json`). Basename de-duplication incorrectly reports 22
because the distinct `format_on_save.py` and `security_guard.py` paths
exist under both roots. `plugin/commands/handoff.md` separately resolves
to `plugin/hooks/_handoff_cli.py`, making 25 unique hook-plus-command
execution paths; the Markdown command remains the informational subject and
its resolved Python implementation is always scanned, becoming a separate
producer only if a projection call or positive envelope is detected. Adding a signature requires adding its discovery mutation and
receipt in the same change. The fixture is execution-base evidence owned by
Task 1B, not retroactively attributed to Task 0.

D10 has no producer opt-out classification. Surface-subject membership
is derived from production behavior, not a self-declared `helper`
label; commands and templates are subjects by construction, while hooks
and Python adapters become subjects when the sweep detects a registered
projection call or a positive envelope signature. Each interactive subject
carries two ordered surface-preference lists, `cold` and `warm`, whose route
tokens are `mcp-native:<transport-id>`, `host-native:<profile-id>`,
`RICH`, `PORTABLE`, or `HEADLESS`, plus the semantic and lifecycle requirements
that a route must satisfy. Informational subjects are exempt from those lists:
each has a closed event-qualified `delivery_routes` mapping to `user_notice` or
`model_context`, with content/destination/delivery evidence for every key.

The initial subject defaults make the cold/warm distinction concrete:

- cold `interactive_form` discovery prefers
  `mcp-native:native-elicitation`, then each trusted route-active in-process
  host profile in registry priority, then PORTABLE, then HEADLESS;
- warm `interactive_form` prefers RICH, then negotiated
  `mcp-native:native-elicitation`, then its receipted host-native profile,
  then PORTABLE, then HEADLESS;
- cold `interactive_workspace` prefers PORTABLE then HEADLESS, while
  warm prefers RICH then PORTABLE then HEADLESS;
- a noninteractive execution path prefers HEADLESS; and
- informational artifacts/deliveries use their event-qualified
  `delivery_routes`; if one independently owns a receipted enhanced renderer,
  that creates a separate interactive surface subject.

These are registry data, not hardcoded vendor branches, and may change
only with their parity/lifecycle receipts.

Projection and transport are orthogonal. The MCP-native route uses the
standalone-form record's HEADLESS `form_to_elicitation_schema` serializer once,
then the unified server handler sends that schema through authenticated
`session.elicit_form` for host display and receives its completion on that same
transport.
The bare HEADLESS route uses the same data projection programmatically without
a host. The shared projection does not make the candidate order a repeated
HEADLESS render, and the MCP transport owns a distinct lifecycle/delivery
receipt rather than a duplicate renderer target.
Tier provenance classifies the observed presentation, not this shared
projection: a server-observed completion from negotiated native elicitation
stamps `rendered_tier: host_native`, while bare programmatic use stamps
`rendered_tier: headless`; the exact `selected_route` remains separate. A
requested route and its render receipt prove selection, not presentation, so
neither may stamp the tier. Non-MCP presentation requires either an
authenticated deferred host-adapter callback bound to the active receipt or
the same-call HostQuestionAdapter completion bound to its server-owned
PresentationChallenge; ordinary caller input cannot assert transport
provenance.
The concrete non-MCP seam is a server-registered immutable
`HostQuestionAdapter` with `adapter_id`, `adapter_version`, and `profile_id`
plus one asynchronous
`present_and_collect(payload, *, presentation_challenge,
validation_feedback: ValidationFeedbackEnvelope | None)` method.
`validation_feedback` is `None` on
the first presentation or the server-created immutable
`ValidationFeedbackEnvelope` whose digest is captured by that fresh challenge;
the adapter cannot originate or modify it.
The server creates the opaque in-memory challenge, calls the adapter directly,
and accepts only the returned frozen `HostQuestionCompletion` carrying the same
challenge object identity. The challenge captures the authoritative session,
subject/schema, selected-route and canonical-payload state but is neither an
active action receipt nor serializable. After a trusted completion, the server
atomically creates the `SurfaceInteractionRecord` from that captured state and
issues/consumes or rotates its receipt according to the completion lifecycle;
a transport error creates no active receipt and records `render_failed`, while
session close invalidates the challenge before completion may commit. Neither
challenge nor completion can be supplied through an MCP argument, and two
concurrent completions for one challenge admit at most one commit. The adapter is available to routing only when
its profile ID equals the installed `InteractionProfile.id` and the selected
route-active renderer target's profile ID. A profile, cached doctor cell, or
serialized batch without this live object is not a deliverable host-native
candidate and falls through before rendering. Unit tests may use a fake
adapter to prove the interface, but only Task 11's live production-adapter
receipt proves host display.
Deferred RICH/PORTABLE presentation has a separate immutable,
server-registered `DeferredPresentationAdapter` contract with `adapter_id`,
`adapter_version`, closed supported route tokens, and one
`begin_presentation(payload, *, receipt_id, callback_challenge)` boundary. The
server-owned single-use callback challenge binds adapter/session identity,
receipt, selected route, payload digest, expiry, and opaque adapter correlation.
Only the adapter's authenticated callback endpoint can create the internal,
non-serializable `CollectionTransportContext`; serialized collection input
cannot supply or override it. A missing context may still validate through the
published compatibility collector but is `unverified_transport`; a supplied
context with the wrong adapter/correlation fails `transport_mismatch` or
`correlation_mismatch` with no receipt rotation. Callback replay,
post-session callback, or wrong receipt fails closed. This seam is optional for
projection-only compatibility, but it is mandatory before Task 11 may claim a
deferred RICH or PORTABLE display.
The same rule covers every route: absent a server-observed completion or an
authenticated adapter callback, the validated envelope is
`provenance_status: unverified_transport` with no `rendered_tier`, even when
policy selected RICH, PORTABLE, or host-native. The legacy fixed-shape `elicitation_render_form` followed by the legacy
form-plus-answers collector has no authenticated presentation callback. Its
validated envelope is therefore explicitly
`provenance_status: unverified_compatibility` with no `rendered_tier`; the
session ledger increments a separate raw unverified-compatibility counter and
excludes it from tier/Other denominators. The existing native
`_handle_elicitation_ask` does have server-observed `session.elicit_form`
completion evidence, so Task 11 stamps that path as `host_native` alongside the
unified MCP-native arm.

Surface choice has one deterministic precedence:

1. **Authoritative accessibility constraints** filter candidates.
   These come only from server-owned user/session settings or a trusted
   in-process host adapter; a producer, tool argument, model response,
   or caller-written context cannot assert them. The closed constraints
   describe usability needs such as text-only or no live updates, not a
   generic `disable_dynamic_ui` escape.
2. **Trusted host capabilities** filter unsupported candidates. MCP
   native elicitation and MCP Apps support come only from the negotiated
   request/session capabilities. AskUserQuestion and other non-MCP
   host-native profiles come only from a trusted in-process adapter's
   installed `InteractionProfile` ID; MCP negotiation cannot be used to
   invent them. Unknown fields are unsupported.
3. **Interaction requirements** remove routes that cannot preserve the
   subject's schema, validation, postback, and required lifecycle.
4. **Verified context** chooses the subject's `warm` or `cold` ordered
   list using the receipt predicate below. Unknown is cold; the list is
   never reordered.
5. The first remaining token wins. Interactive lists carry their
   receipted PORTABLE then HEADLESS fallback candidates explicitly. Candidate
   filtering is metadata-only and invokes no renderer. If no
   declared token remains admissible, the resolver returns
   `no_supported_surface`; it never invents or trial-renders a route.

The resolver receives a `CapabilitySnapshot` from a provider seam; it
does no network probing and invokes no renderer while deciding. It
performs at most one lookup in the receipt store and at most one projection
renderer invocation: exactly one for a selected route, zero for
`no_supported_surface`. If that selected renderer raises, unexpectedly returns
unsupported, or cannot deliver, the attempt ends as `render_failed`; the
resolver records the failure and does not cycle to another token. Each route
receipt records the full registry-snapshot hash,
constraint and capability snapshot IDs/provenance, context reason,
every candidate in evaluated order with its disposition, selected
token, `selection_elapsed_ms`, `renderer_attempt_count`, and the separate
`presentation_attempt_count`. Feedback-capable retries reuse the original
projection and selected token; they increment only presentation attempts. The
profile's positive `max_validation_attempts` includes the initial presentation,
and the original server deadline never resets. Each retry has a fresh
single-use challenge retaining the selected route and frozen bindings. CI gates the
deterministic causes of lower latency (zero probe calls and no option
cycling). A keyless characterization harness, never the production request
path, records the legacy failed-rich-then-fallback baseline against the same
canonical fixture; route receipts compare observed cold/warm selection latency
with that non-gating baseline without imposing a cross-platform wall-clock
threshold. The one-lookup bound counts only receipt-store access; the same
server-side decision/transaction may read the authoritative session registry
and current workspace record once each. Those state reads are not additional
receipt lookups and never perform network I/O.

Task 1B adds the missing session seam. For a payload-return route, every
successful policy-owned render captures the authoritative state used to
render and stores a server-owned `SurfaceInteractionRecord`. It ensures exactly
one opaque `receipt_id` is the record's `active_receipt_id`: it issues or
rotates when authoritative state or collection binding changes, and otherwise
returns the unchanged active receipt for the caller to echo. The same-call MCP/HostQuestion transports use the
PresentationChallenge flow below and create that record only after trusted
completion. This includes otherwise stateless forms. An idempotent pure
re-render of unchanged authoritative state returns the same active receipt, so
it cannot invalidate a concurrent action. Every collection/action submission
has a server-issued `submission_id`. The opaque authenticated ID names a
`SubmissionTokenRecord` in the same receipt-chain store, initially `pending`,
bound to server/store instance, session and chain, active receipt, selected
route, payload digest, and collection-binding/validator digest. Each successful
payload-return render call atomically mints/registers a fresh pending ID and
returns it beside the unchanged or new active receipt; the public collector must
echo it. Thus a separately rendered concurrent presentation has a different ID
without rotating an unchanged receipt. Same-call trusted transports mint and
consume the same record internally without exposing it. The collector's one
receipt-store lookup resolves the token plus chain state; malformed,
unauthentic, or unissued tokens return `invalid_submission`, while an authentic
token bound to another receipt/session/route/payload/binding returns
`submission_mismatch`, before validator invocation or side effects. A network
retry repeats the original ID and canonical response. Commit atomically stores
the canonical-response digest and exact transition result and marks the token
`committed`; same ID/same digest returns that byte-identical stored result even
after the receipt was tombstoned, while same ID/different digest returns
`submission_conflict` without mutation. An independent concurrent submission
uses the ID issued with its own presentation. Unused pending IDs are invalidated
with receipt supersession/terminal action, expiry, or session close. The closed
collector error union adds exactly `invalid_submission`,
`submission_mismatch`, and `submission_conflict` beside the existing
receipt/transport dispositions. A committed validation-feedback
response compare-and-swaps both
`chain.active_receipt_id == echoed_receipt_id` and the unchanged authoritative
revision/schema binding, atomically tombstones the predecessor as
`superseded`, activates the same-state successor, and records the validation
event without fabricating a domain-state transition. A non-terminal action atomically stores the successor
interaction/workspace record, issues and activates its fresh receipt,
stores `submission_id` with the transition result, and tombstones the prior
receipt as `superseded` before returning. A failure
inside the durable state transaction or while constructing its response
before that transaction commits leaves the predecessor active. Network
delivery is not part of that atomic boundary: delivery loss after commit never
rolls state back. The same committed `submission_id` and response digest return
the stored transition result and successor receipt without repeating the action; a
different ID receives the ordinary `superseded_receipt`/`terminal` loser
disposition. A terminal action atomically replaces the consumed receipt with a
`terminal` tombstone stamped at commit, closes the chain, and issues no active
or warm successor.

The same-call native MCP and HostQuestionAdapter transports capture that state
in a server-owned in-memory `PresentationChallenge` before the external call;
they create/advance the record and receipt only after a trusted completion.
That challenge is not warm or action-capable. Failure records `render_failed`
in the route-attempt/decision receipt and creates no **new** active receipt; an
existing predecessor remains active, while a cold attempt has none. Session
close and completion commit share the session lock. Challenge
compare-and-consume returns `challenge_consumed` for a second completion and
`session_ended` / `challenge_invalidated` when close or explicit invalidation
won first; every rejected completion performs no receipt mutation.
`challenge_consumed` is a response/challenge disposition only and never joins
the `{accept, abort, timeout, validation_feedback_delivery}` evidence set.

For a form route that legitimately returns a presentation payload for later collection,
Task 1B gives the same `SurfaceInteractionRecord` a frozen, route-neutral
collection-state slot holding canonical validator input, `payload_digest`,
selected route, expected authenticated collection transport, and opaque
adapter-owned correlation data. The generic public collector accepts only the
opaque receipt, `submission_id`, and host response and performs the record's
one receipt-store lookup. Its authenticated server/adapter boundary may also
supply the internal non-serializable `CollectionTransportContext` defined
above; that context, never caller input, proves adapter/session/correlation
identity. Missing context validates as `unverified_transport`; mismatched
context fails with the closed transport/correlation reason and no rotation.
The collector uses the frozen state for common validation and never accepts a caller-supplied form, profile, binding
map, tier, or payload digest. Receipt rotation carries forward freshly rendered
collection state; superseded and terminal receipts cannot collect. AF-2 host
questions do not use that caller-mediated deferred path: Task 2 passes their
frozen `profile_id`, closed `response_correlation` mode, and
`answer_bindings: tuple[QuestionAnswerBinding, ...]` directly through the
same-call trusted adapter/collector boundary; those AF-2 types are not a Task
1B dependency. The MCP-native arm is likewise collected inside
`_handle_elicitation_route_form` from the server-observed
`session.elicit_form` completion and records trusted transport provenance
without a second public collection call. Task 11 alone later maps that evidence
to `rendered_tier`.

Two different-submission concurrent uses of one receipt admit at most one commit: after a
non-terminal winner the loser gets `superseded_receipt`; after a
terminal winner it gets `terminal`. The stored
`SurfaceContextReceipt` carries `server_instance_id`, `session_id`,
`chain_id`, immutable `subject_kind`, `subject_id`, `schema_id`, canonical
`schema_digest`, timezone-aware `observed_at`, and `terminal: false` for every
active subject kind; terminality exists only as a tombstone reason. A workspace receipt also carries
`workspace_id`, `adapter_id`,
`adapter_version`, `revision`, `event_sequence`, `contract_hash`,
and `action_nonce`. The workspace comparison target is the
current server-owned `CommandWorkspaceHost.get(workspace_id)` record. When
that lookup returns `None`, current workspace shape is invalid and predicate 8
returns `record_shape_mismatch`. When
present, a form uses its deterministic `FormSchema.form_id` as identity and a
canonical digest of the full form/questions/validation schema as content. An
empty or absent ID is permitted but cold; the empty string remains the required
form-kind `subject_id` value but can never establish warmth. Reusing an explicit ID with changed
schema content produces the cold route reason `schema_mismatch`; the mismatched
receipt is ineligible for warm selection, not an invalid-form refusal.

Session close and receipt mutation share one server-side transaction/lock.
Closing a session first marks the session registry entry ended and replaces
every active receipt in that session with a `session_ended` tombstone before a
new action can commit. A late action therefore cannot remain warm merely by
echoing the same stable session ID. Opaque receipt authenticity uses an
installation-scoped key distinct from `server_instance_id`; that key survives
a normal process restart, while the default receipt store does not. A
well-formed old ID is consequently `foreign_receipt` after restart, whereas a
bad MAC is `invalid_receipt`. `server_instance_mismatch` remains a defense for
an injected/shared receipt-store implementation and is mutation-tested even
though the default process-local store cannot normally produce it.

Active records and tombstones use different clocks. Active-record age is
`now - observed_at`; a tombstone stores immutable `reason` and
`tombstoned_at`, and its retention age is `now - tombstoned_at`. Below the
two-hour retention boundary a tombstone always returns its stored terminal
reason, while an active record follows the ordered comparison table and returns
`expired` only after earlier mismatches have been checked. At age `>= 7200`
seconds either record is logically absent and the well-formed ID returns
`foreign_receipt`, regardless of whether physical cleanup has run. GC is
opportunistic under the same lock; exact `7199.999` and `7200` classifications
cannot race eviction.

The receipt schema is discriminated by subject kind. A form record requires no
workspace fields and forbids them; a workspace record requires all of
`workspace_id`, `adapter_id`, `adapter_version`, `revision`, `event_sequence`,
`contract_hash`, and `action_nonce`. `subject_id` is permanently bound to its
`subject_kind`. Predicate 8 validates the closed per-kind shape, including
forbidden extra fields; predicate 14 compares workspace IDs only after both
records have valid workspace shape. Predicates 15–20 likewise execute only when
both current and stored subjects are workspaces.

Warm requires a successful server-side receipt lookup, exact equality
for the current server instance, open session, active chain receipt,
subject, schema, and every applicable workspace binding field,
`terminal == false`, and an age in the half-open interval
`[0, 3600 seconds)`. Timestamp alone never establishes warmth. The
predicate is total and first-match-wins in this exact order:

| Order | Predicate | Route reason |
| ---: | --- | --- |
| 1 | an applicable current form has an empty or absent deterministic ID | `empty_form_id` |
| 2 | no echoed receipt ID | `missing_receipt` |
| 3 | ID is malformed or unauthentic | `invalid_receipt` |
| 4 | well-formed ID resolves to no record, or the record/tombstone retention age is at least 7200 seconds | `foreign_receipt` |
| 5 | retained tombstone stores ended host-session reason | `session_ended` |
| 6 | retained tombstone stores superseded reason | `superseded_receipt` |
| 7 | retained tombstone stores terminal reason | `terminal` |
| 8 | stored/current subject kind is unknown, or a required field is missing/invalid, or a forbidden field is present | `record_shape_mismatch` |
| 9 | issuing server instance differs | `server_instance_mismatch` |
| 10 | stable session ID differs | `session_mismatch` |
| 11 | interaction chain ID differs | `chain_mismatch` |
| 12 | immutable subject kind or subject ID differs | `subject_mismatch` |
| 13 | schema ID or canonical schema digest differs | `schema_mismatch` |
| 14 | workspace-only: workspace ID differs | `workspace_mismatch` |
| 15 | workspace-only: adapter ID differs | `adapter_id_mismatch` |
| 16 | workspace-only: adapter version differs | `adapter_version_mismatch` |
| 17 | workspace-only: revision differs | `revision_mismatch` |
| 18 | workspace-only: event sequence differs | `event_sequence_mismatch` |
| 19 | workspace-only: contract hash differs | `contract_hash_mismatch` |
| 20 | workspace-only: action nonce differs | `action_nonce_mismatch` |
| 21 | `observed_at` is later than current UTC | `future_timestamp` |
| 22 | active-record age is at least 3600 seconds | `expired` |
| 23 | no preceding rejection predicate matches | `warm` |

Ended-session, superseded, and terminal tombstone reasons remain distinguishable
for their two-hour tombstone-retention window; an unconsumed active record is
`expired` during `[3600, 7200)` after all earlier comparisons pass. A restart therefore
reports a previously well-formed, installation-authentic opaque ID as
`foreign_receipt`, while malformed or bad-MAC input remains `invalid_receipt`.

Subjects outside the receipt-owning server seam — including hooks,
commands, and templates — cannot self-assert warmth; without an echoed
server-issued receipt they deterministically use their cold route.

The provider seam uses the installed `attune-forms` `HostCapabilities`
as the observed bitmap and `InteractionProfile` as a static, receipted
conformance contract; request flags never synthesize a profile. Task 1B
supplies request-local MCP and trusted in-process host-adapter providers
that return one immutable `CapabilitySnapshot`. The MCP provider accepts only
the authenticated initialize/session capability object handed to the server
adapter; the non-MCP provider accepts only the profile exposed by its
server-registered immutable adapter object. A static profile or doctor cache
cannot synthesize the live delivery object. Tool arguments, arbitrary request
fields, and model output cannot write either source. Task 10 later supplies
the persistent doctor-backed provider, diagnoses and cross-host-
conformance-tests it, and wires that provider through
`surface_policy.py` and `server.py`; a fresh request-local snapshot wins
over stale persisted evidence. Each capability cell carries a typed source
kind (`session_negotiated` or `host_static`), `observed`, `supported`,
source/host binding, and observation time;
`observed=true,supported=false` is a current negative, while
`observed=false` is unknown. For the closed MCP capability vocabulary, a
completed authenticated initialize/session negotiation treats an omitted
capability as `observed=true,supported=false`; unknown is reserved for a
missing/uncompleted provider source, so cached positives cannot resurrect an
unadvertised feature. MCP-native elicitation and MCP Apps cells are always
`session_negotiated`: if current authenticated negotiation is absent, no
persisted value may select them. A persisted snapshot carries timezone-aware
`observed_at` and `expires_at`; its validity interval is
`[observed_at, expires_at)`, with `0 < expires_at - observed_at <= 3600
seconds`. A future `observed_at` or over-long/non-positive interval rejects the
snapshot rather than clamping it; duration may equal 3600 seconds, while exact
`expires_at` is stale because validity is half-open. An unexpired host-bound
doctor snapshot may fill only unknown `host_static` cells, never fill a
`session_negotiated` cell or elevate a current negative. This makes "optimal" a deterministic
policy choice rather than an unverified claim without putting capability
discovery on the render path. An opt-in header marker remains
insufficient because an unmarked producer would escape.

Each renderer and subject enhanced-route target creates its own derived
obligation key: renderer keys use the form above; subject keys are
`subject:<subject-id>:surface:RICH` or
`subject:<subject-id>:host-native:<profile-id>`. `mcp-native:*` is a
transport key by design and therefore owns lifecycle/delivery evidence rather
than a duplicate projection-parity key. Every enhanced obligation requires
PORTABLE and HEADLESS twins plus a parity receipt. A portable-only
informational subject uses `delivery_routes` and does not fabricate an enhanced
route. A recognized
`systemMessage` or `hookSpecificOutput.additionalContext` producer is
an informational-delivery subject (`user_notice` or `model_context`)
owing content-schema and destination/delivery evidence, not an enhanced
surface obligation. If the same producer also invokes a registered
renderer, that call creates its normal, separately anchored surface
subject; the delivery classification cannot hide it.

Lifecycle receipts attach to the production subject that owns the
transition, not blindly to each pure renderer function. The closed
`subject_kind` matrix is:

- `interactive_form`: `accept` plus validation-content evidence. Its required
  `route_transport_refs` mapping has exactly the union of the form subject's
  declared cold/warm route tokens as keys. Each value is discriminated as
  `{kind: "subject", id: <interaction-transport-subject-id>}` or
  `{kind: "host_profile", id: <host-profile-id>}` and must resolve to
  `abort`, `timeout`, and `validation_feedback_delivery` lifecycle receipts;
- `interaction_transport`: `abort`, `timeout`, and delivery of validation
  feedback for its closed `form_subject_ids` set;
- `interactive_workspace`: `accept`, `abort`, `timeout`, and
  `validation_feedback_delivery` end to end;
- `informational_artifact`: command/template content schema, render,
  destination, and delivery only; and
- `informational_delivery`: hook content schema plus `user_notice` or
  `model_context` destination/delivery only; and
- `compatibility_endpoint`: the exact two fixed-shape anchors, fixed specialized
  target/response/provenance contract, and no policy or cold/warm routes.

Neither informational kind invents accept, abort, timeout, validation-
feedback, or accepted-payload state.
Their closed evidence dimensions are
`informational_artifact = {content_schema, render, destination,
delivery}` and `informational_delivery = {content_schema, destination,
delivery}`.

A form route is unsupported until its exact `route_transport_refs` entry
resolves to a known interaction-transport subject or host-profile record and
that target's receipt set covers
`{abort, timeout, validation_feedback_delivery}` exactly once. An
`mcp-native:<transport-id>` key must name the matching interaction-transport
subject; a `host-native:<profile-id>` key must name that exact host profile;
RICH, PORTABLE, and HEADLESS keys name interaction-transport subjects. When a
reference names an `interaction_transport`, the current form subject ID must
also occur in that transport's closed `form_subject_ids` set, and the
relationship is reciprocal: `transport.form_subject_ids` equals exactly the
IDs of forms with at least one `route_transport_refs` value naming that
transport. A complete transport for Form B cannot satisfy Form A, and an
orphan, missing route key, extra route key, wrong-kind token, or one-way
association fails the gate. Host ownership is never treated as proof.
Host profiles intentionally remain generic capability/admissibility records:
the form's forward reference plus its executed admissibility fixture binds the
pair, while only specialized interaction transports declare a reciprocal
closed `form_subject_ids` set.
Accepted payloads for interactive
subjects must have identical recursive key/type schemas and canonical
values after normalizing only each registry record's closed, rationale-bearing
nonsemantic volatile paths. Revision, event sequence, contract hash,
subject/schema/action IDs, and other semantic bindings remain equal and cannot
be normalized away; lifecycle
receipts compare normalized state, commit, retryability, and field IDs.
Informational subjects compare render content/destination/delivery and
have no accepted payload schema.

The canonical machine inventory is
`docs/specs/host-surface-parity/parity-registry.json`; it has separate
`renderers`, `subjects`, `host_profiles`, `host_envelope_signatures`,
`constraint_schema`, `capability_snapshot_schema`,
`context_receipt_schema`, `producer_baseline`, `receipts`, `experiments`,
`experiment_history`, and `experiment_exceptions` collections.
`producer_baseline` contains the separately typed anchor,
registration/path/event, and helper-reachability sets described above; it is
never used as a single magic count.
The gate derives the complete enhanced-target obligation set from
`renderers` and `subjects`; it is not hand-authored. Record, subject,
host-profile, obligation, and receipt IDs are unique in their own
namespaces. A `parity` receipt names exactly one `obligation_key`; a
`lifecycle` receipt names exactly one typed `subject_id` or
`host_profile_id` plus one closed lifecycle state; an informational
`delivery` receipt names exactly one `subject_id` plus one dimension
from that informational kind's closed set. Every foreign key and host-native
profile token must resolve, and each interactive form's
`route_transport_refs` key set must exactly equal its declared cold/warm route
union. The gate derives three complete required
sets: enhanced-target parity obligations, every subject/host-profile's
own or delegated lifecycle-state obligations, and every per-kind
informational evidence obligation. Each required set must equal
its corresponding receipted set exactly; a missing accept state or
delivery dimension therefore cannot false-green. Receipts for
non-obligated targets are rejected rather than counted as coverage.
Every receipt kind binds the current owning implementation, executable
fixture/evidence, and canonical owning-record-slice digests. Every receipt
whose fixture normalizes payload or state—including parity and lifecycle
receipts—also binds the normalization-rules digest. The gate executes each canonical fixture and
recomputes the digests, so lifecycle or delivery behavior cannot change
under a stable key while reusing stale evidence. The Markdown ledger is
evidence keyed to receipt IDs and is
never parsed as the gate's authority. The closed interactive lifecycle set is
`accept`, `abort`, `timeout`, and `validation_feedback_delivery`; form-level
validation content is evidence for the last transport-delivery token, not a
fifth state; removing or changing that bound content or normalization makes the
existing receipt fail. Canonical fixtures make revision, event sequence, contract hash,
subject/schema/action IDs, and other semantic bindings equal across routes.
Each record may declare a closed list of truly nonsemantic volatile paths
(for example a renderer-only DOM nonce/element path or render timestamp) with
rationale. Authoritative `action_nonce`, `revision`, event sequence, contract
hash, subject/schema/action IDs, and every collector binding are never
normalizable.

An experiment
carries `id`, exact `obligation_key`, `root_anchor`, `started_on`,
`expires_on`, `owner`, and `reason`; its UTC duration must be 14–30
calendar days inclusive, `today >= expires_on` is expired, and its active interval is exactly
`started_on <= today < expires_on`; the active registry rejects a future start.
Dates
must be valid UTC calendar dates. `root_anchor` must resolve to a
package-excluded experiment location rather than a shipped artifact.
At most one experiment may name an obligation at a time; intervals may not
overlap or touch. Continuous waiver is capped at 30 days per obligation in any
180-day window, so a nominal renewal cannot reset the clock. A record in
`experiment_exceptions` binds one experiment ID, the same stable obligation
key, current implementation digest, decision reference, and bounded dates. It
only authorizes that named experiment to exceed the rolling cap; it never
subtracts an obligation itself, bypasses receipt conflict/expiry/sibling checks,
or erases prior intervals from `experiment_history`. An implementation change alone
cannot mint a new key; only a genuinely new target naturally derives one.
The gate subtracts only the active experiment's exact obligation key
from the parity-required set; it cannot waive sibling target,
lifecycle, or delivery obligations. An active experiment and a current machine
parity receipt for the same obligation are mutually exclusive; their overlap
fails as `experiment_receipt_conflict`. Starting means one reviewed registry
mutation that atomically adds the currently active experiment, removes the
current machine receipt, and appends the interval to machine history; its
historical human-ledger row remains append-only. Expiry restores the obligation immediately and requires a newly
executed receipt—the removed receipt cannot silently reactivate. A machine-readable inventory owns
these references, while
`docs/specs/host-surface-parity/receipts.md` carries the human evidence
ledger. Missing any requirement fails with the exact subject and
shortfall. Task 11's tier provenance remains the live falsifier that
the selected surface actually rendered; Task 1B proves the policy and
fallback matrix, not host-display truth.

The gate is added to the collaboration contract as the enforcer of
principle 1 for surfaces, so the master's "aspirational" label comes
off for this case. This is the Discipline article's §7 rule applied
to surfaces — "if a property matters, something must fail when it
stops being true" (attune-ai.dev/discipline).

## R3 — Memory index projection

The projector gains a generated projection source, not a second
authority: `content/collaboration/lesson-index.md`, produced by
`scripts/project_lesson_index.py` from the promoted store. Each line
is `- [<lesson name>](<target-relative store link>) — <one-line hook>`.
Every link is projected from the same canonical, path-validated promotion
record and must resolve back to that record; target-specific relative text may
differ, so parity compares canonical lesson IDs/order and hooks rather than raw
Markdown link bytes. The file
carries independent per-host line and byte budgets that the projector drift-
guards. Each byte budget is also capped by the residual headroom beneath the
collaboration contract's 20,000-byte eager-load ceiling. The default projection
contains `K` lesson entries, where `K = min(25, capacity(target) for every
configured target)`. For the already-determined reserved-slot-plus-ranking
order, `capacity(target)` is the largest prefix length up to 25 whose projected
block fits that target's line/byte ceilings; `K` must be at least one or
projection fails before any write. If one or more active promotions have never been projected
successfully, the newest such promotion occupies slot 1 for that regeneration
and the remaining `K - 1` use hit frequency with a deterministic tie-break. If
none are awaiting first display, all `K` slots use the normal ranking. Only a
successful projection marks the promotion displayed; on later
regenerations it competes normally and may fall out, so zero-hit promotions get
one guaranteed display rather than permanent reservation.
The authoritative promotion record carries nullable `first_projected_at`.
After every configured target is written successfully, one atomic promotion-
store transaction timestamps every previously-null promotion present in the
emitted block. A target-write failure or metadata-transaction failure leaves
all of those fields null, records stale state, raises `ProjectionSyncError`,
and makes retry idempotent. Existing records without the field
deserialize as null; no eager migration is required, and the first successful
write preserves every existing/unknown frontmatter field and value while adding
the timestamp atomically.
The entries sit below a provenance header containing canonical source and
render digests and between the separate literal sentinel comments
`<!-- ATTUNE:MEMORY:START -->` and `<!-- ATTUNE:MEMORY:END -->`; each
target declares its own total-line ceiling. Stale entries are removed on
regeneration. Check/project mode compares the stored render digest and refuses
a hand edit inside the sentinels; explicit `attune memory project --repair`
may replace only the sentinel-owned block from the current canonical source and
never overwrites host text outside it.

Targets, each inside a marked block the projector owns:

- Cowork project memory: the configured project-memory `MEMORY.md` path
  (the host reads it at session start; the line shape matches the host's
  index convention). It is exercised through a scratch configured path;
  no bare repository `MEMORY.md` target is assumed.
- `.claude/CLAUDE.md` — the sentinel-bracketed block next to the
  existing contract block.
- `AGENTS.md` and `.agents/AGENTS.md` — the same sentinel-bracketed
  block, so Codex and Antigravity read the same index.

`promote()` calls the regenerator after a successful authoritative store
commit. A failure raises typed `ProjectionSyncError` and leaves the promotion
durable. The existing promotion store owns one store-level
`LessonProjectionStatus` record—not a second lesson authority—with `stale`,
`observed_at`, `reason`, and failed target IDs. It clears only after all target
writes and the metadata transaction both succeed. Retry through
`attune memory project` is idempotent; failure never claims rollback or silently succeeds.
`attune memory project` regenerates on demand. Nothing in recall
changes: recall still ranks from the store; the index is a courtesy
to hosts that cannot call recall.

## R4 — MCP Apps round-trip receipt

A scripted run begins from deliberately cold context. It renders the Fix
preview once through PORTABLE, captures and echoes the server-issued receipt,
then reopens the unchanged workspace warm. Only that warm request may select
RICH and supply the widget capture; cold policy is never bypassed merely to
manufacture a widget receipt. The transcript captures (a) whether the host
advertised the Attune UI MIME profile, (b) the cold Markdown and warm widget (or
warm Markdown fallback) that rendered, (c) the public MCP
`fix_workspace_collect_action` response with revision, nonce and
contract hash, (d) deliberate replay, stale-revision, and wrong-contract-
hash actions and their exact fail-closed reasons. Two independent
receipts are required: advertised profile/action round trip and absent-
profile Markdown fallback. The live host capture identifies which case
was observed; a controlled keyless conformance fixture with an immutable
capability snapshot proves the other and labels it simulated rather than
treating it as live evidence. The handler delegates through the stateful
command-workspace host; that host's consumer adapter ultimately invokes
attune-forms `collect_workspace_action`. Task 1B receipts the generic consumer
boundary, while R4 receipts this public Fix-tool seam. `r4-receipts.json` is
the machine authority for these two host-capture records;
each record includes live/simulated provenance, capability-snapshot digest,
render kind, binding fields, and the three fail-closed outcomes. It is separate
from `parity-registry.json`: live host capture is not a replayable canonical
fixture and does not pretend to be a `parity`, `lifecycle`, or `delivery`
receipt. The R4 block in `receipts.md` is human evidence keyed to those two
machine IDs.

## R5 — Scheduled and monitored delivery, twinned

Four canonical YAML definitions under `content/automations/` describe
sweep, bug-predict, release-prep, and the
`~/.attune/telemetry/context_fit.jsonl` monitor. A single projector
generates both `plugin/templates/scheduled/` host bindings and the
portable crontab/`attune` CLI twins; generated outputs refuse hand edits.
Both paths produce the same `.attune/workflow_runs.jsonl` contract. The
semantic kind is `automation_kind: scheduled | monitor | interactive`; the
delivery seam is independently `delivery_adapter: host | cron | interactive`.
`interactive` is reserved for direct/manual runtime receipts and is rejected
in projected master definitions. Host and cron twins of one definition match
after normalized workflow-run semantic fields; adapter-specific event/cursor
configuration lives under the binding's adapter configuration and may differ,
while the normalized receipt differs only on `delivery_adapter`.

The monitor runtime is deliberately small: file events run a
deterministic triage predicate or enqueue an outbox item, never launch an
LLM sweep. It enforces a minimum 60-second debounce, an hourly run cap,
self-origin suppression so its own telemetry row cannot retrigger it,
and explicit acknowledgment before a token-intensive audit. Each monitor
master declares positive integer `max_runs_per_hour`; the per-definition window
is half-open `[hour_start_utc, hour_start_utc + 1h)`. The first event beyond
the cap emits `hourly_cap_exceeded`, launches nothing, consumes no event or
challenge, and leaves the event pending.
A normalized event
receipt remains `pending_ack` until an authenticated host action or an
interactive local operator runs
`attune automation acknowledge <event-receipt-id>` through the local control
channel. A TTY is presentation, not authentication. The portable command must
connect over an owner-only Unix-domain socket or Windows named pipe whose peer
UID/SID matches the event owner, then obtain a positive result from the
platform `OperatorConfirmationProvider` (for example OS password/biometric
confirmation). If authenticated local confirmation is unavailable, the
portable path refuses and the operator must use the authenticated host action;
allocating a PTY is never sufficient.

The server creates an `AckChallenge` with `challenge_id`,
`server_instance_id`, `event_receipt_id`, `operator_id`, a SHA-256 digest of a
256-bit CSPRNG nonce, `issued_at`, `expires_at`, and nullable `consumed_at`.
Its validity interval is
exactly `[issued_at, expires_at)` with a five-minute maximum. The raw nonce
exists only inside the authenticated host/local-control exchange, never argv,
cron payloads, logs, or durable storage. The durable pending-event/outbox
record stores the challenge fields/digest and consumed state in owner-only
SQLite. `BEGIN IMMEDIATE` plus a conditional pending/challenge update provides
the cross-process compare-and-consume boundary. An acknowledgment-server
process restart invalidates any uncompleted raw challenge but preserves pending status
and cross-process replay refusal. A fresh authenticated request may replace an
expired/uncompleted challenge; a client/CLI restart has no effect.
Confirmation verifies peer/operator/event,
nonce digest, TTL, and pending state, then compare-and-consumes challenge plus
event atomically. Mismatch, expiry, disclosure/logging, replay, restart of an
uncompleted challenge, cron/headless use, or OS-auth refusal fails closed. Cron
and headless pollers cannot request or auto-acknowledge a challenge; without an
interactive acknowledgment they leave the event pending. Prompts and
portable invocations both carry the spend cap. The host monitor binding
feeds native file events into this runtime; its cron twin invokes a
bounded poller that reads only rows after a durable cursor. Both adapters
produce the same normalized event and guard receipt, so cron does not
pretend to receive filesystem notifications.

The host acknowledgment path uses a server-registered trusted
`HostAcknowledgmentAdapter` whose immutable adapter/session identity consumes
the same event-bound challenge. Request, prompt, and model fields cannot assert
that identity or substitute a positive result.

This external seam is complete only with a keyless live boundary receipt. The
machine authority is
`docs/specs/host-surface-parity/operator-confirmation-receipts.json`, whose
schema includes the implementation-declared platform support matrix and whose
record IDs are referenced by the Markdown ledger. On
at least one platform the implementation declares supported, the production
`attune automation acknowledge` command must traverse the production
owner-only UDS/named-pipe endpoint, expose its real peer UID/SID to the server,
invoke the real OS `OperatorConfirmationProvider`, consume one pending event,
and refuse a replay. The receipt records the platform/provider kind, observed
peer identity, event/challenge IDs and dispositions but never the raw nonce or
answer content. On each implementation-declared unsupported platform, the
production provider is invoked and receipts explicit
`operator_confirmation_unavailable` while the event remains pending; a mock,
injected permissive provider, or test skip cannot satisfy either branch. A
two-process race receipt proves exactly one audit launch commits.

## R6 — Local-model roles via extensions

**R6a — reranker (Phase A).** An in-repo example extension
`extensions/attune-ext-local-rerank/` implements the memory-backend
contract's optional `rerank(candidates, query) -> ranked` capability
against an Ollama endpoint, falling back to the store's own ranking
on connection/DNS timeout, HTTP error, protocol/version mismatch, malformed
body, duplicate/unknown candidate IDs, or partial/non-permutation ranking. The
health receipt uses a closed degradation reason for each class; fail-open
always returns the original store order, never a partially trusted ranking. It is the "minimal example extension"
Phase A already requires — so it costs the extension work nothing
extra and satisfies D2's demand for a real second implementer.
Recall eval ([memory-recall-eval](../memory-recall-eval/requirements.md))
runs with and without the reranker; the receipt is P@3 on the frozen
benchmark, not a feeling. Acceptance requires reranked P@3 to be no lower than
the store baseline and at least one healthy rerank invocation. The receipt
records raw hits, queries, and successful-rerank count so fail-open cannot
manufacture a vacuous tie; a regression fails even when both numbers were recorded.

**R6b — role workflows (Phase B).** Extensions implementing the
workflow contract for: lesson classification, triage pre-sort,
low-stakes skeptic/countersign, fact-check probes. Each declares
`placement: local` on the existing role-routing record and is routed
by role. This stakes rule applies only to records declaring that local
placement. Precedence is closed: stakes are evaluated first, so an above-
threshold local-preferred role goes directly to the existing hosted `PREMIUM`
enum member; otherwise the router tries the enabled local extension and falls
back to the record's originally declared hosted tier only when local
availability fails. No tier enum changes. The ledger records `stakes_fallback` or
`local_unavailable` as distinct reasons.

**Placement, not tier.** D2 rejected a `LOCAL` enum member. The placement
label lives on `UnifiedAgentConfig`, prefers an enabled local extension,
and falls back to the existing hosted route. Task 12's focused placement
test asserts all four existing in-tree enum call-paths remain exactly
`cheap/capable/premium`; canonical model resolution stays the lazy
attune-rag re-export and no sibling-package edit occurs.
Quality tier remains the role's planning label; it is not pricing evidence for
a local run. `CostTracker` records actual placement and
`pricing_source: local_no_api_charge` with API-billed cost `0` for local
execution, while hosted fallbacks use their actual hosted model/tier pricing.
The session ledger stores declared `placement_preference`, observed
`actual_placement`, and `placement_reason` separately; pre-Phase-A local
preference therefore records `hosted` plus `local_unavailable`, never a local
execution claim.
Local compute utilization may be reported separately but is never fabricated
as hosted API spend.

## R7 — Roster as data

`src/attune/roundtable/roster.py` loads the embedded default automatically.
The only non-default source is the explicit operator-owned path
`~/.attune/roundtable/roster.yaml`, outside the worktree; it must be a regular
non-symlink file owned by the current user with owner-only access (`0600` or
the platform-equivalent ACL). `~` is resolved from the authenticated OS account
record (`getpwuid(geteuid()).pw_dir` on POSIX or the token-bound Windows profile
directory), never `HOME`, `USERPROFILE`, or another process environment value. A
repository-local `.attune` file, environment-selected arbitrary path, or
worktree content can never activate an override.

```yaml
slots:
  - slot_id: moderator
    role: moderator        # receipts, board I/O, synthesis
    seat: claude
    recipe: ["claude", "-p", "{brief}"]
    brief_transport: argv_placeholder
    execution_mode: interactive
    trust_boundary: subscription_cli
    required_capabilities: [synthesis, board_io]
    receipt_obligations: [round_receipt, board_post]
  - slot_id: plan_reviewer
    role: plan_reviewer     # plan-only; cannot emit code
    seat: antigravity
    recipe: ["agy", "--add-dir", ".", "-p", "{brief}", "--mode", "plan"]
    brief_transport: argv_placeholder
    execution_mode: plan_only
    trust_boundary: subscription_cli
    required_capabilities: [plan_review]
    receipt_obligations: [review_reply]
  - slot_id: code_proposer
    role: code_proposer     # code-native
    seat: codex
    recipe: ["codex", "exec", "--skip-git-repo-check", "-"]
    brief_transport: stdin
    execution_mode: code_native
    trust_boundary: local_worktree
    required_capabilities: [code_proposal]
    receipt_obligations: [diff_manifest]
```

Any non-default roster also requires a fresh `RosterOverrideReceipt` at the
fixed operator-owned path
`~/.attune/roundtable/roster-override-receipt.json`. An interactive `attune roster approve`
action writes `roster_digest`, `trusted_path`, `operator_id`, `decisions_ref`,
`issued_at`, and `expires_at`, binding the receipt to the complete roster,
exact trusted path, local operator identity, and recorded chair decision. Its
`operator_id` comes from the kernel effective UID/SID used for the owner check;
the TTY is presentation only and no Task-5 confirmation provider is required.
Task 6 owns a separate `RosterOperatorConfirmationProvider` backed by the
platform's authenticated user-confirmation service; unavailable/refused
confirmation fails closed. The command stamps server UTC itself and rejects caller-supplied/future times.
Validity is half-open and bounded to `(0, 30 days]`; non-TTY use,
path substitution, digest mismatch, missing decision, or expiry fails closed.
Loader verification is deliberately reusable and non-consuming until expiry,
including across process restarts. Replay refusal applies to approval issuance:
a second `roster approve` for the same digest/decision while an unexpired
receipt exists fails `approval_already_active` rather than minting another
authorization. The receipt path has the same owner/no-symlink/owner-only checks
as the roster. The embedded default requires no override receipt. A fourth slot still
requires its separate extension-specific `RosterActivationReceipt` in addition
to the roster-wide override receipt.

The composition root loads one immutable `ActiveRosterSnapshot` from that
trusted source before any seat invocation. `CANONICAL_SEATS`, `SEAT_RECIPES`
and `PLAN_ONLY_SEATS` are derived from that exact snapshot so every current
import keeps working without a second load. The snapshot is process-wide;
changing the external file has no effect until an explicit restart or
new process, and every invocation in one process observes the same digest.
The loader validates the four capability/governance fields (execution mode,
trust boundary, required capabilities, and receipt obligations) plus the
required `slot_id`/role/seat/recipe identity fields and typed brief transport.
Every `slot_id` and `seat` ID is unique, and each slot ID matches
`^[a-z][a-z0-9_-]{0,63}$`. For `argv_placeholder`, exactly one whole argv token
must equal `{brief}` and the runner sends no stdin brief. For `stdin`, the recipe contains zero `{brief}` tokens and
the runner pipes the complete brief on standard input. Any other transport
fails. Required cardinality is keyed by reserved role: exactly one
`moderator`, `plan_reviewer`, and `code_proposer`. An extension role may declare
`execution_mode: plan_only` and joins `PLAN_ONLY_SEATS` without becoming the
reserved plan-reviewer role. Workspace gates
compare against `len(roster.slots)`. The brief preamble is templated
from the slot count and seat names. A fourth slot is representable only with
role `extension:<role>` and fails to load unless that named, enabled extension
provides its recipe and a typed activation artifact authorizes it.
The fourth slot's explicit `slot_id` remains an independent stable slug; it is
never derived from the colon-bearing role value.
`RosterActivationReceipt` contains `slot_id`, `roster_digest`, `extension_id`,
`operator_id`, `decisions_ref`, `issued_at`, and `expires_at`. The loader verifies that the
decision reference names a recorded chair ruling, the four identities match
current state, `issued_at` is not future, the interval is in `(0, 30 days]`,
and the half-open validity interval has not expired; mismatch, absence, or
expiry fails closed. It is loaded only from the fixed owner-only, non-symlink
path `~/.attune/roundtable/activations/<slot-id>.json`, with the same
current-user ownership checks as the roster override. Before interpolation,
`slot_id` must match `^[a-z][a-z0-9_-]{0,63}$`; the resolved path must remain a
direct child of the activations root. Absolute/traversal IDs, containment
escapes, and symlinked roots/files fail before any read.
The issuance command is `attune roster activate <slot-id>`; it binds the same
kernel-derived operator identity and chair decision, stamps server UTC, refuses
an already-active identical authorization, and rejects caller-supplied or
future issue times. `ActiveRosterSnapshot.valid_until` is the earliest expiry
of its override/activation receipts, or `None` for the embedded default. The roster files are never reread in the
process, but every seat invocation refuses at or after `valid_until` and
requires a new process/snapshot before spawning another seat.

## R8 — Asks-per-outcome

The session ledger already records spend per seat invocation. It gains raw
events keyed by `session_id` and `work_unit_id`: structured asks issued;
terminal **work-unit** outcomes
partitioned as accepted, cancelled, aborted, timed_out, or blocked; sessions with
zero terminal outcomes; and surface fallbacks. Answer contents are never
written. Asks per session remains a secondary diagnostic.

A work unit is one declared session/workflow objective—such as one Fix run,
workflow run, or promotion attempt—not each structured question. It emits at
most one terminal outcome under a uniqueness constraint, while any number of
structured asks with the same `work_unit_id` may precede it;
asks per outcome therefore does not collapse to one by construction.

This is a session-outcome taxonomy, not a new R2 interaction lifecycle.
When an interaction exists, accepted maps to `accept`, cancelled or
aborted maps to `abort`, and timed_out maps to `timeout`; blocked is a terminal
work-unit result that never reached a successful interaction. Only when a
session closes does it increment `zero_terminal_outcome_sessions`, and only if
none of its work units emitted a terminal result.

`friction_gate` computes asks per terminal outcome over a trailing 30-day
aggregate grouped by project/workflow key in the existing ledger JSONL. It
renders the ratio only when that aggregate has at least
`MIN_TERMINAL_OUTCOMES = 10`; below that floor it
renders `insufficient_evidence` with the raw numerator/denominator. It
also reports zero-outcome rate and fallback frequency. The ratio is a
derived display value, never a persisted field. No new store or per-session
ten-outcome assumption is introduced; the ledger's existing JSONL carries the
raw events. Its numerator includes asks attributed to every work unit that
terminated in the same half-open window/key, including
cancelled/aborted/blocked units. Asks on still-open or zero-outcome units are
reported separately as `unattributed_open_asks` and never silently enter or
disappear from the ratio.

## Sequencing

| Increment | Depends on | Target |
| --- | --- | --- |
| D2 / Task 12 | Task 0 | attune-ai 16.3 release train |
| AF-1 | Task 0 characterization | attune-forms 0.13.0 |
| Requirement R2 / Task 1B | released AF-1 registry | attune-ai 16.3 prerequisite; separate go |
| Requirement R4 / Task 4 | Task 1B green; host access | attune-ai 16.3 release train |
| Requirement R9 / Task 10 | Task 4 receipt | attune-ai 16.3 release train |
| AF-2 | Task 10 provider/conformance layer | attune-forms 0.14.0 |
| Requirement R1 / Task 2 | released AF-2 renderer | attune-ai 16.3 release train |
| Requirement R10 / Task 11 | Task 2; separate chair go | post-16.3 separately authorized |
| Requirement R3 / Task 3 | Task 0 projector characterization | attune-ai 16.4-class; dependency-eligible |
| Requirement R5 / Task 5 | Task 1B green (templates are parity subjects) | next 16.4-class minor |
| Requirement R7 / Task 6 | Task 0 roster characterization | attune-ai 16.4-class; dependency-eligible |
| Requirement R6a / Task 7 | Phase A substrate on disk | the minor that completes A |
| Requirement R8 / Task 9 | Task 0 characterization only | attune-ai 16.4-class; dependency-eligible |
| Requirement R6b / Task 8 | Tasks 6, 7, 12 + released Phase B | following minor |

Nothing here blocks passenger 4; R6a is the example extension Phase A
already owes.

The attune-ai spec runner starts tasks in document order and does not schedule
from `<dependencies>`. `tasks.md` therefore uses the ruled
topological/authorization queue; “independent” means dependency-eligible, not
schedule-independent or allowed to jump an earlier gated block. The current
runner has no task-ID selector, so those tasks execute only when the document
queue reaches them (or after a separately chaired spec reorder). External AF
milestones are prose handoffs and cannot be mistaken for local file paths.

## Receipts

Each task in [tasks.md](tasks.md) names its receipt. The initiative's
overall projection-equivalence receipt is a single demo form projected for five surfaces —
Cowork tier 0, Claude Code widget, Codex Markdown, Antigravity
Markdown, headless text. The canonical answer is pre-fed through each
projection's common validator and must yield one identical validated payload;
this is projection equivalence, not a claim that five hosts displayed and
returned the answer,
recorded in `tier-provenance-receipts.json` and `receipts.md`.
`scripts/render_demo_forms.py` regenerates the canonical projection and bare
HEADLESS control; it does not impersonate host display. The distinct live
presentation receipt requires the keyless, non-mocked negotiated MCP-native
completion plus its bare HEADLESS control. Any other hosted row counts as
actual-display evidence only with its own authenticated adapter callback;
otherwise it is retained as `unverified_transport`, proves projection only,
and never blocks or contaminates the two-row live receipt.
