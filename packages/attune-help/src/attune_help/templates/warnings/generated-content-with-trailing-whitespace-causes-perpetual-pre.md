---
type: warning
name: generated-content-with-trailing-whitespace-causes-perpetual-pre
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Generated content with trailing whitespace causes perpetual
  pre-commit failures

## Condition

If a Jinja2 template renders source data that contains trailing spaces (e.g

## Risk

Ignoring this guidance may cause: Generated content with trailing whitespace causes perpetual
  pre-commit failures

## Mitigation

1. strip trailing whitespace per-line in the generator's render output before writing: `"\n".join(line.rstrip() for line in rendered .splitlines()) + "\n"`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Generated content with trailing whitespace causes perpetual
  pre-commit failures
