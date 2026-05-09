---
type: error
name: attune-workflow-run-code-review-and-security-audit-require-a
confidence: Verified
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: `attune workflow run code-review` and
  `security-audit` require a DIRECTORY for `--path`, not
  a single file — passing a file raises
  `NotADirectoryError` deep inside the Claude Agent SDK
  call

## Signature

`attune workflow run code-review` and
  `security-audit` require a DIRECTORY for `--path`, not
  a single file — passing a file raises
  `NotADirectoryError` deep inside the Claude Agent SDK
  call

## Root Cause

discovered while trying to deep-review two specific files (`rag_hook.py`, `rag_code_gen.py`). Direct file paths fail after a few seconds of spurious SDK spin-up (wasted API budget). Two ways to adapt: (a) pass the parent directory and filter the workflow's findings back down to your target file in post-processing — noisy, scanner reports issues in adjacent files as if they were in your scope; (b) abandon the workflow for single-file reviews and do direct reading + `grep`-based analysis — cheaper and more precise. For targeted reviews of 1–3 files, option (b) is strictly better. Reserve the workflow for directory-scoped passes (module, package, subsystem).

## Resolution

1. discovered while trying to deep-review two specific files (`rag_hook.py`, `rag_code_gen.py`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
