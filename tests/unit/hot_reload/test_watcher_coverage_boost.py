"""Unit tests for file system watcher for workflow hot-reload.

This test suite provides comprehensive coverage for the file system watcher
that monitors workflow directories and triggers reloads on file changes.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest.importorskip("watchdog", reason="watchdog required for hot-reload tests")

from watchdog.events import FileSystemEvent  # noqa: E402

from attune.hot_reload.watcher import WorkflowFileHandler, WorkflowFileWatcher  # noqa: E402


@pytest.mark.unit
class TestWorkflowFileHandlerInit:
    """Test suite for WorkflowFileHandler initialization."""

    def test_init_stores_reload_callback(self):
        """Test that initialization stores reload callback."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        assert handler.reload_callback is callback

    def test_init_creates_empty_processing_set(self):
        """Test that initialization creates empty processing set."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        assert handler._processing == set()


@pytest.mark.unit
class TestWorkflowFileHandlerOnModified:
    """Test suite for WorkflowFileHandler.on_modified."""

    def test_on_modified_ignores_directory_events(self):
        """Test that directory events are ignored."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = True
        event.src_path = "/path/to/directory"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_on_modified_ignores_non_python_files(self):
        """Test that non-Python files are ignored."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_on_modified_ignores_pycache_files(self):
        """Test that __pycache__ files are ignored."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/path/__pycache__/workflow.cpython-310.pyc"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_on_modified_ignores_test_files(self):
        """Test that test files are ignored."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/path/to/test_workflow.py"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_on_modified_processes_workflow_files(self):
        """Test that workflow Python files are processed."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/workflows/code_review.py"

        handler.on_modified(event)

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == "code_review"
        assert call_args[1] == "/workflows/code_review.py"

    def test_on_modified_handles_bytes_path(self):
        """Test that byte string paths are decoded."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = b"/workflows/bug_predict.py"

        handler.on_modified(event)

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == "bug_predict"
        assert call_args[1] == "/workflows/bug_predict.py"

    def test_on_modified_prevents_duplicate_processing(self):
        """Test that duplicate events for same file are prevented."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/workflows/test_workflow.py"

        # Simulate file being processed
        handler._processing.add("/workflows/test_workflow.py")

        handler.on_modified(event)

        # Callback should not be called since file is already being processed
        callback.assert_not_called()

    def test_on_modified_removes_from_processing_after_completion(self):
        """Test that file is removed from processing set after completion."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/workflows/workflow.py"

        handler.on_modified(event)

        # File should be removed from processing set
        assert "/workflows/workflow.py" not in handler._processing

    def test_on_modified_handles_callback_exception(self):
        """Test that exceptions in callback are handled gracefully."""
        callback = MagicMock(side_effect=ValueError("Callback error"))
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/workflows/workflow.py"

        # Should not raise exception
        handler.on_modified(event)

        # File should still be removed from processing set
        assert "/workflows/workflow.py" not in handler._processing

    def test_on_modified_handles_extract_workflow_id_exception(self):
        """Test that exceptions in workflow ID extraction are handled."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        # Patch _extract_workflow_id to raise exception
        with patch.object(handler, "_extract_workflow_id", side_effect=Exception("Extract error")):
            event = Mock(spec=FileSystemEvent)
            event.is_directory = False
            event.src_path = "/workflows/workflow.py"

            # Should not raise exception
            handler.on_modified(event)

        # Callback should not be called
        callback.assert_not_called()


@pytest.mark.unit
class TestWorkflowFileHandlerExtractWorkflowId:
    """Test suite for WorkflowFileHandler._extract_workflow_id."""

    def test_extract_workflow_id_from_simple_filename(self):
        """Test extracting workflow ID from simple filename."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        workflow_id = handler._extract_workflow_id("/workflows/code_review.py")

        assert workflow_id == "code_review"

    def test_extract_workflow_id_removes_workflow_suffix(self):
        """Test that '_workflow' suffix is removed."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        workflow_id = handler._extract_workflow_id("/workflows/bug_predict_workflow.py")

        assert workflow_id == "bug_predict"

    def test_extract_workflow_id_removes_workflow_prefix(self):
        """Test that 'workflow_' prefix is removed."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        workflow_id = handler._extract_workflow_id("/workflows/workflow_security.py")

        assert workflow_id == "security"

    def test_extract_workflow_id_converts_to_lowercase(self):
        """Test that workflow ID is converted to lowercase."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        workflow_id = handler._extract_workflow_id("/workflows/CodeReview.py")

        assert workflow_id == "codereview"

    def test_extract_workflow_id_handles_complex_paths(self):
        """Test extracting workflow ID from complex paths."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        workflow_id = handler._extract_workflow_id(
            "/home/user/project/src/attune/workflows/test_gen.py"
        )

        assert workflow_id == "test_gen"

    def test_extract_workflow_id_with_extension_only_filename(self):
        """Test extracting workflow ID from filename that's just extension."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        # Path.stem for "/.py" returns ".py" (the filename before extension)
        workflow_id = handler._extract_workflow_id("/.py")

        # Should return lowercase version of the stem
        assert workflow_id == ".py"


@pytest.mark.unit
class TestWorkflowFileWatcherInit:
    """Test suite for WorkflowFileWatcher initialization."""

    def test_init_stores_workflow_dirs_as_paths(self):
        """Test that workflow directories are stored as Path objects."""
        callback = MagicMock()
        dirs = ["/path/to/workflows", "/path/to/custom_workflows"]

        watcher = WorkflowFileWatcher(workflow_dirs=dirs, reload_callback=callback)

        assert len(watcher.workflow_dirs) == 2
        assert all(isinstance(d, Path) for d in watcher.workflow_dirs)
        assert watcher.workflow_dirs[0] == Path("/path/to/workflows")
        assert watcher.workflow_dirs[1] == Path("/path/to/custom_workflows")

    def test_init_stores_reload_callback(self):
        """Test that reload callback is stored."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)

        assert watcher.reload_callback is callback

    def test_init_creates_observer(self):
        """Test that Observer instance is created."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)

        assert watcher.observer is not None

    def test_init_creates_event_handler(self):
        """Test that WorkflowFileHandler instance is created."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)

        assert isinstance(watcher.event_handler, WorkflowFileHandler)
        assert watcher.event_handler.reload_callback is callback

    def test_init_sets_running_to_false(self):
        """Test that _running is initially False."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)

        assert watcher._running is False


@pytest.mark.unit
class TestWorkflowFileWatcherStart:
    """Test suite for WorkflowFileWatcher.start."""

    def test_start_does_nothing_if_already_running(self):
        """Test that start does nothing if already running."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        with patch.object(watcher.observer, "start") as mock_start:
            watcher.start()
            mock_start.assert_not_called()

    def test_start_schedules_valid_directories(self, tmp_path):
        """Test that start schedules watching for valid directories."""
        callback = MagicMock()

        # Create valid directories
        dir1 = tmp_path / "workflows1"
        dir2 = tmp_path / "workflows2"
        dir1.mkdir()
        dir2.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[dir1, dir2], reload_callback=callback)

        with patch.object(watcher.observer, "schedule") as mock_schedule:
            with patch.object(watcher.observer, "start") as mock_start:
                watcher.start()

                # Should schedule both directories
                assert mock_schedule.call_count == 2
                mock_start.assert_called_once()

        assert watcher._running is True

    def test_start_skips_nonexistent_directories(self, tmp_path):
        """Test that start skips directories that don't exist."""
        callback = MagicMock()

        # One valid, one nonexistent
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        invalid_dir = tmp_path / "nonexistent"

        watcher = WorkflowFileWatcher(
            workflow_dirs=[valid_dir, invalid_dir], reload_callback=callback
        )

        with patch.object(watcher.observer, "schedule") as mock_schedule:
            with patch.object(watcher.observer, "start"):
                watcher.start()

                # Should only schedule valid directory
                assert mock_schedule.call_count == 1

    def test_start_skips_files_not_directories(self, tmp_path):
        """Test that start skips paths that are files, not directories."""
        callback = MagicMock()

        # Create a file instead of directory
        file_path = tmp_path / "workflow.py"
        file_path.write_text("# workflow")

        # Create a valid directory
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(
            workflow_dirs=[file_path, valid_dir], reload_callback=callback
        )

        with patch.object(watcher.observer, "schedule") as mock_schedule:
            with patch.object(watcher.observer, "start"):
                watcher.start()

                # Should only schedule valid directory
                assert mock_schedule.call_count == 1

    def test_start_does_nothing_with_no_valid_directories(self):
        """Test that start does nothing if no valid directories."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/nonexistent"], reload_callback=callback)

        with patch.object(watcher.observer, "start") as mock_start:
            watcher.start()

            # Observer should not be started
            mock_start.assert_not_called()

        assert watcher._running is False

    def test_start_sets_running_to_true(self, tmp_path):
        """Test that start sets _running to True."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher.observer, "start"):
            watcher.start()

        assert watcher._running is True


@pytest.mark.unit
class TestWorkflowFileWatcherStop:
    """Test suite for WorkflowFileWatcher.stop."""

    def test_stop_does_nothing_if_not_running(self):
        """Test that stop does nothing if not running."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = False

        with patch.object(watcher.observer, "stop") as mock_stop:
            watcher.stop()
            mock_stop.assert_not_called()

    def test_stop_stops_observer(self):
        """Test that stop calls observer.stop()."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        with patch.object(watcher.observer, "stop") as mock_stop:
            with patch.object(watcher.observer, "join"):
                watcher.stop()
                mock_stop.assert_called_once()

    def test_stop_joins_observer_with_timeout(self):
        """Test that stop joins observer with timeout."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        with patch.object(watcher.observer, "stop"):
            with patch.object(watcher.observer, "join") as mock_join:
                watcher.stop()
                mock_join.assert_called_once_with(timeout=5.0)

    def test_stop_sets_running_to_false(self):
        """Test that stop sets _running to False."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        with patch.object(watcher.observer, "stop"):
            with patch.object(watcher.observer, "join"):
                watcher.stop()

        assert watcher._running is False


@pytest.mark.unit
class TestWorkflowFileWatcherIsRunning:
    """Test suite for WorkflowFileWatcher.is_running."""

    def test_is_running_returns_true_when_running(self):
        """Test that is_running returns True when running."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        assert watcher.is_running() is True

    def test_is_running_returns_false_when_not_running(self):
        """Test that is_running returns False when not running."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = False

        assert watcher.is_running() is False


@pytest.mark.unit
class TestWorkflowFileWatcherContextManager:
    """Test suite for WorkflowFileWatcher context manager."""

    def test_context_manager_starts_watcher_on_enter(self, tmp_path):
        """Test that context manager starts watcher on __enter__."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher, "start") as mock_start:
            with watcher:
                mock_start.assert_called_once()

    def test_context_manager_stops_watcher_on_exit(self, tmp_path):
        """Test that context manager stops watcher on __exit__."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher, "start"):
            with patch.object(watcher, "stop") as mock_stop:
                with watcher:
                    pass
                mock_stop.assert_called_once()

    def test_context_manager_returns_self_on_enter(self, tmp_path):
        """Test that context manager returns self on __enter__."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher, "start"):
            with watcher as w:
                assert w is watcher

    def test_context_manager_stops_on_exception(self, tmp_path):
        """Test that context manager stops watcher even on exception."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher, "start"):
            with patch.object(watcher, "stop") as mock_stop:
                try:
                    with watcher:
                        raise ValueError("Test exception")
                except ValueError:
                    pass

                # Stop should still be called
                mock_stop.assert_called_once()


@pytest.mark.unit
class TestWorkflowFileWatcherEdgeCases:
    """Test suite for edge cases."""

    def test_watcher_with_empty_workflow_dirs_list(self):
        """Test watcher with empty workflow directories list."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=[], reload_callback=callback)

        assert watcher.workflow_dirs == []
        assert watcher._running is False

    def test_watcher_with_mixed_valid_invalid_dirs(self, tmp_path):
        """Test watcher with mix of valid and invalid directories."""
        callback = MagicMock()

        valid1 = tmp_path / "valid1"
        valid2 = tmp_path / "valid2"
        valid1.mkdir()
        valid2.mkdir()

        invalid1 = tmp_path / "nonexistent"
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        watcher = WorkflowFileWatcher(
            workflow_dirs=[valid1, invalid1, valid2, file_path], reload_callback=callback
        )

        with patch.object(watcher.observer, "schedule") as mock_schedule:
            with patch.object(watcher.observer, "start"):
                watcher.start()

                # Should only schedule the 2 valid directories
                assert mock_schedule.call_count == 2

    def test_handler_callback_receives_correct_arguments(self):
        """Test that callback receives correct arguments."""
        callback = MagicMock()
        handler = WorkflowFileHandler(reload_callback=callback)

        event = Mock(spec=FileSystemEvent)
        event.is_directory = False
        event.src_path = "/workflows/security_audit_workflow.py"

        handler.on_modified(event)

        # Should extract "security_audit" as workflow ID
        callback.assert_called_once_with("security_audit", "/workflows/security_audit_workflow.py")

    def test_multiple_start_calls_idempotent(self, tmp_path):
        """Test that multiple start calls are idempotent."""
        callback = MagicMock()
        valid_dir = tmp_path / "workflows"
        valid_dir.mkdir()

        watcher = WorkflowFileWatcher(workflow_dirs=[valid_dir], reload_callback=callback)

        with patch.object(watcher.observer, "start") as mock_start:
            watcher.start()
            watcher.start()  # Second call
            watcher.start()  # Third call

            # Observer should only be started once
            assert mock_start.call_count == 1

    def test_multiple_stop_calls_idempotent(self):
        """Test that multiple stop calls are idempotent."""
        callback = MagicMock()
        watcher = WorkflowFileWatcher(workflow_dirs=["/path"], reload_callback=callback)
        watcher._running = True

        with patch.object(watcher.observer, "stop") as mock_stop:
            with patch.object(watcher.observer, "join"):
                watcher.stop()
                watcher.stop()  # Second call
                watcher.stop()  # Third call

                # Observer should only be stopped once
                assert mock_stop.call_count == 1
