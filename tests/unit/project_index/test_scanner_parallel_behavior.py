"""Behavioral tests for scanner_parallel's worker and dependency path.

Covers the two gaps the guard-focused suite (test_scanner_parallel.py)
leaves open: the picklable ``_analyze_file_worker`` function (called
IN-PROCESS here — it is a plain function; no Pool is ever created), and
``scan(analyze_dependencies=True)``. Every scan stays far below
``_PARALLEL_MIN_FILES`` so the sequential fallback runs — real
multiprocessing is a fork hazard inside test hosts and is exercised
only via the mocked-Pool tests in the sibling file.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path

from attune.project_index.models import FileCategory, IndexConfig
from attune.project_index.scanner_parallel import (
    ParallelProjectScanner,
    _analyze_file_worker,
)

# Record paths and test_file_map keys are OS-native relative paths
# (both sides come from str(Path.relative_to(...))) — build expected
# values the same way so the assertions hold on Windows.
MOD_PATH = str(Path("src") / "mod.py")
USES_PATH = str(Path("src") / "uses.py")


def _make_project(tmp_path):
    """A tiny two-file project: one source module, one test for it."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_mod.py").write_text(
        "from src.mod import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )


def _config_dict(config: IndexConfig) -> dict:
    """The exact three-key serialization _analyze_files_parallel ships."""
    return {
        "exclude_patterns": list(config.exclude_patterns),
        "no_test_patterns": list(config.no_test_patterns),
        "staleness_threshold_days": config.staleness_threshold_days,
    }


class TestAnalyzeFileWorker:
    """The picklable worker reconstructs its scanner and analyzes."""

    def test_worker_returns_record_for_source_file(self, tmp_path):
        _make_project(tmp_path)
        record = _analyze_file_worker(
            str(tmp_path / "src" / "mod.py"),
            str(tmp_path),
            _config_dict(IndexConfig()),
            {},
        )
        assert record is not None
        assert record.path == MOD_PATH  # relative, OS-native separators
        assert record.category is FileCategory.SOURCE
        assert record.language == "python"

    def test_worker_applies_test_file_map(self, tmp_path):
        _make_project(tmp_path)
        record = _analyze_file_worker(
            str(tmp_path / "src" / "mod.py"),
            str(tmp_path),
            _config_dict(IndexConfig()),
            {MOD_PATH: "test_mod.py"},
        )
        assert record is not None
        assert record.tests_exist
        assert record.test_file_path == "test_mod.py"


class TestScanWithDependencies:
    """scan(analyze_dependencies=True) — the branch the guard suite skips."""

    def test_dependency_analysis_populates_reverse_edges_and_impact(self, tmp_path):
        # Two source files with a real import edge: uses.py -> mod.py.
        # The dependency branch is what builds REVERSE edges
        # (imported_by) and impact scores; probed live 2026-07-30:
        # analyze_dependencies=False leaves imported_by=[] and
        # impact_score=0.0 on the same tree.
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("def add(a, b):\n    return a + b\n")
        (tmp_path / "src" / "uses.py").write_text(
            "from src.mod import add\n\n\ndef double(x):\n    return add(x, x)\n"
        )
        scanner = ParallelProjectScanner(str(tmp_path), workers=2)
        records, summary = scanner.scan(analyze_dependencies=True)
        assert summary.total_files == 2
        by_path = {r.path: r for r in records}
        assert by_path[MOD_PATH].imported_by == [USES_PATH]
        assert by_path[MOD_PATH].impact_score > 0
