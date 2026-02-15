"""Unit tests for TaskDecomposer and DecomposedTask.

Tests cover:
- DecomposedTask data class: to_dict, to_xml
- TaskDecomposer XML parsing: _parse_tasks_from_xml
- XML extraction helpers: _extract_tag, _extract_files, _extract_list, _extract_risks
- decompose() with mocked LLM

Created: 2026-02-15
"""

import pytest

from unittest.mock import AsyncMock, MagicMock

from attune.wizards.decomposer import DecomposedTask, TaskDecomposer


# =========================================================================
# DecomposedTask
# =========================================================================


class TestDecomposedTask:
    """Test DecomposedTask data class."""

    def test_defaults(self):
        """Test default values."""
        task = DecomposedTask(task_id="1", name="task1", objective="Do something")
        assert task.files_to_create == []
        assert task.files_to_modify == []
        assert task.validation_checks == []
        assert task.risks == []
        assert task.dependencies == []

    def test_to_dict(self):
        """Test serialization to dict."""
        task = DecomposedTask(
            task_id="1",
            name="add-auth",
            objective="Add authentication",
            files_to_create=[{"path": "src/auth.py", "description": "Auth module"}],
            files_to_modify=[{"path": "src/app.py", "description": "Add auth middleware"}],
            validation_checks=["Auth endpoint returns 401 for unauthenticated"],
            risks=[{"severity": "medium", "description": "May break existing sessions"}],
            dependencies=["0"],
        )
        d = task.to_dict()

        assert d["task_id"] == "1"
        assert d["name"] == "add-auth"
        assert d["objective"] == "Add authentication"
        assert len(d["files_to_create"]) == 1
        assert d["files_to_create"][0]["path"] == "src/auth.py"
        assert len(d["files_to_modify"]) == 1
        assert len(d["validation_checks"]) == 1
        assert len(d["risks"]) == 1
        assert d["dependencies"] == ["0"]

    def test_to_xml_basic(self):
        """Test basic XML rendering."""
        task = DecomposedTask(
            task_id="1",
            name="simple-task",
            objective="Do a thing",
        )
        xml = task.to_xml()

        assert '<task id="1" name="simple-task">' in xml
        assert "<objective>Do a thing</objective>" in xml
        assert "</task>" in xml

    def test_to_xml_with_files(self):
        """Test XML rendering includes files sections."""
        task = DecomposedTask(
            task_id="2",
            name="files-task",
            objective="Create and modify files",
            files_to_create=[{"path": "new.py", "description": "New file"}],
            files_to_modify=[{"path": "old.py", "description": "Update old file"}],
        )
        xml = task.to_xml()

        assert "<files-to-create>" in xml
        assert '<file path="new.py">New file</file>' in xml
        assert "<files-to-modify>" in xml
        assert '<file path="old.py">Update old file</file>' in xml

    def test_to_xml_with_validation(self):
        """Test XML rendering includes validation checks."""
        task = DecomposedTask(
            task_id="3",
            name="validated-task",
            objective="Do validated thing",
            validation_checks=["Tests pass", "No regressions"],
        )
        xml = task.to_xml()

        assert "<validation>" in xml
        assert "<check>Tests pass</check>" in xml
        assert "<check>No regressions</check>" in xml

    def test_to_xml_with_risks(self):
        """Test XML rendering includes risks."""
        task = DecomposedTask(
            task_id="4",
            name="risky-task",
            objective="Do risky thing",
            risks=[{"severity": "high", "description": "May break production"}],
        )
        xml = task.to_xml()

        assert "<risks>" in xml
        assert '<risk severity="high">May break production</risk>' in xml

    def test_to_xml_with_dependencies(self):
        """Test XML rendering includes dependencies."""
        task = DecomposedTask(
            task_id="3",
            name="dep-task",
            objective="Depends on others",
            dependencies=["1", "2"],
        )
        xml = task.to_xml()

        assert "<dependencies>" in xml
        assert "<dep>1</dep>" in xml
        assert "<dep>2</dep>" in xml

    def test_to_xml_empty_optional_sections(self):
        """Test XML excludes empty optional sections."""
        task = DecomposedTask(task_id="5", name="minimal", objective="Minimal task")
        xml = task.to_xml()

        assert "<files-to-create>" not in xml
        assert "<files-to-modify>" not in xml
        assert "<validation>" not in xml
        assert "<risks>" not in xml
        assert "<dependencies>" not in xml


# =========================================================================
# TaskDecomposer XML parsing
# =========================================================================


class TestTaskDecomposerParsing:
    """Test TaskDecomposer XML parsing methods."""

    def setup_method(self):
        """Set up a decomposer with a mock workflow."""
        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def test_parse_single_task(self):
        """Test parsing a single task element."""
        xml = """
        <tasks>
          <task id="1" name="add-auth">
            <objective>Add user authentication</objective>
            <files-to-create>
              <file path="src/auth.py">Authentication module</file>
            </files-to-create>
            <files-to-modify>
              <file path="src/app.py">Add auth middleware</file>
            </files-to-modify>
            <validation>
              <check>Auth endpoint returns 401 for unauthenticated</check>
            </validation>
            <risks>
              <risk severity="medium">May break existing sessions</risk>
            </risks>
            <dependencies>
              <dep>0</dep>
            </dependencies>
          </task>
        </tasks>
        """
        tasks = self.decomposer._parse_tasks_from_xml(xml)

        assert len(tasks) == 1
        task = tasks[0]
        assert task.task_id == "1"
        assert task.name == "add-auth"
        assert task.objective == "Add user authentication"
        assert len(task.files_to_create) == 1
        assert task.files_to_create[0]["path"] == "src/auth.py"
        assert len(task.files_to_modify) == 1
        assert len(task.validation_checks) == 1
        assert len(task.risks) == 1
        assert task.risks[0]["severity"] == "medium"
        assert task.dependencies == ["0"]

    def test_parse_multiple_tasks(self):
        """Test parsing multiple task elements."""
        xml = """
        <tasks>
          <task id="1" name="task-one">
            <objective>First task</objective>
          </task>
          <task id="2" name="task-two">
            <objective>Second task</objective>
            <dependencies><dep>1</dep></dependencies>
          </task>
        </tasks>
        """
        tasks = self.decomposer._parse_tasks_from_xml(xml)

        assert len(tasks) == 2
        assert tasks[0].task_id == "1"
        assert tasks[1].task_id == "2"
        assert tasks[1].dependencies == ["1"]

    def test_parse_no_tasks(self):
        """Test parsing response with no task elements."""
        xml = "Some non-XML response from the LLM"
        tasks = self.decomposer._parse_tasks_from_xml(xml)

        assert tasks == []

    def test_parse_task_without_name(self):
        """Test parsing task where name attribute is missing."""
        xml = '<task id="1"><objective>Test</objective></task>'
        tasks = self.decomposer._parse_tasks_from_xml(xml)

        assert len(tasks) == 1
        assert tasks[0].name == "1"  # Falls back to task_id

    def test_parse_markdown_wrapped_xml(self):
        """Test parsing XML wrapped in markdown code fences."""
        xml = """Here is the decomposition:

```xml
<tasks>
  <task id="1" name="fix-bug">
    <objective>Fix the bug</objective>
  </task>
</tasks>
```

That should do it!"""
        tasks = self.decomposer._parse_tasks_from_xml(xml)

        assert len(tasks) == 1
        assert tasks[0].name == "fix-bug"

    def test_extract_tag(self):
        """Test _extract_tag helper."""
        assert self.decomposer._extract_tag("<a>hello</a>", "a") == "hello"
        assert self.decomposer._extract_tag("<a>  spaced  </a>", "a") == "spaced"
        assert self.decomposer._extract_tag("<b>test</b>", "a") == ""

    def test_extract_files(self):
        """Test _extract_files helper."""
        xml = """
        <files-to-create>
          <file path="a.py">File A</file>
          <file path="b.py">File B</file>
        </files-to-create>
        """
        files = self.decomposer._extract_files(xml, "files-to-create")

        assert len(files) == 2
        assert files[0] == {"path": "a.py", "description": "File A"}
        assert files[1] == {"path": "b.py", "description": "File B"}

    def test_extract_files_no_section(self):
        """Test _extract_files when section is missing."""
        files = self.decomposer._extract_files("<other>data</other>", "files-to-create")
        assert files == []

    def test_extract_list(self):
        """Test _extract_list helper."""
        xml = """
        <validation>
          <check>Tests pass</check>
          <check>No regressions</check>
        </validation>
        """
        items = self.decomposer._extract_list(xml, "validation", "check")

        assert items == ["Tests pass", "No regressions"]

    def test_extract_list_no_section(self):
        """Test _extract_list when section is missing."""
        items = self.decomposer._extract_list("<other/>", "validation", "check")
        assert items == []

    def test_extract_risks(self):
        """Test _extract_risks helper."""
        xml = """
        <risks>
          <risk severity="high">Breaking change</risk>
          <risk severity="low">Minor impact</risk>
        </risks>
        """
        risks = self.decomposer._extract_risks(xml)

        assert len(risks) == 2
        assert risks[0] == {"severity": "high", "description": "Breaking change"}
        assert risks[1] == {"severity": "low", "description": "Minor impact"}

    def test_extract_risks_no_section(self):
        """Test _extract_risks when section is missing."""
        risks = self.decomposer._extract_risks("<other/>")
        assert risks == []


# =========================================================================
# TaskDecomposer.decompose()
# =========================================================================


class TestTaskDecomposerDecompose:
    """Test TaskDecomposer.decompose() with mocked LLM."""

    @pytest.mark.asyncio
    async def test_decompose_success(self):
        """Test successful decomposition via LLM."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(
            return_value=(
                '<tasks><task id="1" name="fix"><objective>Fix it</objective></task></tasks>',
                100,
                50,
            )
        )
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Fix the auth bug",
            codebase_context="Flask app",
            constraints=["No breaking changes"],
        )

        assert len(tasks) == 1
        assert tasks[0].name == "fix"
        mock_workflow._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_decompose_non_tuple_result(self):
        """Test decompose handles non-tuple LLM result."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(
            return_value='<tasks><task id="1" name="t"><objective>O</objective></task></tasks>'
        )
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Test",
            codebase_context="Context",
        )

        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_decompose_llm_failure(self):
        """Test decompose returns empty list on LLM failure."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Test",
            codebase_context="Context",
        )

        assert tasks == []

    @pytest.mark.asyncio
    async def test_decompose_no_constraints(self):
        """Test decompose with no constraints."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Test",
            codebase_context="",
        )

        assert tasks == []

    @pytest.mark.asyncio
    async def test_decompose_empty_codebase_context(self):
        """Test decompose with empty codebase context."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Do something",
            codebase_context="",
        )

        # Verify codebase context section is not in prompt
        call_args = mock_workflow._call_llm.call_args
        prompt = call_args[0][0]
        assert "Codebase context:" not in prompt
