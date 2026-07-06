# Stash Extractor Provenance — Requirements

**Status:** complete (2026-07-06) — shipped with the fix PR (single
PR, spec + change, the memorygraph-value-gate precedent).
**Born:** issue #1263 (2026-07-05 housekeeping session dogfood).

## Problem

The Stop-hook stash extractor (`plugin/hooks/session_stash.py`)
promotes *content the session merely read* into "session findings."
Evidence (2026-07-05): a session that spent most of its time reading
and editing memory files as data produced a stash where 3 of 5
findings were garbled paraphrases of the files under edit — one
inverted a memory file's meaning ("fatigue or ego does not
necessarily imply a low-quality work session"), one conflated two
unrelated memory files. The bad records had to be deleted by ID via
`agent_memory_client` (that gap is #1264 → `redis_memory_forget`).

## Root cause

`_read_transcript_tail` → `_text_of` recursively collects **all**
content blocks, including `tool_result` blocks — which are user-role
messages in the transcript JSONL. Every file the assistant Read
entered the extractor's input as `user: <file contents>`: the leaked
prose was not merely ambient, it was **mislabeled as user speech**.
Neither the Ollama prompt nor the heuristic fallback had any signal
to distinguish asserted-by-the-session from present-in-context.

## Requirements

- **R1 — role-faithful tail.** The extractor's transcript tail MUST
  exclude `tool_result` / `tool_use` block content, leaving a short
  omission marker so narrative flow survives. Assistant prose and
  genuine user text remain.
- **R2 — provenance-aware prompt.** The extraction prompt MUST
  instruct the model to extract only what the assistant concluded or
  the user decided, never restating file/tool contents.
- **R3 — heuristic parity.** The marker-line heuristic fallback
  benefits from R1 automatically (it reads the same tail); no
  separate filter.
- **R4 — no schema change.** Ambient content is dropped at
  extraction, not tagged; stash records keep their shape. A
  provenance ranking field is future work if evidence demands it.
- **R5 — deterministic failure replay.** Tests reproduce the
  2026-07-05 poisoning shape (tool_result carrying memory-file prose
  alongside real assistant conclusions) and assert: tool-result text
  absent from the tail, heuristic surfaces nothing from it, real
  assistant/user content survives.
