---
type: faq
name: codecov-patch-0-usually-means-tests-skipped-not-failed
tags: [ci, testing, imports, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does codecov/patch 0% usually means tests *skipped*, not failed?

## Answer

The `codecov/patch` check measures coverage of the diff — new/changed lines. If new tests use `pytest.importorskip` on an optional dep that CI doesn't install, every assertion skips, and the diff shows 0% covered even though all tests "pass".

```
codecov/patch
```

## Related Topics
- **Error**: Detailed error: `codecov/patch` 0% usually means tests *skipped*, not
  failed
