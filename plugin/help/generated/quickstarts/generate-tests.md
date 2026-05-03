---
name: generate-tests
source: src/attune/cli_minimal.py
summary: This template shows how to automatically generate pytest test cases for uncovered
  code in a Python module using the Attune workflow command.
tags:
- workflow
- testing
type: quickstart
---

# Quickstart: Generate Tests for a Module

Automatically generate pytest tests for uncovered code in a specified module.

```bash
attune workflow run test-gen --path src/attune/help/engine.py
```

**Result:** A test file is generated containing edge cases and assertions for the target module.

**Next:** Run `pytest` to verify that the generated tests pass.

## Related Topics

_No related topics yet._
