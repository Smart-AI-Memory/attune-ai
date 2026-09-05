# Adaptive session interactions — Evidence

## Scope and source snapshots

Planning source snapshot: 3588c5487e641925b9617035abb483b1b936d616.
Preservation base: be15968fa2259d9fdc15d8e5eb8af70261d866a0 (fetched origin/main, 2026-09-05).
The inspected path diff between those revisions was empty. Future execution
must inspect its own checkout and active work; this is a dated source record,
not an assertion that a later runtime is unchanged.

| Pack item | Source and observation | Limit |
| --- | --- | --- |
| E1 | [Elicitation bridge](../../../src/attune/elicitation/__init__.py), [elicit skill](../../../plugin/skills/elicit/SKILL.md), [communication grammar](../../../.claude/rules/attune/communication-grammar.md): existing forms boundary and interaction guidance | Guidance alone does not prove consistent invocation |
| E2 | [MCP server](../../../src/attune/mcp/server.py): widget handler calls _record_surface_choice with chosen=widget after tool selection | Recommendation is advisory there; no new selector presumed necessary |
| E3 | [Command workspace host](../../../src/attune/elicitation/command_workspace.py): CommandWorkspaceHost.collect owns canonical action validation; [spec adapter](../../../src/attune/spec/workspace.py) reuses it | Source presence is not a complete host safety receipt |
| E4 | Existing [release/machine receipts](../../probes/latency/release-machine-receipts.json) and [latency probe notes](../../probes/latency/README.md) retain the earlier forms integration evidence | Package/import/HTML checks do not establish native visibility or usefulness |
| E5 | [Host parity requirements](../host-surface-parity/requirements.md), [intake tasks](../workflow-intake-forms/tasks.md), [workspace requirements](../shared-command-workspaces/requirements.md) define existing ownership | Spec/task prose is not proof of shipped behavior |
| E6 | [Chair decisions](decisions.md): all seven requirements approved; commit-only exception to repo freeze | No feature task is authorized |
| E7 | [Task reader](../../../src/attune/pipeline/spec_reader.py), [decomposer](../../../src/attune/wizards/decomposer.py), [state](../../../src/attune/spec/state.py): real resume/document seams | Document validation does not execute or validate the feature |

## Installed dependency source check (2026-09-05)

A direct distribution metadata read in the main checkout's existing Python
environment reported attune-forms 0.12.3. Installed bridge.py defines
select_form_surface; its routing call uses form, widget_capable and
keyboard_mode, while chosen is used afterward for agreement/logging.
Installed form_events.py defines log_workspace_stage and workspace_latency;
the latter explicitly includes dwell and excludes paint. This is installed
source evidence, not a claim about a running Claude process.

| File | SHA-256 of inspected bytes |
| --- | --- |
| attune_forms/bridge.py | db7b47cee8cc144d4149dd9007b9f8ffaf5b25184fa337aefa0a240bb0f47fed |
| attune_forms/form_events.py | 1ff428b80058fb6f933822bb3891ed52df35ba9c133a16f6b2117c4001e9ef6f |

## Review coverage and limits

One round, three CLI returns, one compiler-clean critique. Antigravity's
ready-with-edits response counted. Claude's response failed target-heading
grammar; Codex's failed the required pack/file citation form. Those raw
responses remain local, excluded from consensus. No retry exceeded the
three-invocation cap. The seven requirements were then approved individually.
Round durations are not form latency data.

A separate read-only preservation review found four real document issues:
missing mapping context, stale status/provenance, parsed-away task contexts,
and lifecycle/resume ambiguity. The corrections are recorded in D4. The
integrating seat verified those corrections centrally; receipts follow.

## Preservation verification

Checks executed on 2026-09-05 in the isolated preservation worktree:

| Claim | Probe actually run | Result |
| --- | --- | --- |
| Approved content and context preserved | Existing compiler parse_draft against local approved artifact; body equality for ASI-1 through ASI-7; original mapping equality | 7/7 bodies identical; table identical |
| Final requirement shape valid | Existing compiler lint_final on requirements.md | No findings |
| Future parser retains the ladder | read_spec comparison to the original five XML blocks: IDs, names, copied context in objectives, validation checks and dependencies | 5/5 preserved; dependencies none, 1, 2, 3, 4 |
| No execution state implied | load_state of tasks.md | None; no completed/current/auto-run state written |
| Lifecycle status is legible | status_line_gate on this spec directory | PASS; highest phase parked, Resume-Trigger present |
| Package links are portable | Resolve every relative Markdown file target in all five spec files | 32/32 resolve |
| Installed routing does not consume chosen | AST inspection of select_form_surface's _route call | One route call; chosen absent from its arguments |
| Requirements boundary accepts the documents | run_boundary, phase requirements, this slug and five actual spec paths, no waivers | symbol-reality, falsifiability, format-lint all PASS |
| Tasks boundary accepts the documents | run_boundary, phase tasks, same paths, no waivers | symbol-reality and falsifiability both PASS |
| Status and ledger guards accept this tree | Serial keyless targeted pytest command below | 105 passed in 0.30 s |
| Pinned commit checks accept the seven intended files | pre-commit run --files over this package, branch handoff and R5 ledger | All applicable hooks passed; code-only hooks skipped |

The boundary probes used the existing runner directly and wrote its receipt
ledger to a temporary local file. They used the docs-only preservation paths,
not an invented future implementation scope. Execution gates must run again
against actual implementation paths after the appropriate task go.

Targeted test invocation (existing interpreter, no environment sync):

```text
PYTHONPATH=src ANTHROPIC_API_KEY='' python -B -m pytest tests/unit/gates/test_status_line_gate.py tests/unit/scripts/test_ledger_precision.py tests/unit/gates/test_ledger_rejection_format.py tests/unit/gates/test_ledger_countersign_format.py -q -p no:xdist -p no:cacheprovider -o addopts=
```

No feature implementation, host trial, renderer optimization, or production
behavior test is claimed by these document checks. Review coverage remains
one compiler-clean roundtable seat; the later preservation review checked
packaging only and does not increase product-design consensus.

## T1 inventory (2026-09-05, accepted — decisions D6)

The T1 reconcile-and-characterize inventory, run read-only from the
execution checkout with headless probes and a serial suite receipt, is
[`t1-inventory.md`](t1-inventory.md). It selects the `spec` review-stage
choice as the ASI-5 consumer and records existing capability versus
demonstrated gap per requirement. The chair accepted T1 the same day (D6).

## T2 execution record (2026-09-05, pending chair acceptance)

Scope executed under the D6 go: guidance only, no source change. Files:
`plugin/skills/spec/SKILL.md` (new "The review choice — adaptive default"
section), `plugin/skills/elicit/SKILL.md` (new "Scoped preferences"
section naming the session store and the markdown text lane), both
`.agents/skills/` mirrors reprojected with `scripts/sync_agents_skills.py
--write`, `design.md` (open choices 1–2 resolved; preference facility
proposed: MCP session context, key `interaction_preference`, process
lifetime), `tasks.md` (status flipped to active; spec-state comment now
`completed: ["1"], current: "2"` via `attune.spec.save_state`), and
`tests/unit/spec/test_adaptive_review_guidance.py`.

| Claim | Probe actually run | Result |
| --- | --- | --- |
| The four behavioral cases are pinned | new test file: guidance sentences in both masters and both mirrors; review stage = two non-consequential alternatives; Markdown skeleton carries the binding; a settled choice cannot be re-submitted; `context_set`/`context_get` round trip is process-scoped | 18 passed |
| Mirrors are in sync | `tests/unit/plugins/test_sync_agents_skills.py` | passed (serial) |
| Skill tool references resolve | `tests/unit/plugins/test_plugin_reference_validation.py` | passed |
| Consumer behavior unchanged | `tests/unit/spec/test_workspace.py` | 16 passed |
| Ratchets and doc gates accept the tree | `tests/unit/gates`, `test_generated_doc_import_drift.py`, `test_status_line_gate.py` | passed (see the PR for the exact tail) |
| Pinned hooks | pre-commit over every changed file | all applicable hooks passed |

Not established by T2: that any host honors the guidance live. That is
T3's receipt (named host round trip through the review choice on both
lanes), and it has no go yet.

## T3 execution record (2026-09-05, pending chair acceptance)

Scope executed under the D7 go: the `spec` review choice connected to the
host and canonical-state boundaries on the NAMED host, both lanes, with
the ASI-3/ASI-4 probes run against the live server. No source change.

### Host and runtime (recorded, not inferred)

| Item | Value | How known |
| --- | --- | --- |
| Host | Claude desktop app, Code tab, session worktree `resume-attune-forms-planning-a3179d` | this session |
| attune-ai MCP server | the plugin server this session started: `.venv/bin/python -m attune.mcp.server` from the worktree venv | `ps` parent chain to this session's `uv run` |
| attune-ai source the server imports | this worktree's `src/` (tree `be15968fa`; no `src/` change since) | `attune.__file__` under that interpreter |
| Python / attune-forms | 3.11.14 / 0.12.3 (installed distribution) | `importlib.metadata` under that interpreter |
| Rendering path | `command_workspace_open` HTML passed to the host's `show_widget`; the widget posts the bound payload back through the conversation; `command_workspace_collect_action` consumes it | tool log |
| Named human observer | Patrick (submitted the widget lane himself) | this session |

### Widget lane — actual-host round trip (workspace `spec-c7e5fc780bdc40ed9e75807206996839`)

| Step | Receipt |
| --- | --- |
| `route=new` opened (rev 0, instance `cc0e29bc…`) | `workspace_rendered` telemetry row 19:59:55Z |
| `create_spec` confirmed and accepted (rev 0 → 1) | `workspace_accepted` 20:00:28Z; result delegates `spec.create`; no spec files were created — the delegate is the agent's to act on and T3 declined to (ASI-5: no consequential work solely to test an approval) |
| `artifacts_created` published pointing at the REAL plan (`docs/specs/adaptive-session-interactions/tasks.md`, tasks 1–5) | rev 2, `gate_running` |
| `lifecycle_gate` published with the REAL receipts of `attune gates check tasks --spec adaptive-session-interactions` run 2026-09-05 (symbol-reality `3d7ca78131fc` PASS, falsifiability `c51170db1332` PASS) | rev 3, **review** stage, actions `redo_plan` / `approve_plan`; `workspace_rendered` 20:00:53Z instance `73ac1b79…` |
| Widget shown to the user | tool return 20:01:30Z — a tool-return time, **not paint** |
| User clicked **Approve plan** (named human: Patrick) | payload arrived at the agent 20:02:22Z; `command_workspace_collect_action` accepted it; `workspace_accepted` 20:02:22.536Z rev 3 instance `73ac1b79…` action `approve_plan`; successor rev 4 = **approval** stage rendered (instance `682d2543…`) |

Dwell between the render event and acceptance was 89 s and includes the
agent's own turn and the human's reading; it is not a paint or a
usability number. Paint timing on this host: **unmeasured** (no host
observation boundary). Usability: **attested** by the named human who
completed the control, per ASI-3.

### Probes against the live server (ASI-4), all after the accepted click

| Probe | Result |
| --- | --- |
| Replay the consumed review payload (rev 3 nonce) | rejected: title mismatch, action not allowed by the rendered view, revision / nonce / contract-hash mismatch |
| Stale revision (rev 2) with the live nonce and hash | rejected: revision does not match |
| Unknown action `ship_it` on the live binding | rejected: not allowed by the rendered view |
| `execution_progress` published while the approval choice is pending | rejected: "Spec progress requires execution stage" — an unrelated progress event cannot displace the pending choice |
| Canonical answer preserved | the successor view is the approval stage; the review choice cannot be re-answered (replay above) |
| `instance_id` is correlation only | it appears in telemetry rows and nowhere in the acceptance decision (the stale/replay probes carried the correct instance and were still rejected) |

### Unavailable surface (ASI-3)

`elicitation_ask` (native MCP elicitation) on this host returned
`{"success": false, "action": "decline"}` with **no dialog rendered** —
the auto-declined host path the requirement names, distinguishable from
an observed user rejection (the user saw nothing). The fallback (widget
lane above; Markdown lane below) completed the interaction; nothing was
discarded.

### Scoped preference facility on the named host (ASI-2)

`context_get interaction_preference` → not found (the default, no inferred
opt-out); `context_set … conversation` → `context_get` returned
`conversation`; reset to `default` afterwards. The facility T2 named
round-trips on the live server for this session.

### Draft recovery (ASI-2)

The workspace widget HTML contains no client draft mechanism
(`localStorage` / `sessionStorage` / `indexedDB` / `beforeunload` /
autosave: zero occurrences); re-render always comes from canonical state.
**Unsubmitted client input is NOT recoverable on this host** — recorded
as a disclosed limit, not promised.

### Markdown lane — actual-host round trip (workspace `spec-dcc3e8ef7acc403fbafba3b545b2d0bb`)

Driven to the review stage by the same chain (real plan, real gate
receipts; rev 3, instance `d9850419…`). The returned Markdown was
presented verbatim and the user was asked to answer in words.
The user answered **"approve"** in words (20:11:28Z, agent side). The agent
transcribed it into the bound payload from the returned skeleton
(`workspace_id`, `revision` 3, `action_nonce` `SmXPPpmV…`, `contract_hash`
`5d8deddc…`, `title`, `view`, `action: approve_plan`, `confirmed: false`,
`instance_id` `d9850419…`) and submitted it through
`command_workspace_collect_action`: **accepted**, revision 3 → 4, successor
= approval stage (instance `3ec4323f…`). Same collector, same binding
grammar, same acceptance semantics as the widget lane — the spoken word
authorized nothing by itself; only the transcribed, bound, validated
payload advanced the revision (ASI-4). No `start_execution` was submitted
on either workspace.

### Not established by T3

Paint timing on any host; usefulness of the automatic default (T4); any
host other than the one named above; native-dialog rendering on this host
(observed: auto-decline). Telemetry rows written by these probes live in
the local `form_events.jsonl`; they are receipts, not measurements.
