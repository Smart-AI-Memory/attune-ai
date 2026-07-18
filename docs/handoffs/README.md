# Agent handoffs

Per-branch portable handoffs (cross-provider collaboration
contract, D1). One file per active branch:

- Path: `docs/handoffs/<branch-slug>.md`, where the slug is the
  branch name with `/` replaced by `-`
  (`codex/using-projectors` -> `codex-using-projectors.md`).
- Created from `templates/agent-handoff.md` (projected from
  `content/collaboration/contract.md` - do not hand-edit the
  template).
- Tracked on the branch so any agent can discover it from the
  branch name alone; deleted when the branch merges.

A handoff is context, not authority: the receiving agent verifies
it against Git state and tests before continuing.
