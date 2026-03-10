"""Tests for pipeline spec reader."""

import pytest

from attune.pipeline.spec_reader import read_spec


class TestReadSpec:
    """Tests for read_spec function."""

    def test_reads_real_plan(self):
        """read_spec extracts tasks from a real plan file."""
        tasks = read_spec(".claude/plans/pipeline-orchestrator.md")
        assert len(tasks) == 5
        assert tasks[0].task_id == "1"
        assert tasks[0].name == "spec-reader"
        assert "spec_reader" in tasks[0].objective.lower()

    def test_task_has_files(self):
        """Tasks include files_to_create and files_to_modify."""
        tasks = read_spec(".claude/plans/pipeline-orchestrator.md")
        # Task 1 creates __init__.py and spec_reader.py
        assert len(tasks[0].files_to_create) >= 2

    def test_task_has_validation(self):
        """Tasks include validation checks."""
        tasks = read_spec(".claude/plans/pipeline-orchestrator.md")
        assert len(tasks[0].validation_checks) >= 1

    def test_task_has_dependencies(self):
        """Tasks include dependency references."""
        tasks = read_spec(".claude/plans/pipeline-orchestrator.md")
        # Task 3 depends on tasks 1 and 2
        task3 = tasks[2]
        assert "1" in task3.dependencies
        assert "2" in task3.dependencies

    def test_task_has_risks(self):
        """Tasks include risk entries with severity."""
        tasks = read_spec(".claude/plans/pipeline-orchestrator.md")
        # Task 1 has a low-severity risk
        assert len(tasks[0].risks) >= 1
        assert tasks[0].risks[0]["severity"] == "low"

    def test_empty_file_returns_empty(self, tmp_path):
        """Empty file returns empty list."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        assert read_spec(str(empty)) == []

    def test_no_xml_returns_empty(self, tmp_path):
        """File with no XML returns empty list."""
        plain = tmp_path / "plain.md"
        plain.write_text("# Just a heading\n\nSome text.\n")
        assert read_spec(str(plain)) == []

    def test_file_not_found(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            read_spec("/nonexistent/plan.md")

    def test_empty_path_raises(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            read_spec("")

    def test_reads_validation_framework_spec(self):
        """read_spec works on the validation framework plan."""
        tasks = read_spec(".claude/plans/workflow-validation-framework.md")
        # This spec should have tasks too
        assert len(tasks) >= 1
