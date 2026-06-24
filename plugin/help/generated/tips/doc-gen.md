---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: tip
---

# Generate new documentation from source code with three specialized subagents

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `DocumentGenerationWorkflow` and its async `execute` (plus the
  `default_context` classmethod for composition), and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_gen`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Audit first, then generate.** Run doc-audit to find the gaps,
  then point doc-gen at the modules that need new content.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one module is far faster than a `deep` pass over `src/`.
- **Take the output from `final_output`.** Doc-gen returns
  generated content; review it and place it where it belongs.
