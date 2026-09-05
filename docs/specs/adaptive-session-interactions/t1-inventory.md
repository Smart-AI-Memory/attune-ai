# Adaptive session interactions — T1 inventory (reconcile and characterize)

**Status:** T1 executed 2026-09-05 (Claude, lead), read-only — awaiting the
chair's T1 acceptance. No source, skill, or dependency changes were made.
T2 does not start on this document; it starts on the chair's acceptance
plus its own go.

**Task go:** planning form response `resp-20260905-150806-0f0dffe9`
(2026-09-05, Patrick picked "T1 reconcile-and-characterize on the ASI spec
(read-only inventory)"). The same form authorized landing the spec package
(attune-ai #2428) and pushing attune-forms `codex/af-2-scoring-protocol`.

## Execution checkout and runtime (ASI-3, ASI-7)

| Item | Value | How known |
| --- | --- | --- |
| Worktree | `.claude/worktrees/resume-attune-forms-planning-a3179d`, branch `claude/resume-attune-forms-planning-a3179d` | `git branch --show-current` |
| Tree | `be15968fa` (origin/main, fetched 2026-09-05) + cherry-pick of the spec commit `8185e72fd` (docs only) | `git rev-parse HEAD origin/main` |
| Source under probe | this worktree's `src/` via explicit `PYTHONPATH` (the editable install maps `attune` to the main checkout — see the core worktree lesson) | probe preamble |
| Python | 3.10.11 (`~/attune-ai/.venv`) | `sys.version` |
| attune-forms | 0.12.3, installed distribution (not editable) | `importlib.metadata.version` |
| attune-ai distribution label | 16.2.1 (label cannot distinguish published wheel from source; the probes ran this worktree's source) | `importlib.metadata.version` + `attune.__file__` |
| Host for the live form receipt | Claude desktop app, Code tab, this session; attune-forms plugin MCP server (`elicitation_render_widget` / `elicitation_collect_response`); widget shown through the host's `show_widget` | this session's tool log |
| Inspected-path drift since the spec's planning snapshot `3588c5487` | none in `src/attune/elicitation`, `src/attune/mcp/server.py`, `src/attune/spec`, `src/attune/roundtable`, `plugin/skills/elicit`, `plugin/skills/spec` | `git diff 3588c5487 be15968fa --stat -- <paths>` empty (evidence.md already recorded the same for `be15968fa`; re-checked here against the cherry-picked tree, which adds only `docs/`) |

Preflight: `scripts/collaboration_preflight.py` — 0 failed, 1 warning
(main checkout dirty with another session's untracked files; not pulled).

## Source-backed inventory

### Consumers: every registered command-workspace adapter

`CommandWorkspaceHost` (`src/attune/elicitation/command_workspace.py`) is
the single canonical host; the MCP server registers thirteen adapters at
construction (`src/attune/mcp/server.py:142-160`):

| adapter_id | Module | Choice shape |
| --- | --- | --- |
| `spec` | `src/attune/spec/workspace.py` | stage machine: preview → creating → gate_running → review → approval → executing → task_gate → receipt |
| `roundtable` | `src/attune/roundtable/workspace.py` | preview → rounds → `apply_rulings` (action-scoped `response_fields`, the atomic 3+3+1 batch) → promote/decline |
| `fix` | `src/attune/elicitation/fix_workspace.py` | two-action preview (the original authority loop) |
| `smart-test`, `bug-predict`, `doc-gen`, `verify`, `security-audit`, `image-analysis`, `release-prep`, `bulk`, `memory-and-context`, `workflow-orchestration` | `src/attune/workspaces/*.py` | intake → preview → progress → receipt (version-1 cohort, shared-command-workspaces spec, completed 2026-09-01) |

The generic tools are `command_workspace_open` / `command_workspace_collect_action`
/ `command_workspace_publish` (`server.py:935-1015`); every result carries
`mcp_app` metadata (`resource_uri: ui://attune-forms/dynamic-surface/v1`,
`collect_mode: response`).

### Selection: where a surface is chosen today

- **The agent chooses the tool; the router observes.** `select_form_surface`
  (`attune_forms.bridge`) is called only inside the two form render handlers,
  after the fact, with `chosen=` (`server.py:863-894`). Its docstring names
  itself advisory (architecture review F9). `_route` reads `form`,
  `widget_capable`, `keyboard_mode`; `chosen` reaches only the telemetry
  call — re-verified by reading the installed 0.12.3 source, confirming
  evidence.md's AST check.
- **Capability is never observed server-side.** No call in `src/attune`
  passes `widget_capable` (grep: zero hits), so the router's capability
  floor always evaluates `True`; the only capability signal in the live
  system is which tool the agent invoked. attune-forms exports
  `HostCapabilities` / `ConformanceReceipt` / `ConformanceReport`;
  attune-ai imports none of them (host-surface-parity Task 10 owns that
  wiring; D8 go, not started).
- **Workspace consumers do not route at all.** `command_workspace_open`
  returns BOTH `html` and `markdown` for every render and lets the agent
  present either (spec skill: "Present the returned widget, or its
  returned Markdown verbatim"). There is no per-workspace surface
  decision in code — the choice is guidance.
- **Need selection is guidance only:** the Socratic rule (`.claude/CLAUDE.md`),
  `plugin/skills/elicit/SKILL.md` (batching rule, construct catalogue,
  surface ladder), `.claude/rules/attune/communication-grammar.md` (shape)
  and `decision-routine.md` (when). For `spec`, the need→control mapping
  is already encoded in the adapter's stage machine (see the consumer
  section below); no classifier exists or is needed for the pilot.

### Preferences: the facilities that exist

| Facility | Scope | Semantics | Fit for ASI-2 |
| --- | --- | --- | --- |
| `keyboard_mode` (`attune_forms.bridge.keyboard_mode_enabled` / `set_keyboard_mode`) | **project** (`attune-forms.config.json` > `attune.config.json`), with **shell-session** env override `ATTUNE_FORMS_KEYBOARD_MODE` (legacy `ATTUNE_KEYBOARD_MODE`) in both directions | "terse forms": route expressible forms to `AskUserQuestion`; never drops `number`/`date`/`textarea` (precedence pinned by 29 tests in `tests/unit/elicitation/test_select_form_surface.py`) | NOT "just talk to me" — it still asks, via a flatter control. Not one-interaction scoped. Confirms ASI-2's T1 note: keyboard mode is not the session-wide conversational preference. |
| MCP server `_context` (`context_set` / `context_get`, `server.py:126,724-755`) | **server process** lifetime (dies with the MCP server; in-memory `dict[str, str]`) | free-form key/value | Closest existing home for a session-wide interaction preference with zero new store. Limits: string values only; not read by any render path today; one server instance per host session. |
| Keyboard hint (`maybe_keyboard_hint`, `form_events`) | telemetry threshold | nudges a user who submits many forms toward keyboard mode; never fires for opted-in users | Evidence that a preference nudge already exists; not a preference store. |
| One-interaction override | **none** | — | Today the agent's tool choice IS the per-interaction override. No facility records it as a user preference; a binding check would need a new field (guidance first per ASI-7). |
| Unsubmitted client input recovery | **unverified** | the workspace widget re-renders from canonical state on every revision; no draft persistence was found in `command_workspace.py` or the render dict | ASI-2 requires disclosure, not a promise: treat draft recovery as unavailable until a probe shows otherwise. |

### Host readiness evidence that exists today (ASI-3)

| Host / surface | Interaction | What is established | Receipt | Gap |
| --- | --- | --- | --- | --- |
| Claude desktop app (Code tab), attune-forms plugin MCP 0.12.3, widget via `show_widget` | **form** (progress + decision + multi_select) | rendered, visibly usable (Patrick submitted it), validated by `elicitation_collect_response` | `resp-20260905-150806-0f0dffe9` (this session, 2026-09-05) | paint timing unmeasured; workspace path not exercised on this host in this session |
| Codex native host, standalone Forms | **form** | validated collector reached | `resp-20260905-001239-c2185558` (Codex 30be `native-host-blocker.md`) | workspace instance marker absent until host reload; loaded runtime unverified; no native timing |
| Controlled in-app browser harness, public MCP stdio, merged `c2138be2d` + forms 0.12.3 | **workspace** (roundtable 7-candidate fixture) | 20/20 canonical acceptances joined by workspace/revision/instance; batching cut cumulative acceptance waits | `docs/probes/latency/` (#2421, tracked) + `merged-2026-09-05/` (Codex 30be, uncommitted; PR requested of Codex 2026-09-05) | not a chat host; no model generation; two repeats per condition |
| Headless (this worktree, no host) | **workspace** (`spec`) | see the probe section below | this document | proves semantics, not visibility |

Tier provenance on validated answers (R10, host-surface-parity Task 11) is
not implemented: an answer does not carry which tier rendered it.

**The conformance design ASI-3 refers to already ships in attune-forms**
(0.12.0, IQC Task 2 — handoff `docs/handoffs/codex-iqc-conformance-harness.md`
in that repo): `HostCapabilities(rich_markup, forms, multi_select,
live_updates, postback)`, `run_workspace_conformance`, `ConformanceReport`
/ `ConformanceReceipt`, and `UnavailableReceipt` — the type that keeps an
unobserved host receipt recorded as unavailable rather than inferred
passing. attune-ai calls none of it (grep: zero imports). T3's named-host
receipt should be produced through that harness once Task 10 wires it, not
through a bespoke check. The IQC Task 5 boundaries named in that handoff —
transport acknowledgement, progress delivery, terminal publication, human
dwell — are outside anything T3 or T4 may claim from local render timing.

### Authority: the canonical action path (ASI-4)

`CommandWorkspaceHost.collect` (`command_workspace.py:295-373`) is the only
mutation path for client actions. Per call it: takes the per-workspace lock;
rejects unknown/expired ids, terminal records, adapter mismatch and
adapter-version drift; re-projects the canonical state and rejects if the
view or `contract_hash` changed since render; validates the payload with
`attune_forms.collect_workspace_action` against the rendered view and
binding (revision, `action_nonce`, `contract_hash`, `title`, `view`,
`confirmed`); applies the adapter transition; stores the successor
(revision + 1); THEN emits `log_workspace_stage("accepted", …)`.
`instance_id` from the payload is passed only to that telemetry call —
correlation, not authorization (ASI-4 holds by construction).
`publish` is the trusted adapter-event path; `execution_progress` carries
`authority_changed=False`.

Existing pins: `tests/unit/elicitation/test_command_workspace.py` (17: replay,
altered, stale, concurrent confirmation, projection/contract drift, progress
cannot smuggle authority, acceptance telemetry only after canonical
transition), `test_command_workspace_contract.py` (6), `tests/unit/spec/
test_workspace.py` (16), `tests/unit/roundtable/test_workspace.py` (24).

### Measurement stores that exist (ASI-6)

`attune_forms.form_events`: `log_surface_decision` (surface, reason,
`chosen`, `agreed`, inferred-field counts), `log_form_build` (source
`dict` vs `template:<name>`), `log_form_rendered`, `log_submission`
(`form_id` + `instance_id` join), `log_workspace_stage` (`rendered` /
`accepted`, workspace, revision, instance, adapter, action), read-backs
`stage_latency()` / `workspace_latency()` (the latter includes dwell,
excludes paint — as evidence.md states). Live file on this machine at
probe time: 117 builds (105 `dict`, 4 `elicit-form`, 8 `workspace-action`),
50 renders, 142 submissions, 1 joined pair; workspace: 5 renders, 0
accepted before the headless probes below ran (they emitted `accepted`
rows into the local telemetry file — a side effect to note, not a
measurement).

Not recorded today: the preference source/scope behind a surface choice,
user overrides as such, and clarification turns. Live interaction metrics
are owned by Interaction Quality Contract Task 5 (shared-command-workspaces
requirements, status line) — ASI-6 work must consume, not duplicate.

## Current-behavior probes (run 2026-09-05, this worktree, keyless)

**Suite receipt (serial, `-p no:xdist`):** the five suites above —
`121 passed in 0.71s`.

**Headless spec workspace round trip** (in-memory `CommandWorkspaceHost`
+ `SpecWorkspaceAdapter`, helpers imported from `tests/unit/spec/test_workspace.py`;
a temporary repo for the new-spec path, this worktree for the resume path):

| Probe | Result |
| --- | --- |
| `route=resume` on a real XML plan (`docs/specs/host-surface-parity/tasks.md`, 13 tasks, no persisted state) | opens at stage `executing`, view "Spec in progress", **no actions**, `contract_hash` and `action_nonce` empty, `binding` raises "not awaiting a bound action". Resume is not a choice point. |
| `route=new` preview | actions `edit_spec`, `create_spec` (consequence, `requires_explicit_choice`); hash + nonce set |
| `create_spec` without `confirmed` | rejected: "requires explicit confirmation" |
| replay of the consumed preview nonce | rejected: "not awaiting a bound action" |
| `artifacts_created` → `lifecycle_gate` PASS | stage **review**, title "Spec review", actions `redo_plan`, `approve_plan` (no consequence, no confirm) — the ASI-5 candidate |
| review text fallback | `markdown` ends in the bound JSON payload skeleton (`title`, `view`, `action`, `confirmed`, `workspace_id`, `revision`, `action_nonce`, `contract_hash`); widget `html` 9,272 bytes with `data-workspace-view` |
| stale revision (+3) | rejected: "revision does not match" |
| unknown action `ship_it` | rejected: "not allowed by the rendered view" |
| unknown payload key (`nonce` instead of `action_nonce`) | rejected: "unknown key" — closed payload grammar |
| `approve_plan` on the live render | accepted → revision 4, stage **approval**, actions `redo_plan`, `start_execution` (consequence + explicit choice) |
| re-submitting the superseded review payload | rejected: title mismatch + action not allowed |
| `execution_progress` publish at approval stage | rejected: "Spec progress requires execution stage" — an unrelated progress event cannot displace the pending choice |

Client obligation observed: the echo payload must carry exactly
`__elicitation_response__`, `action`, `action_nonce`, `confirmed`,
`contract_hash`, `revision`, `title`, `view`, `workspace_id`.

## Consumer selection (ASI-5)

**Selected: the `spec` adapter's `review` stage choice** (`redo_plan` /
`approve_plan`). ASI-5's three conditions, checked:

1. **Established fallback** — yes, two of them: the returned Markdown with
   its bound payload skeleton (the agent transcribes the user's words
   into the bound payload and calls `command_workspace_collect_action`),
   and the spec skill's pre-workspace Stage 2 `AskUserQuestion` ("Does
   this plan look right?" — looks good / edit / start over).
2. **Typed validation** — yes: `collect_workspace_action` + adapter
   `apply`; probes above.
3. **Observable canonical acceptance** — yes: successor stored, revision
   advanced, `log_workspace_stage("accepted")` emitted after storage.

It also satisfies ASI-1's pilot trigger: a real, unresolved choice with two
genuine alternatives whose answer is needed for the next step, arising at a
meaningful boundary (plan drafted, gates passed). It carries no
consequence flag, so the trial does not manufacture an approval gate; the
consequential `start_execution` choice one stage later stays confirm-gated
and is NOT part of the trial.

Rejected alternatives: `roundtable.apply_rulings` (atomic batch with
response fields — richer than the first trial needs and mid-measurement
by Codex); the `spec` preview (`create_spec` is consequential — trialling
it would violate ASI-5's "do not create consequential work solely to test
an approval"); `resume` (no choice at all, see probe).

## Existing capability versus demonstrated gap, per requirement

| Req | Already satisfied by | Demonstrated gap (or none) | Where it belongs |
| --- | --- | --- | --- |
| ASI-1 | spec stage machine + skill/rule guidance | none for the pilot; guidance is dual-path (see ASI-4 row) | T2 guidance |
| ASI-2 | keyboard mode (project + env) | no session-wide "conversation" preference; no one-interaction override record; draft recovery unverified → disclose | T2: propose `_context` as the minimal owner/lifetime; guidance first |
| ASI-3 | `mcp_app` advertisement; the three host receipts above | capability never observed server-side; no tier provenance on answers (R10) | host-surface-parity Tasks 10/11 (do not duplicate) |
| ASI-4 | `CommandWorkspaceHost.collect` — probed | none in code. Guidance gap: the spec skill's Stage 2 `AskUserQuestion` review path runs beside the workspace path; when the workspace is open, a spoken "looks good" must be transcribed into the bound `approve_plan` payload, not acted on directly | T2 guidance (skill master + mirror reprojection) |
| ASI-5 | `spec` review stage — selected | none | T3 readiness receipts on the named host |
| ASI-6 | form_events stores + read-backs | preference source/scope, overrides and clarification turns are not recorded; IQC Task 5 owns live metrics | T4 protocol (freeze before collection) |
| ASI-7 | owners mapped above | in-flight overlap: host-surface-parity Tasks 10/11 (D8 go), Codex merged-build receipts (uncommitted), IQC Task 5 | reconcile at each task's go |

## Baseline and named host for T3/T4 (recorded now, frozen at T4's go)

- Baseline = the `spec` review choice as presented today: the agent picks
  widget or Markdown from the `command_workspace_open` result by the
  skill's guidance; the user answers through the widget's bound action
  or by words the agent transcribes.
- Named host = Claude desktop app (Code tab) with the attune-ai plugin MCP
  server; the widget path renders through the host's `show_widget`. This
  is the only host with a same-day validated form round trip observed by a
  named human (Patrick, this session). The workspace path on this host has
  no receipt yet — T3's first job.

## Research premises checked against the code (attune-forms `docs/research/`)

The attune-forms research corpus (`authority-envelope.md`,
`interaction-benchmark-v0.md`, `implementation-status.md`, the AF-1 evidence
record and its SHA-256 manifest) was read for this inventory. Two things
carry over; the rest is context.

**Authority envelope: the five candidate scenarios map onto today's host.**
The concept paper is explicitly "not a runtime API", but its invariants are
what `CommandWorkspaceHost` already enforces, and its scenarios are the
probes T3 should keep:

| Envelope scenario | Status in the `spec` consumer |
| --- | --- |
| Stale approval | probed: stale revision rejected; contract-hash drift rejected before `apply` |
| Replay | probed: consumed `action_nonce` rejected |
| Conversational ambiguity ("looks good" with a pending action) | the ASI-4 guidance gap above — the host cannot see the words; the skill must transcribe them into the bound payload or not act |
| Cross-surface parity | widget and Markdown carry the same binding (probe: the Markdown skeleton holds the same `revision` / `action_nonce` / `contract_hash`); host-surface-parity R2/R10 own the drift guard and provenance |
| Scope confusion (staging vs production) | not applicable: the `spec` adapter has no scope dimension; leave to a consumer that does |

**Benchmark v0: its publication rule bounds what this document claims.**
The benchmark distinguishes conformance, software-correctness, and
behavioral evidence. Everything in this inventory is software-correctness
evidence plus three conformance-class host receipts. No behavioral claim
(that the widget helps, that batching is faster for a human) is made or
supported here; that is T4's job, under ASI-6's preregistration, which
mirrors the benchmark's own controls (declared success criteria, recorded
model/host, missing data reported). The benchmark itself stays blocked at
Checkpoint B.1 (chair-required; provider fields blank; zero API budget) and
is independent of this ladder — it must not be reverse-fit to the pilot.

## What T1 did not do

No code, skill, rule, or dependency changed. No provider call. No host
trial. The headless probes mutated only in-memory state and appended a few
`rendered`/`accepted` rows to the local telemetry file. Chair acceptance of
this inventory, then a separate T2 go, precede any change.
