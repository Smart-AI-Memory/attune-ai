---
type: warning
name: uv-pip-install-e-sibling-path-no-deps-is-the-clean-venv-local
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Warning: `uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap

## Condition

attune-ai caps `attune-help>=0.5.1,<0.8` but we needed 0.9.0 visible in the venv for local testing before the cap bump lands

## Risk

A plain `uv pip install -e ../attune-help/` might fail on cap resolution; `--force-reinstall --no-deps` bypasses dependency checks entirely and just drops the editable path in site-packages

## Mitigation

1. attune-ai caps `attune-help>=0.5.1,<0.8` but we needed 0.9.0 visible in the venv for local testing before the cap bump lands

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap
