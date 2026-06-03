# Tasks: consolidate-claude-md-lessons

> **Status:** handoff (not started). See [README](README.md) for
> method + inventory.

## Phase 1 — cross-linked lessons (lowest risk, highest yield)

- **T1:** Extract the 60 cross-referenced lessons (grep
  `Pairs with|Companion|same (shape|root cause|family)|extends the
  existing`). For each "A pairs with B" pair, merge into one lesson
  where they describe the same mechanism; keep distinct if the
  mechanisms differ. Sub-bullet the specifics.

## Phase 2 — largest clusters (descending yield)

One commit per cluster so each is reviewable. Order by lines:

- **T2:** `test` (45 / 628) — likely the biggest win; many are
  per-module test-scaffold variants that collapse to archetypes.
- **T3:** `ci` (31 / 550)
- **T4:** `workflow` (28 / 510)
- **T5:** `path` (27 / 428) — Windows/path-separator family is dense.
- **T6:** `merge` + `tag` + `squash` + `rebase` + `stash` (git
  release-mechanics, ~813 combined across overlaps) — merge as one
  pass; heavy redundancy in the admin-merge / stacked-PR lessons.
- **T7:** `worktree` (10 / 308) — proof cluster; collapses to
  ~3-4 (code/venv resolution · git state · per-worktree gotchas).
- **T8:** `windows` (12 / 223), `sdk` (12 / 219), `spec` (12 / 219),
  remaining mid clusters.

## Phase 3 — verify + ship

- **T9:** Final verify: lesson-count delta (expect modest drop, not
  a cliff), line delta (target -30–40%), zero dangling cross-refs,
  markdown-lint clean. Open as one docs PR.

## Notes for the executor

- Use Opus (per `feedback_use_opus_for_spec_work` — judgment-heavy).
- `CLAUDE.md` is auto-loaded every session; edits via the Edit tool
  on the worktree copy, not shell splice.
- This is the LESSONS section only; leave the rest of CLAUDE.md
  (standards, structure, rules) untouched.
