# Design — Cross-Provider Collaboration Projector

**Status:** shipped (2026-07-18) — implemented as designed (#1436)

## Data flow

```text
content/collaboration/contract.md          (master — the only edit surface)
  ├─ "## Shared contract" section
  │    → rendered as "## Cross-provider collaboration" block
  │    → replaced between <!-- attune:collaboration:start/end -->
  │         ├─ AGENTS.md            (loaded by Codex, NOT by Claude)
  │         └─ .claude/CLAUDE.md    (loaded by Claude, NOT by Codex)
  └─ "## Portable handoff template" section
       → whole-file write → templates/agent-handoff.md
```

Loading boundaries (verified 2026-07-18 against a live Codex session
rollout and Claude session context): Codex loads repo-root
`AGENTS.md` + `~/.codex/AGENTS.md`; Claude Code loads
`.claude/CLAUDE.md` + `~/.claude/CLAUDE.md`. Neither reads the
other's file — hence one projected copy per provider, one master.

## Projector phases

1. **Parse** — split the master on exactly the two declared H2
   headings; nested H2s inside the handoff template are preserved
   because only declared headings delimit (covered by
   `handoff_projection_preserves_nested_h2_sections`).
2. **Preflight** — validate master presence/sections; resolve and
   contain every path (symlink-aware); read every target; compute
   every expected output; any failure raises before a single write.
3. **Write/report** — `--check` lists stale paths and exits 1;
   write mode writes only changed targets and reports
   written/unchanged.

Error taxonomy (`ProjectionError`): master missing · required
section missing/empty · path escapes repository · target missing ·
marker count ≠ 1 pair · markers out of order.

## Receipts (as of 2026-07-18, branch codex/using-projectors)

- 12 focused tests pass serially (list in the test file; includes
  the AC-1/AC-2/AC-3 failure-sensitive cases).
- Projector coverage 92.25%; Black and Ruff pass.
- Real CLI: `--check` on the synchronized tree prints three
  `unchanged` lines and exits 0 (re-verified independently by a
  second agent, 2026-07-18 ~11:15 UTC).

## Constraints learned elsewhere (binding on this design)

- Codex executes NO hooks.json hooks in the current build, and
  rewrites `~/.codex/hooks.json` on session close — enforcement
  (D3) and any automation must live in CI/pre-commit or
  instruction-file content, never in Codex hook config.
- The repo already runs three single-source projectors
  (help, skills, features); this one follows the same
  edit-master-then-regenerate discipline, and its gate should match
  their pre-commit + CI convention (D3).
