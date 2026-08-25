# Agent work handoff

## Goal

#2239 slice 1 shipped: SDK adapter core + `sdk_errors` live in the
models layer, `attune.models` imports zero `attune.workflows`
modules, workflows-layer importers unchanged behind facades; the
remainder (Edge 1 / `WorkflowConfig` / flat cluster) owned by the
`models-workflows-layering` spec draft.

## Acceptance criteria

- Full test tree green locally (`pytest tests`), CI green on the PR.
- Subprocess layering probe passes
  (`tests/unit/models/test_sdk_adapter_layering.py`).
- Spec draft at `docs/specs/models-workflows-layering/requirements.md`
  awaiting chair review.

## Scope and assumptions

- Branch/worktree: `claude/closing-issues-6590d0` at
  `.claude/worktrees/closing-issues-6590d0`
- Provider/session: Claude (lead), chair-approved via form:
  "Slice 1 now + spec the rest".
- Assumptions: chair reads the PR (lead-authored src diff → D11
  risk-class check: refactor of persistence-adjacent SDK plumbing —
  different-model review lane recommended before merge).

## Current state

- Status: implementation complete, full-suite run in flight.
- Changed files: `git mv` `workflows/sdk_errors.py` →
  `models/sdk_errors.py`, `workflows/agent_sdk_adapter.py` →
  `models/sdk_adapter.py` (core trimmed to used imports); new
  facades at both old paths; `models/single_turn.py` eager import
  (lazy layering import removed); `workflows/sdk_output_parser.py`
  TYPE_CHECKING repoint; test patch-target migrations
  (`test_iter_agent_messages`, `test_agent_sdk_adapter`,
  `test_task_budget_wiring`, `test_subagent_transcripts`,
  `test_sdk_error_fidelity*`, `test_sdk_error_no_signal_stderr`);
  ratchet baselines updated (broad-except path swap,
  path-validation allowlist swap); query-loop drift guard now scans
  workflows + models; new
  `tests/unit/models/test_sdk_adapter_layering.py`; CHANGELOG entry;
  spec draft.
- Decisions: facades KEPT (not deleted) — docs/doc-import gate and
  external importers; mutable cache `_CLI_SUPPORTS_TASK_BUDGET`
  deliberately NOT re-exported on the facade (stale-snapshot trap),
  pinned by test.
- Risks or open questions: none known beyond CI; the 15 fidelity
  phase-test failures seen mid-migration were the expected
  vacuous-patch class and were fixed by repointing string targets to
  `attune.models.sdk_errors`.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| models imports no workflows | subprocess import probe (layering test) | pass |
| facade/shim identity | identity assertions (layering test) | pass |
| affected suites green | 234 tests serially (adapter, fidelity, gates) | pass |
| full tree green | `pytest tests` (background run) | in flight |

## Next action

Verify the full-suite result, commit (message via `git commit -F`),
push, open the PR referencing #2239, run the D11 different-model
review lane, then delete this file when the branch merges.
