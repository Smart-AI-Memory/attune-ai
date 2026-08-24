"""#2236 regression: NativeWorkflow parallel fan-out survives one raise.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio

import pytest

from attune.agent_factory.adapters.native import NativeWorkflow


class _FakeAgent:
    def __init__(self, name, *, raises=False):
        self.name = name
        self._raises = raises

    async def invoke(self, input_data, context):  # noqa: ANN001
        if self._raises:
            raise RuntimeError("agent exploded")
        return {"output": f"{self.name}-ok"}


class _Cfg:
    mode = "parallel"


@pytest.mark.asyncio
async def test_parallel_one_raise_yields_error_result_and_survivors():
    wf = NativeWorkflow(_Cfg(), [_FakeAgent("a"), _FakeAgent("b", raises=True)])
    results = await wf._run_parallel("hi")
    by_agent = {r["agent"]: r for r in results}
    assert by_agent["a"]["output"] == "a-ok"
    assert by_agent["b"]["success"] is False
    assert "RuntimeError" in by_agent["b"]["error"]


@pytest.mark.asyncio
async def test_parallel_cancellation_reraises():
    class _Cancelled(_FakeAgent):
        async def invoke(self, input_data, context):  # noqa: ANN001
            raise asyncio.CancelledError

    wf = NativeWorkflow(_Cfg(), [_Cancelled("c")])
    with pytest.raises(asyncio.CancelledError):
        await wf._run_parallel("hi")
