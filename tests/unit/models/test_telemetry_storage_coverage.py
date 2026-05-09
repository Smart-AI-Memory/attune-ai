"""Coverage tests for attune.models.telemetry.storage.

Targets previously-uncovered lines/branches:
- 104: empty/whitespace-only line skipped
- 115: extra_filter excludes record
- 119-122: malformed JSON record swallowed
- 156: log_file_test path
- 331-339: get_file_tests filter combinations
- 370-441: get_summary workflow + calls fallbacks
- 462-477: get_latest_file_test
- 498-523: get_files_needing_tests
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from attune.models.telemetry.data_models import (
    FileTestRecord,
    LLMCallRecord,
    WorkflowRunRecord,
)
from attune.models.telemetry.storage import TelemetryStore


@pytest.fixture
def store(tmp_path: Path) -> TelemetryStore:
    return TelemetryStore(storage_dir=str(tmp_path))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_call_seq = [0]


def _llm_record(workflow="wf1") -> LLMCallRecord:
    _call_seq[0] += 1
    return LLMCallRecord(
        call_id=f"call-{_call_seq[0]}",
        timestamp=_now(),
        workflow_name=workflow,
        model_id="claude-haiku-4-5",
        provider="anthropic",
        input_tokens=10,
        output_tokens=20,
        estimated_cost=0.001,
        latency_ms=100,
        success=True,
    )


def _file_test_record(path="x.py", result="passed", is_stale=False) -> FileTestRecord:
    return FileTestRecord(
        file_path=path,
        timestamp=_now(),
        last_test_result=result,
        test_count=1,
        coverage_percent=80.0,
        is_stale=is_stale,
    )


class TestReadJsonlEdgeCases:
    def test_empty_lines_skipped(self, store: TelemetryStore):
        """Line 104: empty / whitespace-only lines are skipped."""
        store.calls_file.write_text("\n   \n" + json.dumps(_llm_record().to_dict()) + "\n")
        result = store.get_calls()
        assert len(result) == 1

    def test_extra_filter_excludes_record(self, store: TelemetryStore):
        """Line 115: extra_filter returning False → continue."""
        store.log_call(_llm_record(workflow="wf1"))
        store.log_call(_llm_record(workflow="wf2"))
        result = store.get_calls(workflow_name="wf1")
        assert len(result) == 1
        assert result[0].workflow_name == "wf1"

    def test_malformed_record_swallowed(self, store: TelemetryStore):
        """Lines 120-122: JSONDecodeError logs debug and continues."""
        store.calls_file.write_text("not-json\n" + json.dumps(_llm_record().to_dict()) + "\n")
        # Should still return the valid record
        result = store.get_calls()
        assert len(result) == 1

    def test_limit_truncates_results(self, store: TelemetryStore):
        """Line 119: break out of the loop when limit reached."""
        for _ in range(5):
            store.log_call(_llm_record())
        assert len(store.get_calls(limit=2)) == 2


class TestLogFileTest:
    def test_log_file_test_appends(self, store: TelemetryStore):
        """Line 156: log_file_test calls _append_record."""
        store.log_file_test(_file_test_record())
        assert store.file_tests_file.exists()


class TestGetFileTestsFilters:
    def test_filter_by_path(self, store: TelemetryStore):
        """Lines 331-345: filter by file_path."""
        store.log_file_test(_file_test_record(path="a.py"))
        store.log_file_test(_file_test_record(path="b.py"))
        result = store.get_file_tests(file_path="a.py")
        assert len(result) == 1
        assert result[0].file_path == "a.py"

    def test_filter_by_result(self, store: TelemetryStore):
        """Filter by result_filter."""
        store.log_file_test(_file_test_record(path="a.py", result="passed"))
        store.log_file_test(_file_test_record(path="b.py", result="failed"))
        result = store.get_file_tests(result_filter="failed")
        assert len(result) == 1
        assert result[0].last_test_result == "failed"

    def test_no_filter_returns_all(self, store: TelemetryStore):
        """has_extra=False → no filter applied."""
        store.log_file_test(_file_test_record(path="a.py"))
        store.log_file_test(_file_test_record(path="b.py"))
        result = store.get_file_tests()
        assert len(result) == 2


class TestGetSummary:
    def test_workflow_summary(self, store: TelemetryStore):
        """Lines 370-403: workflow path."""
        wf = WorkflowRunRecord(
            run_id="r1",
            workflow_name="wf",
            started_at=_now(),
            completed_at=_now(),
            success=True,
            total_cost=0.5,
            total_input_tokens=100,
            total_output_tokens=50,
        )
        store.log_workflow(wf)
        result = store.get_summary()
        assert result["source"] == "workflows"
        assert result["workflow_count"] == 1
        assert result["total_cost"] == 0.5
        assert result["total_tokens"] == 150

    def test_workflow_summary_with_since_filter(self, store: TelemetryStore):
        """Line 383-384: skip records before 'since' cutoff."""
        from datetime import timedelta

        old = datetime.now(timezone.utc) - timedelta(days=10)
        wf = WorkflowRunRecord(
            run_id="r1",
            workflow_name="wf",
            started_at=old.isoformat(),
            completed_at=_now(),
            success=True,
            total_cost=0.5,
            total_input_tokens=100,
            total_output_tokens=50,
        )
        store.log_workflow(wf)
        # since now → old workflow excluded
        result = store.get_summary(since=datetime.now(timezone.utc))
        # No workflows match → fall back to calls (also empty)
        assert result["source"] == "none"

    def test_workflow_malformed_swallowed(self, store: TelemetryStore):
        """Lines 389-394: malformed workflow record skipped."""
        store.workflows_file.write_text("not-json\n")
        # Falls through to calls (empty) → "none"
        result = store.get_summary()
        assert result["source"] == "none"

    def test_calls_fallback_summary(self, store: TelemetryStore):
        """Lines 405-439: calls fallback when no workflows."""
        store.log_call(_llm_record())
        result = store.get_summary()
        assert result["source"] == "calls"
        assert result["call_count"] == 1
        assert result["total_cost"] > 0

    def test_calls_with_since_filter(self, store: TelemetryStore):
        """Line 419-420: skip calls before 'since'."""
        from datetime import timedelta

        old = datetime.now(timezone.utc) - timedelta(days=10)
        rec = _llm_record()
        rec.timestamp = old.isoformat()
        store.log_call(rec)
        result = store.get_summary(since=datetime.now(timezone.utc))
        assert result["source"] == "none"

    def test_calls_malformed_swallowed(self, store: TelemetryStore):
        """Lines 425-430: malformed calls record skipped."""
        store.calls_file.write_text("not-json\n")
        result = store.get_summary()
        assert result["source"] == "none"

    def test_no_data_returns_none_source(self, store: TelemetryStore):
        """Lines 441-447: no workflows + no calls → source 'none'."""
        result = store.get_summary()
        assert result == {
            "workflow_count": 0,
            "call_count": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "source": "none",
        }

    def test_workflow_summary_skips_empty_lines(self, store: TelemetryStore):
        """Line 378: empty lines in workflows file are skipped."""
        wf = WorkflowRunRecord(
            run_id="r1",
            workflow_name="wf",
            started_at=_now(),
            success=True,
            total_cost=1.0,
            total_input_tokens=10,
            total_output_tokens=10,
        )
        # File with empty line + valid record
        store.workflows_file.write_text("\n   \n" + json.dumps(wf.to_dict()) + "\n")
        result = store.get_summary()
        assert result["source"] == "workflows"
        assert result["workflow_count"] == 1

    def test_workflow_summary_since_includes_recent(self, store: TelemetryStore):
        """Line 383->385: 'since' set, ts >= since → record included."""
        from datetime import timedelta

        wf = WorkflowRunRecord(
            run_id="r1",
            workflow_name="wf",
            started_at=_now(),
            success=True,
            total_cost=1.0,
            total_input_tokens=10,
            total_output_tokens=10,
        )
        store.log_workflow(wf)
        # since is well in the past, so the record passes
        result = store.get_summary(since=datetime.now(timezone.utc) - timedelta(days=1))
        assert result["source"] == "workflows"
        assert result["workflow_count"] == 1

    def test_calls_summary_skips_empty_lines(self, store: TelemetryStore):
        """Line 414: empty lines in calls file are skipped."""
        rec = _llm_record()
        store.calls_file.write_text("\n  \n" + json.dumps(rec.to_dict()) + "\n")
        result = store.get_summary()
        assert result["source"] == "calls"
        assert result["call_count"] == 1

    def test_calls_summary_since_includes_recent(self, store: TelemetryStore):
        """Line 419->421: calls 'since' branch where ts >= since."""
        from datetime import timedelta

        store.log_call(_llm_record())
        result = store.get_summary(since=datetime.now(timezone.utc) - timedelta(days=1))
        assert result["source"] == "calls"


class TestGetLatestFileTest:
    def test_no_file_returns_none(self, store: TelemetryStore):
        """Lines 462-463: file doesn't exist → None."""
        assert store.get_latest_file_test("any.py") is None

    def test_returns_latest_match(self, store: TelemetryStore):
        """Lines 466-477: streams to find last matching path."""
        # Two records for same path; second is more recent
        rec1 = _file_test_record(path="x.py", result="failed")
        store.log_file_test(rec1)
        rec2 = _file_test_record(path="x.py", result="passed")
        store.log_file_test(rec2)
        # Other path
        store.log_file_test(_file_test_record(path="y.py"))

        result = store.get_latest_file_test("x.py")
        assert result is not None
        assert result.last_test_result == "passed"

    def test_returns_none_for_unknown_path(self, store: TelemetryStore):
        """Function exists, just no match."""
        store.log_file_test(_file_test_record(path="x.py"))
        assert store.get_latest_file_test("missing.py") is None

    def test_malformed_records_skipped(self, store: TelemetryStore):
        """Lines 475-476: JSONDecodeError → continue."""
        # Mix of valid + malformed
        valid_data = _file_test_record(path="x.py").to_dict()
        store.file_tests_file.write_text("not-json\n" + json.dumps(valid_data) + "\n")
        result = store.get_latest_file_test("x.py")
        assert result is not None

    def test_skips_empty_lines(self, store: TelemetryStore):
        """Line 469: empty line skipped in get_latest_file_test."""
        rec = _file_test_record(path="x.py")
        store.file_tests_file.write_text("\n   \n" + json.dumps(rec.to_dict()) + "\n")
        result = store.get_latest_file_test("x.py")
        assert result is not None


class TestGetFilesNeedingTests:
    def test_no_file_returns_empty(self, store: TelemetryStore):
        """Line 499: file doesn't exist → empty result."""
        assert store.get_files_needing_tests() == []

    def test_default_returns_stale_failed_no_tests(self, store: TelemetryStore):
        """Default: stale OR failed OR no_tests."""
        store.log_file_test(_file_test_record(path="ok.py", result="passed"))
        store.log_file_test(_file_test_record(path="bad.py", result="failed"))
        store.log_file_test(_file_test_record(path="stale.py", is_stale=True))

        result = store.get_files_needing_tests()
        paths = {r.file_path for r in result}
        assert "bad.py" in paths
        assert "stale.py" in paths
        assert "ok.py" not in paths

    def test_stale_only(self, store: TelemetryStore):
        """stale_only filter."""
        store.log_file_test(_file_test_record(path="bad.py", result="failed"))
        store.log_file_test(_file_test_record(path="stale.py", is_stale=True))
        result = store.get_files_needing_tests(stale_only=True)
        paths = {r.file_path for r in result}
        assert paths == {"stale.py"}

    def test_failed_only(self, store: TelemetryStore):
        """failed_only filter."""
        store.log_file_test(_file_test_record(path="bad.py", result="failed"))
        store.log_file_test(_file_test_record(path="error.py", result="error"))
        store.log_file_test(_file_test_record(path="stale.py", is_stale=True))
        result = store.get_files_needing_tests(failed_only=True)
        paths = {r.file_path for r in result}
        assert paths == {"bad.py", "error.py"}

    def test_keeps_only_latest_per_file(self, store: TelemetryStore):
        """Lines 507-509: keeps only latest record per file path."""
        import time

        # Older: failed
        rec1 = _file_test_record(path="x.py", result="failed")
        store.log_file_test(rec1)
        time.sleep(0.01)
        # Newer: passed
        rec2 = _file_test_record(path="x.py", result="passed")
        store.log_file_test(rec2)

        result = store.get_files_needing_tests()
        # x.py should be filtered out — latest is "passed"
        assert all(r.file_path != "x.py" for r in result)

    def test_malformed_swallowed(self, store: TelemetryStore):
        """Lines 510-511: JSONDecodeError → continue."""
        store.file_tests_file.write_text(
            "not-json\n"
            + json.dumps(_file_test_record(path="bad.py", result="failed").to_dict())
            + "\n"
        )
        result = store.get_files_needing_tests()
        assert any(r.file_path == "bad.py" for r in result)

    def test_skips_empty_lines(self, store: TelemetryStore):
        """Line 503: empty line skipped in get_files_needing_tests."""
        rec = _file_test_record(path="bad.py", result="failed")
        store.file_tests_file.write_text("\n  \n" + json.dumps(rec.to_dict()) + "\n")
        result = store.get_files_needing_tests()
        assert any(r.file_path == "bad.py" for r in result)

    def test_older_record_does_not_replace_existing(self, store: TelemetryStore):
        """Line 508->501: when existing.timestamp >= record.timestamp, skip update."""
        from datetime import timedelta

        # Write the newer record first, then an older one for the same path
        newer_ts = datetime.now(timezone.utc).isoformat()
        older_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        newer = _file_test_record(path="x.py", result="passed")
        newer.timestamp = newer_ts
        older = _file_test_record(path="x.py", result="failed")
        older.timestamp = older_ts

        # Order: newer first, older second → older shouldn't replace
        store.file_tests_file.write_text(
            json.dumps(newer.to_dict()) + "\n" + json.dumps(older.to_dict()) + "\n"
        )
        result = store.get_files_needing_tests()
        # x.py would only show up if "failed" was kept; if "passed" is kept, it won't
        assert all(r.file_path != "x.py" for r in result)
