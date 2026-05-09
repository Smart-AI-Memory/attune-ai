---
type: error
name: pypi-trusted-publisher-workflow-name-field-wants-the-filename
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: PyPI trusted publisher "Workflow name" field wants the
  FILENAME, not the YAML display name

## Signature

PyPI trusted publisher "Workflow name" field wants the
  FILENAME, not the YAML display name

## Root Cause

The PyPI pending-publisher form has a "Workflow name" field that must match the `workflow_ref` claim GitHub sends — which is the filename (`publish.yml`), NOT the value of `name:` at the top of the YAML (`Publish to PyPI`). If they mismatch, the publish job fails with `invalid-publisher: valid token, but no corresponding publisher`. The OIDC debug output shows the actual claim — compare it to the PyPI config field-by-field. Other common mismatches: owner with wrong case or underscore-vs-hyphen, environment name case, repository name.

## Resolution

1. The PyPI pending-publisher form has a "Workflow name" field that must match the `workflow_ref` claim GitHub sends — which is the filename (`publish.yml`), NOT the value of `name:` at the top of the YAML (`Publish to PyPI`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
