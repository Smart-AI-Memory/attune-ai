---
type: faq
name: wizards-call-workflows-internally-they-are-not-duplicates
tags: [git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about wizards call workflows internally — they are not duplicates?

## Answer

`attune wizard run` = interactive guided UX; `attune workflow run` = non-interactive multi-stage pipeline. `WizardInternalWorkflow` is the bridge.

```
attune wizard run
```

## Related Topics
- **Error**: Detailed error: Wizards call workflows internally — they are not duplicates
