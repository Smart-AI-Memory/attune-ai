---
type: faq
name: pypi-environment-requires-manual-approval-in-github-actions
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about pypi environment requires manual approval in GitHub Actions?

## Answer

The `publish-pypi.yml` workflow uses `environment: pypi` which has a required reviewer gate. After the build job passes, the publish job appears to be "running" but is actually waiting for approval at the Actions run page.

```
publish-pypi.yml
```

## Related Topics
- **Error**: Detailed error: `pypi` environment requires manual approval in GitHub Actions
