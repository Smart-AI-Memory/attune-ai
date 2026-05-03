---
name: hot-reload-subsystem-was-1-038-lines-of-dead-code
source: .claude/CLAUDE.md
summary: This template explains how to identify, understand, and prevent dead code
  that passes all its tests because it's never actually imported or used by the rest
  of the codebase.
tags:
- testing
- imports
type: faq
---

# FAQ: How Did a 1,038-Line Subsystem Turn Out to Be Dead Code?

## Answer

The `hot_reload/` subsystem had zero inbound imports from any file outside its own package. Despite this, it maintained a dedicated test suite of 1,409 lines — and every test passed. This created a false signal of health and integration, allowing the dead code to go undetected.

**The core lesson:** passing tests are not evidence of integration. A self-contained test suite only proves that a module works in isolation — not that anything in the broader codebase actually calls it.

## How to Detect This Problem

Before considering any feature or subsystem active, verify that it is genuinely imported and used outside of its own package.

**Search for external imports of the module:**

```bash
grep -r "hot_reload" socratic/ --include="*.py" | grep -v "hot_reload/"
```

If this returns no results, the module is an island — referenced by nothing outside itself.

**Audit your import graph systematically:**

```bash
# List every file that imports from a given package
grep -rn "from socratic.embeddings" socratic/ | grep -v "embeddings/"
```

## Why This Happens

| Cause | Explanation |
|---|---|
| Incremental abandonment | A feature is deprioritized but never formally removed |
| Self-contained test suites | Tests import only from within the module, masking the lack of external usage |
| No import-graph tooling | Without static analysis, dead packages are invisible at a glance |
| Optimistic metrics | Line counts and test pass rates signal effort, not integration |

## How to Prevent It

- **Add import-graph analysis** to your CI pipeline using tools like [`importchecker`](https://pypi.org/project/importchecker/) or [`vulture`](https://github.com/jendrikseipp/vulture)
- **Require an integration test** — at minimum one test that exercises the module from outside its own package boundary
- **Review unreferenced packages** as part of any refactor or dependency audit
- **Treat zero external imports as a deletion candidate**, not a passing grade

## Related Topics

- [Understanding the difference between unit tests and integration tests](#)
- [Static analysis tools for dead code detection](#)
- **Error reference:** `hot_reload/` subsystem identified as 1,038 lines of unreachable code
