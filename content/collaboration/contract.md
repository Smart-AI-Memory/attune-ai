# Cross-Provider Collaboration Contract

This is the single source for the collaboration contract shared by
Codex/ChatGPT tools and Claude in this repository. Edit this master,
then run `python scripts/project_collaboration_contract.py`; do not
hand-edit its projected blocks or the handoff template.

## Shared contract

### Shared truth

- Treat the current worktree, Git state, and relevant test results as
  authoritative. Do not rely on hidden chat context for a handoff.
- Preserve unrelated working-tree changes and do not touch another
  agent's worktree.
- Discover capabilities from the available tools, MCP server, and
  tracked skills; do not rely on hard-coded capability counts.

### Session protocol

- State the goal, acceptance criteria, assumptions, and intended
  verification before non-trivial implementation.
- Prefer existing repository conventions and public interfaces before
  adding a parallel mechanism.
- Keep provider-specific setup in adapters. The shared contract must
  still work when only one provider is available.

### Handoffs

- For multi-step work, create or update a portable handoff from
  `templates/agent-handoff.md` in the branch or task's tracked work.
- A receiving agent verifies the handoff against the current Git state
  and tests before continuing; a handoff is context, not authority.
- Record only concrete evidence: commands actually run, their results,
  changed files, unresolved risks, and the next action.

## Portable handoff template

# Agent work handoff

## Goal

<!-- What should be true when this work is complete? -->

## Acceptance criteria

<!-- Concrete conditions that demonstrate completion. -->

## Scope and assumptions

- Branch/worktree:
- Provider/session:
- Assumptions:

## Current state

- Status:
- Changed files:
- Decisions:
- Risks or open questions:

## Verification

| Command | Result |
| --- | --- |
| <!-- command actually run --> | <!-- pass / fail / not run --> |

## Next action

<!-- One concrete, ordered action for the receiving agent. -->
