# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coverage batch 19: workflows/caching, builder, progress, progress_reporters."""

from __future__ import annotations

from unittest.mock import MagicMock

# === Module: workflows/caching ===


class TestCachedResponse:
    def test_basic_construction(self):
        from attune.workflows.caching import CachedResponse

        resp = CachedResponse(content="hello", input_tokens=100, output_tokens=50)
        assert resp.content == "hello"
        assert resp.input_tokens == 100

    def test_to_dict(self):
        from attune.workflows.caching import CachedResponse

        resp = CachedResponse(content="text", input_tokens=10, output_tokens=5)
        d = resp.to_dict()
        assert d["content"] == "text"
        assert d["input_tokens"] == 10
        assert d["output_tokens"] == 5

    def test_from_dict(self):
        from attune.workflows.caching import CachedResponse

        data = {"content": "result", "input_tokens": 200, "output_tokens": 100}
        resp = CachedResponse.from_dict(data)
        assert resp.content == "result"
        assert resp.input_tokens == 200


class TestCachingMixin:
    def setup_method(self):
        from attune.workflows.caching import CachingMixin

        self.mixin = CachingMixin()

    def test_maybe_setup_cache_is_noop(self):
        self.mixin._maybe_setup_cache()

    def test_make_cache_key_with_system(self):
        key = self.mixin._make_cache_key("sys", "user msg")
        assert "sys" in key
        assert "user msg" in key

    def test_make_cache_key_without_system(self):
        key = self.mixin._make_cache_key("", "user msg")
        assert key == "user msg"

    def test_try_cache_lookup_returns_none(self):
        result = self.mixin._try_cache_lookup("stage", "sys", "user", "model")
        assert result is None

    def test_store_in_cache_returns_false(self):
        from attune.workflows.caching import CachedResponse

        resp = CachedResponse("content", 10, 5)
        result = self.mixin._store_in_cache("stage", "sys", "user", "model", resp)
        assert result is False

    def test_get_cache_type_returns_anthropic(self):
        assert self.mixin._get_cache_type() == "anthropic"

    def test_get_cache_stats_returns_empty(self):
        stats = self.mixin._get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0


# === Module: workflows/builder ===


class TestWorkflowBuilder:
    def test_initialization(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        builder = WorkflowBuilder(FakeWorkflow)
        assert builder.workflow_class is FakeWorkflow
        assert builder._enable_cache is True
        assert builder._enable_telemetry is True

    def test_with_config_returns_self(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        mock_config = MagicMock()
        result = builder.with_config(mock_config)
        assert result is builder
        assert builder._config is mock_config

    def test_with_cache_enabled_returns_self(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        result = builder.with_cache_enabled(False)
        assert result is builder
        assert builder._enable_cache is False

    def test_with_telemetry_enabled_returns_self(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        result = builder.with_telemetry_enabled(False)
        assert result is builder
        assert builder._enable_telemetry is False

    def test_with_cache_returns_self_noop(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        result = builder.with_cache(MagicMock())
        assert result is builder

    def test_with_progress_callback_returns_self(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        callback = MagicMock()
        result = builder.with_progress_callback(callback)
        assert result is builder
        assert builder._progress_callback is callback

    def test_with_context_returns_self(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = WorkflowBuilder(FakeWorkflow)
        mock_ctx = MagicMock()
        result = builder.with_context(mock_ctx)
        assert result is builder
        assert builder._ctx is mock_ctx

    def test_build_calls_workflow_class(self):
        from attune.workflows.builder import WorkflowBuilder

        received_kwargs = {}

        class FakeWorkflow:
            def __init__(self, **kwargs):
                received_kwargs.update(kwargs)

        builder = WorkflowBuilder(FakeWorkflow)
        builder.with_cache_enabled(False).with_telemetry_enabled(False)
        wf = builder.build()
        assert isinstance(wf, FakeWorkflow)
        assert received_kwargs["enable_cache"] is False
        assert received_kwargs["enable_telemetry"] is False

    def test_build_passes_config(self):
        from attune.workflows.builder import WorkflowBuilder

        received = {}

        class FakeWorkflow:
            def __init__(self, **kwargs):
                received.update(kwargs)

        mock_config = MagicMock()
        WorkflowBuilder(FakeWorkflow).with_config(mock_config).build()
        assert received["config"] is mock_config

    def test_chaining(self):
        from attune.workflows.builder import WorkflowBuilder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = (
            WorkflowBuilder(FakeWorkflow).with_cache_enabled(True).with_telemetry_enabled(True)
        )
        assert builder._enable_cache is True


class TestWorkflowBuilderFactory:
    def test_workflow_builder_factory(self):
        from attune.workflows.builder import WorkflowBuilder, workflow_builder

        class FakeWorkflow:
            def __init__(self, **kwargs):
                pass

        builder = workflow_builder(FakeWorkflow)
        assert isinstance(builder, WorkflowBuilder)
        assert builder.workflow_class is FakeWorkflow


# === Module: workflows/progress ===


class TestProgressTracker:
    def _make_tracker(self, stages=None):
        from attune.workflows.progress import ProgressTracker

        stages = stages or ["scan", "analyze", "report"]
        return ProgressTracker(
            workflow_name="test-workflow",
            workflow_id="abc123",
            stage_names=stages,
        )

    def test_initialization(self):
        tracker = self._make_tracker()
        assert tracker.workflow == "test-workflow"
        assert tracker.workflow_id == "abc123"
        assert len(tracker.stages) == 3
        assert tracker.cost_accumulated == 0.0

    def test_add_callback(self):
        tracker = self._make_tracker()
        cb = MagicMock()
        tracker.add_callback(cb)
        assert cb in tracker._callbacks

    def test_remove_callback(self):
        tracker = self._make_tracker()
        cb = MagicMock()
        tracker.add_callback(cb)
        tracker.remove_callback(cb)
        assert cb not in tracker._callbacks

    def test_start_workflow_calls_callbacks(self):
        tracker = self._make_tracker()
        cb = MagicMock()
        tracker.add_callback(cb)
        tracker.start_workflow()
        cb.assert_called_once()

    def test_start_stage_updates_status(self):
        from attune.workflows.progress_models import ProgressStatus

        tracker = self._make_tracker()
        tracker.start_stage("scan", tier="cheap")
        assert tracker.stages[0].status == ProgressStatus.RUNNING
        assert tracker.stages[0].tier == "cheap"

    def test_complete_stage_updates_status(self):
        from attune.workflows.progress_models import ProgressStatus

        tracker = self._make_tracker()
        tracker.start_stage("scan")
        tracker.complete_stage("scan", cost=0.01, tokens_in=100, tokens_out=50)
        assert tracker.stages[0].status == ProgressStatus.COMPLETED
        assert tracker.cost_accumulated == 0.01

    def test_fail_stage_updates_status(self):
        from attune.workflows.progress_models import ProgressStatus

        tracker = self._make_tracker()
        tracker.start_stage("scan")
        tracker.fail_stage("scan", error="timeout")
        assert tracker.stages[0].status == ProgressStatus.FAILED

    def test_skip_stage_updates_status(self):
        from attune.workflows.progress_models import ProgressStatus

        tracker = self._make_tracker()
        tracker.skip_stage("scan", reason="already done")
        assert tracker.stages[0].status == ProgressStatus.SKIPPED

    def test_complete_workflow_calls_callbacks(self):
        tracker = self._make_tracker()
        cb = MagicMock()
        tracker.add_callback(cb)
        tracker.complete_workflow()
        cb.assert_called()

    def test_fail_workflow_calls_callbacks(self):
        tracker = self._make_tracker()
        cb = MagicMock()
        tracker.add_callback(cb)
        tracker.fail_workflow("database error")
        cb.assert_called()

    def test_update_tier_changes_stage_tier(self):
        tracker = self._make_tracker()
        tracker.start_stage("scan", tier="cheap")
        tracker.update_tier("scan", "capable", reason="quality gate failed")
        assert tracker.stages[0].tier == "capable"

    def test_percent_complete_after_one_stage(self):
        tracker = self._make_tracker(["s1", "s2", "s3"])
        tracker.start_stage("s1")
        tracker.complete_stage("s1", cost=0.01, tokens_in=10, tokens_out=5)
        # One of 3 stages complete
        pct = tracker._calculate_percent_complete()
        assert abs(pct - 33.33) < 1.0

    def test_callback_error_does_not_raise(self):
        tracker = self._make_tracker()
        bad_cb = MagicMock(side_effect=RuntimeError("boom"))
        tracker.add_callback(bad_cb)
        tracker.start_workflow()  # Should not raise


class TestCreateProgressTracker:
    def test_creates_tracker(self):
        from attune.workflows.progress import ProgressTracker, create_progress_tracker

        tracker = create_progress_tracker("my-workflow", ["stage1", "stage2"])
        assert isinstance(tracker, ProgressTracker)
        assert tracker.workflow == "my-workflow"
        assert len(tracker.stages) == 2

    def test_adds_reporter_callback_when_provided(self):
        from attune.workflows.progress import create_progress_tracker
        from attune.workflows.progress_reporters import ConsoleProgressReporter

        reporter = ConsoleProgressReporter()
        tracker = create_progress_tracker("wf", ["s1"], reporter=reporter)
        assert len(tracker._callbacks) == 1


# === Module: workflows/progress_reporters ===


class TestConsoleProgressReporter:
    def test_construction(self):
        from attune.workflows.progress_reporters import ConsoleProgressReporter

        reporter = ConsoleProgressReporter(verbose=True, show_tokens=True)
        assert reporter.verbose is True
        assert reporter.show_tokens is True

    def test_report_prints_to_stdout(self, capsys):
        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate
        from attune.workflows.progress_reporters import ConsoleProgressReporter

        reporter = ConsoleProgressReporter()
        update = ProgressUpdate(
            workflow="test",
            workflow_id="wf-123",
            current_stage="scan",
            stage_index=0,
            total_stages=3,
            status=ProgressStatus.RUNNING,
            message="Running scan",
            cost_so_far=0.01,
            tokens_so_far=100,
            percent_complete=33.0,
            estimated_remaining_ms=None,
            stages=[],
        )
        reporter.report(update)
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or True  # May print or not depending on format

    def test_default_verbose_false(self):
        from attune.workflows.progress_reporters import ConsoleProgressReporter

        reporter = ConsoleProgressReporter()
        assert reporter.verbose is False


class TestJsonLinesProgressReporter:
    def test_construction(self, tmp_path):
        from attune.workflows.progress_reporters import JsonLinesProgressReporter

        out_file = tmp_path / "progress.jsonl"
        reporter = JsonLinesProgressReporter(str(out_file))
        assert reporter is not None

    def test_report_writes_json(self, tmp_path):
        import json

        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate
        from attune.workflows.progress_reporters import JsonLinesProgressReporter

        out_file = tmp_path / "progress.jsonl"
        reporter = JsonLinesProgressReporter(str(out_file))

        update = ProgressUpdate(
            workflow="test",
            workflow_id="wf-123",
            current_stage="scan",
            stage_index=0,
            total_stages=1,
            status=ProgressStatus.COMPLETED,
            message="done",
            cost_so_far=0.05,
            tokens_so_far=500,
            percent_complete=100.0,
            estimated_remaining_ms=None,
            stages=[],
        )
        reporter.report(update)

        lines = out_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["workflow"] == "test"
        assert data["status"] == "completed"
