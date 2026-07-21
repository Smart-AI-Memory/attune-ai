# Design — self-healing traps

**Status:** approved (2026-07-21 — chair approved design + T1-T5 via
AskUserQuestion; execute on rescue/self-healing-traps → PR #1554)

---

## Shape

One new plugin hook + a reworked `attune.telemetry.lessons` package
(rescued on PR #1554), integrating with the existing stash:

```
Bash tool result (PostToolUse)
  └─ plugin/hooks/trap_stash.py            (new hook, matcher: Bash)
       └─ attune.telemetry.lessons.listener.extract_trap(...)
            │  deterministic signature match → TrapEvent | None
       └─ attune.telemetry.lessons.synthesizer.format_trap(event)
            │  compact factual description (no canned prose)
       └─ attune.memory.session_stash.stash_entry(
              SessionStashEntry(type="bug",
                                tags=["trap", "trap:<family>"], ...))
```

## Components

- **`listener.py` (rework)** — pure functions over
  `(command, tool_result)`:
  - `extract_trap(command, output) -> TrapEvent | None`
  - Signature families (R6/non-goals: only these two):
    - `precommit_rejection` — output contains a pre-commit hook
      failure block (`- hook id:` + `Failed`, or the security-guard
      exit-2 marker) while the command is a `git commit` variant.
    - `pytest_failure` — output contains a pytest summary line
      (`= FAILURES =` / `short test summary info` with `FAILED …::`),
      any command. Extracts the first N failing node ids + the
      assertion tail.
  - `TrapEvent` dataclass: `family`, `signature` (stable dedupe key:
    e.g. hook id, or sorted failing node ids hash), `detail`
    (bounded excerpt), `command`.
- **`synthesizer.py` (shrink)** — `format_trap(event) -> str`:
  one-paragraph factual description ("pre-commit hook 'X' rejected
  `git commit` — <first error line>"). No "Prevention:" boilerplate,
  no truncated-ellipsis theater.
- **`hydrator.py` — DELETED** (R6). The curated corpus is out of
  scope; stash → `/recall` is the read path.
- **`plugin/hooks/trap_stash.py` (new)** — PostToolUse, matcher Bash:
  - reads `{tool_name, tool_input, tool_result}` payload (same shape
    `help_on_error.py` consumes);
  - per-session dedupe sentinel: `~/.attune/trap_stash/<session>.json`
    holding seen signatures (R3);
  - on match → `stash_entry` (existing PII gate + backend resolution;
    silent no-op without a backend, R4);
  - `ATTUNE_TRAP_STASH=0` disables; SDK-subprocess gated like
    sibling hooks; never exits non-zero.
- **`hooks.json`** — one PostToolUse/Bash entry, timeout 4000ms.

## Why type="bug" + tags, not a new type

`VALID_TYPES` is shared vocabulary mirrored from PersonalMemory;
traps are factually "a bug encountered". `tags=["trap",
"trap:precommit"|"trap:pytest"]` gives `/recall` filtering without
widening the type vocabulary.

## Testing (R5)

- Unit: signature extraction on real captured outputs (pre-commit
  failure block, pytest failure tail, negative cases: green run,
  non-commit command with "Failed" text).
- Round trip (non-mocked): tmp-dir file backend → feed a real failing
  pytest output through the hook via stdin subprocess → assert the
  entry lands in the backend and `recall_entries` finds it. Run
  serially.
- Live-fire (pre-ship receipt, recorded in decisions.md): trigger a
  real pre-commit rejection in a session with the hook registered;
  show the finding via `/recall`.

## Risks

- **Noise** (medium): red TDD loops → mitigated by per-session
  signature dedupe (R3) and the two-family scope.
- **Payload drift** (low): PostToolUse `tool_result` shape is already
  consumed by `help_on_error.py`; reuse its access pattern.
- **Backend absence** (low): silent no-op by contract (R4).
