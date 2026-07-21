# Decisions — self-healing-traps

## D1 — Positioning: feed the existing stash (2026-07-21, Patrick)

Ruled via AskUserQuestion during the /spec pass on PR #1554's design
gate. Options offered: feed-the-stash (recommended) / full inbox /
close-as-duplicate / park-for-usage-signal. **Ruling: feed the
existing stash.** Traps become a deterministic, zero-LLM source for
`attune.memory.session_stash` — reusing the PII gate, backend
resolution, and `/recall` surfacing. No new user surface; the curated
`.claude/lessons.md` corpus stays fully human-ratified; the inbox
idea is DEFERRED until stash-sourced trap findings prove valuable in
recall (reopen condition: a ruled complaint that a valuable trap
finding died in the stash TTL without promotion).

## D2 — Capture seam: PostToolUse Bash hook (2026-07-21, Patrick)

Options offered: PostToolUse Bash hook (recommended) / pytest plugin /
both / Stop-hook-only. **Ruling: PostToolUse Bash hook.** Preserves
the moment-of-failure determinism that is this track's delta over the
end-of-session `session_stash` sweep. pytest-plugin seam explicitly
out of scope (revisit only with evidence that non-agent test runs are
a real capture gap).

## D3 — Rescued-code disposition (2026-07-21, agent, per D1)

Consequence of D1, recorded for the executor: `hydrator.py` deleted
(corpus writer with no role under D1); `synthesizer.py` reduced to a
factual stash-description formatter; `listener.py` reworked into the
deterministic signature extractor. PR #1554 is repurposed from
"rescue" to the implementation PR of this spec.

## D4 — Execution receipts (2026-07-21, agent)

T1-T4 executed on the branch (PR #1554): extract_trap two-family
listener, format_trap formatter, hydrator deleted, trap_stash.py
PostToolUse hook registered, per-session dedupe. Receipts: 16 tests
green including the R5 non-mocked FileStashBackend round trip
(write → recall verified on disk) and subprocess stdin round trips
through the real hook script (HOME sandboxed, AMS forced
unreachable). Guard suite test_plugin_config_validation green with
the new hooks.json entry. OPEN: live-fire /recall receipt in a real
session (required before status flips to shipped).
