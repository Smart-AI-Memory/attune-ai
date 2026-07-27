"""Error-path tests for ``_parallel_polish``.

The audit identified the parallel-polish error paths as a real coverage
gap. ``_parallel_polish`` runs ``_maybe_polish`` across a ThreadPoolExecutor
and propagates the first exception via ``Future.result()``. These tests
inject failures into ``_maybe_polish`` and assert the cascade behavior
without spending API tokens.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.authoring.generator import _parallel_polish
from attune.authoring.manifest import Feature
from attune.authoring.polish import PolishError


@pytest.fixture
def feature() -> Feature:
    return Feature(
        name="auth",
        description="Auth module",
        files=["src/auth/**"],
        tags=["security"],
    )


def _pending(tmp_path: Path, n: int) -> list[tuple[str, str, Path]]:
    """Build a list of ``(depth, content, out_path)`` tuples for testing."""
    return [(f"depth_{i}", f"content_{i}", tmp_path / f"out_{i}.md") for i in range(n)]


# ---------------------------------------------------------------------------
# Happy path — establishes the baseline behavior
# ---------------------------------------------------------------------------


def test_parallel_polish_returns_dict_keyed_by_depth(tmp_path: Path, feature: Feature) -> None:
    pending = _pending(tmp_path, 3)
    with patch(
        "attune.authoring.generator._maybe_polish",
        side_effect=lambda content, *a, **kw: f"polished:{content}",
    ):
        results = _parallel_polish(
            pending=pending, feature=feature, source_info=object(), use_rag=False
        )
    assert set(results) == {"depth_0", "depth_1", "depth_2"}
    for depth, (polished, out_path) in results.items():
        idx = depth.split("_")[1]
        assert polished == f"polished:content_{idx}"
        assert out_path == tmp_path / f"out_{idx}.md"


def test_parallel_polish_handles_single_pending_item(tmp_path: Path, feature: Feature) -> None:
    pending = _pending(tmp_path, 1)
    with patch(
        "attune.authoring.generator._maybe_polish",
        side_effect=lambda content, *a, **kw: content.upper(),
    ):
        results = _parallel_polish(
            pending=pending, feature=feature, source_info=object(), use_rag=False
        )
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Error injection — first failure propagates via Future.result()
# ---------------------------------------------------------------------------


def test_parallel_polish_propagates_polish_error(tmp_path: Path, feature: Feature) -> None:
    """One worker raises PolishError → ``_parallel_polish`` propagates it."""
    pending = _pending(tmp_path, 3)

    def _flaky(content: str, *args, **kwargs) -> str:
        if "content_1" in content:
            raise PolishError("polish failed for depth_1")
        return f"polished:{content}"

    with patch("attune.authoring.generator._maybe_polish", side_effect=_flaky):
        with pytest.raises(PolishError, match="polish failed for depth_1"):
            _parallel_polish(
                pending=pending,
                feature=feature,
                source_info=object(),
                use_rag=False,
            )


def test_parallel_polish_propagates_runtime_error(tmp_path: Path, feature: Feature) -> None:
    """A non-PolishError exception (e.g. timeout) also bubbles up."""
    pending = _pending(tmp_path, 2)
    with patch(
        "attune.authoring.generator._maybe_polish",
        side_effect=TimeoutError("anthropic API timeout"),
    ):
        with pytest.raises(TimeoutError, match="anthropic API timeout"):
            _parallel_polish(
                pending=pending,
                feature=feature,
                source_info=object(),
                use_rag=False,
            )


def test_parallel_polish_all_workers_fail_propagates_one(tmp_path: Path, feature: Feature) -> None:
    """When every worker fails, the first-completed error is what surfaces.
    The exact exception identity isn't pinned — futures complete in
    nondeterministic order — but *some* exception must propagate."""
    pending = _pending(tmp_path, 4)
    call_counter = {"n": 0}

    def _all_fail(content: str, *args, **kwargs) -> str:
        call_counter["n"] += 1
        raise RuntimeError(f"failed call #{call_counter['n']}")

    with patch("attune.authoring.generator._maybe_polish", side_effect=_all_fail):
        with pytest.raises(RuntimeError, match="failed call"):
            _parallel_polish(
                pending=pending,
                feature=feature,
                source_info=object(),
                use_rag=False,
            )


# ---------------------------------------------------------------------------
# Workers / concurrency
# ---------------------------------------------------------------------------


def test_parallel_polish_uses_at_most_max_workers(tmp_path: Path, feature: Feature) -> None:
    """With more pending items than workers, all items still complete."""
    pending = _pending(tmp_path, 8)
    with patch(
        "attune.authoring.generator._maybe_polish",
        side_effect=lambda content, *a, **kw: content,
    ):
        results = _parallel_polish(
            pending=pending, feature=feature, source_info=object(), use_rag=False
        )
    assert len(results) == 8


def test_parallel_polish_passes_use_rag_through(tmp_path: Path, feature: Feature) -> None:
    """use_rag must reach _maybe_polish unchanged so RAG grounding can be opted out."""
    pending = _pending(tmp_path, 1)
    seen: list[bool] = []

    def _capture(content, *args, use_rag: bool = False, **kwargs) -> str:
        seen.append(use_rag)
        return content

    with patch("attune.authoring.generator._maybe_polish", side_effect=_capture):
        _parallel_polish(pending=pending, feature=feature, source_info=object(), use_rag=True)
    assert seen == [True]


def test_parallel_polish_passes_template_type_through(tmp_path: Path, feature: Feature) -> None:
    """Each worker invokes _maybe_polish with template_type=<depth>."""
    pending = [
        ("concept", "c", tmp_path / "c.md"),
        ("reference", "r", tmp_path / "r.md"),
    ]
    seen: dict[str, str] = {}

    def _capture(content, *args, template_type: str = "", **kwargs) -> str:
        seen[content] = template_type
        return content

    with patch("attune.authoring.generator._maybe_polish", side_effect=_capture):
        _parallel_polish(pending=pending, feature=feature, source_info=object(), use_rag=False)
    assert seen == {"c": "concept", "r": "reference"}
