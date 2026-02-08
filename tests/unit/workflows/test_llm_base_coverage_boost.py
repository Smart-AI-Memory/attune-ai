"""Comprehensive coverage tests for LLM Base Workflow Generator.

Tests LLMWorkflowGenerator base class and TestGeneratorLLM example.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

import attune.workflows.llm_base as llm_base_module

LLMWorkflowGenerator = llm_base_module.LLMWorkflowGenerator
TestGeneratorLLM = llm_base_module.TestGeneratorLLM


# Concrete implementation for testing abstract base class
class MockLLMGenerator(LLMWorkflowGenerator):
    """Mock implementation for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_calls = []
        self.validate_calls = []
        self.validate_return = True

    def _generate_with_template(self, context):
        """Track template generation calls."""
        self.template_calls.append(context)
        return f"Template output for {context.get('name', 'unknown')}"

    def _validate(self, result):
        """Track validation calls."""
        self.validate_calls.append(result)
        return self.validate_return


@pytest.mark.unit
class TestLLMWorkflowGeneratorInit:
    """Test LLMWorkflowGenerator initialization."""

    def test_llm_generator_initialization_defaults(self):
        """Test creating LLMWorkflowGenerator with defaults."""
        gen = MockLLMGenerator()

        assert gen.model_tier == "capable"
        assert gen.enable_cache is True
        assert gen.cache_ttl == timedelta(hours=24)
        assert gen._cache == {}

    def test_llm_generator_initialization_custom_tier(self):
        """Test creating generator with custom model tier."""
        gen = MockLLMGenerator(model_tier="premium")

        assert gen.model_tier == "premium"

    def test_llm_generator_initialization_cache_disabled(self):
        """Test creating generator with caching disabled."""
        gen = MockLLMGenerator(enable_cache=False)

        assert gen.enable_cache is False

    def test_llm_generator_initialization_custom_ttl(self):
        """Test creating generator with custom cache TTL."""
        gen = MockLLMGenerator(cache_ttl_hours=48)

        assert gen.cache_ttl == timedelta(hours=48)

    def test_llm_generator_stats_initialization(self):
        """Test that statistics are initialized correctly."""
        gen = MockLLMGenerator()

        assert gen._stats["llm_requests"] == 0
        assert gen._stats["llm_failures"] == 0
        assert gen._stats["template_fallbacks"] == 0
        assert gen._stats["cache_hits"] == 0
        assert gen._stats["cache_misses"] == 0
        assert gen._stats["total_tokens"] == 0
        assert gen._stats["total_cost_usd"] == 0.0


@pytest.mark.unit
class TestCaching:
    """Test caching functionality."""

    def test_make_cache_key_consistent(self):
        """Test cache key is consistent for same inputs."""
        gen = MockLLMGenerator()

        context = {"name": "test", "value": 123}
        prompt = "Generate test"

        key1 = gen._make_cache_key(context, prompt)
        key2 = gen._make_cache_key(context, prompt)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex digest

    def test_make_cache_key_different_for_different_inputs(self):
        """Test cache key changes with different inputs."""
        gen = MockLLMGenerator()

        key1 = gen._make_cache_key({"a": 1}, "prompt1")
        key2 = gen._make_cache_key({"a": 2}, "prompt1")
        key3 = gen._make_cache_key({"a": 1}, "prompt2")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_put_in_cache_stores_value(self):
        """Test _put_in_cache stores value with timestamp."""
        gen = MockLLMGenerator()

        gen._put_in_cache("test_key", "test_value")

        assert "test_key" in gen._cache
        value, timestamp = gen._cache["test_key"]
        assert value == "test_value"
        assert isinstance(timestamp, datetime)

    def test_get_from_cache_returns_value(self):
        """Test _get_from_cache retrieves stored value."""
        gen = MockLLMGenerator()

        gen._put_in_cache("test_key", "test_value")
        result = gen._get_from_cache("test_key")

        assert result == "test_value"

    def test_get_from_cache_returns_none_for_missing_key(self):
        """Test _get_from_cache returns None for missing key."""
        gen = MockLLMGenerator()

        result = gen._get_from_cache("nonexistent")

        assert result is None

    def test_get_from_cache_expires_old_entries(self):
        """Test cache entries expire after TTL."""
        gen = MockLLMGenerator(cache_ttl_hours=1)

        # Manually add expired entry
        old_timestamp = datetime.now() - timedelta(hours=2)
        gen._cache["old_key"] = ("old_value", old_timestamp)

        result = gen._get_from_cache("old_key")

        assert result is None
        assert "old_key" not in gen._cache  # Should be deleted

    def test_clear_cache_empties_cache(self):
        """Test clear_cache removes all entries."""
        gen = MockLLMGenerator()

        gen._put_in_cache("key1", "value1")
        gen._put_in_cache("key2", "value2")
        assert len(gen._cache) == 2

        gen.clear_cache()

        assert len(gen._cache) == 0


@pytest.mark.unit
class TestGenerateWithTemplate:
    """Test template generation fallback."""

    def test_generate_uses_template_when_cache_disabled(self):
        """Test generate calls template when caching disabled."""
        gen = MockLLMGenerator(enable_cache=False)

        # Mock LLM to always fail
        gen.validate_return = False

        context = {"name": "test"}
        result = gen.generate(context, "prompt")

        assert result == "Template output for test"
        assert len(gen.template_calls) == 1
        assert gen.template_calls[0] == context

    def test_generate_falls_back_to_template_on_validation_failure(self):
        """Test template fallback when LLM result fails validation."""
        gen = MockLLMGenerator()
        gen.validate_return = False

        with patch.object(gen, "_generate_with_llm", return_value="invalid_result"):
            context = {"name": "test"}
            result = gen.generate(context, "prompt")

            assert result == "Template output for test"
            assert gen._stats["template_fallbacks"] == 1

    def test_generate_falls_back_to_template_on_llm_error(self):
        """Test template fallback when LLM raises exception."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", side_effect=Exception("API error")):
            context = {"name": "test"}
            result = gen.generate(context, "prompt")

            assert result == "Template output for test"
            assert gen._stats["llm_failures"] == 1
            assert gen._stats["template_fallbacks"] == 1


@pytest.mark.unit
class TestValidation:
    """Test validation flow."""

    def test_generate_validates_llm_result(self):
        """Test that LLM results are validated."""
        gen = MockLLMGenerator()
        gen.validate_return = True

        with patch.object(gen, "_generate_with_llm", return_value="valid_result"):
            gen.generate({}, "prompt")

            assert len(gen.validate_calls) == 1
            assert gen.validate_calls[0] == "valid_result"

    def test_generate_uses_validated_result(self):
        """Test that validated LLM result is returned."""
        gen = MockLLMGenerator()
        gen.validate_return = True

        with patch.object(gen, "_generate_with_llm", return_value="valid_result"):
            result = gen.generate({}, "prompt")

            assert result == "valid_result"

    def test_generate_rejects_invalid_result(self):
        """Test that invalid LLM result triggers template fallback."""
        gen = MockLLMGenerator()
        gen.validate_return = False

        with patch.object(gen, "_generate_with_llm", return_value="invalid"):
            result = gen.generate({"name": "test"}, "prompt")

            assert result == "Template output for test"


@pytest.mark.unit
class TestCacheHitMiss:
    """Test cache hit/miss statistics."""

    def test_cache_miss_on_first_request(self):
        """Test cache miss incremented on first request."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", return_value="result"):
            gen.generate({}, "prompt")

            assert gen._stats["cache_misses"] == 1
            assert gen._stats["cache_hits"] == 0

    def test_cache_hit_on_second_request(self):
        """Test cache hit on repeated request."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", return_value="result"):
            # First request
            gen.generate({"key": "value"}, "prompt")

            # Second request with same inputs
            result = gen.generate({"key": "value"}, "prompt")

            assert gen._stats["cache_hits"] == 1
            assert gen._stats["cache_misses"] == 1
            assert result == "result"

    def test_cache_disabled_no_cache_stats(self):
        """Test that cache stats not updated when caching disabled."""
        gen = MockLLMGenerator(enable_cache=False)

        with patch.object(gen, "_generate_with_llm", return_value="result"):
            gen.generate({}, "prompt")
            gen.generate({}, "prompt")

            assert gen._stats["cache_hits"] == 0
            assert gen._stats["cache_misses"] == 0


@pytest.mark.unit
class TestStatistics:
    """Test statistics tracking."""

    def test_update_usage_stats_cheap_tier(self):
        """Test cost calculation for cheap tier."""
        gen = MockLLMGenerator(model_tier="cheap")

        result = "x" * 400  # 100 tokens
        gen._update_usage_stats(result)

        assert gen._stats["total_tokens"] == 100
        # Cheap: $1/M tokens = $0.0001 for 100 tokens
        assert gen._stats["total_cost_usd"] == pytest.approx(0.0001)

    def test_update_usage_stats_capable_tier(self):
        """Test cost calculation for capable tier."""
        gen = MockLLMGenerator(model_tier="capable")

        result = "x" * 400  # 100 tokens
        gen._update_usage_stats(result)

        assert gen._stats["total_tokens"] == 100
        # Capable: $15/M tokens = $0.0015 for 100 tokens
        assert gen._stats["total_cost_usd"] == pytest.approx(0.0015)

    def test_update_usage_stats_premium_tier(self):
        """Test cost calculation for premium tier."""
        gen = MockLLMGenerator(model_tier="premium")

        result = "x" * 400  # 100 tokens
        gen._update_usage_stats(result)

        assert gen._stats["total_tokens"] == 100
        # Premium: $75/M tokens = $0.0075 for 100 tokens
        assert gen._stats["total_cost_usd"] == pytest.approx(0.0075)

    def test_get_stats_calculates_rates(self):
        """Test get_stats calculates success rates."""
        gen = MockLLMGenerator()

        # Simulate requests
        gen._stats["llm_requests"] = 10
        gen._stats["llm_failures"] = 2
        gen._stats["template_fallbacks"] = 3

        stats = gen.get_stats()

        assert stats["llm_success_rate"] == pytest.approx(0.8)  # 8/10
        assert stats["template_fallback_rate"] == pytest.approx(0.3)  # 3/10

    def test_get_stats_handles_zero_requests(self):
        """Test get_stats when no requests have been made."""
        gen = MockLLMGenerator()

        stats = gen.get_stats()

        assert stats["llm_success_rate"] == 0.0
        assert stats["template_fallback_rate"] == 0.0

    def test_get_stats_calculates_cache_hit_rate(self):
        """Test get_stats calculates cache hit rate."""
        gen = MockLLMGenerator()

        gen._stats["cache_hits"] = 7
        gen._stats["cache_misses"] = 3

        stats = gen.get_stats()

        assert stats["cache_hit_rate"] == pytest.approx(0.7)  # 7/10

    def test_get_stats_handles_zero_cache_ops(self):
        """Test get_stats when no cache operations."""
        gen = MockLLMGenerator()

        stats = gen.get_stats()

        assert stats["cache_hit_rate"] == 0.0

    def test_get_stats_returns_copy(self):
        """Test that get_stats returns a copy, not reference."""
        gen = MockLLMGenerator()

        stats1 = gen.get_stats()
        stats1["llm_requests"] = 999

        stats2 = gen.get_stats()

        assert stats2["llm_requests"] == 0  # Original not modified


@pytest.mark.unit
class TestTestGeneratorLLM:
    """Test the concrete TestGeneratorLLM implementation."""

    def test_test_generator_initialization(self):
        """Test TestGeneratorLLM initialization."""
        gen = TestGeneratorLLM(model_tier="cheap")

        assert gen.model_tier == "cheap"
        assert gen.enable_cache is True

    def test_generate_with_template_creates_test_file(self):
        """Test _generate_with_template creates valid test file."""
        gen = TestGeneratorLLM()

        context = {
            "module_name": "auth_handler",
            "module_path": "src/auth_handler.py",
        }

        result = gen._generate_with_template(context)

        assert "auth_handler" in result
        assert "import pytest" in result
        assert "def test_auth_handler_placeholder():" in result
        assert '"""Behavioral tests for auth_handler.' in result

    def test_generate_with_template_handles_missing_context(self):
        """Test template generation with missing context fields."""
        gen = TestGeneratorLLM()

        result = gen._generate_with_template({})

        assert "unknown" in result
        assert "import pytest" in result

    def test_validate_accepts_valid_test_file(self):
        """Test _validate accepts valid test file structure."""
        gen = TestGeneratorLLM()

        valid_test = '''"""Test module for comprehensive testing.

This module contains tests for the authentication system.
"""

import pytest

def test_something():
    """Test function that validates authentication."""
    assert True
'''

        assert gen._validate(valid_test) is True

    def test_validate_rejects_missing_pytest(self):
        """Test _validate rejects file without pytest import."""
        gen = TestGeneratorLLM()

        invalid_test = '''"""Test module."""

def test_something():
    pass
'''

        assert gen._validate(invalid_test) is False

    def test_validate_rejects_missing_test_function(self):
        """Test _validate rejects file without test function."""
        gen = TestGeneratorLLM()

        invalid_test = '''"""Test module."""

import pytest

def helper_function():
    pass
'''

        assert gen._validate(invalid_test) is False

    def test_validate_rejects_too_short(self):
        """Test _validate rejects files that are too short."""
        gen = TestGeneratorLLM()

        too_short = "import pytest\ndef test_x():\n    pass"

        assert gen._validate(too_short) is False

    def test_validate_rejects_missing_docstring(self):
        """Test _validate requires docstring."""
        gen = TestGeneratorLLM()

        no_docstring = (
            """
import pytest
def test_something():
    assert True
"""
            * 5
        )  # Make it long enough

        assert gen._validate(no_docstring) is False


@pytest.mark.unit
class TestIntegration:
    """Integration tests for LLMWorkflowGenerator."""

    def test_full_workflow_with_llm_success(self):
        """Test complete workflow when LLM succeeds."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", return_value="llm_output"):
            result = gen.generate({"key": "value"}, "Generate something")

            assert result == "llm_output"
            assert gen._stats["llm_requests"] == 1
            assert gen._stats["template_fallbacks"] == 0
            assert gen._stats["cache_misses"] == 1

    def test_full_workflow_with_cache_hit(self):
        """Test workflow uses cache on repeated calls."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", return_value="llm_output") as mock_llm:
            # First call
            result1 = gen.generate({"key": "value"}, "prompt")

            # Second call with same inputs
            result2 = gen.generate({"key": "value"}, "prompt")

            assert result1 == result2 == "llm_output"
            assert mock_llm.call_count == 1  # LLM called only once
            assert gen._stats["cache_hits"] == 1
            assert gen._stats["cache_misses"] == 1

    def test_full_workflow_with_validation_failure(self):
        """Test workflow falls back when validation fails."""
        gen = MockLLMGenerator()
        gen.validate_return = False

        with patch.object(gen, "_generate_with_llm", return_value="invalid"):
            context = {"name": "test"}
            result = gen.generate(context, "prompt")

            assert result == "Template output for test"
            assert gen._stats["template_fallbacks"] == 1
            assert len(gen.validate_calls) == 1

    def test_multiple_requests_accumulate_stats(self):
        """Test statistics accumulate across multiple requests."""
        gen = MockLLMGenerator()

        with patch.object(gen, "_generate_with_llm", return_value="result"):
            # Make 5 requests
            for i in range(5):
                gen.generate({"req": i}, "prompt")

            stats = gen.get_stats()
            assert stats["llm_requests"] == 5
            assert stats["cache_misses"] == 5  # All different contexts

    def test_test_generator_end_to_end(self):
        """Test TestGeneratorLLM end-to-end."""
        gen = TestGeneratorLLM()

        context = {
            "module_name": "calculator",
            "module_path": "src/calculator.py",
        }

        # Force template generation (no LLM)
        result = gen._generate_with_template(context)

        # Verify template output is valid
        assert gen._validate(result) is True
        assert "calculator" in result
        assert "import pytest" in result
