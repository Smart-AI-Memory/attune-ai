---
description: Generate a copy-pasteable resume prompt for a fresh Claude Code session
allowed-tools: Bash(python3:*)
---

You are generating a *resume prompt* the user will copy into a
new Claude Code session to pick up where this one left off.

Run the helper to produce the resume prompt:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_handoff_cli.py"
```

Print the helper's stdout **verbatim** as your reply. Do not add
commentary, headers, or framing — the user wants ONLY the
markdown blockquote so they can paste it directly.

The helper also appends the prompt to
`~/.attune/last-handoff.md` (timestamped, append-only) so the
user can recover earlier handoffs.
