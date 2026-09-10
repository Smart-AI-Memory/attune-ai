# attune-verify 0.6.1 lock-bump handoff

## Goal

Resolve `attune-ai` against the published `attune-verify 0.6.1` artifacts so plugin and package consumers receive the maintenance release.

## Acceptance criteria

- `uv.lock` pins `attune-verify 0.6.1` with the published wheel and sdist hashes.
- The installed `/verify` integration contract passes against the locked dependency.
- Lock consistency and targeted dependency tests pass.

## Scope and assumptions

- Branch/worktree: `codex/bump-attune-verify-0.6.1` in `attune-ai-lock-bump`.
- Provider/session: Codex, 2026-09-10.
- Assumptions: the existing `>=0.1.0,<1.0` compatibility range remains correct; no `attune-ai` version bump is part of this PR.

## Current state

- Status: verified and ready to commit.
- Changed files: `CHANGELOG.md`, `pyproject.toml`, `uv.lock`, the cross-review receipt ledger, and this handoff.
- Decisions: preserve the existing dependency range and upgrade only the locked package.
- Risks or open questions: none identified.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Lock resolves the published release | `uv lock --check` | Pass |
| `/verify` API remains compatible | `uv run pytest tests/integration/test_verify_skill_contract.py -q` | Pass: 11 tests |
| Runtime imports the intended version | `uv run python -c 'import attune_verify; print(attune_verify.__version__)'` | Pass: `0.6.1` |
| Changed files satisfy repository hooks | `uv run --with pre-commit pre-commit run --files ...` | Pass |
| Dependency claims survive independent review | gpt-5.5 evidence-chain review plus central re-run | Pass after accepting one P3 wording correction |

## Next action

Commit the verified diff, push the branch, and open the PR.
