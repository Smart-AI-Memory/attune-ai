---
type: faq
name: validate-file-path-needed-on-reads-too-not-just-writes
tags: [security, imports]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about _validate_file_path needed on reads too, not just writes?

## Answer

`load_state(user_id)` and `delete_state(user_id)` built paths from user input without validation. Even though the existing `save_state()` validated, the read and delete paths did not.

```
load_state(user_id)
```

## Related Topics
- **Error**: Detailed error: `_validate_file_path` needed on reads too, not just writes
