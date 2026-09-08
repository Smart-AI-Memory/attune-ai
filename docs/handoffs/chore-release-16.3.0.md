# Agent work handoff

## Goal

attune-ai v16.3.0 is prepared on one PR from this branch, merged by
Patrick, tagged from the full merge SHA, published after his `pypi` gate
click, and verified on the PyPI simple index.

## Acceptance criteria

- The prep PR is green on every required check, chair-read, and merged
  by Patrick after #2471 (register gates C3 / C4b, 16.3.0 content).
- `/attune-release-check attune-ai 16.3.0` passes (reach snapshot is
  warn-only), `scripts/release_recall_gate.py` passes, and
  `scripts/release_artifact_smoke.py 16.3.0` exits 0 for the wheel and
  the sdist built from the merge SHA.
- Tag `v16.3.0` at the full 40-char merge SHA; the publish-pypi run enters
  `waiting`; Patrick clicks; wheel + sdist appear on the simple index.
- release_state memory and the next-session starter are updated. Step 16
  (post-release self-review, API-billed) waits for Patrick's replacement
  card.

## Scope and assumptions

- Branch/worktree: `chore/release-16.3.0` in
  `.claude/worktrees/release-session-1-381568`.
- Provider/session: Claude (lead). A Codex cross-review lane runs BEFORE
  the PR opens (D11: release surface; subscription seat, no API spend).
- Assumptions: #2471 merges first — the release intro already names C3
  and C4b. No docs regen on the prep commit (Codex does it post-release).
  Zero API spend throughout. The "D8 renumber" named in an earlier
  starter has no referent in `docs/specs/release-16-manifest` and was
  dropped.

## Current state

- Status: prep commit on the branch; waiting on #2471 before rebase,
  Codex lane, push, and PR.
- Changed files: the 10 `bump_version.py` sites + `uv.lock` self-entry;
  `CHANGELOG.md` (`[Unreleased]` → `[16.3.0] - 2026-09-08`, intro, fresh
  empty `[Unreleased]`); `README.md` (rotating slot → 16.3.0; the 16.2.1
  forms note moved to the permanent Interactive forms section; the 16.2.1
  parser-fix note stays in the CHANGELOG only);
  `docs/specs/usage-signals/snapshots/2026-09-08.json` (incomplete, 1/5).
- Decisions: duplicate `### Added` / `### Changed` / `### Fixed` headers
  inside the 16.3.0 section are consolidated after the rebase onto #2471,
  entry order preserved within each category.
- Risks or open questions: the reach before-snapshot is NOT complete in
  the 24–72h window. US-4 warning, verbatim from
  `python scripts/reach_snapshot.py --verify-before 2026-09-09`:
  `WARNING: NO COMPLETE BEFORE-SNAPSHOT in the 24-72h pre-tag window
  (planned tag 2026-09-09T00:00:00+00:00). the 24h window floor has
  passed — the release may continue only with this incomplete-receipt
  warning attached (US-4); do not capture a substitute at tag time.`

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Every version site moved to 16.3.0 | `grep -rIl '16\.2\.1'` outside CHANGELOG/lock/snapshots/handoffs/specs/lessons | only README (the moved 16.2.1 note) |
| Version projections agree | `tests/unit/plugins/test_plugin_config_validation.py` + README anchor/badge tests | 42 passed |
| README in-page links resolve | `python scripts/check_readme_anchors.py` | pass |
| README badges not over-claiming | `.venv/bin/python scripts/check_badge_freshness.py` | Badge freshness OK |
| Lockfile current after the bump | `uv lock` | only the attune-ai self-entry changed (1 line) |
| Pinned hooks clean on every touched file | `uv run --with pre-commit pre-commit run --files …` | all passed |
| Whole tree keyless | `ANTHROPIC_API_KEY="" .venv/bin/python -m pytest tests -n auto` | 26,097 passed, 266 skipped, 3 xfailed, 0 failed in 96 s (prep commit 0a6a95bdd, before the #2471 rebase) |
| Commit signed | `git log -1 --format=%G?` | G |

## Next action

When #2471 merges: `git fetch` + rebase onto origin/main, run the
changelog header consolidation, re-run the whole tree, run the Codex
cross-review lane on the final diff, push, open the PR chair-read. Then
release-check + recall gate + artifact smoke from the merge SHA; tag and
`pypi` click are Patrick's.
