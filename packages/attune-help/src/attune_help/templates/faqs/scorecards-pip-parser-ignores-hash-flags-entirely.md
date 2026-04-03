---
type: faq
name: scorecards-pip-parser-ignores-hash-flags-entirely
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about scorecard's pip parser ignores --hash flags entirely?

## Answer

Even single-line `pip3 install 'pkg==1.0' --hash=sha256:abc...` is flagged as "not pinned by hash". Scorecard's `PinnedDependenciesID` check does not recognize pip's `--hash` CLI flag — it only recognizes `--require-hashes` with a requirements file, or possibly other formats.

```
pip3 install 'pkg==1.0' --hash=sha256:abc...
```

## Related Topics
- **Error**: Detailed error: Scorecard's pip parser ignores `--hash` flags entirely
