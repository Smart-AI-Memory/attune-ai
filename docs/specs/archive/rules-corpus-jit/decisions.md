# Rules-Corpus JIT — Decisions

## D1 — Triage table (per-file disposition)

Measured 2026-07-04; dispositions chosen by firing shape, not size
alone.

| File | KB | Disposition | Why |
|------|----|-------------|-----|
| coding-standards-index.md | 29.3 | JIT-tail | Quick-ref that grew into a manual; load-bearing rules already duplicated in CLAUDE.md "Critical Rules"; full doc at `docs/CODING_STANDARDS.md` |
| advanced-optimization-plan.md | 26.2 | relocate → `docs/archive/planning/` | Jan-2026 planning doc, not a rule; week-by-week roadmap long stale |
| list-copy-guidelines.md | 10.7 | JIT-tail | Review-time reference; fires on perf-review work, not per-session |
| communication-grammar.md | 7.4 | paths-scoped | Anchored to elicitation/meta_workflows sources + elicit skill |
| decision-routine.md | 6.0 | **resident** | Fires on request shape (3+ files, design forks) — cannot path-scope |
| doc-fiction-triage.md | 5.3 | paths-scoped | Doc-cleanup pre-flight; anchored to docs/content |
| doc-import-gate.md | 5.0 | paths-scoped | Anchored to docs/content/audit script/workflow |
| removing-dead-code.md | 4.1 | JIT-tail | Judgment gate for deletion/surfacing work; trigger is intent, not path — INDEX line carries the trip-wire |
| debugging.md | 4.1 | relocate → `docs/archive/` | Auto-generated commit-pattern dump, mostly website fixes, "root cause: unknown" |
| vscode-extension-limitations.md | 3.0 | relocate → `docs/archive/` | Self-declared "Archived — directory no longer exists" |
| xml-enhanced-prompts.md | 2.9 | **resident** | Canonical criteria referenced by CLAUDE.md Critical Rules + decision-routine |
| scanner-patterns.md | 2.6 | JIT-tail | Fires when reviewing bug-predict output |
| documentation-patterns.md | 2.3 | paths-scoped | Anchored to docs/ |
| plugin-reference-validation.md | 2.1 | paths-scoped | Anchored to plugin/, .agents/, tool_schemas.py |
| website-content-accuracy.md | 1.7 | paths-scoped | Anchored to website/content |
| os-walk-dirs-pattern.md | 1.5 | JIT-tail | Content-shaped (os.walk usage anywhere); src/**/*.py scope would defeat the purpose |
| output-formatting.md | 1.5 | **resident** | Response-formatting behavior, fires every session |
| markdown-formatting.md | 0.8 | **delete** | Verbatim duplicate of CLAUDE.md "Markdown Formatting" section |

Eager after cutover: decision-routine + xml-enhanced-prompts +
output-formatting + INDEX.md ≈ 13KB (was 116.6KB). Path-scoped
23.8KB loads only on matching reads.

## D2 — `.claude/rules-tail/attune/` as the JIT-tail home

Mirrors the lessons precedent (`.claude/lessons.md` — canonical,
in-repo, NOT auto-loaded). Rejected `docs/rules/` (these are
agent-facing, would leak into mkdocs surface decisions) and deleting
in favor of Redis-only (violates git-as-source-of-truth).

## D3 — INDEX.md is the recall contract, not the hooks

Path-scoped rules fire on READS only; JIT-tail rules fire on nothing
automatic (Phase 1). The resident INDEX.md therefore carries one
trigger line per non-resident rule ("doing X → read Y"). This is the
MEMORY.md pattern applied to rules. Hook/Redis coverage (R6) is
additive, not load-bearing — so a hook regression can't silently
lose a rule.

## D4 — Drift guard enforces the budget

`tests/unit/rules/test_rules_residency_budget.py`: every
`.claude/rules/**/*.md` without `paths:` frontmatter must be on the
resident allowlist AND the allowlist's total bytes ≤ 20,000. A new
rule must either scope, go to the tail, or consciously widen the
allowlist in the same diff (enforcement-vs-documentation: the test
is the rule).

## D5 — Frontmatter compatibility risk accepted

On a Claude Code version predating `paths:` scoping, the frontmatter
would load as visible text and the rule loads eagerly — the failure
mode is "no savings", never "rule lost". Safe to ship without
version gating.

## D6 — debugging.md archived, not regenerated

Its content is 84 auto-mined commit patterns (mostly the retired
website/ tree, root causes "unknown"). If pattern-mining returns,
it should feed the lessons/Redis layer, not an always-loaded rules
file. Archive as-is with provenance note.
