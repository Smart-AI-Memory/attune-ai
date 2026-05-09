---
type: troubleshooting
name: workflow-not-running
tags: [workflow, auth, setup]
source: common support pattern
---

# Troubleshooting: Workflow won't run

## Symptom

Running `attune workflow run <name>` produces no output or an authentication error.

## Diagnosis

1. Check if ANTHROPIC_API_KEY is set: `echo $ANTHROPIC_API_KEY`
2. Verify the workflow name exists: `attune workflow list`
3. Run `attune auth status` to check authentication strategy
4. Run `attune doctor` for a full environment check

## Fix

Set your API key: `export ANTHROPIC_API_KEY=your-key`. If using subscription auth, run `attune auth setup`.

## Prevention

Add `ANTHROPIC_API_KEY` to your shell profile (`.zshrc` or `.bashrc`).

## Related Topics

_No related topics yet._
