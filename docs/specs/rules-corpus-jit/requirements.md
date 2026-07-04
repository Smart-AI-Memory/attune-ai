# Rules-Corpus JIT — Requirements

**Status:** approved-by-Patrick 2026-07-04 ("spec it and then
implement"), same-session implementation.
**Owner:** patrick + agent

---

## Problem

Every session eagerly loads ~185KB (~45k tokens) of standing context
before the first user word. The single biggest line item is
`.claude/rules/attune/` — **116.6KB across 18 files, all auto-loaded
unconditionally** by Claude Code's rules discovery (recursive, eager
for any rules file without `paths:` frontmatter).

The lessons corpus already solved this shape: a thin Patrick-ratified
core stays resident in `.claude/CLAUDE.md`; the 428-lesson tail lives
in `.claude/lessons.md` (not auto-loaded) and is served just-in-time
(SessionStart hydration into `idx:attune_memory`, UserPromptSubmit
topical recall, PreToolUse `jit_recall.py` at decision points). The
rules corpus never got that cutover.

On subscription, the cost is not dollars — it is context headroom:
earlier compaction, diluted attention across a 29KB "quick reference"
manual irrelevant to most turns.

## Verified mechanics (2026-07-04)

- Claude Code loads ALL `.md` under `.claude/rules/` recursively at
  launch — **except** files with `paths:` YAML frontmatter (glob
  list), which load only when Claude reads a matching file.
  Path-scoped rules trigger on READS, not writes — a scoped rule may
  not fire when authoring a new file, so the resident index must
  carry the trigger line.
- Docs guidance: target under 200 lines per always-loaded file.
- Nothing in this repo programmatically loads rules files — all
  references found are prose/docstring citations (3 test docstrings,
  `.claude/CLAUDE.md`, elicit SKILL.md ×2, historical specs/archives).

## Requirements

- **R1 — Residency budget.** Eagerly-loaded rules content (files
  without `paths:` frontmatter under `.claude/rules/`) drops from
  116.6KB to ≤20KB, enforced by a unit test (drift guard), not by
  convention.
- **R2 — No guidance lost.** Every demoted rule remains in-repo,
  discoverable via a resident `INDEX.md` whose per-rule trigger line
  says WHEN to pull it and from WHERE. Git stays the source of
  truth.
- **R3 — Right mechanism per rule.** Each file gets the cheapest
  mechanism that preserves its firing behavior:
  - *resident* — behavior rules that fire on request shape, not file
    paths (cannot be path-scoped);
  - *paths-scoped* — rules genuinely anchored to file globs;
  - *JIT-tail* — reference/judgment rules moved to
    `.claude/rules-tail/attune/` (outside the auto-load path),
    pulled via INDEX trigger lines (and later the Redis layer);
  - *relocate/delete* — content that was never a rule (stale plans,
    archived docs, verbatim duplicates of CLAUDE.md sections).
- **R4 — Citations stay true.** Docstring/skill references to moved
  files are repointed in the same PR (doc-import-gate discipline,
  applied to paths).
- **R5 — Receipt.** The PR records before/after eager-byte
  measurements; the drift-guard test IS the regression receipt.
- **R6 (follow-up, local).** Index `rules-tail` bodies into
  `idx:attune_memory` as `@layer:{rule}` via
  `~/.attune/memory/session_hydrate.py` so FT.SEARCH recall covers
  them — a memory-repo change, not part of the attune-ai PR.

## Non-goals

- `.claude/CLAUDE.md` core-lessons mirror (Patrick-ratified set,
  own review cadence) and `MEMORY.md` (harness-owned index) are out
  of scope.
- No new Lua stored procedures; no hook code changes in Phase 1
  (`jit_recall.py` / `lesson_recall.py` untouched — INDEX pointers
  and paths-scoping carry the load; R6 extends coverage without
  code changes).
- No tuning of which rules are "core" beyond the triage table —
  fire-frequency data can revisit residency later.
