---
type: error
name: attune-author-check-staleness-load-manifest-is-the-python-api
confidence: Verified
tags: [ci, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection

## Signature

`attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection

## Root Cause

the `attune-author status` CLI emits only markdown tables. Parsing those with awk is brittle (divider rows sneak through, feature- name-starts-with-lowercase is hacky). The package exposes a clean Python path: `from attune_author import check_staleness, load_manifest; manifest = load_manifest(help_dir); report = check_staleness(manifest, help_dir, project_root); report.stale_features`. Use this anywhere automation would otherwise parse the status table (GitHub Actions, SessionStart hooks, pre-commit scripts). The CLI is for humans; the API is for automation.

## Resolution

1. Use this anywhere automation would otherwise parse the status table (GitHub Actions, SessionStart hooks, pre-commit scripts)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection
