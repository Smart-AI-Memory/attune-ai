# Spec: Self-Healing Traps — deterministic failure capture into the stash

> When a pre-commit hook rejects a commit or a test run fails inside an
> agent session, capture structured failure telemetry AT THE MOMENT OF
> FAILURE and feed it to the existing session-stash/recall pipeline —
> so the next session that hits the same wall finds the prior
> encounter via `/recall` instead of rediscovering it.

**Status:** shipped (2026-07-21 — merged in #1554; live-fire
receipt recorded in decisions.md D5)
**Owner:** Patrick + agent
**Related:** PR #1554 (rescue branch), `plugin/hooks/session_stash.py`,
`attune.memory.session_stash`, docs/handoffs/rescue-self-healing-traps.md

---

## Problem

Failure events with durable diagnostic value (pre-commit rejections,
pytest failures) are currently captured only IF the end-of-session
`session_stash` LLM/heuristic sweep happens to surface them from the
transcript tail — best-effort, lossy, and end-of-session. The rescued
Antigravity code (PR #1554) named the right events but had no capture
seam and wrote canned lessons straight toward the curated corpus.

## Requirements

- **R1 (positioning, D1):** Traps are a deterministic, zero-LLM SOURCE
  for the existing stash — `attune.memory.session_stash.stash_entry`
  with a distinct type. NO new user surface, NO writes to
  `.claude/lessons.md` (the curated corpus stays human-ratified), NO
  inbox (deferred until stash-sourced findings prove valuable).
- **R2 (seam, D2):** Capture happens in a PostToolUse Bash plugin
  hook matching failure signatures in tool output. Stop-hook and
  pytest-plugin seams are explicitly out of scope for this spec.
- **R3 (dedupe):** At most one stash entry per distinct failure
  signature per session — a red TDD loop must not spam the stash.
- **R4 (degrade silently):** The hook never blocks or breaks a tool
  call; backend-unreachable means skip, per the memory-layer contract.
- **R5 (receipt):** A non-mocked round trip — real failing output →
  hook → stash file/backend → retrievable — plus live-fire evidence
  from a real session before the spec flips to shipped.
- **R6 (cleanup):** The rescued `hydrator.py` (corpus writer) is
  deleted; `synthesizer.py` shrinks to a compact stash-description
  formatter (no canned "Prevention:" prose); `listener.py` becomes the
  signature-matching extractor.

## Non-goals

- LLM synthesis of lessons (the stash summary/Ollama path already
  exists downstream).
- Writing to the curated lessons corpus or any auto-ratification.
- Capturing CLI failures beyond the two signature families named
  (pre-commit rejection, pytest failure) — extend later by evidence.

## Done when

- Trap hook registered in `plugin/hooks/hooks.json`, green CI.
- Non-mocked round-trip test passes serially.
- A real session's pre-commit failure appears in `/recall` output
  (live-fire receipt recorded in decisions.md).
- PR #1554 (repurposed) merged; handoff file deleted.
