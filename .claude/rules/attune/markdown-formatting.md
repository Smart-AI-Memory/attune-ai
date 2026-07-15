---
paths:
  - "**/*.md"
---

# Markdown Formatting

**Migrated:** 2026-07-15 (from `.claude/CLAUDE.md`, via `/doctor`
lazy-loading check) — task-specific, only relevant when authoring
or editing `.md` files.

---

All `.md` files should follow these rules:

- Start every `.md` file with a single `#` (h1) heading
- Heading levels must increment by one (don't skip from
  `#` to `###`)
- Put a single space after `#` in headings
- Surround headings with blank lines (one above, one below)
- Surround fenced code blocks (```) with blank lines
- Surround lists with blank lines
- Use `-` (dash) for unordered list markers, not `*` or `+`
- No trailing whitespace on lines
- No hard tabs — use spaces
- No multiple consecutive blank lines
- End files with a single trailing newline
- Keep lines under 80 characters (except tables and URLs)
- Do not manually pad or align table cells with extra
  spaces — tables are exempt from trailing space rules
