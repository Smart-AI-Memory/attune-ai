---
type: error
name: uv-pip-install-e-sibling-path-no-deps-is-the-clean-venv-local
confidence: Verified
tags: [testing, git, packaging]
source: .claude/CLAUDE.md
---

# Error: `uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap

## Signature

`uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap

## Root Cause

attune-ai caps `attune-help>=0.5.1,<0.8` but we needed 0.9.0 visible in the venv for local testing before the cap bump lands. A plain `uv pip install -e ../attune-help/` might fail on cap resolution; `--force-reinstall --no-deps` bypasses dependency checks entirely and just drops the editable path in site-packages. Any `uv sync` afterwards will overwrite it (per the existing lesson) — that's the intended property: shadow lives until the next sync cycle or a real release. Companion to the "`[tool.uv.sources]` overrides are discouraged" policy comment in attune-ai's pyproject.toml: use venv shadow, not a committed source override, when the cap bump isn't ready yet.

## Resolution

1. attune-ai caps `attune-help>=0.5.1,<0.8` but we needed 0.9.0 visible in the venv for local testing before the cap bump lands

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv pip install -e <sibling-path> --no-deps` is the
  clean venv-local shadow when a sibling dep's
  in-flight version exceeds the current cap
- Task: Update test mocks and assertions
