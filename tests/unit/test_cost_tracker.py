"""Tests for attune.cost_tracker"""

from attune.cost_tracker import CostTracker, cmd_costs, get_tracker, log_request


class TestCostTracker:
    """Tests for CostTracker class."""

    def test_initialization(self, tmp_path):
        """Test CostTracker initialization."""
        tracker = CostTracker(storage_dir=str(tmp_path))

        assert tracker is not None
        assert tracker.storage_dir == tmp_path
        assert tracker.costs_file == tmp_path / "costs.json"
        assert tracker.costs_jsonl == tmp_path / "costs.jsonl"
        assert tracker.batch_size == 50
        assert isinstance(tracker._buffer, list)
        assert len(tracker._buffer) == 0
        assert "requests" in tracker.data
        assert "daily_totals" in tracker.data

    def test_log_request_basic(self, tmp_path):
        """Test logging a basic API request."""
        tracker = CostTracker(storage_dir=str(tmp_path))

        request = tracker.log_request(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            task_type="summarize",
        )

        assert request is not None
        assert request["model"] == "claude-3-haiku-20240307"
        assert request["input_tokens"] == 1000
        assert request["output_tokens"] == 500
        assert request["task_type"] == "summarize"
        assert request["tier"] == "cheap"
        assert "actual_cost" in request
        assert "baseline_cost" in request
        assert "savings" in request
        assert request["actual_cost"] > 0
        assert request["baseline_cost"] > 0

    def test_log_request_buffering(self, tmp_path):
        """Test that requests are buffered before flushing."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=10)

        # Log 5 requests (below batch size)
        for _i in range(5):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=100,
                output_tokens=50,
                task_type="test",
            )

        # Buffer should have 5 requests
        assert len(tracker._buffer) == 5

        # JSONL file should not exist yet (not flushed)
        assert not tracker.costs_jsonl.exists()

    def test_automatic_flush(self, tmp_path):
        """Test that buffer flushes automatically at batch size."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=10)

        # Log 10 requests (exactly batch size)
        for _i in range(10):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=100,
                output_tokens=50,
                task_type="test",
            )

        # Buffer should be empty (auto-flushed)
        assert len(tracker._buffer) == 0

        # JSONL file should exist
        assert tracker.costs_jsonl.exists()

    def test_manual_flush(self, tmp_path):
        """Test manual flush of buffered requests."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=100)

        # Log a few requests
        for _i in range(3):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=100,
                output_tokens=50,
                task_type="test",
            )

        # Verify buffered
        assert len(tracker._buffer) == 3

        # Manually flush
        tracker.flush()

        # Buffer should be empty
        assert len(tracker._buffer) == 0

        # JSONL file should exist
        assert tracker.costs_jsonl.exists()

    def test_get_summary_basic(self, tmp_path):
        """Test getting cost summary."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=5)

        # Log several requests
        for _i in range(5):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=1000,
                output_tokens=500,
                task_type="summarize",
            )

        summary = tracker.get_summary(days=7)

        assert summary["days"] == 7
        assert summary["requests"] == 5
        assert summary["input_tokens"] == 5000
        assert summary["output_tokens"] == 2500
        assert summary["actual_cost"] > 0
        assert summary["baseline_cost"] > 0
        assert summary["savings"] > 0
        assert "by_tier" in summary
        assert "by_task" in summary

    def test_get_summary_includes_buffered(self, tmp_path):
        """Test that summary includes buffered (unflushed) requests."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=100)

        # Log requests without triggering flush
        for _i in range(3):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=1000,
                output_tokens=500,
                task_type="test",
            )

        # Verify still buffered
        assert len(tracker._buffer) == 3

        # Summary should still include buffered requests
        summary = tracker.get_summary(days=1)
        assert summary["requests"] == 3
        assert summary["input_tokens"] == 3000

    def test_get_report_format(self, tmp_path):
        """Test formatted report generation."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=5)

        # Log some requests
        for _i in range(5):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=1000,
                output_tokens=500,
                task_type="summarize",
            )

        report = tracker.get_report(days=7)

        assert isinstance(report, str)
        assert "COST TRACKING REPORT" in report
        assert "Total requests:" in report
        assert "Actual cost:" in report
        assert "You saved:" in report

    def test_get_today(self, tmp_path):
        """Test getting today's cost summary."""
        tracker = CostTracker(storage_dir=str(tmp_path), batch_size=5)

        # Log today's requests
        for _i in range(5):
            tracker.log_request(
                model="claude-3-haiku-20240307",
                input_tokens=1000,
                output_tokens=500,
                task_type="test",
            )

        today = tracker.get_today()

        assert today["requests"] == 5
        assert today["input_tokens"] == 5000
        assert today["output_tokens"] == 2500
        assert today["actual_cost"] > 0

    def test_tier_detection(self, tmp_path):
        """Test automatic tier detection from model name."""
        tracker = CostTracker(storage_dir=str(tmp_path))

        # Test haiku (cheap)
        req1 = tracker.log_request(
            model="claude-3-haiku-20240307",
            input_tokens=100,
            output_tokens=50,
            task_type="test",
        )
        assert req1["tier"] == "cheap"

        # Test sonnet (capable)
        req2 = tracker.log_request(
            model="claude-3-5-sonnet-20241022",
            input_tokens=100,
            output_tokens=50,
            task_type="test",
        )
        assert req2["tier"] == "capable"

        # Test opus (premium)
        req3 = tracker.log_request(
            model="claude-opus-4-20250514",
            input_tokens=100,
            output_tokens=50,
            task_type="test",
        )
        assert req3["tier"] == "premium"


def test_get_tracker_singleton(tmp_path):
    """Test get_tracker returns singleton instance."""
    # Reset global tracker
    import attune.cost_tracker

    attune.cost_tracker._tracker = None

    tracker1 = get_tracker(storage_dir=str(tmp_path))
    tracker2 = get_tracker(storage_dir=str(tmp_path))

    # Should be same instance
    assert tracker1 is tracker2


def test_log_request_convenience(tmp_path):
    """Test convenience log_request function."""
    # Reset global tracker
    import attune.cost_tracker

    attune.cost_tracker._tracker = None

    # First call creates tracker
    request = log_request(
        model="claude-3-haiku-20240307",
        input_tokens=1000,
        output_tokens=500,
        task_type="test",
    )

    assert request is not None
    assert request["model"] == "claude-3-haiku-20240307"
    assert request["input_tokens"] == 1000
    assert request["output_tokens"] == 500


def test_cmd_costs_basic(tmp_path):
    """Test cmd_costs CLI command."""
    tracker = CostTracker(storage_dir=str(tmp_path), batch_size=5)

    # Log some requests
    for _i in range(5):
        tracker.log_request(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            task_type="test",
        )

    # Create args object
    class Args:
        empathy_dir = str(tmp_path)
        days = 7
        json = False

    args = Args()

    # Test command execution
    result = cmd_costs(args)

    assert result == 0


def test_cmd_costs_json_output(tmp_path, capsys):
    """Test cmd_costs with JSON output."""
    tracker = CostTracker(storage_dir=str(tmp_path), batch_size=5)

    # Log some requests
    for _i in range(5):
        tracker.log_request(
            model="claude-3-haiku-20240307",
            input_tokens=1000,
            output_tokens=500,
            task_type="test",
        )

    # Create args object with json flag
    class Args:
        empathy_dir = str(tmp_path)
        days = 7
        json = True

    args = Args()

    # Test command execution
    result = cmd_costs(args)

    assert result == 0

    # Verify JSON output
    captured = capsys.readouterr()
    assert "{" in captured.out
    assert "requests" in captured.out
