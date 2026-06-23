---
type: tip
name: smart-test-tip
feature: smart-test
depth: tip
generated_at: 2026-06-23T15:57:46.208360+00:00
source_hash: d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe
status: generated
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
