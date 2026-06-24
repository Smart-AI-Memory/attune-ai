---
type: comparison
name: help-system-comparison
feature: help-system
depth: comparison
generated_at: 2026-06-24T11:38:37.880839+00:00
source_hash: ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab
status: generated
---

# The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help

## Comparison

The help engine *produces and serves* help content; other surfaces
*author* or *display* it:

| | help-system (engine) | rollout tooling | ops-dashboard help tab |
|--|----------------------|-----------------|------------------------|
| Role | Discover/generate/populate/maintain templates | Author single-source masters → project them | Display coverage + search |
| Where | `src/attune/help/` | `scripts/project_features.py`, `content/features/` | `attune.ops.help_data` |
| Entry | `import attune.help` | `python scripts/project_features.py <F>` | `python -m attune.ops` |

The engine is the runtime; the rollout tooling is the authoring
pipeline; the ops dashboard is one read-only consumer.
