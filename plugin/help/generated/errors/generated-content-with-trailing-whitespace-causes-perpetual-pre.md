---
type: error
name: generated-content-with-trailing-whitespace-causes-perpetual-pre
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Generated content with trailing whitespace causes perpetual
  pre-commit failures

## Signature

Generated content with trailing whitespace causes perpetual
  pre-commit failures

## Root Cause

If a Jinja2 template renders source data that contains trailing spaces (e.g. a sentence ending with "after "), the `trailing-whitespace` pre-commit hook strips it on commit. But the generator reproduces the trailing space on the next run, so `--check` mode always reports "out of sync".

## Resolution

1. strip trailing whitespace per-line in the generator's render output before writing: `"\n".join(line.rstrip() for line in rendered .splitlines()) + "\n"`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Generated content with trailing whitespace causes perpetual
  pre-commit failures
