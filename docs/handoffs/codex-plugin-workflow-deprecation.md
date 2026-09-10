# Agent work handoff

## Goal

Deprecate the obsolete plugin analyzer base compatibly for issue #2238.

## Acceptance criteria

Existing analyzers still execute; construction emits an actionable warning;
bundled plugin discovery returns engine workflows; required CI passes.

## Scope and assumptions

- Branch/worktree: codex/plugin-workflow-deprecation in /private/tmp/attune-plugin-workflow-deprecation.
- Provider/session: Codex, advisory to Patrick.
- Assumptions: public class removal remains a major-release decision.

## Current state

- Status: implementation and focused tests pass; review findings fixed; publication pending.
- Changed files: plugin base, plugin tests, changelog.
- Decisions: preserve exports, abstract methods, and registration behavior.
- Risks or open questions: public removal remains a major-release decision.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Plugin behavior retained | keyless pytest tests/plugins tests/unit/plugins tests/unit/workflows/test_entry_point_groups.py -n 0 --no-cov | 234 passed, 3 skipped |
| Changed module meets coverage floor | keyless pytest tests/plugins tests/unit/plugins/test_registry_coverage.py -n 0 --cov=attune.plugins.base --cov-fail-under=85 | 234 passed, 3 skipped; 98.78% |
| Changelog order correct | scripts/consolidate_changelog.py Unreleased --check | passed |

## Next action

Finish independent review, publish PR, verify required CI, and retire this handoff.
