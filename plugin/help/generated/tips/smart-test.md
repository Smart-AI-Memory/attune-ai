---
name: smart-test
source: content/features/smart-test.md
tags:
- tests
- coverage
- generation
type: tip
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  the three workflow classes and their async `execute`, plus the
  `WorkflowResult` they return. Internal helpers (underscore-
  prefixed names, the AST/coverage parsing utilities) may change.
- **Audit before you generate.** Running `test-audit` first tells
  you *where* the gaps are so a `test-gen` pass spends its budget on
  the modules that matter.
- **Keep runs cheap with `path` and `depth`.** A `quick` pass over
  one module is far faster than a `deep` pass over `src/`.
- **Single-module generation is most reliable via CLI / Python.**
  Drive it with `attune workflow run test-gen --path <module>` or
  `TestGenerationWorkflow().execute(path=<module>)`.
