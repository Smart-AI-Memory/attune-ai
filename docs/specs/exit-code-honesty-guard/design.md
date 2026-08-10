# Exit-Code Honesty Guard — Design

**Status:** draft (2026-08-10) — awaiting chair review. Authored
under the requirements' authorization ("Design/tasks may now be
authored"); implementation authority begins at the next phase gate.
**Requirements:** [requirements.md](requirements.md) (approved
2026-08-09)

## Code reality (verified 2026-08-10)

`run_workflow_with_exit_code` (`src/attune/cli_commands/
_exit_codes.py`) has THREE post-result steps; only one is guarded:

| Step | Line region | Guarded today? |
| --- | --- | --- |
| `_emit_json_result` (json mode) | 198–199 | NO |
| `print_result` (human mode) | 200–201 | NO |
| `on_result` (spend-gate record) | 203–211 | yes (local try) |

An exception in either unguarded step propagates out of the
function after `exit_code` was already determined — the caller
crashes and the process exits with a code the workflow outcome
never produced. This is precisely the #1904 class (run
`87d8438e3e8c`: SUCCEEDED review exited 1 from post-success
run-meta emission).

## D-1 — One guard at the orchestrator layer (R2)

All three post-result steps run through a single local helper:

```python
def _post_result_step(label: str, step: Callable[[], None]) -> None:
    try:
        step()
    except Exception:  # noqa: BLE001
        # INTENTIONAL (exit-code-honesty-guard): post-result
        # plumbing must never overwrite the result-derived exit
        # code. The visibility actions below are themselves
        # post-result plumbing (a failing log handler, a closed
        # stderr pipe — the #1904 vector — or a Windows cp1252
        # encoding error can raise here too), so each is
        # individually suppressed. ASCII-only message by design.
        with contextlib.suppress(Exception):
            logger.exception(
                "post-result step %r failed; exit code preserved",
                label,
            )
        with contextlib.suppress(Exception):
            print(
                f"warning: post-result step '{label}' failed; "
                "exit code unchanged",
                file=sys.stderr,
            )
```

The handler hardening (nested `suppress`, ASCII-only stderr text)
is a cross-review lane adoption — codex flagged that an unguarded
`logger.exception` / emoji-bearing `print` inside the guard could
itself raise and re-corrupt the exit code, which is the exact
class this spec exists to contain (R5 ledger row, 2026-08-10).

`exit_code` is computed BEFORE any of the three steps (already
true today, line 196) and returned unconditionally after them.
Callbacks are not trusted to guard themselves; `on_result`'s
existing local guard becomes redundant and is removed in favor of
the shared helper (one mechanism, not two).

Uncaught exceptions BEFORE the result exists keep the existing
exit-2 contract untouched (the `except Exception` around
`execute()`, lines 184–194).

## D-2 — Rendering-failure semantics

When `print_result` / `_emit_json_result` dies, stdout may be
empty or truncated while the process exits 0/1. This is the
designed trade: `$?` is already documented as authoritative and
the JSON contract fields are "a convenience mirror"
(`_emit_json_result` docstring). The stderr warning plus the
logged event make the breakage visible without corrupting the
exit-code contract. Consumers that require rendered output must
treat empty-stdout-with-exit-0 as a plumbing alarm, not a result.

## D-3 — Q1 answer (proposed): named log event, no new persistence

The guard logs via `logger.exception` with the stable message
prefix `post-result step` — grep-able in daemon/CI logs. Chronic
breakage shows up as repetition of one label. A run-record
annotation is NOT added now: the annotation writer is itself
post-result plumbing (the class this spec exists to contain), and
wiring it in would put a failure-prone step inside the failure
handler. Reopen trigger: stderr warnings observed recurring across
runs while nobody notices — evidence that log-only visibility is
insufficient.

## D-4 — Q2 answer (proposed): MCP path out of scope

`_workflow_response` (`src/attune/mcp/workflow_handlers.py`)
returns a `success` FIELD in a JSON response — there is no process
exit code to overwrite, and its error-shape contract has its own
tests. The failure class doesn't map 1:1. Deferred with a named
reopen trigger: an MCP handler observed returning an error shape
for a workflow whose `execute()` succeeded, caused by post-result
plumbing.

## Test design (R1/R3 — the drift guard)

New file `tests/unit/cli_commands/test_exit_code_honesty_guard.py`,
parametrized over the three hook points (raising `print_result`,
raising `on_result`, json mode with emission forced to raise):

- successful `WorkflowResult` + raising step → returns
  `EXIT_SUCCESS` (0), stderr carries the warning line;
- planned-failure result + raising step → returns
  `EXIT_PLANNED_FAILURE` (1), same warning;
- `execute()` raising → still `EXIT_UNPLANNED_FAILURE` (2)
  (contract untouched — guard applies only after a result exists);
- the guard holds even with `_emit_run_meta_for_daemon`'s internal
  OSError catch removed from the picture (R1's refactor-away
  clause): the injected `print_result` raises unconditionally, so
  the test never depends on the callback's own defenses;
- the HANDLER itself is failure-proof (codex lane finding): with a
  raising step AND `sys.stderr` replaced by a raising writer AND a
  logging handler that raises, the function still returns the
  result-derived code — nothing escapes.

Red-before/green-after is recorded in decisions.md at
implementation time (acceptance criterion), alongside a serial run
of the #1904 suite (`tests/unit/cli/
test_workflow_commands_run_meta.py`) proving it unchanged.
