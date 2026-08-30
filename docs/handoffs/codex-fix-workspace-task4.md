# Agent work handoff

## Goal

Deliver the approved Fix command-workspace Task 4, beginning with a
safe preview/action round trip bound to the exact canonical contract.

## Acceptance criteria

- The plugin exposes a real workspace render/collect surface.
- `FixWorkspaceState` is JSON-serializable and restores validated intake.
- Preview executes nothing and carries a deterministic contract hash.
- Edit invalidates approval; stale, mutated, unknown, or replayed Run
  actions fail closed.
- Existing `attune fix` flags, derivations, execution path, and exit
  codes remain backward compatible.
- Targeted tests, changed-code coverage, lint, pre-commit, and a
  non-mocked render/action receipt pass.

## Scope and assumptions

- Branch/worktree: `codex/fix-workspace-task4` in
  `attune-ai-fix-workspace-task4`.
- Provider/session: Codex GPT-5.6 Sol, Extra High; Patrick is chair;
  no paid model calls or live Fix execution authorized.
- Assumptions: PR:2354 and PR:2371 are merged. The generic workspace
  binding seam shipped from attune-forms PR:64 at merge `83501ae6` and
  is published on PyPI as 0.9.1. The downstream floor and lock now resolve
  that released package directly.

## Current state

- Status: the first end-to-end dynamic preview/action slice is implemented
  and locally verified. Intake no longer carries an execution choice; the MCP
  host builds and stores canonical preview state, renders widget + Markdown
  projections, recomputes the contract at action time, and consumes one-time
  approval.
- Changed files: Fix structured DTOs, new `fix_workspace` authority module,
  intake, MCP schemas/handlers, Fix skill, architecture/changelog, and focused
  tests.
- Decisions: renderers are disposable projections; canonical state and
  Fix command authority remain in `attune-ai`. The client-provided hash
  is checked evidence, never authority.
- Risks or open questions: execution has no truthful four-stage event
  seam yet; Task 4A does not fabricate progress and its validator executes
  nothing. Antigravity's advisory review is complete and clean. The upstream
  dependency gate is closed; downstream PR promotion is now safe.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Task 3 dependency merged | `gh pr view 2371 --json state,mergeCommit` | pass — merged as `844e1a01` |
| Other active Fix PR merged | `gh pr view 2354 --json state,mergeCommit` | pass — merged as `bcf627d8` |
| Upstream action-binding slice is green | `python -m pytest -q` in `attune-forms-fix-workspace` | pass — 874 tests |
| Upstream package builds | `python -m build` | pass — 0.9.1 sdist and wheel |
| Focused Fix + MCP compatibility | targeted eight-file pytest set | pass — 207 tests |
| Post-refactor regression closure | sync, complexity, MCP count, and workspace tests | pass — 105 tests |
| Authority slice coverage | serial pytest + branch coverage | pass — 86.66%, 129 tests; 85% required |
| Complete keyless suite | `pytest -q --ignore=tests/memory/test_redis_integration.py` | pass — 24,971 passed, 232 skipped, 4 xfailed |
| Repository gates | `pre-commit run --all-files` | pass — all blocking hooks green; unrelated broken-link warnings remain non-blocking |
| Upstream external review | Antigravity branch review | clean — 11 sent, 0 omitted, 0 findings |
| Downstream external review | Antigravity branch review + scoped re-lane | clean — 10 primary + 13 scoped substantive files, 0 findings; generated mirrors covered by freshness gates |
| Upstream release | PR:64 + signed `v0.9.1` + PyPI simple index | pass — merge `83501ae6`; wheel and sdist published |
| Released dependency import | `.venv/bin/python` import receipt | pass — attune-forms 0.9.1 and workspace APIs imported from site-packages |
| Final released-dependency suite | `.venv/bin/python -m pytest -q --ignore=tests/memory/test_redis_integration.py` | pass — 24,985 passed, 231 skipped, 4 xfailed |

## Next action

Commit the released dependency floor/lock, push the rebased feature branch,
open the `attune-ai` PR, and merge only after all required checks pass.
