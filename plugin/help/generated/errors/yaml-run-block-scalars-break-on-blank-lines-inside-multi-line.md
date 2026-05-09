---
type: error
name: yaml-run-block-scalars-break-on-blank-lines-inside-multi-line
confidence: Verified
tags: [imports, git]
source: .claude/CLAUDE.md
---

# Error: YAML `run:` block scalars break on blank lines
  inside multi-line bash strings

## Signature

` (with a literal blank line in the heredoc) fails with `Implicit keys need to be on a single line` errors, because YAML's literal block scalar interprets the blank line as terminating the scalar. Fix: build multi-line strings via shell grouping `{ echo 'line1'; echo; echo 'line2'; } > /tmp/msg.txt`, then pass via `-F /tmp/msg.txt` (git commit) or `--body-file /tmp/msg.txt` (gh pr create). Related to the existing

## Root Cause

a `run:` block containing `git commit -m "line1\n\nline2"` (with a literal blank line in the heredoc) fails with `Implicit keys need to be on a single line` errors, because YAML's literal block scalar interprets the blank line as terminating the scalar.

## Resolution

1. build multi-line strings via shell grouping `{ echo 'line1'; echo; echo 'line2'; } > /tmp/msg.txt`, then pass via `-F /tmp/msg.txt` (git commit) or `--body-file /tmp/msg.txt` (gh pr create)
2. Always verify YAML validity before pushing: `python -c "import yaml; yaml.safe_load(open('< workflow>.yml'))"`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: YAML `run:` block scalars break on blank lines
  inside multi-line bash strings
