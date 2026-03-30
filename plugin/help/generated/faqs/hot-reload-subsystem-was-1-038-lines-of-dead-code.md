---
type: faq
name: hot-reload-subsystem-was-1-038-lines-of-dead-code
tags: [testing, imports]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: `hot_reload/` subsystem was 1,038 lines of dead code?

## Answer

Zero inbound imports from any file outside the package, but it had its own test suite (1,409 lines) that all passed — making it look alive. Lesson: passing tests are not evidence of integration.


**Fix:**

- Always grep for imports outside the module itself before considering a feature active

```
socratic/embeddings/
```

## Related Topics
- **Error**: Detailed error: `hot_reload/` subsystem was 1,038 lines of dead code
