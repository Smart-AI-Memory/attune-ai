# Rules Index — pull the body when the trigger fires

Most rule bodies are NOT resident (see
`docs/specs/rules-corpus-jit/`). Two tiers below. When a trigger
matches your current work, Read the named file BEFORE acting —
the one-liner here is the trip-wire, not the rule.

## Tail rules (`.claude/rules-tail/attune/` — never auto-load)

- **Deleting, surfacing, or "fixing access to" a registered
  capability** → `removing-dead-code.md` — the should-this-exist
  gate; never surface before dogfooding the real run path.
- **Pushing a lead-authored src/tests diff (esp. into a D11b
  review lane)** → `d11-preflight-checklist.md` — six repeat-class
  probes (fail-open, windows, record-before-stamp, path prefix,
  key collisions, USERPROFILE) run BEFORE the lane.
- **Writing/reviewing Python style, exceptions, path validation,
  security patterns** → `coding-standards-index.md` — expanded
  quick-ref; the binding rules are already in CLAUDE.md Critical
  Rules; full doc at `docs/CODING_STANDARDS.md`.
- **Perf review of list/sort/dedup code, top-N queries** →
  `list-copy-guidelines.md` — heapq.nlargest, dict.fromkeys,
  generator-pipeline patterns + decision matrix.
- **Reviewing bug-predict / scanner output** →
  `scanner-patterns.md` — severity meanings and the built-in
  false-positive filters (don't re-flag them).
- **Touching `os.walk` traversal code, or a scanner flags
  `dirs[:]`** → `os-walk-dirs-pattern.md` — `dirs[:] = [...]` is
  required in-place filtering, NOT a copy to "fix".
- **Cleaning up docs that name a "removed" symbol** →
  `doc-fiction-triage.md` (+ `doc-import-gate.md`, the CI gate,
  and its `doc-import-skip` escape hatch) — a `jit_recall`
  one-liner fires on Edit/Write touching `docs/` or `content/`;
  Read the full body before acting (migrated off harness
  path-scope 2026-07-16 — one body, deduped, not a doubled
  full-body auto-load).

## Path-scoped rules (auto-load on READS of matching files only)

They do NOT fire when only WRITING a new file — pull manually then:

- **Authoring/reorganizing docs** → `documentation-patterns.md` —
  consolidate over scatter, delete + redirect, ~150-line guideline.
- **Editing plugin commands/skills/hooks or MCP tools** →
  `plugin-reference-validation.md` — verify every referenced
  skill/tool/class resolves; new-MCP-tool checklist.
- **Website/feature-page counts or capability claims** →
  `website-content-accuracy.md` — verify against live registries;
  `website/lib/features.ts` is canonical.
- **Elicitation constructs (decision/pushback/progress forms) or a
  display widget (chart/kernel-rendered)** →
  `communication-grammar.md` — both member classes (interactive
  forms, display kernels) + how to add the next member.
- **Writing/editing any `.md` file** → `markdown-formatting.md` —
  heading/list/table formatting rules; migrated 2026-07-15 from
  the always-loaded CLAUDE.md.

Resident (full bodies load every session): `decision-routine.md`,
`xml-enhanced-prompts.md`, `output-formatting.md`. Budget enforced
by `tests/unit/rules/test_rules_residency_budget.py`.
