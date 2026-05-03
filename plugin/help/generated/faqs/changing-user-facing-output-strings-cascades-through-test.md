---
name: changing-user-facing-output-strings-cascades-through-test
source: .claude/CLAUDE.md
summary: This developer help template covers how modifying user-facing output strings
  in shared code paths causes multiple test failures and explains the best practices
  for managing such changes safely.
tags:
- testing
type: faq
---

# FAQ: Why Does Changing a User-Facing Output String Break Multiple Test Assertions?

## Answer

Modifying a user-facing output string in a shared code path will cascade failures across every test that asserts against that exact string. For example, replacing `"Workflow completed"` with a personality-driven message broke 6 assertions across 4 test classes in a single change.

Whenever you modify a string returned by a shared output function like `_print_workflow_result`, grep the entire test suite for the old string **before** considering the change complete:

```bash
grep -r "Workflow completed" ./tests
```

Update every matching assertion to reflect the new string, or consider extracting the string into a named constant so tests and source stay in sync automatically.

## Key Takeaway

User-facing strings in shared output paths are implicit test contracts. Treat any change to them as a potentially breaking change that requires a full test-suite search.

## Related Topics

- **Error:** Changing user-facing output strings cascades through test assertions
