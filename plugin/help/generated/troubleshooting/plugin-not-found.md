---
name: plugin-not-found
source: CLAUDE.md Lessons Learned
summary: This template guides developers through diagnosing and resolving issues where
  Claude Code plugin skills like `/attune` commands are unavailable, including steps
  to verify installation, identify conflicts, and prevent future problems.
tags:
- claude-code
- plugin
- setup
type: troubleshooting
---

# Troubleshooting: Claude Code Plugin Skills Not Available

## Symptom

Typing `/attune` or other skill commands returns no matches in Claude Code.

## Diagnosis

Run the following checks in order:

1. **Confirm the plugin is installed:**
   ```bash
   claude plugin list
   ```
2. **Verify the marketplace source is registered:**
   ```bash
   claude plugin marketplace list
   ```
3. **Check for duplicate plugins** that may be conflicting with skill triggers.

## Fix

Reinstall the plugin using the commands below, then remove any conflicting plugins:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

## Prevention

Install only one Attune plugin variant at a time — either `attune-lite` or `attune-ai`, not both. Duplicate installations can cause conflicting skill triggers.

## Related Topics

- [Duplicate plugins cause conflicting skill triggers](#)
