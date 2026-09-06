# Agent work handoff

## Goal

Complete Host Surface Parity Task 0 without production changes: characterize
the current form tiers, fixed Roundtable roster gates, and collaboration
projector refusal behavior.

## Acceptance criteria

- The audit demo reaches the RICH widget DOM, PORTABLE Markdown parser, and
  HEADLESS native MCP elicitation handler with identical validated responses.
- `CANONICAL_SEATS`, `SEAT_RECIPES`, `PLAN_ONLY_SEATS`, the invocation-cap
  refusal, and `round_complete` roster behavior are pinned exactly.
- A hand edit inside a valid collaboration marker block is reported stale.
- Lifecycle gates, targeted tests, formatting, lint, and projector drift check
  pass; no production file changes.

## Scope and assumptions

- Branch/worktree: `codex/host-surface-parity-task0` at
  `/private/tmp/attune-host-surface-parity-task0-20260904`
- Provider/session: Codex lead; local different-model D11 review by GPT-5.4;
  no external provider workflow launched.
- Assumptions: Task 0 only is authorized. Task 1 still requires a separate
  chair go.

## Current state

- Status: implementation complete and uncommitted; awaiting chair acceptance.
- Changed files:
  - `tests/unit/elicitation/test_surface_tiers_characterization.py`
  - `tests/unit/roundtable/test_roster_characterization.py`
  - `tests/unit/scripts/test_project_collaboration_contract.py`
  - `docs/specs/host-surface-parity/tasks.md`
  - `docs/specs/host-surface-parity/decisions.md`
  - `docs/specs/cross-review/receipts.md`
  - `docs/handoffs/codex-host-surface-parity-task0.md`
- Decisions: the Task 0 manifest now names the projector regression because
  the earlier claim that it already existed was false. Slash-compressed
  conformance type citations were expanded to their real exported symbols so
  the symbol-reality gate can verify them.
- Risks or open questions: the RICH test intentionally reuses the standing
  widget DOM simulator from `test_widget_roundtrip.py`; this is test-only
  coupling to the existing renderer receipt, not a production dependency.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| All Task 0 and adjacent seams pass | `.venv/bin/python -m pytest tests/unit/elicitation/test_surface_tiers_characterization.py tests/unit/roundtable/test_roster_characterization.py tests/unit/scripts/test_project_collaboration_contract.py tests/unit/roundtable/test_workspace.py tests/unit/mcp/handlers/test_elicitation_ask.py -q` | 69 passed |
| Task 0 parses and passes the spec pipeline's test path | `PipelineOrchestrator(..., skip_gates=True, skip_simplify=True).run_gates_for_task(task_0)` | `tests_passed=True`, `cost=0.0`; API-backed stages skipped under D8 |
| Execution and verification boundaries remain open | `attune gates check execution|verification --spec host-surface-parity --changed <Task 0 paths>` | symbol-reality and falsifiability PASS at both boundaries |
| Projected instruction files have no drift | `.venv/bin/python scripts/project_collaboration_contract.py --check` | all four targets unchanged |
| Python test changes meet repository style | pinned Black pre-commit hook plus `.venv/bin/ruff check <three test paths>` | PASS |
| D11 review found no unresolved issue | GPT-5.4 read-only re-lane over the full five-path implementation manifest | 0 findings after two accepted fixes |
| Production remains untouched | `git diff --name-only` plus untracked-file inventory | no `src/`, `plugin/`, or production package path |

## Next action

Review and land Task 0. Do not begin Task 1 without its separate chair go.
