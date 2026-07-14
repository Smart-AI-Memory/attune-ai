# Design: SDK teardown-exit-1 guard

**Status:** DRAFT (2026-06-26) — recommitted at 2026-07-14 triage (failure class still live)
**Requirements:** [requirements.md](requirements.md) ·
**Decisions:** [decisions.md](decisions.md)

---

## Architecture

A single async wrapper sits between each workflow's consumption loop and
`claude_agent_sdk.query()`. It passes every message straight through
(so `collect_agent_output` works unchanged), remembers whether a
`subtype="success"` `ResultMessage` was seen, and — only then — swallows
a subsequent teardown "Command failed" exit so the caller's loop ends
normally and returns its already-captured result.

```text
workflow loop
  async for message in iter_agent_messages(claude_agent_sdk.query(...)):
        |                         |
        |                         +-- wraps the SDK async iterator
        |                             - yields each message unchanged
        |                             - sets saw_success on ResultMessage(subtype="success")
        |                             - on __anext__ raising:
        |                                 saw_success and benign-teardown -> stop (recover)
        |                                 else                            -> re-raise (fail closed)
        +-- collect_agent_output(message, ...) -> run_result   (UNCHANGED)
  run_result.result_text = build_result_text(...)   # now reached on teardown-after-success
  return run_result
```

The guard changes only *when the loop stops*, never *what messages the
loop sees*. `collect_agent_output`, `build_result_text`, scoring, and the
diagnostic path are untouched.

### The wrapper (new, in `agent_sdk_adapter.py`)

```python
async def iter_agent_messages(query: AsyncIterator[Any]) -> AsyncIterator[Any]:
    """Yield SDK messages, recovering from a teardown exit after success.

    Wraps ``claude_agent_sdk.query(...)``. Passes every message through
    unchanged. If the underlying stream raises a benign teardown
    "Command failed" exception AFTER a ``ResultMessage(subtype="success")``
    was already yielded, stop cleanly so the caller returns its captured
    result. Any other exception — or one before success — propagates,
    preserving fail-closed semantics (never a false green).
    """
    saw_success = False
    iterator = query.__aiter__()
    while True:
        try:
            message = await iterator.__anext__()
        except StopAsyncIteration:
            return
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: a non-zero teardown exit AFTER a successful
            # ResultMessage is benign — the work completed; recover it.
            # Anything else (incl. pre-success failures) re-raises so a
            # genuine error never fake-passes.
            if saw_success and _is_benign_teardown_exit(exc):
                logger.warning(
                    "SDK exited non-zero after a successful ResultMessage; "
                    "surfacing captured result (%s)",
                    exc,
                )
                return
            raise
        if (
            isinstance(message, claude_agent_sdk.ResultMessage)
            and getattr(message, "subtype", None) == "success"
        ):
            saw_success = True
        yield message


def _is_benign_teardown_exit(exc: Exception) -> bool:
    """True for the SDK's bare post-result 'Command failed' teardown exit."""
    return "command failed" in str(exc).lower()
```

`BaseException` (KeyboardInterrupt / SystemExit / CancelledError) is never
caught — only `Exception`. The `saw_success` gate is the primary safety;
the message match is a conservative second gate so an unrelated bug in our
own message handling is not silently swallowed.

### Success signal (OQ1 → D1): `subtype == "success"`

Use `ResultMessage.subtype == "success"`, **not** `not is_error`. SDK
0.2.102 / bundled CLI 2.1.178 emitted `is_error=True` *together with*
`subtype="success"` on successful runs (fixed in CLI 2.1.183 / SDK
0.2.105). `subtype` was correct throughout that window, so it is the
trustworthy marker across pins. `collect_agent_output` already records
`subtype`, so no new capture is needed.

---

## Adoption — one line per workflow

Each of the eight SDK workflows changes its loop header only:

```python
# BEFORE
async for message in claude_agent_sdk.query(prompt=..., options=...):

# AFTER
async for message in iter_agent_messages(
    claude_agent_sdk.query(prompt=..., options=...)
):
```

Workflows: `code_review`, `security_audit`, `perf_audit`,
`dependency_check`, `bug_predict`, `rag_code_gen`, `research_synthesis`,
`simplify_code`. No other change to their bodies — `collect_agent_output`
and the post-loop `build_result_text` / `return` stay as-is.

---

## File plan

### Create

- `tests/unit/workflows/test_iter_agent_messages.py` — fake async streams
  exercising R1/R2/R3 (success-then-teardown recovers; pre-success raise
  propagates; error/non-success ResultMessage then teardown not masked;
  `BaseException` passes through).

### Modify

- `src/attune/workflows/agent_sdk_adapter.py` — add `iter_agent_messages`
  + `_is_benign_teardown_exit`; export them.
- The eight workflow modules — wrap the `claude_agent_sdk.query(...)`
  call in `iter_agent_messages(...)` (one line each).
- `CHANGELOG.md` — `### Fixed` entry.

---

## Tasks

```xml
<task id="1" name="teardown-guard-helper">
  <objective>
    Add iter_agent_messages + _is_benign_teardown_exit to
    agent_sdk_adapter.py: pass messages through, track a
    subtype="success" ResultMessage, and swallow a benign teardown
    "Command failed" exit ONLY after success; re-raise otherwise.
  </objective>
  <context>
    <existing-code path="src/attune/workflows/agent_sdk_adapter.py">
      collect_agent_output (captures ResultMessage incl. subtype);
      capture_subprocess_failure (diagnostic path for genuine failures).
    </existing-code>
  </context>
  <files-to-create>
    <file path="tests/unit/workflows/test_iter_agent_messages.py">
      Fake async iterators: (a) [AssistantMessage, ResultMessage(success)]
      then raise Exception("Command failed with exit code 1") -> wrapper
      stops cleanly, all messages yielded; (b) raise before any
      ResultMessage -> propagates; (c) ResultMessage(subtype="error...")
      then teardown -> propagates; (d) KeyboardInterrupt -> propagates.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/workflows/agent_sdk_adapter.py">
      <change location="module functions">
        Add async generator iter_agent_messages(query) and
        _is_benign_teardown_exit(exc); guard on saw_success + message match.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>pytest tests/unit/workflows/test_iter_agent_messages.py green</check>
    <check>R2/R3: pre-success or non-success-then-teardown re-raises</check>
  </validation>
  <risks>
    <risk severity="medium">Over-broad swallow masks a real failure —
      mitigated by the saw_success gate + subtype="success" signal + the
      "command failed" message match; BaseException never caught.</risk>
  </risks>
</task>

<task id="2" name="adopt-across-workflows">
  <objective>
    Wrap each SDK workflow's claude_agent_sdk.query(...) call in
    iter_agent_messages(...) — one line each — so the teardown guard
    applies everywhere. No other body changes.
  </objective>
  <files-to-modify>
    <file path="src/attune/workflows/code_review.py" />
    <file path="src/attune/workflows/security_audit.py" />
    <file path="src/attune/workflows/perf_audit.py" />
    <file path="src/attune/workflows/dependency_check.py" />
    <file path="src/attune/workflows/bug_predict.py" />
    <file path="src/attune/workflows/rag_code_gen.py" />
    <file path="src/attune/workflows/research_synthesis.py" />
    <file path="src/attune/workflows/simplify_code.py" />
  </files-to-modify>
  <validation>
    <check>Existing per-workflow unit tests stay green</check>
    <check>grep confirms every claude_agent_sdk.query( in workflows/ is
      wrapped by iter_agent_messages(</check>
  </validation>
</task>

<task id="3" name="dogfood-receipt">
  <objective>
    Optional non-mocked receipt: run a real workflow nested-in-session
    via the env-scrub and confirm it now returns success (not the
    teardown false-negative). Documents the fix works end-to-end.
  </objective>
  <validation>
    <check>With the guard, a real code-review over a temp file returns
      success=True + a score + cost > 0 even nested in a session</check>
  </validation>
  <risks>
    <risk severity="low">Real API spend; gate behind a manual/keyed run
      like the generic-agent-teams R5 dogfood. Not a CI test.</risk>
  </risks>
</task>

<task id="4" name="finalize-docs">
  <objective>
    CHANGELOG ### Fixed entry; decisions.md final (D1 success signal, D2
    wrapper shape, D3 false-green constraint).
  </objective>
  <files-to-modify>
    <file path="CHANGELOG.md" />
  </files-to-modify>
</task>
```

---

## Sequencing

T1 (guard + unit proof) → T2 (adopt everywhere) → T3 (optional real
dogfood receipt) → T4 (lock). T1+T2 fix the bug for all workflows; T3 is
the end-to-end receipt analogous to generic-agent-teams' R5.
