"""Tests for the generator <-> faithfulness wiring + telemetry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from attune.authoring.faithfulness import JudgeOutcome
from attune.authoring.generator import (
    _faithfulness_telemetry,
    _run_faithfulness_judge,
    reset_faithfulness_telemetry,
)


def _outcome(
    score: float | None, *, threshold_met: bool, skipped: str | None = None
) -> JudgeOutcome:
    return JudgeOutcome(
        score=score,
        threshold_met=threshold_met,
        cost_estimate_usd=0.0123,
        supported_claims=[],
        unsupported_claims=["bad"] if score is not None and not threshold_met else [],
        reasoning="r",
        skipped_reason=skipped,
    )


def setup_function() -> None:
    reset_faithfulness_telemetry()


def test_run_faithfulness_judge_disabled_via_env(tmp_path: Path, monkeypatch) -> None:
    """ATTUNE_AUTHOR_FAITHFULNESS=off short-circuits before doing any work."""
    monkeypatch.setenv("ATTUNE_AUTHOR_FAITHFULNESS", "off")
    polished = tmp_path / "x.md"
    polished.write_text("# x\n", encoding="utf-8")

    with patch("attune.authoring.faithfulness.judge_polished_file") as mock_judge:
        _run_faithfulness_judge(polished, [], tmp_path)

    mock_judge.assert_not_called()


def test_run_faithfulness_judge_disabled_via_config(tmp_path: Path) -> None:
    """No pyproject.toml -> config.enabled defaults to False -> no judge call."""
    polished = tmp_path / "x.md"
    polished.write_text("# x\n", encoding="utf-8")

    with patch("attune.authoring.faithfulness.judge_polished_file") as mock_judge:
        _run_faithfulness_judge(polished, [], tmp_path)

    mock_judge.assert_not_called()


def _enable_via_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.attune-author.fact-check.faithfulness]\nenabled = true\n",
        encoding="utf-8",
    )


def test_run_faithfulness_judge_telemetry_on_success(tmp_path: Path) -> None:
    _enable_via_pyproject(tmp_path)
    polished = tmp_path / "x.md"
    polished.write_text("# x\n", encoding="utf-8")

    outcome = _outcome(0.97, threshold_met=True)
    with patch("attune.authoring.faithfulness.judge_polished_file", return_value=outcome):
        _run_faithfulness_judge(polished, [], tmp_path)

    telemetry = _faithfulness_telemetry()
    assert telemetry["calls"] == 1
    assert telemetry["skipped"] == 0
    assert telemetry["cost_usd"] == 0.0123


def test_run_faithfulness_judge_telemetry_on_skip(tmp_path: Path) -> None:
    _enable_via_pyproject(tmp_path)
    polished = tmp_path / "x.md"
    polished.write_text("# x\n", encoding="utf-8")

    outcome = _outcome(None, threshold_met=True, skipped="over-budget")
    with patch("attune.authoring.faithfulness.judge_polished_file", return_value=outcome):
        _run_faithfulness_judge(polished, [], tmp_path)

    telemetry = _faithfulness_telemetry()
    assert telemetry["calls"] == 0
    assert telemetry["skipped"] == 1
    assert telemetry["cost_usd"] == 0


def test_run_faithfulness_judge_appends_review_block_when_below_threshold(
    tmp_path: Path,
) -> None:
    _enable_via_pyproject(tmp_path)
    polished = tmp_path / "x.md"
    polished.write_text("# Original\n", encoding="utf-8")

    outcome = _outcome(0.5, threshold_met=False)
    with patch("attune.authoring.faithfulness.judge_polished_file", return_value=outcome):
        _run_faithfulness_judge(polished, [], tmp_path)

    final = polished.read_text(encoding="utf-8")
    assert "## Faithfulness review" in final
    assert "bad" in final


def test_run_faithfulness_judge_swallows_unexpected_exceptions(tmp_path: Path) -> None:
    """A buggy judge layer must never break the polish pipeline."""
    _enable_via_pyproject(tmp_path)
    polished = tmp_path / "x.md"
    polished.write_text("# Original\n", encoding="utf-8")

    with patch(
        "attune.authoring.faithfulness.judge_polished_file",
        side_effect=RuntimeError("kaboom"),
    ):
        # Should not raise.
        _run_faithfulness_judge(polished, [], tmp_path)


def test_reset_faithfulness_telemetry_zeros_counters(tmp_path: Path) -> None:
    _enable_via_pyproject(tmp_path)
    polished = tmp_path / "x.md"
    polished.write_text("# x\n", encoding="utf-8")
    outcome = _outcome(0.97, threshold_met=True)
    with patch("attune.authoring.faithfulness.judge_polished_file", return_value=outcome):
        _run_faithfulness_judge(polished, [], tmp_path)

    reset_faithfulness_telemetry()
    telemetry = _faithfulness_telemetry()
    assert telemetry == {"calls": 0.0, "skipped": 0.0, "cost_usd": 0.0}
