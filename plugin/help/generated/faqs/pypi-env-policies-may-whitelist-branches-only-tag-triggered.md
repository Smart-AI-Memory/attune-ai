---
type: faq
name: pypi-env-policies-may-whitelist-branches-only-tag-triggered
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why does pyPI env policies may whitelist branches only — tag- triggered publishes get rejected?

## Answer

`pypi` environment deployment branch policies on attune-ai allowed `main` and `release/*` branches but not any tag pattern. A `publish-pypi.yml` run fired by `release: types: [published]` executes against the tag ref (`refs/tags/v6.1.0`), which the env rejected with "Tag <X> is not allowed to deploy due to environment protection rules." Previous releases never hit this because they all ran via `workflow_dispatch --ref main`.

```
 environment deployment branch policies on attune-ai allowed
```

## Related Topics
- **Error**: Detailed error: PyPI env policies may whitelist branches only — tag-
  triggered publishes get rejected
