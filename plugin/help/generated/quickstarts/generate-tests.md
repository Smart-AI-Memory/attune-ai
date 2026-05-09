---
type: quickstart
name: generate-tests
tags: [workflow, testing]
source: src/attune/cli_minimal.py
---

# Quickstart: Generate tests for a module

Auto-generate pytest tests for uncovered code.

```
attune workflow run test-gen --path src/attune/help/engine.py
```

**Result:** Generated test file with edge cases and assertions.

**Next:** Run `pytest` to verify the generated tests pass.

## Related Topics

_No related topics yet._
