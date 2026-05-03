---
name: dispatch-tables-hold-direct-function-references-mocks-must
source: .claude/CLAUDE.md
summary: This template explains why mocking CLI command functions requires patching
  the dispatch table dictionary directly rather than patching the module attribute,
  because the dispatch table stores direct function references captured at import
  time rather than dynamically resolving module names at call time.
tags:
- testing
- imports
type: faq
---

# FAQ: Why must mocks target the dispatch table rather than the module attribute?

## Answer

When `_SUBCOMMAND_DISPATCH` or `_SIMPLE_DISPATCH` in `cli_minimal.py` captures a function reference like `cmd_foo` at import time, the dispatch table stores a direct reference to that function object. Patching the module attribute with `@patch("attune.cli_minimal.cmd_foo")` replaces the name in the module's namespace, but the dispatch table still holds the original reference and will continue calling it — bypassing your mock entirely.

This behavior caused 20+ pre-existing test failures.

**How to fix:**

Patch the entry inside the dispatch table itself using `patch.dict`:

```python
patch.dict(
    "attune.cli_minimal._SUBCOMMAND_DISPATCH",
    {command: {**orig, subcommand: mock_fn}}
)
```

This replaces the function reference stored in `_SUBCOMMAND_DISPATCH` directly, ensuring your mock is actually invoked when the CLI dispatches the command.

**Why this happens:**

Python dispatch tables bind function objects at the time they are constructed — typically at module import. Unlike attribute lookups, which are resolved dynamically at call time, a dictionary entry pointing to a function will not reflect subsequent reassignments of the module-level name. Mocking must therefore target wherever the reference *lives*, not where it was originally *defined*.

## Related Topics

- [Python `unittest.mock.patch.dict` documentation](https://docs.python.org/3/library/unittest.mock.html#patch-dict)
- **Common error:** `Dispatch tables hold direct function references — mocks must target the table, not the module name`
