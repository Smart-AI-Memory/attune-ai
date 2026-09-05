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
