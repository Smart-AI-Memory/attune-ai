"""Core behavioral tests for ProjectIndex (project_index/index.py).

Covers persistence (load/save/round-trip + failure modes), Redis sync,
the update API, the full query/stats/context getter surface, and the
refresh / refresh_incremental scan paths (scanners + git subprocess
mocked). Records are built in-memory so no real scan runs.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from attune.project_index.index import ProjectIndex
from attune.project_index.models import (
    FileCategory,
    FileRecord,
    ProjectSummary,
    TestRequirement,
)

MOD = "attune.project_index.index"


def _rec(path: str, **kw) -> FileRecord:
    return FileRecord(path=path, name=path.split("/")[-1], **kw)


def _populated(tmp_path):
    """An index with three varied records (no scan)."""
    idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
    records = [
        _rec(
            "src/a.py",
            category=FileCategory.SOURCE,
            language="python",
            test_requirement=TestRequirement.REQUIRED,
            tests_exist=False,
            is_stale=True,
            staleness_days=10,
            lines_of_code=100,
            impact_score=8.0,
            needs_attention=True,
            coverage_percent=0.0,
            imports=["src.b"],
            imported_by=[],
        ),
        _rec(
            "src/b.py",
            category=FileCategory.SOURCE,
            language="python",
            test_requirement=TestRequirement.REQUIRED,
            tests_exist=True,
            is_stale=False,
            impact_score=2.0,
            needs_attention=False,
            coverage_percent=80.0,
            imported_by=["src/a.py"],
        ),
        _rec(
            "tests/test_a.py",
            category=FileCategory.TEST,
            language="python",
            test_requirement=TestRequirement.NOT_APPLICABLE,
        ),
    ]
    idx._records = {r.path: r for r in records}
    return idx


class TestPersistence:
    def test_save_then_load_round_trips(self, tmp_path):
        idx = _populated(tmp_path)
        assert idx.save() is True
        assert idx._index_path.exists()

        fresh = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        assert fresh.load() is True
        assert set(fresh._records) == {"src/a.py", "src/b.py", "tests/test_a.py"}

    def test_load_missing_file_returns_false(self, tmp_path):
        assert ProjectIndex(project_root=str(tmp_path)).load() is False

    def test_load_schema_mismatch_returns_false(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        idx._index_path.parent.mkdir(parents=True, exist_ok=True)
        idx._index_path.write_text(json.dumps({"schema_version": "0.0"}), encoding="utf-8")
        assert idx.load() is False

    def test_load_bad_json_returns_false(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        idx._index_path.parent.mkdir(parents=True, exist_ok=True)
        idx._index_path.write_text("{not json", encoding="utf-8")
        assert idx.load() is False

    def test_save_oserror_returns_false(self, tmp_path):
        idx = _populated(tmp_path)
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert idx.save() is False

    def test_save_triggers_redis_sync_when_enabled(self, tmp_path):
        idx = _populated(tmp_path)
        idx.redis_client = MagicMock()
        idx.config.use_redis = True
        idx.save()
        idx.redis_client.set.assert_called()
        idx.redis_client.hset.assert_called()


class TestSyncToRedis:
    def test_no_client_is_noop(self, tmp_path):
        idx = _populated(tmp_path)
        idx.redis_client = None
        idx._sync_to_redis()  # must not raise

    def test_writes_summary_files_and_meta(self, tmp_path):
        idx = _populated(tmp_path)
        idx.redis_client = MagicMock()
        idx._sync_to_redis()
        assert idx.redis_client.set.call_count >= 2  # summary + meta
        assert idx.redis_client.hset.call_count == 3  # one per record

    def test_exception_is_swallowed(self, tmp_path):
        idx = _populated(tmp_path)
        idx.redis_client = MagicMock()
        idx.redis_client.set.side_effect = RuntimeError("redis down")
        idx._sync_to_redis()  # logged, not raised


class TestUpdateApi:
    def test_update_file_sets_attr_and_metadata(self, tmp_path):
        idx = _populated(tmp_path)
        assert idx.update_file("src/a.py", coverage_percent=55.0, custom_tag="x") is True
        rec = idx.get_file("src/a.py")
        assert rec.coverage_percent == 55.0
        assert rec.metadata["custom_tag"] == "x"  # unknown key -> metadata

    def test_update_file_missing_returns_false(self, tmp_path):
        assert _populated(tmp_path).update_file("nope.py", x=1) is False

    def test_update_coverage_matches_and_normalizes_prefix(self, tmp_path):
        idx = _populated(tmp_path)
        updated = idx.update_coverage({"./src/a.py": 42.0, "ghost.py": 99.0})
        assert updated == 1
        assert idx.get_file("src/a.py").coverage_percent == 42.0

    def test_update_coverage_no_matches_returns_zero(self, tmp_path):
        assert _populated(tmp_path).update_coverage({"ghost.py": 10.0}) == 0

    def test_recalculate_summary_averages_covered(self, tmp_path):
        idx = _populated(tmp_path)
        idx.update_coverage({"src/a.py": 40.0})  # b already 80 -> avg 60
        assert idx.get_summary().test_coverage_avg == pytest.approx(60.0)


class TestQueryGetters:
    def test_get_file_hit_and_miss(self, tmp_path):
        idx = _populated(tmp_path)
        assert idx.get_file("src/a.py").path == "src/a.py"
        assert idx.get_file("missing.py") is None

    def test_iter_and_get_all(self, tmp_path):
        idx = _populated(tmp_path)
        assert len(idx.get_all_files()) == 3
        assert {r.path for r in idx.iter_all_files()} == set(idx._records)

    def test_files_needing_tests(self, tmp_path):
        idx = _populated(tmp_path)
        paths = [r.path for r in idx.get_files_needing_tests()]
        assert paths == ["src/a.py"]  # required + no tests

    def test_stale_files(self, tmp_path):
        assert [r.path for r in _populated(tmp_path).get_stale_files()] == ["src/a.py"]

    def test_needing_attention_sorted_by_impact(self, tmp_path):
        idx = _populated(tmp_path)
        idx._records["src/b.py"].needs_attention = True  # impact 2.0
        result = idx.get_files_needing_attention()
        assert [r.path for r in result] == ["src/a.py", "src/b.py"]  # 8.0 before 2.0

    def test_high_impact_files(self, tmp_path):
        # threshold default 5.0 -> only a (8.0)
        assert [r.path for r in _populated(tmp_path).get_high_impact_files()] == ["src/a.py"]

    def test_by_category_and_language(self, tmp_path):
        idx = _populated(tmp_path)
        assert {r.path for r in idx.get_files_by_category("source")} == {"src/a.py", "src/b.py"}
        assert len(idx.get_files_by_language("python")) == 3
        assert idx.get_files_by_language("rust") == []

    def test_search_files_glob(self, tmp_path):
        idx = _populated(tmp_path)
        assert {r.path for r in idx.search_files("src/*.py")} == {"src/a.py", "src/b.py"}

    def test_dependents_and_dependencies(self, tmp_path):
        idx = _populated(tmp_path)
        assert [r.path for r in idx.get_dependents("src/b.py")] == ["src/a.py"]
        assert [r.path for r in idx.get_dependencies("src/a.py")] == ["src/b.py"]

    def test_dependents_dependencies_missing(self, tmp_path):
        idx = _populated(tmp_path)
        assert idx.get_dependents("ghost.py") == []
        assert idx.get_dependencies("ghost.py") == []


class TestStats:
    def test_test_gap_stats(self, tmp_path):
        stats = _populated(tmp_path).get_test_gap_stats()
        assert stats["files_without_tests"] == 1
        assert stats["high_impact_untested"] == 1  # a is impact 8.0
        assert stats["total_loc_untested"] == 100
        assert stats["by_directory"] == {"src": 1}

    def test_staleness_stats(self, tmp_path):
        stats = _populated(tmp_path).get_staleness_stats()
        assert stats["stale_count"] == 1
        assert stats["avg_staleness_days"] == 10
        assert stats["max_staleness_days"] == 10

    def test_group_by_directory_top_level_file(self, tmp_path):
        # A path with no "/" buckets under "." in _group_by_directory.
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        idx._records = {
            "setup.py": _rec(
                "setup.py",
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                lines_of_code=20,
            ),
        }
        assert idx.get_test_gap_stats()["by_directory"] == {".": 1}

    def test_staleness_stats_empty(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        stats = idx.get_staleness_stats()
        assert stats["stale_count"] == 0
        assert stats["avg_staleness_days"] == 0
        assert stats["max_staleness_days"] == 0


class TestWorkflowContext:
    def test_test_gen(self, tmp_path):
        ctx = _populated(tmp_path).get_context_for_workflow("test_gen")
        assert "files_needing_tests" in ctx
        assert ctx["priority_files"] == ["src/a.py"]

    def test_code_review(self, tmp_path):
        ctx = _populated(tmp_path).get_context_for_workflow("code_review")
        assert "high_impact_files" in ctx and "stale_files" in ctx

    def test_security_audit(self, tmp_path):
        ctx = _populated(tmp_path).get_context_for_workflow("security_audit")
        assert "all_source_files" in ctx and "untested_files" in ctx

    def test_default(self, tmp_path):
        ctx = _populated(tmp_path).get_context_for_workflow("unknown")
        assert "files_needing_attention" in ctx

    def test_documentation(self, tmp_path):
        # #2220 — this branch did not exist: the doc-orchestrator read
        # files_without_docstrings for years while nothing produced it,
        # so every scan "found no gaps". Undocumented source files must
        # be listed; documented ones must not.
        idx = _populated(tmp_path)
        for record in idx._records.values():
            record.has_docstrings = record.path != "src/a.py"
        ctx = idx.get_context_for_workflow("documentation")
        assert "files_without_docstrings" in ctx
        listed = [f["path"] for f in ctx["files_without_docstrings"]]
        assert "src/a.py" in listed
        assert "src/b.py" not in listed
        assert all("loc" in f for f in ctx["files_without_docstrings"])


class TestRefresh:
    def test_refresh_parallel(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=True)
        with patch(f"{MOD}.ParallelProjectScanner") as PS:
            PS.return_value.scan.return_value = ([_rec("src/a.py")], ProjectSummary())
            idx.refresh()
        PS.assert_called_once()
        assert idx.get_file("src/a.py") is not None

    def test_refresh_sequential(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        with patch(f"{MOD}.ProjectScanner") as PS:
            PS.return_value.scan.return_value = ([_rec("src/b.py")], ProjectSummary())
            idx.refresh()
        PS.assert_called()
        assert idx.get_file("src/b.py") is not None

    def test_is_excluded_delegates_to_scanner(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        with patch(f"{MOD}.ProjectScanner") as PS:
            PS.return_value._is_excluded.return_value = True
            assert idx._is_excluded(tmp_path / "x.py") is True


class TestRefreshIncremental:
    def test_no_records_raises(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        with pytest.raises(ValueError, match="No existing index"):
            idx.refresh_incremental()

    def test_git_missing_raises_runtime_error(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        idx._records = {"src/a.py": _rec("src/a.py")}
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="Git not found"):
                idx.refresh_incremental()

    def test_git_error_raises_runtime_error(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        idx._records = {"src/a.py": _rec("src/a.py")}
        err = subprocess.CalledProcessError(1, ["git"])
        with patch("subprocess.run", side_effect=err):
            with pytest.raises(RuntimeError, match="Git command failed"):
                idx.refresh_incremental()

    def test_no_changes_returns_zero(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path))
        idx._records = {"src/a.py": _rec("src/a.py")}
        with patch("subprocess.run", return_value=MagicMock(stdout="")):
            assert idx.refresh_incremental() == (0, 0)

    def test_removes_deleted_files(self, tmp_path):
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        idx._records = {"src/gone.py": _rec("src/gone.py"), "src/keep.py": _rec("src/keep.py")}

        def run_side(cmd, **kw):
            if "--diff-filter=D" in cmd:
                return MagicMock(stdout="src/gone.py\n")
            return MagicMock(stdout="")

        with patch("subprocess.run", side_effect=run_side), patch(f"{MOD}.ProjectScanner") as PS:
            PS.return_value._build_summary.return_value = ProjectSummary()
            updated, removed = idx.refresh_incremental()

        assert removed == 1
        assert "src/gone.py" not in idx._records
        assert "src/keep.py" in idx._records

    def test_scans_changed_files(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "new.py").write_text("x = 1\n", encoding="utf-8")
        idx = ProjectIndex(project_root=str(tmp_path), use_parallel=False)
        idx._records = {"src/old.py": _rec("src/old.py")}

        def run_side(cmd, **kw):
            if "--others" in cmd:  # untracked
                return MagicMock(stdout="src/new.py\n")
            return MagicMock(stdout="")

        with (
            patch("subprocess.run", side_effect=run_side),
            patch.object(ProjectIndex, "_is_excluded", return_value=False),
            patch(f"{MOD}.ProjectScanner") as PS,
        ):
            PS.return_value.scan.return_value = ([_rec("src/new.py")], ProjectSummary())
            PS.return_value._build_summary.return_value = ProjectSummary()
            updated, removed = idx.refresh_incremental()

        assert "src/new.py" in idx._records
        assert updated == 1
