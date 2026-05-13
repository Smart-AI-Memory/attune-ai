# Discovery Sweep — Whole-Tree Audit (2026-05-13)

First systematic dogfood run of `discovery-sweep` (Phase 1) against
the full `src/attune/` tree. Run from the
`fix/discovery-sweep-false-positives` branch (PR #306) — the
same-line quoted-region filter and `# noqa: BLE001` waiver are
active.

## Summary

| Metric | Value |
|---|---|
| Scope | `src/attune` |
| Source | `pattern-scan` (non-LLM) |
| Duration | 392 ms |
| Queue | 15 findings |
| Questions | 0 |
| Rejected | 16 (TODO/FIXME below severity threshold) |
| Real signals (triaged) | **1** |
| Multi-line-docstring false positives | 14 |

## Real signal (1)

| File:line | Pattern | Notes |
|---|---|---|
| [ops/routes/specs.py:274](src/attune/ops/routes/specs.py#L274) | `broad_exception` | Cleanup broad-except that correctly re-raises but lacks `# noqa: BLE001` + `# INTENTIONAL: cleanup` annotation required by the coding standards. Either annotate or narrow to `(OSError, ValueError)`. |

## False positives that bypass current filters (14)

All have the same shape: `eval(` / `exec(` mentioned in a
**module-level docstring** that opens many lines above the matching
line. The current `_is_inside_quoted_region` filter is line-local —
it walks quotes only within the current line, so a docstring whose
opening `"""` is on line 1 and whose mention of `eval(` is on line
12 falls through.

| File:line | Evidence |
|---|---|
| [workflows/bug_predict_patterns.py:284](src/attune/workflows/bug_predict_patterns.py#L284) | `- Comments mentioning eval/exec...` |
| [hooks/scripts/security_guard.py:4](src/attune/hooks/scripts/security_guard.py#L4) | `1. Blocks eval()/exec() in Bash commands` |
| [orchestration/execution_strategies.py:20](src/attune/orchestration/execution_strategies.py#L20) | `- No eval() or exec() usage` |
| [orchestration/pattern_learner.py:12](src/attune/orchestration/pattern_learner.py#L12) | `- No eval() or exec() usage` |
| [orchestration/meta_orchestrator.py:8](src/attune/orchestration/meta_orchestrator.py#L8) | `- No eval() or exec() usage` |
| [orchestration/_strategies/nesting.py:15](src/attune/orchestration/_strategies/nesting.py#L15) | `- No eval() or exec() usage` |
| [orchestration/_strategies/conditions.py:9](src/attune/orchestration/_strategies/conditions.py#L9) | `- No eval() or exec() - all operators are whitelisted` |
| [orchestration/_strategies/conditions.py:175](src/attune/orchestration/_strategies/conditions.py#L175) | same shape |
| [orchestration/_strategies/conditional_strategies.py:15](src/attune/orchestration/_strategies/conditional_strategies.py#L15) | `- No eval() or exec() usage` |
| [orchestration/_strategies/advanced_strategies.py:43](src/attune/orchestration/_strategies/advanced_strategies.py#L43) | `- No eval() or exec() usage` |
| [orchestration/_strategies/base.py:8](src/attune/orchestration/_strategies/base.py#L8) | `- No eval() or exec() usage` |
| [orchestration/_strategies/core_strategies.py:13](src/attune/orchestration/_strategies/core_strategies.py#L13) | `- No eval() or exec() usage` |
| [orchestration/agent_templates/models.py:8](src/attune/orchestration/agent_templates/models.py#L8) | `- No eval() or exec() usage` |
| [orchestration/agent_templates/__init__.py:9](src/attune/orchestration/agent_templates/__init__.py#L9) | `- No eval() or exec() usage` |

## Implications for PatternScanSource

The Phase 1 filter is **insufficient** for whole-tree scans. Single-
file or small-package scans on real production code worked (PR #306
took the dogfood from 8 false positives to 0 across 4 targets), but
the whole-tree scan re-exposed the same false-positive class via a
slightly different mechanism (multi-line docstrings vs. same-line
string literals).

### Three fix options

1. **AST-based string-region map.** Parse each `.py` file with
   `ast.parse`, walk `ast.Str` / `ast.Constant` (string) nodes,
   build a set of `(start_line, start_col) — (end_line, end_col)`
   regions. Filter findings whose `(line, col)` falls inside any
   string region. Robust against multi-line strings, f-strings,
   raw strings, b-strings. Cost: one parse per file (~1ms for most
   modules), depends on `ast` (stdlib, no new dep). The cleanest
   structural fix.

2. **Stateful line walk.** Track triple-quote-open state across
   lines while scanning. Two pieces of state: `in_docstring`
   (boolean) and `quote_kind` (`"""` or `'''`). Flip on triple-
   quote tokens. Fragile against escapes and string concatenation
   tricks, but cheap and doesn't depend on AST.

3. **Conservative pattern narrowing.** Require the matched
   `eval(` / `exec(` to be at the start of a line (after
   indentation) AND not preceded by `#` (comment) or `-`/`*`
   (list-marker). Drops the false positives but loses real
   matches where eval is a sub-expression
   (`result = some_fn(eval(x))`). Cheap but blunt.

**Recommendation:** Option 1 (AST). The other two have failure
modes that show up the moment Phase 2A LLM sources ship and start
emitting structured findings with column data that the engine
expects to be reliable.

**Decision (Patrick, 2026-05-13):** Approved — proceed with AST.
Options 2 and 3 are off the table; next-session implementation
should ship Option 1 directly without re-evaluating.

## What didn't surface

The whole-tree scan turned up **zero**:

- bare `except:` clauses (PR #303 + PR #306 standards held)
- `subprocess(..., shell=True)` instances
- broad-except blocks lacking `# noqa: BLE001` *other* than the
  one above (the policy is well-followed)

That's a useful negative result: the codebase is hygienic on the
patterns this scanner catches. The single real finding (one
missing annotation in a cleanup block) is project-policy drift,
not a bug.

## Validation: PR #306 didn't regress anything

Re-ran the four PR #306 dogfood targets from this branch:

| Target | PR #306 result | Whole-tree re-check |
|---|---|---|
| `src/attune/workflows/discovery_sweep/` | 0 | 0 |
| `src/attune/security/` | 0 | 0 |
| `src/attune/memory/short_term/` | 0 | 0 |
| `src/attune/cli_minimal.py` | 0 | 0 |

All four still clean — the filter holds for narrower scopes; only
the cross-package docstring shape evades it.

## State at end of session

- **PR #303** — merged 2026-05-13 (Phase 1 engine + Protocol +
  PatternScanSource + verification + CLI registration).
- **PR #306** — draft, awaiting CI, pre-CI state: 41 → 48 tests
  passing; same-line quote-region + `# noqa: BLE001` filters +
  path-rendering fix. Branch:
  `fix/discovery-sweep-false-positives`.
- This audit: `docs/specs/discovery-sweep/dogfood-audit-2026-05-13.md`
- Two new lessons in `.claude/CLAUDE.md` (workflow registration
  has FOUR drift-guard gates; PatternScanSource self-match was the
  driver for #306).
