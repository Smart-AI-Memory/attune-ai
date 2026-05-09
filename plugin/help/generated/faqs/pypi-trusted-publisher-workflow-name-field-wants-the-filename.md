---
type: faq
name: pypi-trusted-publisher-workflow-name-field-wants-the-filename
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pyPI trusted publisher "Workflow name" field wants the FILENAME, not the YAML display name?

## Answer

The PyPI pending-publisher form has a "Workflow name" field that must match the `workflow_ref` claim GitHub sends — which is the filename (`publish.yml`), NOT the value of `name:` at the top of the YAML (`Publish to PyPI`). If they mismatch, the publish job fails with `invalid-publisher: valid token, but no corresponding publisher`.

```
workflow_ref
```

## Related Topics
- **Error**: Detailed error: PyPI trusted publisher "Workflow name" field wants the
  FILENAME, not the YAML display name
