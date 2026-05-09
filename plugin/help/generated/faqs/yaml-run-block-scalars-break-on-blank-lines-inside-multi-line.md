---
type: faq
name: yaml-run-block-scalars-break-on-blank-lines-inside-multi-line
tags: [imports, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does YAML run: block scalars break on blank lines inside multi-line bash strings?

## Answer

a `run:` block containing `git commit -m "line1\n\nline2"` (with a literal blank line in the heredoc) fails with `Implicit keys need to be on a single line` errors, because YAML's literal block scalar interprets the blank line as terminating the scalar. Related to the existing "YAML `run:` values with colons cause parse errors" lesson but the trigger is different — blank lines, not colons.

**How to fix:**
- build multi-line strings via shell grouping `{ echo 'line1'; echo; echo 'line2'; } > /tmp/msg.txt`, then pass via `-F /tmp/msg.txt` (git commit) or `--body-file /tmp/msg.txt` (gh pr create)
- Always verify YAML validity before pushing: `python -c "import yaml; yaml.safe_load(open('< workflow>.yml'))"`

```
 block containing
```

## Related Topics
- **Error**: Detailed error: YAML `run:` block scalars break on blank lines
  inside multi-line bash strings
