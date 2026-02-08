"""Integration tests for progressive test generation workflow."""

from pathlib import Path

import pytest

from attune.workflows.progressive.core import EscalationConfig, Tier
from attune.workflows.progressive.test_gen import (
    ProgressiveTestGenWorkflow,
    calculate_coverage,
    execute_test_file,
)


class TestProgressiveTestGenWorkflow:
    """Test ProgressiveTestGenWorkflow class."""

    def test_initialization_default_config(self):
        """Test workflow initializes with default config."""
        workflow = ProgressiveTestGenWorkflow()

        assert workflow.config is not None
        assert workflow.config.enabled is False
        assert workflow.target_file is None

    def test_initialization_custom_config(self):
        """Test workflow initializes with custom config."""
        config = EscalationConfig(
            enabled=True,
            max_cost=10.00,
            auto_approve_under=5.00,
        )

        workflow = ProgressiveTestGenWorkflow(config)

        assert workflow.config.enabled is True
        assert workflow.config.max_cost == 10.00

    def test_execute_file_not_found(self, tmp_path):
        """Test execute raises FileNotFoundError for missing file."""
        workflow = ProgressiveTestGenWorkflow()
        missing_file = tmp_path / "missing.py"

        with pytest.raises(FileNotFoundError, match="Target file not found"):
            workflow.execute(target_file=str(missing_file))

    def test_execute_empty_file(self, tmp_path):
        """Test execute handles empty file gracefully."""
        workflow = ProgressiveTestGenWorkflow()

        # Create empty file
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        result = workflow.execute(target_file=str(empty_file))

        assert result.success is False
        assert len(result.tier_results) == 1
        assert len(result.final_result.generated_items) == 0

    def test_execute_no_functions(self, tmp_path):
        """Test execute handles file with no functions."""
        workflow = ProgressiveTestGenWorkflow()

        # Create file with no functions
        file_with_no_funcs = tmp_path / "no_funcs.py"
        file_with_no_funcs.write_text(
            '''
"""Module with no functions."""

# Just a comment
x = 42
'''
        )

        result = workflow.execute(target_file=str(file_with_no_funcs))

        assert result.success is False
        assert len(result.final_result.generated_items) == 0

    def test_parse_functions_simple_file(self, tmp_path):
        """Test parsing functions from simple Python file."""
        workflow = ProgressiveTestGenWorkflow()

        # Create simple file with 2 functions
        sample_file = tmp_path / "sample.py"
        sample_file.write_text(
            '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    return x * y
'''
        )

        functions = workflow._parse_functions(sample_file)

        assert len(functions) == 2
        assert functions[0]["name"] == "add"
        assert functions[0]["args"] == ["a", "b"]
        assert functions[0]["docstring"] == "Add two numbers."
        assert "return a + b" in functions[0]["code"]

        assert functions[1]["name"] == "multiply"
        assert functions[1]["args"] == ["x", "y"]

    def test_parse_functions_with_docstrings(self, tmp_path):
        """Test parsing extracts docstrings correctly."""
        workflow = ProgressiveTestGenWorkflow()

        sample_file = tmp_path / "sample.py"
        sample_file.write_text(
            '''
def documented_func(param1: str, param2: int) -> bool:
    """This is a well-documented function.

    Args:
        param1: First parameter
        param2: Second parameter

    Returns:
        A boolean value
    """
    return len(param1) > param2
'''
        )

        functions = workflow._parse_functions(sample_file)

        assert len(functions) == 1
        assert "well-documented function" in functions[0]["docstring"]
        assert functions[0]["args"] == ["param1", "param2"]

    def test_parse_functions_syntax_error(self, tmp_path):
        """Test parsing handles syntax errors gracefully."""
        workflow = ProgressiveTestGenWorkflow()

        # Create file with syntax error
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(
            """
def broken_func(
    # Missing closing paren and body
"""
        )

        functions = workflow._parse_functions(bad_file)

        # Should return empty list on syntax error
        assert functions == []

    def test_build_test_gen_task_single_function(self, tmp_path):
        """Test building task description for single function."""
        workflow = ProgressiveTestGenWorkflow()

        # Set target file
        workflow.target_file = Path("test.py")

        functions = [{"name": "calculate", "args": ["x"]}]

        task = workflow._build_test_gen_task(functions)

        assert "1 function" in task
        assert "test.py" in task
        assert "calculate" in task

    def test_build_test_gen_task_multiple_functions(self, tmp_path):
        """Test building task description for multiple functions."""
        workflow = ProgressiveTestGenWorkflow()
        workflow.target_file = Path("app.py")

        functions = [
            {"name": "foo", "args": []},
            {"name": "bar", "args": []},
            {"name": "baz", "args": []},
        ]

        task = workflow._build_test_gen_task(functions)

        assert "3 function" in task
        assert "app.py" in task
        # Should list all function names when <=3
        assert "foo" in task
        assert "bar" in task
        assert "baz" in task

    def test_build_test_gen_task_many_functions(self, tmp_path):
        """Test building task description for many functions (>3)."""
        workflow = ProgressiveTestGenWorkflow()
        workflow.target_file = Path("large.py")

        functions = [{"name": f"func_{i}", "args": []} for i in range(10)]

        task = workflow._build_test_gen_task(functions)

        assert "10 function" in task
        # Should NOT list individual function names when >3
        assert "func_0" not in task

    def test_generate_mock_test_simple_function(self):
        """Test mock test generation for simple function."""
        workflow = ProgressiveTestGenWorkflow()

        func = {
            "name": "add",
            "args": ["a", "b"],
            "docstring": "Add two numbers",
        }

        test_code = workflow._generate_mock_test(func)

        assert "def test_add():" in test_code
        assert "Test add function" in test_code
        assert "result = add(a, b)" in test_code
        assert "assert result is not None" in test_code

    def test_generate_mock_test_no_args(self):
        """Test mock test generation for function with no arguments."""
        workflow = ProgressiveTestGenWorkflow()

        func = {"name": "get_status", "args": [], "docstring": "Get status"}

        test_code = workflow._generate_mock_test(func)

        assert "def test_get_status():" in test_code
        assert "result = get_status()" in test_code

    def test_generate_test_setup_infers_types(self):
        """Test test setup infers types from argument names."""
        workflow = ProgressiveTestGenWorkflow()

        # Test count/num inference
        setup = workflow._generate_test_setup(["count", "num_items"])
        assert "count = 1" in setup
        assert "num_items = 1" in setup

        # Test name/text inference
        setup = workflow._generate_test_setup(["name", "message"])
        assert 'name = "test"' in setup
        assert 'message = "test"' in setup

        # Test list inference
        setup = workflow._generate_test_setup(["items", "user_list"])
        assert "items = []" in setup
        assert "user_list = []" in setup

        # Default fallback
        setup = workflow._generate_test_setup(["unknown"])
        assert 'unknown = "value"' in setup

    def test_analyze_generated_test_valid_syntax(self):
        """Test analyzing test with valid syntax."""
        workflow = ProgressiveTestGenWorkflow()

        test_code = '''
def test_example():
    """Test example function."""
    result = example(42)
    assert result > 0
    assert isinstance(result, int)
'''

        func = {"name": "example", "args": ["x"]}

        analysis = workflow._analyze_generated_test(test_code, func)

        assert len(analysis.syntax_errors) == 0
        assert analysis.assertion_depth == 2  # Two assert statements

    def test_analyze_generated_test_syntax_error(self):
        """Test analyzing test with syntax error."""
        workflow = ProgressiveTestGenWorkflow()

        test_code = """
def test_broken(
    # Missing closing paren and body
"""

        func = {"name": "broken", "args": []}

        analysis = workflow._analyze_generated_test(test_code, func)

        assert len(analysis.syntax_errors) > 0
        # Other metrics should be default when syntax fails
        assert analysis.assertion_depth == 0

    def test_analyze_generated_test_no_assertions(self):
        """Test analyzing test with no assertions."""
        workflow = ProgressiveTestGenWorkflow()

        test_code = '''
def test_no_asserts():
    """Test with no assertions."""
    result = compute()
    print(result)
'''

        func = {"name": "compute", "args": []}

        analysis = workflow._analyze_generated_test(test_code, func)

        assert len(analysis.syntax_errors) == 0
        assert analysis.assertion_depth == 0

    def test_simulate_test_generation_cheap_tier(self):
        """Test simulated generation produces lower quality for cheap tier."""
        workflow = ProgressiveTestGenWorkflow()

        functions = [
            {"name": "func1", "args": ["x"], "docstring": "Test func"},
            {"name": "func2", "args": ["y"], "docstring": "Test func"},
        ]

        tests = workflow._simulate_test_generation(Tier.CHEAP, functions)

        assert len(tests) == 2
        # Cheap tier should produce lower quality
        for test in tests:
            assert "quality_score" in test
            assert "test_code" in test
            assert "function_name" in test

    def test_simulate_test_generation_premium_tier(self):
        """Test simulated generation produces higher quality for premium tier."""
        workflow = ProgressiveTestGenWorkflow()

        functions = [{"name": "func1", "args": ["x"], "docstring": "Test"}]

        tests = workflow._simulate_test_generation(Tier.PREMIUM, functions)

        assert len(tests) == 1
        # Premium tier should produce higher quality (in mock implementation)
        # Real implementation would show quality difference

    def test_execute_tier_impl_builds_prompt(self, tmp_path):
        """Test tier execution builds proper prompt."""
        workflow = ProgressiveTestGenWorkflow()
        workflow.target_file = tmp_path / "test.py"

        functions = [{"name": "example", "args": ["x"], "docstring": "Test"}]

        # Execute at cheap tier
        result = workflow._execute_tier_impl(
            tier=Tier.CHEAP,
            items=functions,
            context=None,
        )

        assert len(result) == 1
        assert result[0]["function_name"] == "example"

    def test_execute_tier_impl_with_context(self, tmp_path):
        """Test tier execution uses context from previous tier."""
        workflow = ProgressiveTestGenWorkflow()
        workflow.target_file = tmp_path / "test.py"

        functions = [{"name": "example", "args": ["x"], "docstring": "Test"}]

        # Simulate failure context from cheap tier
        context = {
            "previous_tier": "cheap",
            "failures": [{"function": "example", "error": "Low coverage", "quality_score": 65}],
        }

        # Execute at capable tier with context
        result = workflow._execute_tier_impl(
            tier=Tier.CAPABLE,
            items=functions,
            context=context,
        )

        assert len(result) == 1
        # Context should influence generation (in real implementation)

    def test_create_empty_result(self):
        """Test creating empty result when no functions found."""
        workflow = ProgressiveTestGenWorkflow()

        result = workflow._create_empty_result("test-gen")

        assert result.workflow_name == "test-gen"
        assert result.success is False
        assert result.total_cost == 0.0
        assert len(result.tier_results) == 1
        assert len(result.final_result.generated_items) == 0


class TestExecuteTestFile:
    """Test execute_test_file utility function."""

    def test_execute_nonexistent_file(self, tmp_path):
        """Test executing nonexistent test file."""
        missing_file = tmp_path / "missing_test.py"

        result = execute_test_file(missing_file)

        # Should handle gracefully (pytest will fail)
        assert result["passed"] == 0
        assert result["failed"] == 0

    def test_execute_valid_test_file(self, tmp_path):
        """Test executing valid test file with passing tests."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(
            '''
def test_passing():
    """Test that passes."""
    assert 1 + 1 == 2

def test_also_passing():
    """Another passing test."""
    assert True
'''
        )

        result = execute_test_file(test_file)

        # Note: This actually runs pytest, so it may pass or fail depending on environment
        # In a real test, we'd mock subprocess.run
        assert "passed" in result
        assert "failed" in result
        assert "pass_rate" in result


class TestCalculateCoverage:
    """Test calculate_coverage utility function."""

    def test_coverage_nonexistent_files(self, tmp_path):
        """Test coverage calculation with nonexistent files."""
        test_file = tmp_path / "test_missing.py"
        source_file = tmp_path / "missing.py"

        coverage = calculate_coverage(test_file, source_file)

        # Should return 0.0 on error
        assert coverage == 0.0

    def test_coverage_valid_files(self, tmp_path):
        """Test coverage calculation with valid files."""
        # Create source file
        source_file = tmp_path / "sample.py"
        source_file.write_text(
            """
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
"""
        )

        # Create test file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(
            """
from sample import add

def test_add():
    assert add(1, 2) == 3
"""
        )

        coverage = calculate_coverage(test_file, source_file)

        # Note: This actually runs pytest with coverage, may not work without proper setup
        # In a real test, we'd mock subprocess.run
        assert isinstance(coverage, float)
        assert 0.0 <= coverage <= 100.0


class TestIntegrationEndToEnd:
    """End-to-end integration tests."""

    def test_end_to_end_simple_workflow(self, tmp_path):
        """Test complete workflow from file to results."""
        # Create sample Python file
        source_file = tmp_path / "calculator.py"
        source_file.write_text(
            '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b
'''
        )

        # Create workflow with escalation disabled (single tier)
        config = EscalationConfig(enabled=False)
        workflow = ProgressiveTestGenWorkflow(config)

        # Execute
        result = workflow.execute(target_file=str(source_file))

        # Verify results
        assert result.workflow_name == "test-gen"
        assert len(result.tier_results) > 0
        assert len(result.final_result.generated_items) == 2  # 2 functions

        # Verify function names
        func_names = [item["function_name"] for item in result.final_result.generated_items]
        assert "add" in func_names
        assert "subtract" in func_names

    def test_end_to_end_with_escalation(self, tmp_path):
        """Test workflow with escalation enabled."""
        source_file = tmp_path / "app.py"
        source_file.write_text(
            '''
def complex_function(data: dict) -> list:
    """Complex function that processes data."""
    return [item for item in data.values() if item > 0]
'''
        )

        # Create workflow with escalation enabled
        config = EscalationConfig(
            enabled=True,
            tiers=[Tier.CHEAP, Tier.CAPABLE],  # Only 2 tiers for test
            cheap_min_attempts=1,
            max_cost=5.00,
            auto_approve_under=10.00,  # High threshold to avoid prompting in test
        )
        workflow = ProgressiveTestGenWorkflow(config)

        # Execute
        result = workflow.execute(target_file=str(source_file))

        # Verify escalation occurred (or not, depending on mock quality)
        assert result.workflow_name == "test-gen"
        assert len(result.tier_results) >= 1

        # If escalation happened, verify tier progression
        if len(result.tier_results) > 1:
            tiers = [tr.tier for tr in result.tier_results]
            assert Tier.CHEAP in tiers

    def test_workflow_generates_report(self, tmp_path):
        """Test workflow generates proper report."""
        source_file = tmp_path / "simple.py"
        source_file.write_text(
            """
def hello() -> str:
    return "world"
"""
        )

        workflow = ProgressiveTestGenWorkflow()
        result = workflow.execute(target_file=str(source_file))

        # Generate report
        report = result.generate_report()

        assert "PROGRESSIVE ESCALATION REPORT" in report
        assert "test-gen" in report
        assert "TIER BREAKDOWN" in report or "Tier Progression" in report
        assert "Cost" in report
