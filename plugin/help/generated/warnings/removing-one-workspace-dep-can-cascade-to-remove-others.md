---
type: warning
name: removing-one-workspace-dep-can-cascade-to-remove-others
confidence: Verified
tags: [imports, git]
source: .claude/CLAUDE.md
---

# Warning: Removing one workspace dep can cascade to remove
  others

## Condition

When `attune-ai` declared `attune-author` as a core dep, the lockfile also pulled in `attune-help` (because `attune-author` depends on it)

## Risk

In our case, `attune.help.preamble` already did `try: from attune_help.preamble import _extract_preamble except ImportError: ...` — so the loss was safe — but this is the kind of thing that breaks silently in production if you skip the verification step

## Mitigation

1. Always check the cascade with `uv lock` *before* committing, and verify that any code importing the cascaded-out package has a try/except fallback

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Removing one workspace dep can cascade to remove
  others
