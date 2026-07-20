"""Unit tests for the SDK teardown-exit guard (``iter_agent_messages``).

Covers the recovery path (teardown exit after a success ResultMessage)
and — critically — the fail-closed paths the false-green constraint (D3)
demands: a failure before success, a non-success ResultMessage, a
non-teardown exception, and a BaseException all propagate unchanged.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import attune.workflows.agent_sdk_adapter as adapter
from attune.workflows.agent_sdk_adapter import iter_agent_messages


class _FakeResultMessage:
    """Stand-in for ``claude_agent_sdk.ResultMessage``."""

    def __init__(self, subtype: str = "success", is_error: bool = False):
        self.subtype = subtype
        self.is_error = is_error


class _FakeQuery:
    """A fake ``claude_agent_sdk.query()`` async iterable.

    Yields ``messages`` in order, then raises ``raise_after`` (if given)
    on the next ``__anext__`` — modelling the SDK's teardown exit that
    fires AFTER the final message was already streamed.
    """

    def __init__(self, messages, raise_after=None):
        self._messages = list(messages)
        self._raise_after = raise_after
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i < len(self._messages):
            msg = self._messages[self._i]
            self._i += 1
            return msg
        if self._raise_after is not None:
            exc = self._raise_after
            self._raise_after = None
            raise exc
        raise StopAsyncIteration


@pytest.fixture(autouse=True)
def _patch_result_message(monkeypatch):
    """Make isinstance(msg, claude_agent_sdk.ResultMessage) match our fake."""
    monkeypatch.setattr(adapter.claude_agent_sdk, "ResultMessage", _FakeResultMessage)


async def _drain(query):
    """Collect every message the wrapper yields."""
    return [m async for m in iter_agent_messages(query)]


_TEARDOWN = Exception("Command failed with exit code 1")


@pytest.mark.asyncio
async def test_recovers_teardown_exit_after_success():
    """R1: success ResultMessage then a teardown exit → stop cleanly."""
    assistant = object()
    success = _FakeResultMessage(subtype="success")
    msgs = await _drain(_FakeQuery([assistant, success], raise_after=_TEARDOWN))
    # All messages were yielded; the teardown exit did NOT propagate.
    assert msgs == [assistant, success]


@pytest.mark.asyncio
async def test_failure_before_success_propagates():
    """R2: a teardown-shaped exit before any success → fail closed."""
    with pytest.raises(Exception, match="Command failed"):
        await _drain(_FakeQuery([object()], raise_after=_TEARDOWN))


@pytest.mark.asyncio
async def test_non_success_result_then_teardown_propagates():
    """R3: error ResultMessage then teardown → not treated as success."""
    err = _FakeResultMessage(subtype="error_max_turns", is_error=True)
    with pytest.raises(Exception, match="Command failed"):
        await _drain(_FakeQuery([err], raise_after=_TEARDOWN))


@pytest.mark.asyncio
async def test_is_error_true_with_success_subtype_still_recovers():
    """D1: subtype drives success even when is_error is wrongly True.

    Guards the SDK 0.2.102 / CLI 2.1.178 window where a successful run
    reported is_error=True alongside subtype="success".
    """
    success = _FakeResultMessage(subtype="success", is_error=True)
    msgs = await _drain(_FakeQuery([success], raise_after=_TEARDOWN))
    assert msgs == [success]


@pytest.mark.asyncio
async def test_non_teardown_exception_after_success_propagates():
    """The conservative second gate: only 'command failed' is swallowed."""
    success = _FakeResultMessage(subtype="success")
    with pytest.raises(RuntimeError, match="something else"):
        await _drain(_FakeQuery([success], raise_after=RuntimeError("something else")))


@pytest.mark.asyncio
async def test_base_exception_never_swallowed():
    """KeyboardInterrupt propagates even after a successful result."""
    success = _FakeResultMessage(subtype="success")
    with pytest.raises(KeyboardInterrupt):
        await _drain(_FakeQuery([success], raise_after=KeyboardInterrupt()))


@pytest.mark.asyncio
async def test_clean_stream_passes_through():
    """No teardown exit: every message yielded, loop completes."""
    a, b = object(), _FakeResultMessage(subtype="success")
    assert await _drain(_FakeQuery([a, b])) == [a, b]


# Direct consumption of the raw SDK stream, e.g.
# ``async for message in claude_agent_sdk.query(...)``. Such a loop
# discards an already-successful result when the SDK subprocess raises
# during teardown — the exact failure class iter_agent_messages exists
# to fix.
_UNWRAPPED_LOOP_RE = re.compile(r"async for .+ in claude_agent_sdk\.query\(")


def test_every_workflow_query_loop_is_wrapped():
    """Drift guard: no workflow consumes claude_agent_sdk.query() bare.

    Every SDK consumption loop must go through iter_agent_messages so
    the teardown-exit guard applies. A new workflow (or a revert) that
    iterates the raw query stream reintroduces the discarded-success
    bug this spec fixed — fail loudly with the offending locations.
    """
    workflows_dir = Path(adapter.__file__).resolve().parent
    offenders: list[str] = []
    for path in sorted(workflows_dir.rglob("*.py")):
        if path.name == "agent_sdk_adapter.py":
            # The wrapper's own module documents the raw pattern.
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _UNWRAPPED_LOOP_RE.search(line):
                offenders.append(f"{path.relative_to(workflows_dir)}:{lineno}")
    assert not offenders, (
        "SDK consumption loops not wrapped in iter_agent_messages "
        f"(teardown-exit guard bypassed): {offenders}"
    )
