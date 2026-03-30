---
type: troubleshooting
name: plugin-not-found
tags: [claude-code, plugin, setup]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: Claude Code plugin skills not available

## Symptom

Typing `/attune` or other skill commands shows no matches in Claude Code.

## Diagnosis

1. Check if plugin is installed: `claude plugin list`
2. Verify the marketplace was added: `claude plugin marketplace list`
3. Check for duplicate plugins that may conflict

## Fix

Reinstall: `claude plugin marketplace add Smart-AI-Memory/attune-ai && claude plugin install attune-ai@attune-ai`. Remove any conflicting plugins.

## Prevention

Only install one attune plugin (either attune-lite or attune-ai, not both).

## Related Topics
- **Error**: Duplicate plugins cause conflicting skill triggers
