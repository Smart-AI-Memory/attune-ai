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

### Artifact selection

- Match the artifact to the work before non-trivial implementation and
  name the selected tier in the session contract:
  - **Inline edit** — trivial, one file, no ambiguity.
  - **Structured one-shot** — single-session work framed by a goal,
    constraints, and acceptance criteria.
  - **XML task** — dependent work across three or more files, or work
    that must be executable as a cold handoff.
  - **Spec** — multi-session or multi-PR work, design ambiguity, or an
    irreversible choice.
- Escalate the artifact tier when ambiguity or dependencies grow; do
  not add ceremony to work that still fits a smaller tier.

### Verification receipts

- Before implementation, name the claim and a probe that would fail if
  the claim were false. Report the probe actually run and its result.
- Treat unit tests as evidence only inside their tested boundaries.
  Hooks, persistence, networking, packaging, and other external seams
  require a non-mocked round trip through the real boundary.
- “Configured,” “registered,” and “exited successfully” are not
  working receipts. Prefer evidence of the user-visible behavior.

### Handoffs

- For multi-step work, create or update a portable handoff from
  `templates/agent-handoff.md` at `docs/handoffs/<branch-slug>.md`
  (slug = branch name with `/` replaced by `-`), tracked on the
  branch. Delete the file when the branch merges.
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

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| <!-- behavior claimed --> | <!-- command or live check actually run --> | <!-- pass / fail / not run --> |

## Next action

<!-- One concrete, ordered action for the receiving agent. -->
