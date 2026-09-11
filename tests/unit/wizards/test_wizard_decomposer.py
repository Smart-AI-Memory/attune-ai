"""Unit tests for TaskDecomposer and DecomposedTask.

Tests cover:
- DecomposedTask data class: to_dict, to_xml
- TaskDecomposer XML parsing: _parse_tasks_from_xml
- XML extraction helpers: _extract_tag, _extract_files, _extract_list, _extract_risks
- decompose() with mocked LLM

Created: 2026-02-15
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    async def test_decompose_sends_schema_in_user_message(self):
        """Test decompose folds the schema into the user message.

        The EmpathyLLM interaction layer overrides the ``system`` argument
        with its own level-based prompt, so the decomposition schema must
        travel in the user turn to actually reach the model.
        """
        from attune.wizards.decomposer import DECOMPOSITION_SYSTEM_PROMPT

        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(
            return_value=(
                '<tasks><task id="1" name="t"><objective>O</objective></task></tasks>',
                10,
                5,
            )
        )
        decomposer = TaskDecomposer(workflow=mock_workflow)

        tasks = await decomposer.decompose(
            problem_description="Test",
            codebase_context="Context",
        )

        assert len(tasks) == 1
        call_args = mock_workflow._call_llm.call_args
        assert call_args.kwargs["system"] == ""
        assert DECOMPOSITION_SYSTEM_PROMPT in call_args.kwargs["user_message"]

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

        await decomposer.decompose(
            problem_description="Do something",
            codebase_context="",
        )

        # Verify codebase context section is not in prompt
        call_args = mock_workflow._call_llm.call_args
        prompt = call_args.kwargs["user_message"]
        assert "Codebase context:" not in prompt


# =========================================================================
# Additional uncovered paths
# =========================================================================


class TestDecomposedTaskToXml:
    """Additional to_xml() edge cases."""

    def test_to_xml_file_without_description_key(self):
        """Test to_xml when file dict lacks 'description' key."""
        task = DecomposedTask(
            task_id="1",
            name="edge",
            objective="Edge case",
            files_to_create=[{"path": "src/foo.py"}],  # No 'description' key
        )
        xml = task.to_xml()

        # Should not raise; description should be empty string
        assert '<file path="src/foo.py"></file>' in xml

    def test_to_xml_multiple_risks_different_severities(self):
        """Test to_xml with multiple risks across different severity levels."""
        task = DecomposedTask(
            task_id="2",
            name="multi-risk",
            objective="Many risks",
            risks=[
                {"severity": "critical", "description": "Data loss possible"},
                {"severity": "low", "description": "Minor performance"},
            ],
        )
        xml = task.to_xml()

        assert '<risk severity="critical">Data loss possible</risk>' in xml
        assert '<risk severity="low">Minor performance</risk>' in xml

    def test_to_xml_risk_missing_severity_defaults_to_medium(self):
        """Test to_xml risk dict missing 'severity' uses 'medium' default."""
        task = DecomposedTask(
            task_id="3",
            name="default-sev",
            objective="Test",
            risks=[{"description": "Unknown severity"}],
        )
        xml = task.to_xml()

        assert '<risk severity="medium">Unknown severity</risk>' in xml

    def test_to_xml_risk_missing_description_uses_empty(self):
        """Test to_xml risk dict missing 'description' uses empty string."""
        task = DecomposedTask(
            task_id="4",
            name="empty-desc",
            objective="Test",
            risks=[{"severity": "low"}],
        )
        xml = task.to_xml()

        assert '<risk severity="low"></risk>' in xml

    def test_to_xml_full_task_roundtrip(self):
        """Test full task XML can be parsed back by TaskDecomposer."""
        from unittest.mock import MagicMock

        task = DecomposedTask(
            task_id="7",
            name="complete-task",
            objective="Complete implementation",
            files_to_create=[{"path": "src/new.py", "description": "New module"}],
            files_to_modify=[{"path": "src/old.py", "description": "Update old"}],
            validation_checks=["All tests pass", "No lint errors"],
            risks=[{"severity": "medium", "description": "API change"}],
            dependencies=["6"],
        )
        xml = task.to_xml()

        # Wrap in <tasks> so the parser can find it
        wrapped = f"<tasks>{xml}</tasks>"
        decomposer = TaskDecomposer(workflow=MagicMock())
        parsed = decomposer._parse_tasks_from_xml(wrapped)

        assert len(parsed) == 1
        roundtripped = parsed[0]
        assert roundtripped.task_id == "7"
        assert roundtripped.name == "complete-task"
        assert roundtripped.objective == "Complete implementation"
        assert len(roundtripped.files_to_create) == 1
        assert len(roundtripped.files_to_modify) == 1
        assert len(roundtripped.validation_checks) == 2
        assert len(roundtripped.risks) == 1
        assert roundtripped.dependencies == ["6"]

    def test_to_xml_modify_only_no_create(self):
        """Test XML renders files-to-modify without files-to-create."""
        task = DecomposedTask(
            task_id="5",
            name="modify-only",
            objective="Only modifies",
            files_to_modify=[{"path": "src/update.py", "description": "Update it"}],
        )
        xml = task.to_xml()

        assert "<files-to-create>" not in xml
        assert "<files-to-modify>" in xml
        assert '<file path="src/update.py">Update it</file>' in xml


class TestExtractTagEdgeCases:
    """Test _extract_tag with edge cases."""

    def setup_method(self):
        """Set up decomposer."""
        from unittest.mock import MagicMock

        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def test_extract_tag_multiline_content(self):
        """Test extraction of multiline tag content."""
        xml = "<objective>\n  Line one\n  Line two\n</objective>"
        result = self.decomposer._extract_tag(xml, "objective")
        assert "Line one" in result
        assert "Line two" in result

    def test_extract_tag_strips_whitespace(self):
        """Test extracted content has leading/trailing whitespace stripped."""
        xml = "<tag>   content with spaces   </tag>"
        result = self.decomposer._extract_tag(xml, "tag")
        assert result == "content with spaces"

    def test_extract_tag_empty_content(self):
        """Test extraction of tag with empty content."""
        xml = "<objective></objective>"
        result = self.decomposer._extract_tag(xml, "objective")
        assert result == ""

    def test_extract_tag_missing_returns_empty_string(self):
        """Test extraction of missing tag returns empty string, not None."""
        result = self.decomposer._extract_tag("<other>data</other>", "missing")
        assert result == ""
        assert isinstance(result, str)


class TestExtractFilesEdgeCases:
    """Test _extract_files with edge cases."""

    def setup_method(self):
        """Set up decomposer."""
        from unittest.mock import MagicMock

        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def test_extract_files_single_file_no_description(self):
        """Test extracting a file with empty description."""
        xml = """
        <files-to-create>
          <file path="src/foo.py"></file>
        </files-to-create>
        """
        files = self.decomposer._extract_files(xml, "files-to-create")
        assert len(files) == 1
        assert files[0]["path"] == "src/foo.py"
        assert files[0]["description"] == ""

    def test_extract_files_multiline_description(self):
        """Test file with multiline description is stripped."""
        xml = """
        <files-to-create>
          <file path="src/auth.py">
            Auth module
          </file>
        </files-to-create>
        """
        files = self.decomposer._extract_files(xml, "files-to-create")
        assert len(files) == 1
        assert files[0]["description"] == "Auth module"

    def test_extract_files_modify_section(self):
        """Test extracting files-to-modify section."""
        xml = """
        <files-to-modify>
          <file path="src/main.py">Update imports</file>
          <file path="src/utils.py">Add helper</file>
        </files-to-modify>
        """
        files = self.decomposer._extract_files(xml, "files-to-modify")
        assert len(files) == 2
        assert files[0]["path"] == "src/main.py"
        assert files[1]["path"] == "src/utils.py"


class TestExtractRisksEdgeCases:
    """Test _extract_risks with edge cases."""

    def setup_method(self):
        """Set up decomposer."""
        from unittest.mock import MagicMock

        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def test_extract_risks_critical_severity(self):
        """Test extracting critical severity risk."""
        xml = """
        <risks>
          <risk severity="critical">Data loss</risk>
        </risks>
        """
        risks = self.decomposer._extract_risks(xml)
        assert len(risks) == 1
        assert risks[0]["severity"] == "critical"
        assert risks[0]["description"] == "Data loss"

    def test_extract_risks_all_severity_levels(self):
        """Test extracting multiple risks with all severity levels."""
        xml = """
        <risks>
          <risk severity="critical">Critical issue</risk>
          <risk severity="high">High issue</risk>
          <risk severity="medium">Medium issue</risk>
          <risk severity="low">Low issue</risk>
        </risks>
        """
        risks = self.decomposer._extract_risks(xml)
        assert len(risks) == 4
        severities = [r["severity"] for r in risks]
        assert "critical" in severities
        assert "low" in severities


class TestExtractListEdgeCases:
    """Test _extract_list with edge cases."""

    def setup_method(self):
        """Set up decomposer."""
        from unittest.mock import MagicMock

        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def test_extract_list_single_item(self):
        """Test extracting list with a single item."""
        xml = "<validation><check>Run tests</check></validation>"
        items = self.decomposer._extract_list(xml, "validation", "check")
        assert items == ["Run tests"]

    def test_extract_list_empty_section(self):
        """Test extracting list with no items in section."""
        xml = "<validation></validation>"
        items = self.decomposer._extract_list(xml, "validation", "check")
        assert items == []

    def test_extract_list_dependencies(self):
        """Test extracting dependencies list."""
        xml = """
        <dependencies>
          <dep>task-1</dep>
          <dep>task-2</dep>
          <dep>task-3</dep>
        </dependencies>
        """
        items = self.decomposer._extract_list(xml, "dependencies", "dep")
        assert items == ["task-1", "task-2", "task-3"]


class TestDecomposeWithParams:
    """Test decompose() with various parameter combinations."""

    @pytest.mark.asyncio
    async def test_decompose_with_constraints_appear_in_prompt(self):
        """Test that constraints appear in the constructed prompt."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Add tests",
            codebase_context="Python app",
            constraints=["No breaking changes", "Keep coverage > 80%"],
        )

        call_args = mock_workflow._call_llm.call_args
        prompt = call_args.kwargs["user_message"]
        assert "No breaking changes" in prompt
        assert "Keep coverage > 80%" in prompt

    @pytest.mark.asyncio
    async def test_decompose_with_codebase_context_appears_in_prompt(self):
        """Test that codebase_context appears in the prompt."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Add tests",
            codebase_context="Flask app with Postgres",
        )

        call_args = mock_workflow._call_llm.call_args
        prompt = call_args.kwargs["user_message"]
        assert "Flask app with Postgres" in prompt
        assert "Codebase context:" in prompt

    @pytest.mark.asyncio
    async def test_decompose_none_constraints_treated_as_empty(self):
        """Test that None constraints do not add a constraints section."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Fix bug",
            codebase_context="Context",
            constraints=None,
        )

        call_args = mock_workflow._call_llm.call_args
        prompt = call_args.kwargs["user_message"]
        assert "Constraints:" not in prompt

    @pytest.mark.asyncio
    async def test_decompose_problem_description_in_prompt(self):
        """Test that problem_description appears in the prompt."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Implement OAuth2 login flow",
            codebase_context="",
        )

        call_args = mock_workflow._call_llm.call_args
        prompt = call_args.kwargs["user_message"]
        assert "Implement OAuth2 login flow" in prompt

    @pytest.mark.asyncio
    async def test_decompose_uses_capable_tier(self):
        """Test that decompose calls LLM with ModelTier.CAPABLE."""
        from attune.workflows.compat import ModelTier

        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Test",
            codebase_context="",
        )

        call_args = mock_workflow._call_llm.call_args
        tier_arg = call_args.kwargs["tier"]
        assert tier_arg == ModelTier.CAPABLE

    @pytest.mark.asyncio
    async def test_decompose_uses_decompose_step_id(self):
        """Test that decompose calls LLM with 'decompose' as step_id."""
        mock_workflow = MagicMock()
        mock_workflow._call_llm = AsyncMock(return_value=("<tasks></tasks>", 0, 0))
        decomposer = TaskDecomposer(workflow=mock_workflow)

        await decomposer.decompose(
            problem_description="Test",
            codebase_context="",
        )

        call_args = mock_workflow._call_llm.call_args
        step_id_arg = call_args.kwargs["stage_name"]
        assert step_id_arg == "decompose"


class TestTaskDecomposerDropWarnings:
    """The regex parser drops what it cannot match; it must at least say so."""

    def setup_method(self):
        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def _parse(self, caplog, xml: str) -> tuple[list[DecomposedTask], list[str]]:
        """Drive the REGEX path directly: these tests pin the fallback's
        warnings, which the ElementTree path never needs for well-formed
        input (see TestTaskDecomposerElementTreePath)."""
        with caplog.at_level(logging.WARNING, logger="attune.wizards.decomposer"):
            tasks = self.decomposer._parse_tasks_with_regex(xml)
        return tasks, [record.getMessage() for record in caplog.records]

    def test_well_formed_tasks_emit_no_warnings(self, caplog):
        """Section wrappers must not be miscounted as their own children:
        <files-to-modify> is not a <file>, <risks> is not a <risk>,
        <dependencies> is not a <dep>."""
        xml = """
        <task id="1" name="ok">
          <objective>All tags parsed</objective>
          <files-to-create><file path="a.py">A</file></files-to-create>
          <files-to-modify><file path="b.py">B</file></files-to-modify>
          <validation><check>passes</check></validation>
          <risks><risk severity="low">none</risk></risks>
          <dependencies><dep>0</dep></dependencies>
        </task>
        """
        tasks, messages = self._parse(caplog, xml)
        assert len(tasks) == 1
        assert messages == []

    def test_warns_when_a_task_falls_outside_every_task_block(self, caplog):
        """A single-quoted attribute fails the task regex and the whole task
        vanishes; the caller could not tell a two-task plan from a broken
        three-task plan before this warning."""
        xml = """
        <tasks>
          <task id="1" name="kept"><objective>Parsed</objective></task>
          <task id='2' name='dropped'>
            <objective>Lost to single quotes</objective>
            <files-to-create><file path="src/lost.py">never seen</file></files-to-create>
          </task>
        </tasks>
        """
        tasks, messages = self._parse(caplog, xml)
        assert [task.task_id for task in tasks] == ["1"]
        [message] = [m for m in messages if "outside any <task> block" in m]
        assert "(<file>, <objective>)" in message
        assert "1 task(s) parsed" in message

    def test_warns_when_a_field_tag_yields_no_value(self, caplog):
        """<file> without path= and <risk> without severity= match nothing
        and used to disappear without a word."""
        xml = """
        <task id="1">
          <objective>Attribute-less children</objective>
          <files-to-create><file>src/no_path.py</file></files-to-create>
          <validation><check>still parsed</check></validation>
          <risks><risk>no severity</risk></risks>
        </task>
        """
        tasks, messages = self._parse(caplog, xml)
        [task] = tasks
        assert task.files_to_create == []
        assert task.risks == []
        assert task.validation_checks == ["still parsed"]
        assert any("Task 1: 1 <file tag(s) present but 0 parsed" in m for m in messages)
        assert any("Task 1: 1 <risk tag(s) present but 0 parsed" in m for m in messages)
        assert not any("<check" in m for m in messages)
        assert not any("outside any <task> block" in m for m in messages)

    def test_no_tasks_still_reports_orphaned_content(self, caplog):
        """A response whose ONLY task is malformed must not collapse into the
        generic 'No <task> elements' warning — that is the case the orphan
        diagnostic exists for. Plain prose with no task-shaped tags keeps the
        generic warning alone."""
        tasks, messages = self._parse(caplog, "<task id='1'><objective >x</objective></task>")
        assert tasks == []
        assert messages[0] == "No <task> elements found in decomposition response"
        assert "outside any <task> block (<objective>) - 0 task(s) parsed" in messages[1]
        # The same input through the public entry point parses: it is
        # well-formed XML, and quoting style is the regex path's problem only.
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="attune.wizards.decomposer"):
            [task] = self.decomposer._parse_tasks_from_xml(
                "<task id='1'><objective >x</objective></task>"
            )
        assert task.objective == "x"
        assert [r.getMessage() for r in caplog.records] == []

        caplog.clear()
        tasks, messages = self._parse(caplog, "Sorry, I could not decompose this request.")
        assert tasks == []
        assert messages == ["No <task> elements found in decomposition response"]

    def test_warns_when_a_missing_close_tag_swallows_the_next_task(self, caplog):
        """Without </task> on the first task the non-greedy regex runs through
        the second task's closing tag: one task parses, the other vanishes
        INSIDE its body, out of reach of both other warnings."""
        xml = """
        <task id="1"><objective>First, never closed</objective>
        <task id="2"><objective>Second</objective></task>
        """
        tasks, messages = self._parse(caplog, xml)
        assert [task.task_id for task in tasks] == ["1"]
        assert any("Task 1: body contains another <task> opening" in m for m in messages)
        # Through the public entry point the unclosed tag is not well-formed,
        # so the fallback runs and BOTH warnings reach the caller.
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="attune.wizards.decomposer"):
            self.decomposer._parse_tasks_from_xml(xml)
        messages = [r.getMessage() for r in caplog.records]
        assert any("not well-formed" in m and "falling back" in m for m in messages)
        assert any("Task 1: body contains another <task> opening" in m for m in messages)


class TestTaskDecomposerElementTreePath:
    """Well-formed XML goes through defusedxml; the regex parser's blind
    spots (quoting style, attribute order, whitespace) stop being drops."""

    def setup_method(self):
        self.decomposer = TaskDecomposer(workflow=MagicMock())

    def _parse(self, caplog, xml: str) -> tuple[list[DecomposedTask], list[str]]:
        with caplog.at_level(logging.WARNING, logger="attune.wizards.decomposer"):
            tasks = self.decomposer._parse_tasks_from_xml(xml)
        return tasks, [record.getMessage() for record in caplog.records]

    def test_single_quoted_and_reordered_attributes_parse(self, caplog):
        """Both shapes dropped the task under the regex parser."""
        xml = """
        <tasks>
          <task id='1' name='quoted'><objective>A</objective></task>
          <task name="reordered" id="2" ><objective>B</objective></task>
        </tasks>
        """
        tasks, messages = self._parse(caplog, xml)
        assert [(t.task_id, t.name, t.objective) for t in tasks] == [
            ("1", "quoted", "A"),
            ("2", "reordered", "B"),
        ]
        assert messages == []

    def test_full_task_matches_regex_parser_field_for_field(self, caplog):
        xml = """
        ```xml
        <task id="3" name="full">
          <objective>Add auth</objective>
          <files-to-create><file path="src/auth.py">Auth module</file></files-to-create>
          <files-to-modify><file path="src/app.py">Wire it</file></files-to-modify>
          <validation><check>401 when anonymous</check><check>200 when signed in</check></validation>
          <risks><risk severity="high">Session break</risk></risks>
          <dependencies><dep>1</dep><dep>2</dep></dependencies>
        </task>
        ```
        """
        tasks, messages = self._parse(caplog, xml)
        [task] = tasks
        assert messages == []
        assert task.to_dict() == self.decomposer._parse_tasks_with_regex(xml)[0].to_dict()

    def test_inline_markup_inside_text_is_kept(self, caplog):
        xml = '<task id="1"><objective>Use <code>x</code> here</objective></task>'
        tasks, _ = self._parse(caplog, xml)
        assert tasks[0].objective == "Use <code>x</code> here"

    def test_text_inside_child_tags_is_decoded_once_never_re_escaped(self, caplog):
        """The corpus case: ``->`` inside a <change> block came back as
        ``-&gt;`` when children were re-serialized. Escaped markup in child
        text reads as the text its author meant (lane finding on #2511 —
        the result is prose, not XML)."""
        xml = (
            '<task id="1"><files-to-modify><file path="a.py">'
            '<change location="f">def f(x) -> int: pass</change>'
            " then <code>&lt;div&gt;</code>"
            "</file></files-to-modify></task>"
        )
        tasks, _ = self._parse(caplog, xml)
        assert tasks[0].files_to_modify[0]["description"] == (
            '<change location="f">def f(x) -> int: pass</change> then <code><div></code>'
        )

    def test_nested_task_inside_a_description_is_not_a_phantom_task(self, caplog):
        """A well-formed example <task> inside a body is text, not a task
        (lane finding on #2511: iter('task') minted one)."""
        xml = (
            '<task id="1"><objective>Emit blocks like '
            '<task id="example"><objective>x</objective></task></objective></task>'
            '<task id="2"><objective>real</objective></task>'
        )
        tasks, messages = self._parse(caplog, xml)
        assert [t.task_id for t in tasks] == ["1", "2"]
        assert tasks[0].objective.startswith('Emit blocks like <task id="example">')
        assert any("Task 1: 1 nested <task> element(s) kept as body text" in m for m in messages)

    def test_entities_decode_on_the_parser_path(self, caplog):
        """The one deliberate divergence: ``&amp;`` reaches the caller as ``&``."""
        xml = '<task id="1"><objective>A &amp; B</objective></task>'
        tasks, _ = self._parse(caplog, xml)
        assert tasks[0].objective == "A & B"
        assert self.decomposer._parse_tasks_with_regex(xml)[0].objective == "A &amp; B"

    def test_attribute_less_children_still_warn(self, caplog):
        xml = """
        <task id="1">
          <objective>x</objective>
          <files-to-create><file>src/no_path.py</file></files-to-create>
          <risks><risk>no severity</risk></risks>
        </task>
        """
        tasks, messages = self._parse(caplog, xml)
        assert tasks[0].files_to_create == [] and tasks[0].risks == []
        assert any("Task 1: 1 <file tag(s) present but 0 parsed" in m for m in messages)
        assert any("Task 1: 1 <risk tag(s) present but 0 parsed" in m for m in messages)

    def test_task_without_id_is_skipped_with_a_warning(self, caplog):
        xml = '<task name="anon"><objective>x</objective></task><task id="2"></task>'
        tasks, messages = self._parse(caplog, xml)
        assert [t.task_id for t in tasks] == ["2"]
        assert any("no id attribute" in m for m in messages)

    def test_bare_ampersand_in_prose_falls_back_to_regex(self, caplog):
        xml = """
        <task id="1"><objective>A</objective></task>
        Notes & caveats between the blocks.
        <task id="2"><objective>B</objective></task>
        """
        tasks, messages = self._parse(caplog, xml)
        assert [t.task_id for t in tasks] == ["1", "2"]
        assert any("not well-formed" in m for m in messages)

    def test_entity_declarations_are_refused_and_fall_back(self, caplog):
        xml = (
            '<!DOCTYPE r [<!ENTITY lol "lol">]>' '<task id="1"><objective>&lol;</objective></task>'
        )
        tasks, messages = self._parse(caplog, xml)
        assert [t.task_id for t in tasks] == ["1"]
        assert any("not well-formed" in m for m in messages)

    def test_no_task_block_keeps_the_generic_warning(self, caplog):
        tasks, messages = self._parse(caplog, "no xml at all")
        assert tasks == []
        assert messages == ["No <task> elements found in decomposition response"]
