# Tasks — Cross-Provider Collaboration Projector

## Done (on codex/using-projectors — do not redo)

- [x] Master `content/collaboration/contract.md` (contract +
      handoff template sections).
- [x] Projector `scripts/project_collaboration_contract.py` with
      marker replacement, whole-file template write, `--check`.
- [x] Hardening (currently uncommitted in the working tree):
      preflight-before-mutation, `_validate_file_path` symlink
      containment, mkdir for the template parent.
- [x] 12 focused tests incl. failure-sensitive AC-1/AC-2/AC-3.
- [x] Projected blocks landed in AGENTS.md / .claude/CLAUDE.md /
      templates/agent-handoff.md, synchronized.

## Executed 2026-07-18 (same day as ratification)

- [x] T1 (D3): pre-commit hook `check-collaboration-projection`
      added; CI enforcement = `test_repo_projection_is_in_sync` in
      the unit suite (repo projector convention). AC-4 receipt: a
      deliberate master edit made the hook exit 1 naming the stale
      file; clean tree passes.
- [x] T2 (D2): `GENERATED_NOTICE` rendered inside the marked
      block; both targets re-projected; `--check` exits 0; test
      `test_projected_block_carries_generated_notice`.
- [x] T3 (D1): master Handoffs section names
      `docs/handoffs/<branch-slug>.md`; `docs/handoffs/README.md`
      documents the convention; re-projected to both targets.
- [x] T4 (D4): `_parse_sections` raises ProjectionError on a
      repeated required heading; test
      `test_rejects_duplicate_required_heading`.
- [x] T5 — N/A per D5a: preflight + idempotent rerun accepted as
      the failure guarantee; no rollback work.
- [x] T6: hardening + spec committed on the feature branch;
      14 focused tests pass serially (0.13s tail in the PR).

## Non-goals (this spec)

- Productizing as an `attune` CLI feature (D6 recommends deferring).
- Any Codex hooks.json integration (dead in current build).
