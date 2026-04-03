---
type: error
name: validate-file-path-needed-on-reads-too-not-just-writes
confidence: Verified
tags: [security, imports]
source: .claude/CLAUDE.md
---

# Error: `_validate_file_path` needed on reads too, not just writes

## Signature

`_validate_file_path` needed on reads too, not just writes

## Root Cause

`load_state(user_id)` and `delete_state(user_id)` built paths from user input without validation. Even though the existing `save_state()` validated, the read and delete paths did not. When adding path validation to a module, grep for ALL `open()`, `.unlink()`, and `.read_text()` calls in the same file — not just write operations.

## Resolution

1. `load_state(user_id)` and `delete_state(user_id)` built paths from user input without validation

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `_validate_file_path` needed on reads too, not just writes
