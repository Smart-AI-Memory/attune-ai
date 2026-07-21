# Handoff — rescue/self-healing-traps

**Branch:** `rescue/self-healing-traps` · **Status:** DESIGN-GATED, do not merge as-is

## What this branch is

Rescue of Antigravity's "PR 3: Self-Healing Traps" track (round-table
thread `q-review-five-implementation-plans-001`), which was written to
the non-repo directory `~/antigravity IDE/` and would otherwise be lost.
Code: `src/attune/telemetry/lessons/` (listener, synthesizer, hydrator)
+ `tests/unit/telemetry/test_self_healing_traps.py`.

## What was verified

- `pytest tests/unit/telemetry/test_self_healing_traps.py` → 4 passed
  (they exercise dict construction and markdown formatting only).
- ruff/black clean; hydrator writes with `encoding="utf-8", newline="\n"`
  (the CRLF/cp1252 class fixed on main in #1536).
- The original docstring claimed Redis hydration; no Redis code exists.
  Claim removed.

## Why it is design-gated (must be ruled before wiring)

1. **The listener doesn't listen.** Both methods are dict constructors;
   nothing subscribes to pre-commit, pytest, or CLI failures. The
   integration (hook? pytest plugin? wrapper?) is the actual design
   decision and it is unmade.
2. **Curation gate.** `.claude/lessons.md` is a curated, human-ratified
   corpus. Auto-appending synthesized boilerplate ("Prevention: Inspect
   file parameters…") would pollute it. Any wiring must route through a
   review inbox / chair ruling, mirroring the round-table promotion
   pattern — never straight to the corpus.
3. **Duplication.** The repo already has a lessons pipeline (tracked
   corpus → Redis hydration at session start). This must integrate with
   that, not stand beside it.

## Next action

Chair rules on the design questions above (or routes them through
`/spec`). If ruled valuable: design the capture seam + inbox, then wire.
If not: close the PR; the rescue served its purpose.

Delete this file when the branch merges or closes.
