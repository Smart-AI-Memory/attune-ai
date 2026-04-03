---
type: reference
subtype: procedural
name: skill-refactor-plan
category: skill
tags: [refactoring, skill, plugin, reference]
source: plugin/skills/refactor-plan/SKILL.md
---

# Refactor Plan Reference

Complete reference for the refactor-plan skill — every
debt type it detects, how it prioritizes, and how to
interpret and act on the roadmap.

## Invocation

```
/refactor-plan <path>
```

Or natural language:

```
analyze src/ for refactoring opportunities
find tech debt in the auth module
what should I refactor in src/workflows/?
simplify src/engine.py
```

## How it runs

The skill runs on your Claude subscription — no API key
or additional cost. It reads your code, identifies
structural problems, and produces a prioritized roadmap.

| Mode | What you get |
|------|-------------|
| **Full analysis** | All debt types, prioritized roadmap (default) |
| **Simplify** | Complexity reduction only — flatten nesting, inline trivial helpers, remove dead code |

Set mode with natural language:

```
full refactoring roadmap for src/
simplify src/engine.py
```

## Guided flow

When invoked without a specific path or focus, the skill
asks:

1. **"What file or directory should I analyze?"** —
   scope the scan
2. **"What's bothering you about this code?"** — target
   the analysis (complexity, duplication, everything)
3. **"Quick scan or detailed roadmap?"** — set depth

## All debt types

### Code smells

| Smell | Indicators | Severity | Typical fix |
|-------|------------|----------|-------------|
| Long method | >50 lines, high cyclomatic complexity | High | Extract method |
| God class | >10 responsibilities, >500 lines | High | Split into focused classes |
| Feature envy | Method uses another class more than its own | Medium | Move method to the class it envies |
| Data clump | Same group of parameters passed together | Medium | Extract parameter object |
| Primitive obsession | Strings/ints used where a type would be clearer | Low | Introduce value object |

### Duplication

| Pattern | Indicators | Severity | Typical fix |
|---------|------------|----------|-------------|
| Exact duplicate | Identical blocks in 2+ places | High | Extract shared function |
| Near-duplicate | Similar blocks with minor variation | Medium | Extract with parameters |
| Structural duplicate | Same algorithm, different types | Low | Extract generic helper or protocol |

### Complexity

| Pattern | Indicators | Severity | Typical fix |
|---------|------------|----------|-------------|
| Deep nesting | >4 levels of indentation | High | Early returns, guard clauses |
| High cyclomatic complexity | >15 branches in one function | High | Strategy pattern, dispatch table |
| Long parameter list | >5 parameters | Medium | Parameter object, builder |
| Complex conditional | Multi-line boolean expression | Medium | Extract named predicate |

### Coupling

| Pattern | Indicators | Severity | Typical fix |
|---------|------------|----------|-------------|
| Circular imports | Module A imports B imports A | High | Extract shared interface |
| Shotgun surgery | One change requires edits in 5+ files | High | Consolidate related logic |
| Inappropriate intimacy | Class accesses another's private state | Medium | Add proper API or merge classes |
| Middle man | Class delegates everything, adds nothing | Low | Remove and call delegate directly |

### Naming

| Pattern | Indicators | Severity | Typical fix |
|---------|------------|----------|-------------|
| Abbreviations | `cfg`, `mgr`, `proc`, `ctx` | Medium | Rename to full word |
| Generic names | `data`, `info`, `handler`, `manager` | Medium | Rename to specific intent |
| Inconsistent conventions | Mix of `get_X` and `fetch_X` | Low | Pick one and apply everywhere |
| Misleading names | Name suggests wrong behavior | High | Rename to match actual behavior |

### Dead code

| Pattern | Indicators | Severity | Typical fix |
|---------|------------|----------|-------------|
| Unreachable branch | Always-false condition | Medium | Delete the branch |
| Unused parameter | Param never read in body | Low | Remove (check callers first) |
| Vestigial module | Zero inbound imports | High | Delete (verify with grep first) |
| Commented-out code | Blocks of `# old_function()` | Low | Delete (it's in git history) |

## Prioritization criteria

The roadmap ranks items by a composite score:

| Factor | Weight | Scale |
|--------|--------|-------|
| **Severity** | 40% | How much the issue hurts readability, testability, or safety |
| **Impact** | 30% | How much better the code gets after the fix |
| **Effort** | 20% | Inverse of cost — low-effort fixes score higher |
| **Risk** | 10% | Inverse of regression risk — safe changes score higher |

Items are grouped into priority tiers:

| Tier | Profile | Action |
|------|---------|--------|
| **Priority 1** | High severity, low effort, high impact | Fix this week |
| **Priority 2** | High severity, high effort | Plan a focused sprint |
| **Priority 3** | Low severity or high risk | Fix when convenient |

## Output format

Results are presented as a grouped roadmap:

```markdown
## Refactoring Roadmap

**Score:** 64/100 | **Files:** 23 | **Issues:** 11

### Priority 1 (High Impact, Low Effort)

| File | Issue | Fix | Effort | Risk |
|------|-------|-----|--------|------|
| [engine.py:45](src/engine.py#L45) | God class (14 responsibilities) | Split into Engine + Parser + Validator | ~2h | Medium |
| [utils.py:89](src/utils.py#L89) | Duplicated in 4 places | Extract shared helper | ~30m | Low |
| [auth.py:12](src/auth.py#L12) | Deep nesting (6 levels) | Guard clauses + early returns | ~20m | Low |

### Priority 2 (High Impact, High Effort)

| File | Issue | Fix | Effort | Risk |
|------|-------|-----|--------|------|
| [base.py:201](src/workflows/base.py#L201) | Cyclomatic complexity 28 | Extract strategy pattern | ~4h | High |
| [router.py:55](src/router.py#L55) | Circular import with engine | Extract shared interface | ~3h | Medium |

### Priority 3 (Low Impact)

| File | Issue | Fix | Effort | Risk |
|------|-------|-----|--------|------|
| [config.py:12](src/config.py#L12) | Unclear naming (cfg, mgr) | Rename to intent | ~15m | Low |
```

**Scoring:**

| Range | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | Clean structure, minimal debt |
| 75-89 | Good | Minor issues, no blockers |
| 50-74 | Needs work | Structural problems slowing development |
| 0-49 | Critical | Major debt blocking changes |

## After the roadmap

| Goal | What to say |
|------|-------------|
| Fix the top item | "refactor the god class in engine.py" |
| Simplify one file | "simplify src/engine.py" |
| Write tests first | "generate tests for engine.py before refactoring" |
| Deeper analysis | "deep analysis of coupling between auth and models" |
| Track over time | "compare with last refactor plan" |
| Export for planning | "export roadmap as markdown" |

## Want to learn more?

- Say **"what is refactor plan?"** to go back to the
  overview
- Say **"how do I run a refactor plan?"** for the
  step-by-step guide
- Say **"review my code"** for a broader code quality
  review
- Say **"tell me about deep review"** for multi-pass
  security and quality analysis
