# Cross-Provider Collaboration Projector — Requirements

**Status:** active (2026-07-18) — D1–D6 all ratified by Patrick
(option a in each; see [decisions.md](decisions.md)). Implementation state is recorded
honestly: R1–R6 are already implemented on `codex/using-projectors`;
R7+ are open pending decisions.

## Problem

Claude Code and Codex/ChatGPT tools collaborate in this repo but load
different instruction files (Claude: `.claude/CLAUDE.md`; Codex:
repo-root `AGENTS.md` + `~/.codex/AGENTS.md`). A shared operating
contract hand-copied into both surfaces drifts. The projector makes
one master authoritative and mechanically synchronized.

## Requirements — implemented (receipts in design.md)

- **R1** One master, `content/collaboration/contract.md`, owns the
  shared contract and the portable handoff template. Projected
  surfaces are never hand-edited.
- **R2** The contract section projects into a marker-delimited block
  (`<!-- attune:collaboration:start/end -->`) in `AGENTS.md` and
  `.claude/CLAUDE.md`; content outside the markers is preserved
  byte-for-byte.
- **R3** The handoff template projects whole-file to
  `templates/agent-handoff.md`.
- **R4** `--check` reports drift (exit 1, naming stale files) without
  writing.
- **R5** Security: every path is repo-contained after symlink
  resolution; escapes raise before any I/O.
- **R6** Failure containment: all targets are read and validated
  before any write (preflight), so a malformed later target (e.g.
  broken markers in `.claude/CLAUDE.md`) leaves earlier targets
  (`AGENTS.md`) untouched. Reruns are idempotent and self-healing
  after a partial write.

## Requirements — ratified, not yet implemented

- **R7** (D3) The drift gate is enforced on a named surface (CI
  and/or pre-commit) — currently `--check` exists but nothing runs it.
- **R8** (D2) Projected blocks carry a visible generated-source
  notice so readers of AGENTS.md/CLAUDE.md don't hand-edit them.
- **R9** (D1) Completed handoffs have a canonical home and discovery
  rule both agents share.
- **R10** (D4) Master parsing policy for duplicate/misordered
  required headings is explicit (reject vs. last-wins).

## Acceptance criteria (failure-sensitive)

- AC-1 Malformed Claude target → projector exits 1 AND `AGENTS.md`
  is byte-identical to its pre-run state (already covered by
  `invalid_claude_target_does_not_partially_update_agents`).
- AC-2 Symlinked target resolving outside the repo → exits 1, no
  write (covered by `rejects_symlinked_target_outside_repository`).
- AC-3 Zero or duplicate marker pairs in a target → exits 1 naming
  the file (covered).
- AC-4 Master edit without re-projection → the R7 gate fails the
  commit/PR naming the stale file (open until D3 lands).
- AC-5 Real-CLI receipt: `python scripts/project_collaboration_contract.py
  --check` exits 0 on a synchronized tree — run as a command, not
  only through unit imports.
- AC-6 Cross-platform: the focused test file passes on the Windows
  CI lane (paths, newlines, symlink test skips gracefully where
  unsupported).
