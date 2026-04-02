---
type: faq
name: list-wizards-is-a-function-not-a-class-method
tags: [imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about list_wizards() is a function, not a class method?

## Answer

The wizard registry exposes `from attune.wizards import list_wizards` as a module-level function, not `WizardRegistry().list_wizards()`. The class `WizardRegistry` is not exported from `attune.wizards`.

```
from attune.wizards import list_wizards
```

## Related Topics
- **Error**: Detailed error: `list_wizards()` is a function, not a class method
