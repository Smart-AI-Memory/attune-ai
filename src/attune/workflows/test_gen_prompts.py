"""Autonomous Test Generation Prompt Engineering.

Prompt templates, few-shot examples, and workflow detection for test generation.
Extracted from autonomous_test_gen.py for maintainability.

Contains:
- TestGenPromptMixin: Workflow detection and prompt engineering methods

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re


class TestGenPromptMixin:
    """Mixin providing prompt engineering for autonomous test generation."""

    def _is_workflow_module(self, source_code: str, module_path: str) -> bool:
        """Detect if module is a workflow requiring special handling.

        Args:
            source_code: Source code content
            module_path: Python import path

        Returns:
            True if this is a workflow module needing LLM mocking

        """
        # Check for workflow indicators
        indicators = [
            r"class\s+\w+Workflow",
            r"async\s+def\s+execute",
            r"tier_routing",
            r"LLMProvider",
            r"TelemetryCollector",
            r"from\s+anthropic\s+import",
            r"messages\.create",
            r"client\.messages",
        ]

        return any(re.search(pattern, source_code) for pattern in indicators)

    def _get_example_tests(self) -> str:
        """Get few-shot examples of excellent tests for prompt learning."""
        return """EXAMPLE 1: Testing a utility function with mocking
```python
import pytest
from unittest.mock import Mock, patch
from mymodule import process_data

class TestProcessData:
    def test_processes_valid_data_successfully(self):
        \"\"\"Given valid input data, when processing, then returns expected result.\"\"\"
        # Given
        input_data = {"key": "value", "count": 42}

        # When
        result = process_data(input_data)

        # Then
        assert result is not None
        assert result["status"] == "success"
        assert result["processed"] is True

    def test_handles_invalid_data_with_error(self):
        \"\"\"Given invalid input, when processing, then raises ValueError.\"\"\"
        # Given
        invalid_data = {"missing": "key"}

        # When/Then
        with pytest.raises(ValueError, match="Required key 'key' not found"):
            process_data(invalid_data)
```

EXAMPLE 2: Testing a workflow with LLM mocking
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from mymodule import MyWorkflow

@pytest.fixture
def mock_llm_client(mocker):
    \"\"\"Mock Anthropic LLM client.\"\"\"
    mock = mocker.patch('anthropic.Anthropic')
    mock_response = Mock()
    mock_response.content = [Mock(text="mock LLM response")]
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)
    mock_response.stop_reason = "end_turn"
    mock.return_value.messages.create = AsyncMock(return_value=mock_response)
    return mock

class TestMyWorkflow:
    @pytest.mark.asyncio
    async def test_executes_successfully_with_mocked_llm(self, mock_llm_client):
        \"\"\"Given valid input, when executing workflow, then completes successfully.\"\"\"
        # Given
        workflow = MyWorkflow()
        input_data = {"prompt": "test prompt"}

        # When
        result = await workflow.execute(input_data)

        # Then
        assert result is not None
        assert "response" in result
        mock_llm_client.return_value.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, mock_llm_client):
        \"\"\"Given API failure, when executing, then handles error appropriately.\"\"\"
        # Given
        workflow = MyWorkflow()
        mock_llm_client.return_value.messages.create.side_effect = Exception("API Error")

        # When/Then
        with pytest.raises(Exception, match="API Error"):
            await workflow.execute({"prompt": "test"})
```
"""

    def _get_workflow_specific_prompt(
        self,
        module_name: str,
        module_path: str,
        source_code: str,
    ) -> str:
        """Get workflow-specific test generation prompt with comprehensive mocking guidance."""
        return f"""Generate comprehensive tests for this WORKFLOW module.

⚠️ CRITICAL: This module makes LLM API calls and requires proper mocking.

MODULE: {module_name}
IMPORT PATH: {module_path}

SOURCE CODE (COMPLETE - NO TRUNCATION):
```python
{source_code}
```

WORKFLOW TESTING REQUIREMENTS:

1. **Mock LLM API calls** - NEVER make real API calls in tests
   ```python
   @pytest.fixture
   def mock_llm_client(mocker):
       mock = mocker.patch('anthropic.Anthropic')
       mock_response = Mock()
       mock_response.content = [Mock(text="mock response")]
       mock_response.usage = Mock(input_tokens=100, output_tokens=50)
       mock_response.stop_reason = "end_turn"
       mock.return_value.messages.create = AsyncMock(return_value=mock_response)
       return mock
   ```

2. **Test tier routing** - Verify correct model selection (cheap/capable/premium)
3. **Test telemetry** - Mock and verify telemetry recording
4. **Test cost calculation** - Verify token usage and cost tracking
5. **Test error handling** - Mock API failures, timeouts, rate limits
6. **Test caching** - Mock cache hits/misses if applicable

TARGET COVERAGE: 40-50% (realistic for workflow classes with proper mocking)

Generate a complete test file with:
- Copyright header: "Generated by enhanced autonomous test generation system."
- Proper imports (from {module_path})
- Mock fixtures for ALL external dependencies (LLM, databases, APIs, file I/O)
- Given/When/Then structure in docstrings
- Both success and failure test cases
- Edge case handling
- Docstrings for all tests describing behavior

Return ONLY the complete Python test file, no explanations."""
