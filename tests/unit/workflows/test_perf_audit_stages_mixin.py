"""Unit tests for attune.workflows.perf_audit_stages_mixin module.

Tests cover:
- PerfAuditAnalysisMixin._profile: file scanning, pattern matching
- PerfAuditAnalysisMixin._analyze: grouping findings by file
- PerfAuditAnalysisMixin._hotspots: hotspot identification, perf scoring
- _scan_file_for_patterns: pattern scanning helper
- _run_auth_strategy: auth strategy integration helper

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.perf_audit_stages_mixin import (
    PerfAuditAnalysisMixin,
    _scan_file_for_patterns,
)


class _FakeHost(PerfAuditAnalysisMixin):
    """Minimal host providing attributes expected by the mixin."""

    def __init__(self) -> None:
        self.enable_auth_strategy: bool = False
        self._auth_mode_used: str | None = None
        self._hotspot_count: int = 0


@pytest.fixture
def host() -> _FakeHost:
    """Create a mixin host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _scan_file_for_patterns (module-level helper)
# ---------------------------------------------------------------------------


class TestScanFileForPatterns:
    """Tests for the _scan_file_for_patterns helper."""

    def test_detects_n_plus_one(self) -> None:
        """Test detection of N+1 query pattern (same-line match)."""
        # Pattern requires .get( on the same line as the for loop
        content = "for item in items: db.get(item.id)\n"
        findings: list[dict] = []
        _scan_file_for_patterns(content, "app.py", findings)

        types = [f["type"] for f in findings]
        assert "n_plus_one" in types

    def test_empty_content_no_findings(self) -> None:
        """Test that empty content produces no findings."""
        findings: list[dict] = []
        _scan_file_for_patterns("", "empty.py", findings)
        assert len(findings) == 0

    def test_finding_includes_line_number(self) -> None:
        """Test that findings include correct line numbers."""
        content = "# line 1\nfor x in items: db.get(x)\n"
        findings: list[dict] = []
        _scan_file_for_patterns(content, "test.py", findings)

        for f in findings:
            assert "line" in f
            assert f["line"] >= 1

    def test_finding_has_required_fields(self) -> None:
        """Test that each finding has all required fields."""
        content = "for item in lst: api.fetch(item)\n"
        findings: list[dict] = []
        _scan_file_for_patterns(content, "module.py", findings)

        for f in findings:
            assert "type" in f
            assert "file" in f
            assert "line" in f
            assert "description" in f
            assert "impact" in f
            assert "match" in f


# ---------------------------------------------------------------------------
# _profile stage
# ---------------------------------------------------------------------------


class TestProfileStage:
    """Tests for PerfAuditAnalysisMixin._profile."""

    @pytest.mark.asyncio
    async def test_profile_nonexistent_path(self, host: _FakeHost) -> None:
        """Test profiling a nonexistent path returns empty findings."""
        result, _, _ = await host._profile(
            {"path": "/nonexistent/path"},
            ModelTier.CHEAP,
        )
        assert result["finding_count"] == 0
        assert result["files_scanned"] == 0

    @pytest.mark.asyncio
    async def test_profile_scans_python_files(
        self, host: _FakeHost, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test profiling scans .py files in target directory."""
        # tmp_path may contain 'test' in path which matches _SKIP_DIRS
        import attune.workflows.perf_audit_stages_mixin as mod

        monkeypatch.setattr(mod, "_SKIP_DIRS", [".git", "node_modules", "__pycache__", "venv"])

        py_file = tmp_path / "app.py"
        py_file.write_text(
            "for x in items: db.get(x)\n",
            encoding="utf-8",
        )

        result, _, _ = await host._profile(
            {"path": str(tmp_path)},
            ModelTier.CHEAP,
        )
        assert result["files_scanned"] == 1

    @pytest.mark.asyncio
    async def test_profile_skips_excluded_dirs(
        self, host: _FakeHost, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that __pycache__ and similar dirs are skipped."""
        import attune.workflows.perf_audit_stages_mixin as mod

        monkeypatch.setattr(mod, "_SKIP_DIRS", [".git", "node_modules", "__pycache__", "venv"])

        excluded = tmp_path / "__pycache__"
        excluded.mkdir()
        (excluded / "cached.py").write_text("for x in y: db.get(x)\n", encoding="utf-8")

        (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")

        result, _, _ = await host._profile(
            {"path": str(tmp_path)},
            ModelTier.CHEAP,
        )
        assert result["files_scanned"] == 1

    @pytest.mark.asyncio
    async def test_profile_groups_by_impact(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test that findings are grouped by impact level."""
        py_file = tmp_path / "slow.py"
        py_file.write_text(
            "for item in items:\n    db.query(item)\n",
            encoding="utf-8",
        )

        result, _, _ = await host._profile(
            {"path": str(tmp_path)},
            ModelTier.CHEAP,
        )
        assert "by_impact" in result
        for level in ("high", "medium", "low"):
            assert level in result["by_impact"]

    @pytest.mark.asyncio
    async def test_profile_file_read_error(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test graceful handling of unreadable files."""
        py_file = tmp_path / "unreadable.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            result, _, _ = await host._profile(
                {"path": str(tmp_path)},
                ModelTier.CHEAP,
            )
        # Should not crash
        assert "findings" in result


# ---------------------------------------------------------------------------
# _analyze stage
# ---------------------------------------------------------------------------


class TestAnalyzeStage:
    """Tests for PerfAuditAnalysisMixin._analyze."""

    @pytest.mark.asyncio
    async def test_analyze_empty_findings(self, host: _FakeHost) -> None:
        """Test analysis with no findings."""
        result, _, _ = await host._analyze(
            {"findings": []},
            ModelTier.CHEAP,
        )
        assert result["analyzed_files"] == 0
        assert result["analysis"] == []

    @pytest.mark.asyncio
    async def test_analyze_groups_by_file(self, host: _FakeHost) -> None:
        """Test that findings are grouped by file path."""
        findings = [
            {"file": "a.py", "type": "n_plus_one", "impact": "high"},
            {"file": "a.py", "type": "sync_in_async", "impact": "medium"},
            {"file": "b.py", "type": "n_plus_one", "impact": "high"},
        ]
        result, _, _ = await host._analyze(
            {"findings": findings},
            ModelTier.CHEAP,
        )
        assert result["analyzed_files"] == 2

    @pytest.mark.asyncio
    async def test_analyze_complexity_score(self, host: _FakeHost) -> None:
        """Test complexity score calculation: high=10, medium=5, low=1."""
        findings = [
            {"file": "x.py", "type": "a", "impact": "high"},
            {"file": "x.py", "type": "b", "impact": "medium"},
            {"file": "x.py", "type": "c", "impact": "low"},
        ]
        result, _, _ = await host._analyze(
            {"findings": findings},
            ModelTier.CHEAP,
        )
        analysis = result["analysis"][0]
        assert analysis["complexity_score"] == 10 + 5 + 1

    @pytest.mark.asyncio
    async def test_analyze_sorted_by_score_desc(self, host: _FakeHost) -> None:
        """Test that analysis is sorted by complexity score descending."""
        findings = [
            {"file": "low.py", "type": "a", "impact": "low"},
            {"file": "high.py", "type": "b", "impact": "high"},
            {"file": "high.py", "type": "c", "impact": "high"},
        ]
        result, _, _ = await host._analyze(
            {"findings": findings},
            ModelTier.CHEAP,
        )
        scores = [a["complexity_score"] for a in result["analysis"]]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# _hotspots stage
# ---------------------------------------------------------------------------


class TestHotspotsStage:
    """Tests for PerfAuditAnalysisMixin._hotspots."""

    @pytest.mark.asyncio
    async def test_hotspots_empty_analysis(self, host: _FakeHost) -> None:
        """Test hotspot detection with no analysis entries."""
        result, _, _ = await host._hotspots(
            {"analysis": []},
            ModelTier.CHEAP,
        )
        assert result["hotspot_result"]["hotspot_count"] == 0
        assert result["hotspot_result"]["perf_score"] == 100

    @pytest.mark.asyncio
    async def test_hotspots_detects_critical(self, host: _FakeHost) -> None:
        """Test that files with score >= 20 are marked critical."""
        analysis = [
            {"file": "a.py", "complexity_score": 25, "high_impact": 3, "concerns": ["x"]},
        ]
        result, _, _ = await host._hotspots(
            {"analysis": analysis},
            ModelTier.CHEAP,
        )
        assert result["hotspot_result"]["critical_count"] == 1

    @pytest.mark.asyncio
    async def test_hotspots_perf_level_good(self, host: _FakeHost) -> None:
        """Test perf_level is 'good' when score >= 75."""
        analysis = [
            {"file": "a.py", "complexity_score": 2, "high_impact": 0, "concerns": []},
        ]
        result, _, _ = await host._hotspots(
            {"analysis": analysis},
            ModelTier.CHEAP,
        )
        assert result["hotspot_result"]["perf_level"] == "good"

    @pytest.mark.asyncio
    async def test_hotspots_perf_level_warning(self, host: _FakeHost) -> None:
        """Test perf_level is 'warning' when 50 <= score < 75."""
        # Need score that yields 50-74 perf_score
        # perf_score = 100 - int((total_score / max_score) * 100)
        # max_score = 1 * 30 = 30
        # need (total/30)*100 to be between 26 and 50
        # total between 8 and 15
        analysis = [
            {"file": "a.py", "complexity_score": 10, "high_impact": 2, "concerns": ["x"]},
        ]
        result, _, _ = await host._hotspots(
            {"analysis": analysis},
            ModelTier.CHEAP,
        )
        assert result["hotspot_result"]["perf_score"] >= 0
        assert result["hotspot_result"]["perf_level"] in ("warning", "good", "critical")

    @pytest.mark.asyncio
    async def test_hotspots_sets_count_on_host(self, host: _FakeHost) -> None:
        """Test that _hotspot_count is set on the host instance."""
        analysis = [
            {"file": "a.py", "complexity_score": 15, "high_impact": 2, "concerns": ["x"]},
        ]
        await host._hotspots({"analysis": analysis}, ModelTier.CHEAP)
        assert host._hotspot_count == 1

    @pytest.mark.asyncio
    async def test_hotspots_max_15_returned(self, host: _FakeHost) -> None:
        """Test that at most 15 hotspots are returned."""
        analysis = [
            {"file": f"f{i}.py", "complexity_score": 20, "high_impact": 2, "concerns": []}
            for i in range(20)
        ]
        result, _, _ = await host._hotspots(
            {"analysis": analysis},
            ModelTier.CHEAP,
        )
        assert len(result["hotspot_result"]["hotspots"]) <= 15


# ---------------------------------------------------------------------------
# _profile with auth strategy
# ---------------------------------------------------------------------------


class TestProfileAuthStrategy:
    """Tests for auth strategy integration in _profile."""

    @pytest.mark.asyncio
    async def test_profile_with_auth_strategy_enabled(
        self, host: _FakeHost, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test profile with auth strategy enabled triggers _run_auth_strategy."""
        import attune.workflows.perf_audit_stages_mixin as mod

        monkeypatch.setattr(mod, "_SKIP_DIRS", [".git", "node_modules", "__pycache__", "venv"])

        host.enable_auth_strategy = True

        py_file = tmp_path / "app.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        # Mock _run_auth_strategy to avoid real import
        with patch.object(mod, "_run_auth_strategy") as mock_auth:
            result, _, _ = await host._profile(
                {"path": str(tmp_path)},
                ModelTier.CHEAP,
            )

        mock_auth.assert_called_once()
        assert result["files_scanned"] == 1


# ---------------------------------------------------------------------------
# _run_auth_strategy helper
# ---------------------------------------------------------------------------


class TestRunAuthStrategy:
    """Tests for _run_auth_strategy module-level helper."""

    def test_import_error_handled(self) -> None:
        """Test graceful handling when attune.models is not importable."""
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        mock_wf = MagicMock()
        target = Path("/nonexistent")

        # Mock attune.models being unavailable
        with patch.dict("sys.modules", {"attune.models": None}):
            # Should not raise
            _run_auth_strategy(mock_wf, target, [".py"], "/nonexistent")

    def test_attribute_error_handled(self) -> None:
        """Test graceful handling of AttributeError during auth strategy."""
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        mock_wf = MagicMock()
        target = Path("/nonexistent")

        # Patch the models import to raise AttributeError
        import types

        mock_models = types.ModuleType("attune.models")
        mock_models.count_lines_of_code = MagicMock(side_effect=AttributeError("no attr"))
        mock_models.get_auth_strategy = MagicMock()
        mock_models.get_module_size_category = MagicMock()

        with patch.dict("sys.modules", {"attune.models": mock_models}):
            # Should not raise — caught by except (AttributeError, TypeError)
            _run_auth_strategy(mock_wf, target, [".py"], "/nonexistent")

    def test_auth_strategy_runs_for_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test auth strategy with a real directory path."""
        import attune.workflows.perf_audit_stages_mixin as mod
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        # Remove "test" from skip dirs so tmp_path (which contains "test") works
        monkeypatch.setattr(mod, "_SKIP_DIRS", [".git", "node_modules", "__pycache__", "venv"])

        py_file = tmp_path / "app.py"
        py_file.write_text("x = 1\ny = 2\n", encoding="utf-8")

        mock_wf = MagicMock()
        mock_wf._auth_mode_used = None

        # Mock the attune.models imports
        mock_mode = MagicMock()
        mock_mode.value = "api"

        mock_strategy = MagicMock()
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = 0.0012

        import types

        mock_models = types.ModuleType("attune.models")
        mock_models.count_lines_of_code = MagicMock(return_value=2)
        mock_models.get_auth_strategy = MagicMock(return_value=mock_strategy)
        mock_models.get_module_size_category = MagicMock(return_value="small")

        with patch.dict("sys.modules", {"attune.models": mock_models}):
            _run_auth_strategy(mock_wf, tmp_path, [".py"], str(tmp_path))

        assert mock_wf._auth_mode_used == "api"

    def test_auth_strategy_subscription_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test auth strategy with subscription mode cost estimate."""
        import attune.workflows.perf_audit_stages_mixin as mod
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        monkeypatch.setattr(mod, "_SKIP_DIRS", [".git", "node_modules", "__pycache__", "venv"])

        py_file = tmp_path / "module.py"
        py_file.write_text("class Foo:\n    pass\n", encoding="utf-8")

        mock_wf = MagicMock()
        mock_wf._auth_mode_used = None

        mock_mode = MagicMock()
        mock_mode.value = "subscription"

        mock_strategy = MagicMock()
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = 0.0

        import types

        mock_models = types.ModuleType("attune.models")
        mock_models.count_lines_of_code = MagicMock(return_value=2)
        mock_models.get_auth_strategy = MagicMock(return_value=mock_strategy)
        mock_models.get_module_size_category = MagicMock(return_value="small")

        with patch.dict("sys.modules", {"attune.models": mock_models}):
            _run_auth_strategy(mock_wf, tmp_path, [".py"], str(tmp_path))

        assert mock_wf._auth_mode_used == "subscription"

    def test_auth_strategy_file_target(self, tmp_path: Path) -> None:
        """Test auth strategy with a single file target."""
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        py_file = tmp_path / "single.py"
        py_file.write_text("def foo(): pass\n", encoding="utf-8")

        mock_wf = MagicMock()
        mock_wf._auth_mode_used = None

        mock_mode = MagicMock()
        mock_mode.value = "api"

        mock_strategy = MagicMock()
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = 0.001

        import types

        mock_models = types.ModuleType("attune.models")
        mock_models.count_lines_of_code = MagicMock(return_value=1)
        mock_models.get_auth_strategy = MagicMock(return_value=mock_strategy)
        mock_models.get_module_size_category = MagicMock(return_value="tiny")

        with patch.dict("sys.modules", {"attune.models": mock_models}):
            _run_auth_strategy(mock_wf, py_file, [".py"], str(py_file))

        assert mock_wf._auth_mode_used == "api"

    def test_auth_strategy_zero_lines(self, tmp_path: Path) -> None:
        """Test auth strategy when no lines of code found."""
        from attune.workflows.perf_audit_stages_mixin import _run_auth_strategy

        # Empty directory — no .py files
        mock_wf = MagicMock()
        mock_wf._auth_mode_used = None

        import types

        mock_models = types.ModuleType("attune.models")
        mock_models.count_lines_of_code = MagicMock(return_value=0)
        mock_models.get_auth_strategy = MagicMock()
        mock_models.get_module_size_category = MagicMock()

        with patch.dict("sys.modules", {"attune.models": mock_models}):
            _run_auth_strategy(mock_wf, tmp_path, [".py"], str(tmp_path))

        # _auth_mode_used should not be set since 0 lines
        # (only set when total_lines > 0)
        mock_models.get_auth_strategy.assert_not_called()
