---
type: faq
name: verify-new-dispatch-branches-with-a-known-fixture-not-just
tags: [testing, imports, git]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Verify new dispatch branches with a known fixture, not just
  imports?

## Answer

When adding a new runtime case (e.g. `local_python`) to an existing dispatch table, a clean import doesn't prove the branch fires.


**Fix:**

- Run `Executor.run()` directly with a spec whose `runtime` matches the new case and assert `result.status == "success"` before considering the feature done

```
local_python
```

## Related Topics
- **Error**: Detailed error: Verify new dispatch branches with a known fixture, not just
  imports
