---
type: faq
name: bare-manifest-in-gitignore-silently-excludes-any-manifest
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about bare MANIFEST in .gitignore silently excludes any manifest/ directory on case-insensitive filesystems?

## Answer

attune-author's `.gitignore` had a plain `MANIFEST` entry intended for setuptools' `MANIFEST` artifact. Combined with git's default case-insensitive matching on macOS/Windows, it also excluded the `.help/templates/manifest/` directory — 11 polished template files that existed locally but were never tracked.

**How to fix:**
- scope setuptools patterns to repo root (`/MANIFEST`, `/MANIFEST.in`)

```
.gitignore
```

## Related Topics
- **Error**: Detailed error: Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems
