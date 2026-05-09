---
type: faq
name: gh-workflow-run-file-yml-ref-tag-re-triggers-a-release-gated
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about gh workflow run <file.yml> --ref <tag> re-triggers a release-gated workflow cleanly without churning the release?

## Answer

When a `publish.yml` triggered by `release: types: [published]` fails on the first shot (e.g. invalid trusted publisher config on PyPI side), don't delete and recreate the release — if the workflow also declares `workflow_dispatch:`, `gh workflow run publish.yml --repo owner/repo --ref <tag>` fires a fresh run against the same tag, skipping the release-tag churn.

```
publish.yml
```

## Related Topics
- **Error**: Detailed error: `gh workflow run <file.yml> --ref <tag>` re-triggers
  a release-gated workflow cleanly without churning the
  release
