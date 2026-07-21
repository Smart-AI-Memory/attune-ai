# Handoff — rescue/self-healing-traps

**Branch:** `rescue/self-healing-traps` · **Status:** EXECUTED per
spec docs/specs/self-healing-traps/ (D1/D2 chair-ruled 2026-07-21);
PR #1554 carries the implementation.

## What landed

- `attune.telemetry.lessons`: `listener.py` (deterministic
  `extract_trap` — pre-commit rejection + pytest failure signatures),
  `synthesizer.py` (`format_trap`, factual, no boilerplate),
  `process_bash_result` composition in `__init__`. `hydrator.py`
  DELETED (D3 — no corpus writes).
- `plugin/hooks/trap_stash.py`: PostToolUse/Bash hook, per-session
  signature dedupe under `~/.attune/trap_stash/`,
  `ATTUNE_TRAP_STASH=0` disable, degrades open. Registered in
  `hooks.json`.
- Tests: 16 (extraction units on real output shapes; R5 non-mocked
  round trip through a real `FileStashBackend` → `recall_entries`;
  hook stdin subprocess round trips with HOME sandboxed and
  `AMS_BASE_URL` forced unreachable so no live backend is touched).

## Verified (receipts)

- `pytest tests/unit/telemetry/test_self_healing_traps.py
  tests/unit/hooks/test_trap_stash_hook.py` → 16 passed (serial).
- `tests/unit/plugins/test_plugin_config_validation.py` → green with
  the new hooks.json entry.
- Cleanup receipt: 5 entries leaked into the live AMS by a
  pre-isolation test run were forgotten (`backend.forget`, verified
  0 remaining).

## Remaining before spec flips to `shipped`

Live-fire receipt (requirements R5 / Done-when): in a real session
with the plugin hook active, hit a genuine pre-commit rejection or
pytest failure, then show the finding via `/recall`; record it in the
spec's decisions.md. Then merge PR #1554 and delete this file.
