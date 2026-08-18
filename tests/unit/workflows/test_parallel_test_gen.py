"""Tests for ParallelTestGenerationWorkflow.

Covers initialization, coverage discovery, module analysis,
code extraction, and end-to-end execute().

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.test_gen_parallel import (
    TestGenerationTask,
)


@pytest.mark.unit
class TestParallelTestGenInit:
    """Verify class attributes and initialization."""

    def test_class_attributes(self, parallel_test_gen_workflow):
        wf = parallel_test_gen_workflow
        assert wf.name == "parallel-test-generation"
        assert wf.stages == [
            "discover",
            "generate_templates",
            "complete_tests",
            "validate",
        ]
        assert wf.tier_map == {
            "discover": ModelTier.CHEAP,
            "generate_templates": ModelTier.CHEAP,
            "complete_tests": ModelTier.CAPABLE,
            "validate": ModelTier.CHEAP,
        }

    @pytest.mark.asyncio
    async def test_run_stage_raises(self, parallel_test_gen_workflow):
        """run_stage is not used — execute() overrides the pipeline."""
        with pytest.raises(ValueError, match="Unknown stage"):
            await parallel_test_gen_workflow.run_stage("discover", ModelTier.CHEAP, {})


@pytest.mark.unit
class TestDiscoverLowCoverageModules:
    """Tests for discover_low_coverage_modules()."""

    def test_returns_sorted_modules(self, parallel_test_gen_workflow):
        """Modules should be sorted by coverage ascending."""
        coverage_json = {
            "files": {
                "src/a.py": {"summary": {"percent_covered": 80.0, "num_statements": 50}},
                "src/b.py": {"summary": {"percent_covered": 20.0, "num_statements": 100}},
                "src/c.py": {"summary": {"percent_covered": 50.0, "num_statements": 40}},
            }
        }

        mock_run = MagicMock()
        mock_run.returncode = 0

        with (
            patch("subprocess.run", return_value=mock_run),
            patch(
                "builtins.open",
                MagicMock(
                    return_value=MagicMock(
                        __enter__=lambda s: s,
                        __exit__=MagicMock(return_value=False),
                        read=lambda: json.dumps(coverage_json),
                    )
                ),
            ),
            patch("json.load", return_value=coverage_json),
        ):
            result = parallel_test_gen_workflow.discover_low_coverage_modules(top_n=10)

        # b.py (20%) should come before c.py (50%) before a.py (80%)
        assert len(result) == 3  # c.py included (40 > 30 statements)
        assert result[0][0] == "src/b.py"
        assert result[1][0] == "src/c.py"
        assert result[2][0] == "src/a.py"

    def test_skips_small_files(self, parallel_test_gen_workflow):
        """Files with <=30 statements should be skipped."""
        coverage_json = {
            "files": {
                "src/tiny.py": {"summary": {"percent_covered": 10.0, "num_statements": 5}},
            }
        }

        with (
            patch("subprocess.run"),
            patch("json.load", return_value=coverage_json),
            patch("builtins.open", MagicMock()),
        ):
            result = parallel_test_gen_workflow.discover_low_coverage_modules()

        assert result == []

    def test_returns_empty_on_error(self, parallel_test_gen_workflow):
        """Should return empty list when coverage data unavailable."""
        with patch("subprocess.run", side_effect=FileNotFoundError("coverage not found")):
            result = parallel_test_gen_workflow.discover_low_coverage_modules()

        assert result == []

    def test_skips_non_src_files(self, parallel_test_gen_workflow):
        """Files not under src/ should be excluded."""
        coverage_json = {
            "files": {
                "tests/test_foo.py": {"summary": {"percent_covered": 10.0, "num_statements": 100}},
                "src/bar.py": {"summary": {"percent_covered": 50.0, "num_statements": 100}},
            }
        }

        with (
            patch("subprocess.run"),
            patch("json.load", return_value=coverage_json),
            patch("builtins.open", MagicMock()),
        ):
            result = parallel_test_gen_workflow.discover_low_coverage_modules()

        assert len(result) == 1
        assert result[0][0] == "src/bar.py"


@pytest.mark.unit
class TestAnalyzeModuleStructure:
    """Tests for analyze_module_structure()."""

    def test_extracts_classes_and_functions(self, parallel_test_gen_workflow, tmp_path):
        source = (
            "class Foo:\n" "    def bar(self):\n" "        pass\n" "\n" "def baz():\n" "    pass\n"
        )
        src_file = tmp_path / "module.py"
        src_file.write_text(source)

        result = parallel_test_gen_workflow.analyze_module_structure(str(src_file))

        assert result["file"] == str(src_file)
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Foo"
        assert "bar" in result["classes"][0]["methods"]
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "baz"

    def test_returns_error_on_invalid_file(self, parallel_test_gen_workflow):
        result = parallel_test_gen_workflow.analyze_module_structure("/nonexistent/path.py")

        assert "error" in result

    def test_handles_async_functions(self, parallel_test_gen_workflow, tmp_path):
        source = "class Service:\n" "    async def fetch(self):\n" "        pass\n"
        src_file = tmp_path / "async_mod.py"
        src_file.write_text(source)

        result = parallel_test_gen_workflow.analyze_module_structure(str(src_file))

        assert result["classes"][0]["methods"] == ["fetch"]


@pytest.mark.unit
class TestExtractCode:
    """Tests for _extract_code()."""

    def test_extracts_from_markdown(self, parallel_test_gen_workflow):
        content = (
            "Here is the code:\n" "```python\n" "def test_foo():\n" "    assert True\n" "```\n"
        )
        result = parallel_test_gen_workflow._extract_code(content)
        assert result == "def test_foo():\n    assert True"

    def test_returns_raw_content_without_fences(self, parallel_test_gen_workflow):
        content = "def test_foo():\n    assert True\n"
        result = parallel_test_gen_workflow._extract_code(content)
        assert result == content


@pytest.mark.unit
class TestGenerateTestTemplateWithAI:
    """Tests for generate_test_template_with_ai()."""

    @pytest.mark.asyncio
    async def test_returns_llm_content(self, parallel_test_gen_workflow):
        """Should call _call_llm and return the content string."""
        with patch.object(
            parallel_test_gen_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("def test_example(): pass", 100, 50),
        ) as mock_llm:
            result = await parallel_test_gen_workflow.generate_test_template_with_ai(
                "src/foo.py",
                {"file": "src/foo.py", "classes": [], "functions": [{"name": "foo", "line": 1}]},
            )

        mock_llm.assert_called_once()
        assert "test_example" in result

    @pytest.mark.asyncio
    async def test_returns_empty_on_empty_response(self, parallel_test_gen_workflow):
        """Should return empty string when LLM returns empty content."""
        with patch.object(
            parallel_test_gen_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("", 10, 0),
        ):
            result = await parallel_test_gen_workflow.generate_test_template_with_ai(
                "src/foo.py",
                {"file": "src/foo.py", "classes": [], "functions": []},
            )

        assert result == ""


@pytest.mark.unit
class TestCompleteTestWithAI:
    """Tests for complete_test_with_ai()."""

    @pytest.mark.asyncio
    async def test_reads_source_and_calls_llm(self, parallel_test_gen_workflow, tmp_path):
        """Should read the source file and call _call_llm with template."""
        src_file = tmp_path / "module.py"
        src_file.write_text("def add(a, b): return a + b\n")

        with patch.object(
            parallel_test_gen_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("def test_add(): assert add(1, 2) == 3", 200, 100),
        ) as mock_llm:
            result = await parallel_test_gen_workflow.complete_test_with_ai(
                "def test_add(): # TODO",
                str(src_file),
            )

        mock_llm.assert_called_once()
        assert "test_add" in result

    @pytest.mark.asyncio
    async def test_small_module_keeps_body_in_prompt(self, parallel_test_gen_workflow, tmp_path):
        """Under the token budget the full source passes through."""
        src_file = tmp_path / "module.py"
        src_file.write_text("def add(a, b):\n    return a + b\n")

        with patch.object(
            parallel_test_gen_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("ok", 1, 1),
        ) as mock_llm:
            await parallel_test_gen_workflow.complete_test_with_ai("tpl", str(src_file))

        prompt = mock_llm.call_args.kwargs["user_message"]
        assert "return a + b" in prompt

    @pytest.mark.asyncio
    async def test_oversized_module_degrades_to_skeleton_keeping_tail(
        self, parallel_test_gen_workflow, tmp_path
    ):
        """Over budget the prompt carries the AST skeleton: the last
        function's signature survives (the old [:5000] slice chopped
        it) and function bodies are stripped."""
        src_file = tmp_path / "module.py"
        src_file.write_text(_oversized_module())

        with patch.object(
            parallel_test_gen_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("ok", 1, 1),
        ) as mock_llm:
            await parallel_test_gen_workflow.complete_test_with_ai("tpl", str(src_file))

        prompt = mock_llm.call_args.kwargs["user_message"]
        assert "def zz_tail_function(name: str) -> str:" in prompt
        assert "1000001" not in prompt  # body sentinel stripped


def _oversized_module(n_funcs: int = 40) -> str:
    """Python source well over every prompt budget whose skeleton fits:
    bulky bodies (sentinel constant 1000001), compact signatures."""
    body = "\n".join(f"    v{j} = {j} * 1000001" for j in range(6))
    funcs = [f"def func_{i:03d}(x: int) -> int:\n{body}\n    return x\n" for i in range(n_funcs)]
    funcs.append(f"def zz_tail_function(name: str) -> str:\n{body}\n    return name\n")
    return "\n".join(funcs)


@pytest.mark.unit
class TestProcessModuleBatch:
    """Tests for process_module_batch()."""

    @pytest.mark.asyncio
    async def test_writes_completed_tests(self, parallel_test_gen_workflow, tmp_path):
        """Should write generated tests to output_dir and mark tasks completed."""
        src_file = tmp_path / "src" / "foo.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("def foo(): pass\n")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        modules = [(str(src_file), 30.0)]

        with (
            patch.object(
                parallel_test_gen_workflow,
                "generate_test_template_with_ai",
                new_callable=AsyncMock,
                return_value="def test_foo(): # TODO",
            ),
            patch.object(
                parallel_test_gen_workflow,
                "complete_test_with_ai",
                new_callable=AsyncMock,
                return_value="def test_foo(): assert True",
            ),
        ):
            tasks = await parallel_test_gen_workflow.process_module_batch(
                modules, out_dir, batch_size=10
            )

        assert len(tasks) == 1
        assert tasks[0].status == "completed"
        output_file = out_dir / "test_foo_behavioral.py"
        assert output_file.exists()
        assert "test_foo" in output_file.read_text()

    @pytest.mark.asyncio
    async def test_marks_error_on_template_failure(self, parallel_test_gen_workflow, tmp_path):
        """Tasks should be marked error when template generation fails."""
        src_file = tmp_path / "src" / "bar.py"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("def bar(): pass\n")

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        modules = [(str(src_file), 20.0)]

        with patch.object(
            parallel_test_gen_workflow,
            "generate_test_template_with_ai",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ):
            tasks = await parallel_test_gen_workflow.process_module_batch(
                modules, out_dir, batch_size=10
            )

        assert len(tasks) == 1
        assert tasks[0].status == "error"


@pytest.mark.unit
class TestDefaultContext:
    """Tests for the default_context() classmethod."""

    def test_returns_workflow_context(self):
        """default_context() should return a WorkflowContext."""
        from attune.workflows.context import WorkflowContext
        from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow

        ctx = ParallelTestGenerationWorkflow.default_context()

        assert isinstance(ctx, WorkflowContext)

    def test_accepts_xml_config(self):
        """default_context() should accept optional xml_config."""
        from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow

        ctx = ParallelTestGenerationWorkflow.default_context(xml_config={"key": "value"})

        assert ctx is not None


@pytest.mark.unit
class TestExecute:
    """Tests for the end-to-end execute() method."""

    @pytest.mark.asyncio
    async def test_execute_no_coverage_returns_failure(self, parallel_test_gen_workflow, tmp_path):
        """execute() returns a failed WorkflowResult when no coverage data found."""
        with patch.object(
            parallel_test_gen_workflow,
            "discover_low_coverage_modules",
            return_value=[],
        ):
            result = await parallel_test_gen_workflow.execute(output_dir=str(tmp_path / "out"))

        assert result.success is False
        assert len(result.stages) == 1
        assert result.stages[0].name == "discover"
        assert "error" in result.final_output

    @pytest.mark.asyncio
    async def test_execute_discovers_modules_before_processing(
        self, parallel_test_gen_workflow, tmp_path
    ):
        """Verify discover is called, modules processed, and result is valid."""
        modules = [("src/foo.py", 30.0)]
        out_dir = tmp_path / "out"

        mock_task = TestGenerationTask(
            module_path="src/foo.py",
            coverage=30.0,
            output_path=str(out_dir / "test_foo_behavioral.py"),
            status="completed",
        )

        with (
            patch.object(
                parallel_test_gen_workflow,
                "discover_low_coverage_modules",
                return_value=modules,
            ) as mock_discover,
            patch.object(
                parallel_test_gen_workflow,
                "process_module_batch",
                new_callable=AsyncMock,
                return_value=[mock_task],
            ) as mock_batch,
        ):
            result = await parallel_test_gen_workflow.execute(output_dir=str(out_dir))

        mock_discover.assert_called_once()
        mock_batch.assert_called_once()
        assert result.success is True
        assert len(result.stages) == 3
        assert result.final_output["completed"] == 1


@pytest.mark.unit
class TestTestGenerationTask:
    """Tests for the TestGenerationTask dataclass."""

    def test_default_status(self):
        task = TestGenerationTask(
            module_path="src/foo.py",
            coverage=50.0,
            output_path="tests/test_foo.py",
        )
        assert task.status == "pending"
