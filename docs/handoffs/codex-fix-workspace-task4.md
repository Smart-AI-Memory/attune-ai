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
  binding seam is locally committed in `attune-forms` at `b0ce424` as
  proposed 0.9.1; downstream development may use that local source,
  but no downstream PR may claim the dependency until 0.9.1 is
  reviewed, merged, and published.

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
  nothing. Publishing `attune-forms` 0.9.1 remains an explicit chair gate.
  The environment requires a new explicit authorization before it will send
  these private diffs to Antigravity for the approved advisory review.

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
| External review dispatch | Antigravity cross-review | blocked — specific private-diff transmission authorization required |

## Next action

Receive the specific Antigravity diff-sharing authorization, run advisory
review on both branches, disposition verified findings, then publish the
reviewed `attune-forms` 0.9.1 only after the separate release approval.
