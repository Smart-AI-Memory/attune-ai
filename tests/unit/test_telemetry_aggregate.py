"""Tests for TelemetryStore.get_summary() aggregate method.

Verifies single-pass JSONL aggregation replaces the old fetch-all-and-sum pattern.

Generated with XML-enhanced task prompts.
"""

import json
from datetime import datetime, timedelta

import pytest

from attune.models.telemetry import TelemetryStore

# ---------------------------------------------------------------------------
# Task 2.1: get_summary() aggregation
# ---------------------------------------------------------------------------


class TestGetSummaryWorkflows:
    """Test get_summary() with workflow records."""

    def test_get_summary_workflows(self, tmp_path: str) -> None:
        """Five workflow JSONL records produce correct totals."""
        store = TelemetryStore(storage_dir=str(tmp_path))

        # Write 5 workflow records
        for i in range(5):
            record = {
                "run_id": f"run-{i}",
                "workflow_name": f"wf-{i}",
                "started_at": datetime.utcnow().isoformat(),
                "total_cost": 0.10 * (i + 1),
                "total_input_tokens": 1000 * (i + 1),
                "total_output_tokens": 200 * (i + 1),
            }
            with open(store.workflows_file, "a") as f:
                f.write(json.dumps(record) + "\n")

        summary = store.get_summary()

        assert summary["source"] == "workflows"
        assert summary["workflow_count"] == 5
        # Cost: 0.1 + 0.2 + 0.3 + 0.4 + 0.5 = 1.5
        assert summary["total_cost"] == pytest.approx(1.5)
        # Input: 1000+2000+3000+4000+5000 = 15000
        # Output: 200+400+600+800+1000 = 3000
        # Total: 18000
        assert summary["total_tokens"] == 18000

    def test_get_summary_calls_fallback(self, tmp_path: str) -> None:
        """No workflows: falls back to LLM call records."""
        store = TelemetryStore(storage_dir=str(tmp_path))

        # Write LLM call records (no workflow records)
        for i in range(3):
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "estimated_cost": 0.05 * (i + 1),
                "input_tokens": 500 * (i + 1),
                "output_tokens": 100 * (i + 1),
            }
            with open(store.calls_file, "a") as f:
                f.write(json.dumps(record) + "\n")

        summary = store.get_summary()

        assert summary["source"] == "calls"
        assert summary["call_count"] == 3
        # Cost: 0.05 + 0.10 + 0.15 = 0.30
        assert summary["total_cost"] == pytest.approx(0.30)
        # Input: 500+1000+1500 = 3000
        # Output: 100+200+300 = 600
        assert summary["total_tokens"] == 3600

    def test_get_summary_empty(self, tmp_path: str) -> None:
        """Empty store returns source='none' and zeroes."""
        store = TelemetryStore(storage_dir=str(tmp_path))

        summary = store.get_summary()

        assert summary["source"] == "none"
        assert summary["workflow_count"] == 0
        assert summary["call_count"] == 0
        assert summary["total_cost"] == 0.0
        assert summary["total_tokens"] == 0

    def test_get_summary_since_filter(self, tmp_path: str) -> None:
        """Only includes records after the 'since' cutoff."""
        store = TelemetryStore(storage_dir=str(tmp_path))

        now = datetime.utcnow()
        old_time = (now - timedelta(days=10)).isoformat()
        recent_time = (now - timedelta(hours=1)).isoformat()

        # Write one old and one recent record
        for ts, cost in [(old_time, 1.00), (recent_time, 2.00)]:
            record = {
                "run_id": f"run-{ts}",
                "workflow_name": "test-wf",
                "started_at": ts,
                "total_cost": cost,
                "total_input_tokens": 1000,
                "total_output_tokens": 200,
            }
            with open(store.workflows_file, "a") as f:
                f.write(json.dumps(record) + "\n")

        # Filter: only last 2 days
        since = now - timedelta(days=2)
        summary = store.get_summary(since=since)

        assert summary["source"] == "workflows"
        assert summary["workflow_count"] == 1
        assert summary["total_cost"] == pytest.approx(2.00)

    def test_get_summary_handles_malformed_lines(self, tmp_path: str) -> None:
        """Malformed JSONL lines are skipped without error."""
        store = TelemetryStore(storage_dir=str(tmp_path))

        with open(store.workflows_file, "w") as f:
            f.write("not json\n")
            f.write(
                '{"run_id":"r1","workflow_name":"w","started_at":"'
                + datetime.utcnow().isoformat()
                + '","total_cost":1.0,"total_input_tokens":100,"total_output_tokens":50}\n',
            )
            f.write("\n")  # blank line
            f.write("{bad json}\n")

        summary = store.get_summary()

        assert summary["source"] == "workflows"
        assert summary["workflow_count"] == 1
        assert summary["total_cost"] == pytest.approx(1.0)
        assert summary["total_tokens"] == 150
