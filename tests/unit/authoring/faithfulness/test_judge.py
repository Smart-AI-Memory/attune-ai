"""Tests for the faithfulness judge wrapper."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from attune.authoring.faithfulness import (
    FaithfulnessConfig,
    JudgeOutcome,
    apply_review_block,
    estimate_cost_usd,
    format_review_block,
    judge_polished_file,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeJudgeResult:
    """Stand-in for ``attune_rag.eval.faithfulness.FaithfulnessResult``."""

    def __init__(
        self,
        score: float,
        supported: list[str] | None = None,
        unsupported: list[str] | None = None,
        reasoning: str = "",
    ) -> None:
        self.score = score
        self.supported_claims = supported or []
        self.unsupported_claims = unsupported or []
        self.reasoning = reasoning


def _install_fake_attune_rag(monkeypatch, judge_score: float, **kwargs):
    """Install a fake ``attune_rag.eval.faithfulness`` module into sys.modules.

    The fake exposes a ``FaithfulnessJudge`` whose ``score`` coroutine
    returns a ``_FakeJudgeResult`` with the given score.
    """

    class _FakeJudge:
        def __init__(self, model: str = "x", **_):
            self.model = model

        async def score(self, query, answer, passages):  # noqa: D401
            return _FakeJudgeResult(score=judge_score, **kwargs)

    fake_module = types.ModuleType("attune_rag.eval.faithfulness")
    fake_module.FaithfulnessJudge = _FakeJudge

    parent = types.ModuleType("attune_rag")
    eval_pkg = types.ModuleType("attune_rag.eval")
    eval_pkg.faithfulness = fake_module
    parent.eval = eval_pkg

    monkeypatch.setitem(sys.modules, "attune_rag", parent)
    monkeypatch.setitem(sys.modules, "attune_rag.eval", eval_pkg)
    monkeypatch.setitem(sys.modules, "attune_rag.eval.faithfulness", fake_module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret


def _block_attune_rag(monkeypatch) -> None:
    """Force ``import attune_rag.eval.faithfulness`` to fail with ImportError."""
    monkeypatch.setitem(sys.modules, "attune_rag.eval.faithfulness", None)


# ---------------------------------------------------------------------------
# estimate_cost_usd
# ---------------------------------------------------------------------------


def test_estimate_cost_haiku_cheaper_than_sonnet() -> None:
    haiku = estimate_cost_usd(10_000, model="claude-haiku-4-5")
    sonnet = estimate_cost_usd(10_000, model="claude-sonnet-4-6")
    assert haiku < sonnet


def test_estimate_cost_scales_with_input_size() -> None:
    small = estimate_cost_usd(1_000, model="claude-sonnet-4-6")
    big = estimate_cost_usd(10_000, model="claude-sonnet-4-6")
    assert big > small


def test_estimate_cost_unknown_model_falls_back_to_sonnet() -> None:
    unknown = estimate_cost_usd(10_000, model="unknown-future-model")
    sonnet = estimate_cost_usd(10_000, model="claude-sonnet-4-6")
    assert unknown == pytest.approx(sonnet)


# ---------------------------------------------------------------------------
# judge_polished_file — skip paths
# ---------------------------------------------------------------------------


def test_judge_skipped_when_disabled(tmp_path: Path) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Hi", encoding="utf-8")
    outcome = judge_polished_file(polished, [], config=FaithfulnessConfig(enabled=False))
    assert outcome.score is None
    assert outcome.skipped_reason == "disabled"
    assert outcome.threshold_met is True


def test_judge_skipped_when_polished_file_unreadable(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.md"
    outcome = judge_polished_file(missing, [], config=FaithfulnessConfig(enabled=True))
    assert outcome.score is None
    assert outcome.skipped_reason == "polished file unreadable"


def test_judge_skipped_when_no_readable_sources(tmp_path: Path) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Hi", encoding="utf-8")
    missing_src = tmp_path / "ghost.py"
    outcome = judge_polished_file(polished, [missing_src], config=FaithfulnessConfig(enabled=True))
    assert outcome.score is None
    assert outcome.skipped_reason == "no readable source passages"


def test_judge_skipped_when_over_budget(tmp_path: Path) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("x" * 200_000, encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("y" * 200_000, encoding="utf-8")
    config = FaithfulnessConfig(enabled=True, budget_per_file_usd=0.001)
    outcome = judge_polished_file(polished, [src], config=config)
    assert outcome.score is None
    assert outcome.skipped_reason == "over-budget"


def test_judge_skipped_when_attune_rag_missing(tmp_path: Path, monkeypatch) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Hi", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def x(): pass\n", encoding="utf-8")
    _block_attune_rag(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

    outcome = judge_polished_file(polished, [src], config=FaithfulnessConfig(enabled=True))

    assert outcome.score is None
    assert outcome.skipped_reason is not None
    assert "attune-rag" in outcome.skipped_reason


def test_judge_raises_when_block_polish_on_unavailable_and_extra_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Hi", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def x(): pass\n", encoding="utf-8")
    _block_attune_rag(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

    with pytest.raises(RuntimeError, match="attune-rag"):
        judge_polished_file(
            polished,
            [src],
            config=FaithfulnessConfig(enabled=True, block_polish_on_unavailable=True),
        )


def test_judge_skipped_when_api_key_missing(tmp_path: Path, monkeypatch) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Hi", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def x(): pass\n", encoding="utf-8")
    _install_fake_attune_rag(monkeypatch, judge_score=1.0)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    outcome = judge_polished_file(polished, [src], config=FaithfulnessConfig(enabled=True))

    assert outcome.score is None
    assert outcome.skipped_reason == "ANTHROPIC_API_KEY missing"


# ---------------------------------------------------------------------------
# judge_polished_file — happy path
# ---------------------------------------------------------------------------


def test_judge_runs_and_records_supported_claims(tmp_path: Path, monkeypatch) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("Polished content.", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def real(): pass\n", encoding="utf-8")

    _install_fake_attune_rag(
        monkeypatch,
        judge_score=0.97,
        supported=["claim a"],
        unsupported=[],
        reasoning="all good",
    )

    outcome = judge_polished_file(
        polished,
        [src],
        config=FaithfulnessConfig(enabled=True, threshold=0.95),
    )

    assert outcome.score == pytest.approx(0.97)
    assert outcome.threshold_met is True
    assert outcome.supported_claims == ["claim a"]


def test_judge_below_threshold_flags_threshold_not_met(
    tmp_path: Path,
    monkeypatch,
) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("Polished content.", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def real(): pass\n", encoding="utf-8")

    _install_fake_attune_rag(
        monkeypatch,
        judge_score=0.6,
        supported=["a"],
        unsupported=["b", "c"],
        reasoning="some drift",
    )

    outcome = judge_polished_file(
        polished,
        [src],
        config=FaithfulnessConfig(enabled=True, threshold=0.95),
    )

    assert outcome.score == pytest.approx(0.6)
    assert outcome.threshold_met is False
    assert outcome.unsupported_claims == ["b", "c"]


def test_judge_handles_transient_call_failure(tmp_path: Path, monkeypatch) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("Polished content.", encoding="utf-8")
    src = tmp_path / "src.py"
    src.write_text("def real(): pass\n", encoding="utf-8")

    fake_module = types.ModuleType("attune_rag.eval.faithfulness")

    class _BadJudge:
        def __init__(self, **_): ...

        async def score(self, query, answer, passages):
            raise RuntimeError("transient API failure")

    fake_module.FaithfulnessJudge = _BadJudge
    parent = types.ModuleType("attune_rag")
    eval_pkg = types.ModuleType("attune_rag.eval")
    eval_pkg.faithfulness = fake_module
    parent.eval = eval_pkg

    monkeypatch.setitem(sys.modules, "attune_rag", parent)
    monkeypatch.setitem(sys.modules, "attune_rag.eval", eval_pkg)
    monkeypatch.setitem(sys.modules, "attune_rag.eval.faithfulness", fake_module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

    outcome = judge_polished_file(polished, [src], config=FaithfulnessConfig(enabled=True))

    assert outcome.score is None
    assert outcome.skipped_reason is not None
    assert "judge call failed" in outcome.skipped_reason


# ---------------------------------------------------------------------------
# format_review_block + apply_review_block
# ---------------------------------------------------------------------------


def test_format_review_block_returns_empty_when_score_is_none() -> None:
    outcome = JudgeOutcome(
        score=None,
        threshold_met=True,
        cost_estimate_usd=0.0,
        supported_claims=[],
        unsupported_claims=[],
        reasoning="",
    )
    assert format_review_block(outcome, threshold=0.95) == ""


def test_format_review_block_lists_unsupported_claims() -> None:
    outcome = JudgeOutcome(
        score=0.5,
        threshold_met=False,
        cost_estimate_usd=0.01,
        supported_claims=["good"],
        unsupported_claims=["bad-1", "bad-2"],
        reasoning="explanation",
    )
    block = format_review_block(outcome, threshold=0.95)
    assert "## Faithfulness review" in block
    assert "Score 0.50" in block or "Score** 0.50" in block
    assert "bad-1" in block
    assert "bad-2" in block
    assert "explanation" in block


def test_apply_review_block_appends_block(tmp_path: Path) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Original\n\nBody.", encoding="utf-8")
    outcome = JudgeOutcome(
        score=0.5,
        threshold_met=False,
        cost_estimate_usd=0.01,
        supported_claims=[],
        unsupported_claims=["x"],
        reasoning="r",
    )
    block = format_review_block(outcome, threshold=0.95)
    appended = apply_review_block(polished, block)
    assert appended is True
    final = polished.read_text(encoding="utf-8")
    assert "# Original" in final
    assert "## Faithfulness review" in final


def test_apply_review_block_returns_false_on_empty(tmp_path: Path) -> None:
    polished = tmp_path / "doc.md"
    polished.write_text("# Original", encoding="utf-8")
    assert apply_review_block(polished, "") is False
