---
type: warning
name: pypi-trusted-publisher-workflow-name-field-wants-the-filename
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Warning: PyPI trusted publisher "Workflow name" field wants the
  FILENAME, not the YAML display name

## Condition

The PyPI pending-publisher form has a "Workflow name" field that must match the `workflow_ref` claim GitHub sends — which is the filename (`publish.yml`), NOT the value of `name:` at the top of the YAML (`Publish to PyPI`)

## Risk

If they mismatch, the publish job fails with `invalid-publisher: valid token, but no corresponding publisher`

## Mitigation

1. The PyPI pending-publisher form has a "Workflow name" field that must match the `workflow_ref` claim GitHub sends — which is the filename (`publish.yml`), NOT the value of `name:` at the top of the YAML (`Publish to PyPI`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: PyPI trusted publisher "Workflow name" field wants the
  FILENAME, not the YAML display name
