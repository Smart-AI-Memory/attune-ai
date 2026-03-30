---
type: faq
name: website-feature-lists-can-diverge-from-the-python-registry
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Website feature lists can diverge from the Python registry?

## Answer

The `/workflows` page had 14 manually-authored fictional workflows that didn't match `list_workflows()`.


**Fix:**

- Always verify website feature claims against the live Python code before publishing

```
/workflows
```

## Related Topics
- **Error**: Detailed error: Website feature lists can diverge from the Python registry
