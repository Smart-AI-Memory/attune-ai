"""Comprehensive coverage tests for LLM Executor Protocol.

Tests LLMResponse, ExecutionContext, and MockLLMExecutor.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

import attune.models.executor as executor_module

LLMResponse = executor_module.LLMResponse
ExecutionContext = executor_module.ExecutionContext
MockLLMExecutor = executor_module.MockLLMExecutor


@pytest.mark.unit
class TestLLMResponse:
    """Test LLMResponse dataclass and properties."""

    def test_llm_response_basic_creation(self):
        """Test creating LLMResponse with required fields."""
        response = LLMResponse(
            content="Test response",
            model_id="claude-sonnet-4-5-20250929",
            provider="anthropic",
            tier="capable",
        )

        assert response.content == "Test response"
        assert response.model_id == "claude-sonnet-4-5-20250929"
        assert response.provider == "anthropic"
        assert response.tier == "capable"

    def test_llm_response_with_all_fields(self):
        """Test creating LLMResponse with all fields populated."""
        response = LLMResponse(
            content="Complete response",
            model_id="claude-haiku-4-5-20251001",
            provider="anthropic",
            tier="cheap",
            tokens_input=1000,
            tokens_output=500,
            cost_estimate=0.0015,
            latency_ms=250,
            metadata={"key": "value"},
        )

        assert response.content == "Complete response"
        assert response.tokens_input == 1000
        assert response.tokens_output == 500
        assert response.cost_estimate == 0.0015
        assert response.latency_ms == 250
        assert response.metadata == {"key": "value"}

    def test_llm_response_defaults(self):
        """Test that optional fields have correct defaults."""
        response = LLMResponse(
            content="Test",
            model_id="test-model",
            provider="test",
            tier="test",
        )

        assert response.tokens_input == 0
        assert response.tokens_output == 0
        assert response.cost_estimate == 0.0
        assert response.latency_ms == 0
        assert response.metadata == {}


@pytest.mark.unit
class TestLLMResponseProperties:
    """Test LLMResponse computed properties and aliases."""

    def test_input_tokens_alias(self):
        """Test input_tokens property alias for backwards compatibility."""
        response = LLMResponse(
            content="Test",
            model_id="test",
            provider="test",
            tier="test",
            tokens_input=1500,
        )

        assert response.input_tokens == 1500
        assert response.input_tokens == response.tokens_input

    def test_output_tokens_alias(self):
        """Test output_tokens property alias for backwards compatibility."""
        response = LLMResponse(
            content="Test",
            model_id="test",
            provider="test",
            tier="test",
            tokens_output=750,
        )

        assert response.output_tokens == 750
        assert response.output_tokens == response.tokens_output

    def test_model_used_alias(self):
        """Test model_used property alias for backwards compatibility."""
        response = LLMResponse(
            content="Test",
            model_id="claude-opus-4-5",
            provider="test",
            tier="premium",
        )

        assert response.model_used == "claude-opus-4-5"
        assert response.model_used == response.model_id

    def test_cost_alias(self):
        """Test cost property alias for backwards compatibility."""
        response = LLMResponse(
            content="Test",
            model_id="test",
            provider="test",
            tier="test",
            cost_estimate=0.025,
        )

        assert response.cost == 0.025
        assert response.cost == response.cost_estimate

    def test_total_tokens_property(self):
        """Test total_tokens computed property."""
        response = LLMResponse(
            content="Test",
            model_id="test",
            provider="test",
            tier="test",
            tokens_input=1000,
            tokens_output=500,
        )

        assert response.total_tokens == 1500
        assert response.total_tokens == response.tokens_input + response.tokens_output

    def test_success_property_with_content(self):
        """Test success property returns True when content exists."""
        response = LLMResponse(
            content="Valid response",
            model_id="test",
            provider="test",
            tier="test",
        )

        assert response.success is True

    def test_success_property_without_content(self):
        """Test success property returns False when content is empty."""
        response = LLMResponse(
            content="",
            model_id="test",
            provider="test",
            tier="test",
        )

        assert response.success is False


@pytest.mark.unit
class TestExecutionContext:
    """Test ExecutionContext dataclass."""

    def test_execution_context_defaults(self):
        """Test that all ExecutionContext fields default to None or empty dict."""
        context = ExecutionContext()

        assert context.user_id is None
        assert context.workflow_name is None
        assert context.step_name is None
        assert context.task_type is None
        assert context.provider_hint is None
        assert context.tier_hint is None
        assert context.timeout_seconds is None
        assert context.session_id is None
        assert context.metadata == {}

    def test_execution_context_with_all_fields(self):
        """Test creating ExecutionContext with all fields."""
        context = ExecutionContext(
            user_id="user123",
            workflow_name="security-audit",
            step_name="scan",
            task_type="analyze",
            provider_hint="anthropic",
            tier_hint="premium",
            timeout_seconds=300,
            session_id="session456",
            metadata={"retry": 3, "priority": "high"},
        )

        assert context.user_id == "user123"
        assert context.workflow_name == "security-audit"
        assert context.step_name == "scan"
        assert context.task_type == "analyze"
        assert context.provider_hint == "anthropic"
        assert context.tier_hint == "premium"
        assert context.timeout_seconds == 300
        assert context.session_id == "session456"
        assert context.metadata == {"retry": 3, "priority": "high"}

    def test_execution_context_partial_fields(self):
        """Test creating ExecutionContext with only some fields."""
        context = ExecutionContext(
            workflow_name="test-gen",
            step_name="generate",
            tier_hint="capable",
        )

        assert context.workflow_name == "test-gen"
        assert context.step_name == "generate"
        assert context.tier_hint == "capable"
        # Others should still be None/empty
        assert context.user_id is None
        assert context.provider_hint is None


@pytest.mark.unit
class TestMockLLMExecutor:
    """Test MockLLMExecutor for testing workflows."""

    def test_mock_executor_initialization_defaults(self):
        """Test MockLLMExecutor with default values."""
        executor = MockLLMExecutor()

        assert executor.default_response == "Mock response"
        assert executor.default_model == "mock-model"
        assert executor.call_history == []

    def test_mock_executor_initialization_custom(self):
        """Test MockLLMExecutor with custom values."""
        executor = MockLLMExecutor(
            default_response="Custom response",
            default_model="custom-model",
        )

        assert executor.default_response == "Custom response"
        assert executor.default_model == "custom-model"

    @pytest.mark.asyncio
    async def test_mock_executor_run_basic(self):
        """Test basic run() execution."""
        executor = MockLLMExecutor()

        response = await executor.run(
            task_type="summarize",
            prompt="Test prompt",
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "Mock response"
        assert response.provider == "mock"
        assert response.metadata["mock"] is True
        assert response.metadata["task_type"] == "summarize"

    @pytest.mark.asyncio
    async def test_mock_executor_run_with_system_prompt(self):
        """Test run() with system prompt."""
        executor = MockLLMExecutor()

        response = await executor.run(
            task_type="fix_bug",
            prompt="Fix this bug",
            system="You are a helpful assistant",
        )

        assert response.content == "Mock response"
        assert len(executor.call_history) == 1
        assert executor.call_history[0]["system"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_mock_executor_run_with_context(self):
        """Test run() with ExecutionContext."""
        executor = MockLLMExecutor()
        context = ExecutionContext(
            workflow_name="test-workflow",
            step_name="test-step",
            user_id="test-user",
        )

        response = await executor.run(
            task_type="coordinate",
            prompt="Coordinate agents",
            context=context,
        )

        assert response.content == "Mock response"
        assert len(executor.call_history) == 1
        assert executor.call_history[0]["context"] == context

    @pytest.mark.asyncio
    async def test_mock_executor_run_with_kwargs(self):
        """Test run() with additional kwargs."""
        executor = MockLLMExecutor()

        response = await executor.run(
            task_type="analyze",
            prompt="Analyze code",
            max_tokens=2000,
            temperature=0.7,
        )

        assert response.content == "Mock response"
        assert executor.call_history[0]["kwargs"] == {
            "max_tokens": 2000,
            "temperature": 0.7,
        }

    @pytest.mark.asyncio
    async def test_mock_executor_call_history_tracking(self):
        """Test that call history is tracked correctly."""
        executor = MockLLMExecutor()

        await executor.run(task_type="task1", prompt="prompt1")
        await executor.run(task_type="task2", prompt="prompt2")
        await executor.run(task_type="task3", prompt="prompt3")

        assert len(executor.call_history) == 3
        assert executor.call_history[0]["task_type"] == "task1"
        assert executor.call_history[1]["task_type"] == "task2"
        assert executor.call_history[2]["task_type"] == "task3"

    @pytest.mark.asyncio
    async def test_mock_executor_token_estimation(self):
        """Test that mock executor estimates tokens roughly."""
        executor = MockLLMExecutor(
            default_response="This is a longer mock response with more words"
        )

        response = await executor.run(
            task_type="test",
            prompt="Short prompt",
        )

        # Should estimate tokens (words * 4)
        assert response.tokens_input > 0
        assert response.tokens_output > 0
        # Output should be longer since response has more words
        assert response.tokens_output > response.tokens_input

    @pytest.mark.asyncio
    async def test_mock_executor_response_fields(self):
        """Test that mock executor sets all expected response fields."""
        executor = MockLLMExecutor(default_model="test-model-v1")

        response = await executor.run(
            task_type="summarize",
            prompt="Test",
        )

        assert response.model_id == "test-model-v1"
        assert response.provider == "mock"
        assert response.cost_estimate == 0.0
        assert response.latency_ms == 10
        assert response.tier in ["cheap", "capable", "premium"]  # Should have a tier

    def test_mock_executor_get_model_for_task(self):
        """Test get_model_for_task returns default model."""
        executor = MockLLMExecutor(default_model="my-mock-model")

        model = executor.get_model_for_task("any_task")

        assert model == "my-mock-model"

    def test_mock_executor_estimate_cost(self):
        """Test estimate_cost always returns zero."""
        executor = MockLLMExecutor()

        cost = executor.estimate_cost(
            task_type="expensive_task",
            input_tokens=10000,
            output_tokens=5000,
        )

        assert cost == 0.0


@pytest.mark.unit
class TestMockLLMExecutorIntegration:
    """Integration tests for MockLLMExecutor."""

    @pytest.mark.asyncio
    async def test_multiple_calls_with_different_tasks(self):
        """Test MockLLMExecutor handles multiple different task types."""
        executor = MockLLMExecutor()

        # Simulate a workflow with multiple steps
        response1 = await executor.run(task_type="triage", prompt="Identify issues")
        response2 = await executor.run(task_type="code_analysis", prompt="Analyze code")
        response3 = await executor.run(task_type="code_generation", prompt="Generate tests")
        response4 = await executor.run(task_type="final_review", prompt="Review output")

        # All should succeed
        assert all(
            [
                response1.success,
                response2.success,
                response3.success,
                response4.success,
            ]
        )

        # History should be complete
        assert len(executor.call_history) == 4
        task_types = [call["task_type"] for call in executor.call_history]
        assert task_types == ["triage", "code_analysis", "code_generation", "final_review"]

    @pytest.mark.asyncio
    async def test_mock_executor_with_complex_context(self):
        """Test MockLLMExecutor with realistic complex context."""
        executor = MockLLMExecutor()
        context = ExecutionContext(
            user_id="user-abc-123",
            workflow_name="security-audit",
            step_name="vulnerability-scan",
            task_type="code_analysis",
            provider_hint="anthropic",
            tier_hint="premium",
            timeout_seconds=600,
            session_id="session-xyz-789",
            metadata={
                "retry_policy": {"max_retries": 3, "backoff": "exponential"},
                "fallback_policy": {"enabled": True, "fallback_tier": "capable"},
                "priority": "high",
            },
        )

        response = await executor.run(
            task_type="code_analysis",
            prompt="Scan for SQL injection vulnerabilities",
            system="You are a security expert",
            context=context,
            max_tokens=4000,
            temperature=0.3,
        )

        # Verify response
        assert response.success
        assert response.metadata["mock"] is True

        # Verify call was recorded with all details
        assert len(executor.call_history) == 1
        call = executor.call_history[0]
        assert call["task_type"] == "code_analysis"
        assert call["prompt"] == "Scan for SQL injection vulnerabilities"
        assert call["system"] == "You are a security expert"
        assert call["context"].workflow_name == "security-audit"
        assert call["kwargs"]["max_tokens"] == 4000
        assert call["kwargs"]["temperature"] == 0.3
