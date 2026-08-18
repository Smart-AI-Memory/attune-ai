# Agent work handoff

## Goal

Ship the session-start-integrity spec (approved chair 2026-08-18;
D1–D3 ratified; OQ1 ruled RETIRE) — the three roundtable
recommendations from thread q-context-mgmt-review-001.

## Acceptance criteria

- PR merged with CI green (incl. Windows lanes) and codecov green.
- All R1–R9 enforcers landed; R8/R9 receipts in decisions.md.

## Scope and assumptions

- Branch/worktree: `claude/session-start-context-test-a5f98b` /
  `elegant-mclaren-32a03c`. Delete this file when the branch merges.
- Provider/session: Claude Code (lead).
- Assumptions: sibling repos reachable on this machine.

## Current state

All six spec tasks implemented this session:

- `starter_reconciler.py`: provenance frontmatter parse, fail-closed
  cross-repo refusal, STALE TTL banner, no-provenance annotation,
  `--stamp` writer. 77 unit tests green (serial).
- `starter_prompt_nudge.py`: handoffs-first surfacing (branch slug →
  newest → project starter → labeled legacy global). Tests green.
- `tests/unit/hooks/test_spec_status_corpus.py`: 3 real parsers over
  the real 56-spec corpus, ratchet 0.
- `scripts/sync_session_hooks.py` + `session_hook_fleet.json`:
  fleet projector; all 5 siblings converged, committed there
  (unpushed); preflight gained a `hook-fleet` WARN check.
- Personal infra (machine-local, receipts in decisions.md): global
  starter archived → `~/.attune/next_session_starter.archived-20260818.md`;
  attune-ai queue at `~/attune-ai/.attune/next_session_starter.md`
  (stamped); `~/.claude/hooks/session_start_orientation.sh` regex
  fixed live.

## Verification

- `pytest tests/unit/hooks/test_starter_reconciler.py
  tests/unit/hooks/test_starter_prompt_nudge.py
  tests/unit/hooks/test_spec_status_corpus.py
  tests/unit/scripts/test_sync_session_hooks.py` — all green, serial.
- `sync_session_hooks.py --check` → clean after `--write`;
  spec_orient live runs exit 0 in forms + lite.

## Cross-review (D11 lane, done)

Codex lane ran (11 sent / 2 omitted → scoped follow-up on the
omitted preflight file). 4+1 findings, all accepted and fixed in
commit `cc21622d7`; ledger row appended to
`docs/specs/cross-review/receipts.md`.

## Next action

PR #2086 is open awaiting chair read + merge (CHAIR-ARMS — the
diff touches enforcement surfaces, lead does not arm). Verify CI
incl. Windows lanes (hook scripts touch subprocess + paths).
Sibling repos need a push when convenient.

## Unresolved risks

- Sibling commits are local-only (unpushed).
- `hooks-install` candidate spec (user-facing hook installer) is
  ADJACENT scope — do not conflate with the fleet projector.
- Shared preflight `run_command` remains timeout-free for in-repo
  commands (pre-existing; noted in the ledger for a future pass).
