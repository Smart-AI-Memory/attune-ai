"""Task 2 wiring tests (6.2.0 spec): TaskBudget + thinking/effort.

Asserts that each of the three workflows forwards the token-aware
`task_budget` kwarg to `ClaudeAgentOptions`, and — only for
`depth="deep"` — the `thinking` + `effort` kwargs too. Standard /
quick runs must NOT pay for thinking they didn't ask for.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

pytest.importorskip("claude_agent_sdk")


@pytest.fixture(autouse=True)
def _force_cli_supports_task_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the CLI feature-probe to return True for wiring tests.

    ``get_task_budget()`` returns ``None`` when the resolved ``claude``
    CLI doesn't accept ``--task-budget`` (current bundled CLI doesn't).
    These tests are checking that workflows FORWARD ``task_budget`` to
    the SDK when the helper returns a value — they should not depend
    on which CLI happens to be installed. Override both the function
    and the cached result so any code path returns True.
    """
    import attune.models.sdk_adapter as mod

    monkeypatch.setattr(mod, "_CLI_SUPPORTS_TASK_BUDGET", True)
    monkeypatch.setattr(mod, "_cli_supports_task_budget", lambda: True)


# --- Pure helper tests ----------------------------------------------------


def test_get_task_budget_returns_total_for_each_depth() -> None:
    from attune.models.sdk_adapter import get_task_budget

    for depth, expected in [("quick", 20_000), ("standard", 80_000), ("deep", 200_000)]:
        tb = get_task_budget(depth)
        assert tb is not None, f"TaskBudget missing for {depth!r}"
        # TaskBudget is a TypedDict; access via mapping protocol.
        assert tb.get("total") == expected


def test_get_task_budget_respects_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from attune.models.sdk_adapter import get_task_budget

    monkeypatch.setenv("ATTUNE_TASK_BUDGET_TOKENS", "5000")
    tb = get_task_budget("standard")
    assert tb["total"] == 5000


def test_get_task_budget_ignores_bad_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from attune.models.sdk_adapter import get_task_budget

    monkeypatch.setenv("ATTUNE_TASK_BUDGET_TOKENS", "not-an-int")
    tb = get_task_budget("standard")
    # Falls back to the standard-depth default.
    assert tb["total"] == 80_000


def test_get_thinking_config_none_for_non_deep() -> None:
    from attune.models.sdk_adapter import get_thinking_config

    assert get_thinking_config("quick") is None
    assert get_thinking_config("standard") is None


def test_get_thinking_config_non_none_for_deep() -> None:
    from attune.models.sdk_adapter import get_thinking_config

    cfg = get_thinking_config("deep")
    assert cfg is not None


# --- Workflow wiring tests ------------------------------------------------


def _capture_options(wf_module_path: str, kwargs_bucket: dict) -> object:
    """Patch `ClaudeAgentOptions` on the target module to record kwargs."""
    import claude_agent_sdk

    real = claude_agent_sdk.ClaudeAgentOptions

    def _capture(**kw):
        kwargs_bucket.update(kw)
        return real(**kw)

    return patch(f"{wf_module_path}.claude_agent_sdk.ClaudeAgentOptions", _capture)


def _fake_stream(*_a, **_k):
    """Minimal async generator so `async for` completes without a real SDK run."""
    import claude_agent_sdk

    async def _gen():
        yield claude_agent_sdk.ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=0,
            session_id=None,
            total_cost_usd=0.0,
            usage={"input_tokens": 0, "output_tokens": 0},
            result=None,
            structured_output=None,
        )

    return _gen()


@pytest.fixture
def _patch_rag_pipeline(monkeypatch: pytest.MonkeyPatch):
    """rag_code_gen uses RagPipeline; stub so tests don't hit attune-help."""
    pytest.importorskip("attune_rag")

    class _FakeCitation:
        query = "q"
        hits = ()
        retriever_name = "Test"
        from datetime import datetime, timezone

        retrieved_at = datetime.now(timezone.utc)

    class _FakeResult:
        augmented_prompt = "### CONTEXT\n\n<passage>x</passage>\n\n### USER REQUEST\n\nhi"
        context = "<passage>x</passage>"
        citation = _FakeCitation()
        confidence = 1.0
        fallback_used = False
        elapsed_ms = 1.0

    class _FakePipeline:
        def run(self, *a, **k):
            return _FakeResult()

    monkeypatch.setattr(
        "attune.workflows.rag_code_gen.RagCodeGenWorkflow._get_pipeline",
        lambda self: _FakePipeline(),
    )


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_security_audit_forwards_task_budget(depth: str) -> None:
    from attune.workflows.security_audit import SecurityAuditWorkflow

    wf = SecurityAuditWorkflow()
    captured: dict[str, object] = {}

    with (
        _capture_options("attune.workflows.security_audit", captured),
        patch("attune.workflows.security_audit.claude_agent_sdk.query", _fake_stream),
    ):
        asyncio.run(wf.execute(path=".", depth=depth))

    assert "task_budget" in captured, f"task_budget missing for depth={depth!r}"
    # Standard/quick: no thinking. Deep: thinking + effort=high.
    if depth == "deep":
        assert captured.get("thinking") is not None
        assert captured.get("effort") == "high"
    else:
        assert "thinking" not in captured
        assert "effort" not in captured


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_code_review_forwards_task_budget(depth: str) -> None:
    from attune.workflows.code_review import CodeReviewWorkflow

    wf = CodeReviewWorkflow()
    captured: dict[str, object] = {}

    with (
        _capture_options("attune.workflows.code_review", captured),
        patch("attune.workflows.code_review.claude_agent_sdk.query", _fake_stream),
    ):
        asyncio.run(wf.execute(path=".", depth=depth))

    assert "task_budget" in captured, f"task_budget missing for depth={depth!r}"
    if depth == "deep":
        assert captured.get("thinking") is not None
        assert captured.get("effort") == "high"
    else:
        assert "thinking" not in captured
        assert "effort" not in captured


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_rag_code_gen_forwards_task_budget(depth: str, _patch_rag_pipeline: None) -> None:
    from attune.workflows.rag_code_gen import RagCodeGenWorkflow

    wf = RagCodeGenWorkflow()
    captured: dict[str, object] = {}

    with (
        _capture_options("attune.workflows.rag_code_gen", captured),
        patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", _fake_stream),
    ):
        asyncio.run(wf.execute(query="test query", depth=depth))

    assert "task_budget" in captured, f"task_budget missing for depth={depth!r}"
    if depth == "deep":
        assert captured.get("thinking") is not None
        assert captured.get("effort") == "high"
    else:
        assert "thinking" not in captured
        assert "effort" not in captured
