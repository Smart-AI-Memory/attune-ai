---
type: faq
name: uv-pip-install-e-sibling-path-no-deps-is-the-clean-venv-local
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle uv pip install -e <sibling-path> --no-deps is the clean venv-local shadow when a sibling dep's in-flight version exceeds the current cap?

## Answer

attune-ai caps `attune-help>=0.5.1,<0.8` but we needed 0.9.0 visible in the venv for local testing before the cap bump lands. A plain `uv pip install -e ../attune-help/` might fail on cap resolution; `--force-reinstall --no-deps` bypasses dependency checks entirely and just drops the editable path in site-packages.

```
attune-help>=0.5.1,<0.8
```

## Related Topics
- **Error**: Detailed error: `uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap
