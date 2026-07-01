"""Unit tests for token estimation

Tests the token estimation service for cost prediction.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile
from pathlib import Path

import pytest

from attune.models.token_estimator import (
    TIKTOKEN_AVAILABLE,
    _get_encoding,
    estimate_single_call_cost,
    estimate_tokens,
    estimate_workflow_cost,
)


@pytest.mark.unit
class TestEstimateTokensBasic:
    """Test basic token estimation."""

    def test_estimate_tokens_empty_string(self):
        """Test estimating tokens for empty string."""
        result = estimate_tokens("")

        assert result == 0

    def test_estimate_tokens_simple_text(self):
        """Test estimating tokens for simple text."""
        text = "Hello world"
        result = estimate_tokens(text)

        assert result > 0
        assert isinstance(result, int)

    def test_estimate_tokens_heuristic_fallback(self):
        """Test token estimation works (may use tiktoken, toolkit, or heuristic)."""
        text = "a" * 100  # 100 chars
        result = estimate_tokens(text)

        # Should get a reasonable token count (tiktoken gives ~13 for repeated 'a')
        # Heuristic would give 25, but tiktoken is more accurate
        assert result > 0
        assert result < 50  # Sanity check

    def test_estimate_tokens_different_models(self):
        """Test estimation with different model IDs."""
        text = "Test text"

        claude_result = estimate_tokens(text, model_id="claude-sonnet-4")
        gpt_result = estimate_tokens(text, model_id="gpt-4")

        # Both should return positive integers
        assert claude_result > 0
        assert gpt_result > 0


@pytest.mark.unit
class TestGetEncoding:
    """Test encoding selection."""

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_claude(self):
        """Test encoding for Claude models."""
        encoding = _get_encoding("claude-sonnet-4")

        assert encoding is not None

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_gpt4(self):
        """Test encoding for GPT-4 models."""
        encoding = _get_encoding("gpt-4")

        assert encoding is not None

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_unknown_model(self):
        """Test encoding for unknown model defaults to cl100k_base."""
        encoding = _get_encoding("unknown-model-xyz")

        assert encoding is not None

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_caching(self):
        """Test that encoding is cached (LRU cache)."""
        # First call
        enc1 = _get_encoding("claude-sonnet-4")
        # Second call should return cached result
        enc2 = _get_encoding("claude-sonnet-4")

        assert enc1 is enc2


@pytest.mark.unit
class TestEstimateWorkflowCost:
    """Test workflow cost estimation."""

    def test_estimate_workflow_cost_basic(self):
        """Test basic workflow cost estimation."""
        result = estimate_workflow_cost(
            workflow_name="code-review",
            input_text="def hello(): pass",
            provider="anthropic",
        )

        assert "workflow" in result
        assert "provider" in result
        assert "input_tokens" in result
        assert "stages" in result
        assert "total_min" in result
        assert "total_max" in result
        assert "risk" in result
        assert result["workflow"] == "code-review"
        assert result["provider"] == "anthropic"
        assert result["input_tokens"] > 0

    def test_estimate_workflow_cost_known_workflows(self):
        """Test cost estimation for known workflows."""
        workflows = ["security-audit", "bug-predict", "test-gen", "doc-gen"]

        for workflow in workflows:
            result = estimate_workflow_cost(
                workflow_name=workflow,
                input_text="test code",
                provider="anthropic",
            )

            assert result["workflow"] == workflow
            assert len(result["stages"]) > 0

    def test_estimate_workflow_cost_unknown_workflow(self):
        """Test cost estimation for unknown workflow uses default stages."""
        result = estimate_workflow_cost(
            workflow_name="unknown-workflow",
            input_text="test",
            provider="anthropic",
        )

        # Should use default 3-stage configuration
        assert len(result["stages"]) == 3

    def test_estimate_workflow_cost_risk_levels(self):
        """Test risk level calculation."""
        # Low risk: short input
        low_risk = estimate_workflow_cost(
            workflow_name="doc-gen",
            input_text="x",
            provider="anthropic",
        )

        # High risk: very long input
        high_risk = estimate_workflow_cost(
            workflow_name="security-audit",
            input_text="x" * 10000,
            provider="anthropic",
        )

        assert low_risk["risk"] in ["low", "medium", "high"]
        assert high_risk["risk"] in ["low", "medium", "high"]

    def test_estimate_workflow_cost_with_file_path(self):
        """Test cost estimation with target file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def test(): pass\n" * 50)

            result = estimate_workflow_cost(
                workflow_name="code-review",
                input_text="Review this code",
                provider="anthropic",
                target_path=str(test_file),
            )

            # Input tokens should include both input_text and file content
            assert result["input_tokens"] > 10  # More than just "Review this code"

    def test_estimate_workflow_cost_with_directory_path(self):
        """Test cost estimation with target directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Python files
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def test{i}(): pass\n")

            result = estimate_workflow_cost(
                workflow_name="security-audit",
                input_text="Audit codebase",
                provider="anthropic",
                target_path=tmpdir,
            )

            # Should include file contents
            assert result["input_tokens"] > 5

    def test_estimate_workflow_cost_invalid_provider(self):
        """Test estimation with invalid provider falls back to anthropic."""
        result = estimate_workflow_cost(
            workflow_name="code-review",
            input_text="test",
            provider="invalid-provider-xyz",
        )

        # Should fallback to anthropic
        assert result["provider"] == "anthropic"

    def test_estimate_workflow_cost_stage_details(self):
        """Test that stage details are populated correctly."""
        result = estimate_workflow_cost(
            workflow_name="code-review",
            input_text="test code",
            provider="anthropic",
        )

        # Check stage structure
        for stage in result["stages"]:
            assert "stage" in stage
            assert "tier" in stage
            assert "model" in stage
            assert "estimated_input_tokens" in stage
            assert "estimated_output_tokens" in stage
            assert "estimated_cost" in stage


@pytest.mark.unit
class TestEstimateSingleCallCost:
    """Test single call cost estimation."""

    def test_estimate_single_call_cost_basic(self):
        """Test basic single call cost estimation."""
        result = estimate_single_call_cost(
            text="Summarize this text",
            task_type="summarize",
            provider="anthropic",
        )

        assert "task_type" in result
        assert "tier" in result
        assert "model" in result
        assert "provider" in result
        assert "input_tokens" in result
        assert "estimated_output_tokens" in result
        assert "estimated_cost" in result
        assert "display" in result

    def test_estimate_single_call_cost_different_tasks(self):
        """Test cost estimation for different task types."""
        task_types = ["summarize", "classify", "generate_code", "review"]

        for task_type in task_types:
            result = estimate_single_call_cost(
                text="test input",
                task_type=task_type,
                provider="anthropic",
            )

            assert result["task_type"] == task_type
            assert result["input_tokens"] > 0

    def test_estimate_single_call_cost_output_multipliers(self):
        """Test that output tokens vary by task type."""
        text = "test" * 100

        summarize = estimate_single_call_cost(text, "summarize", "anthropic")
        generate_code = estimate_single_call_cost(text, "generate_code", "anthropic")

        # Generate code should have higher output multiplier than summarize
        assert generate_code["estimated_output_tokens"] > summarize["estimated_output_tokens"]

    def test_estimate_single_call_cost_cost_calculation(self):
        """Test that cost is calculated correctly."""
        result = estimate_single_call_cost(
            text="test",
            task_type="summarize",
            provider="anthropic",
        )

        # Cost should be positive for non-zero input
        assert result["estimated_cost"] >= 0
        # Display should be a formatted string
        assert result["display"].startswith("$")


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_estimate_tokens_very_long_text(self):
        """Test estimation with very long text."""
        long_text = "x" * 100000
        result = estimate_tokens(long_text)

        assert result > 0
        assert isinstance(result, int)

    def test_estimate_tokens_special_characters(self):
        """Test estimation with special characters."""
        text = "Hello! @#$% 你好 🚀"
        result = estimate_tokens(text)

        assert result > 0

    def test_estimate_workflow_cost_empty_input(self):
        """Test workflow cost with empty input."""
        result = estimate_workflow_cost(
            workflow_name="code-review",
            input_text="",
            provider="anthropic",
        )

        assert result["input_tokens"] == 0

    def test_estimate_workflow_cost_nonexistent_file(self):
        """Test workflow cost with nonexistent file path."""
        result = estimate_workflow_cost(
            workflow_name="code-review",
            input_text="test",
            provider="anthropic",
            target_path="/nonexistent/path/to/file.py",
        )

        # Should not crash, just use input text tokens
        assert result["input_tokens"] > 0

    def test_estimate_single_call_unknown_task_type(self):
        """Test single call estimation with unknown task type."""
        result = estimate_single_call_cost(
            text="test",
            task_type="unknown_task_xyz",
            provider="anthropic",
        )

        # Should use default multiplier of 1.0
        assert result["estimated_output_tokens"] > 0


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestEstimateTokensFallbacks:
    """Cover lines 78-83: tiktoken fallback path."""

    def test_tiktoken_fallback_when_count_tokens_import_fails(self, monkeypatch):
        """Lines 75-83: ImportError on count_tokens → use tiktoken."""
        # Make count_tokens import raise ImportError
        import sys
        from unittest.mock import patch as _patch

        from attune.models import token_estimator as mod

        monkeypatch.delitem(sys.modules, "attune.utils.tokens", raising=False)

        import builtins as _b

        real_import = _b.__import__

        def fake_import(name, *args, **kwargs):
            if name == "attune.utils.tokens":
                raise ImportError("toolkit missing")
            return real_import(name, *args, **kwargs)

        with (
            _patch("builtins.__import__", side_effect=fake_import),
            _patch.object(mod, "TIKTOKEN_AVAILABLE", True),
        ):
            result = mod.estimate_tokens("hello world", model_id="claude-sonnet-5")
        assert result > 0

    def test_tiktoken_fallback_with_encoding_exception(self, monkeypatch):
        """Lines 82-83: tiktoken encoding raises → heuristic fallback."""
        import sys
        from unittest.mock import patch as _patch

        from attune.models import token_estimator as mod

        monkeypatch.delitem(sys.modules, "attune.utils.tokens", raising=False)

        import builtins as _b

        real_import = _b.__import__

        def fake_import(name, *args, **kwargs):
            if name == "attune.utils.tokens":
                raise ImportError("toolkit missing")
            return real_import(name, *args, **kwargs)

        # Patch _get_encoding to raise
        with (
            _patch("builtins.__import__", side_effect=fake_import),
            _patch.object(mod, "TIKTOKEN_AVAILABLE", True),
            _patch.object(mod, "_get_encoding", side_effect=RuntimeError("encoding broken")),
        ):
            result = mod.estimate_tokens("hello world", model_id="claude-x")
        # Heuristic fallback
        assert result == max(1, int(len("hello world") * mod.TOKENS_PER_CHAR_HEURISTIC))

    def test_no_tiktoken_uses_heuristic(self, monkeypatch):
        """Line 86: tiktoken unavailable + count_tokens unavailable → heuristic."""
        import sys
        from unittest.mock import patch as _patch

        from attune.models import token_estimator as mod

        monkeypatch.delitem(sys.modules, "attune.utils.tokens", raising=False)

        import builtins as _b

        real_import = _b.__import__

        def fake_import(name, *args, **kwargs):
            if name == "attune.utils.tokens":
                raise ImportError("toolkit missing")
            return real_import(name, *args, **kwargs)

        with (
            _patch("builtins.__import__", side_effect=fake_import),
            _patch.object(mod, "TIKTOKEN_AVAILABLE", False),
        ):
            result = mod.estimate_tokens("hello", model_id="x")
        assert result == max(1, int(len("hello") * mod.TOKENS_PER_CHAR_HEURISTIC))


class TestGetEncodingTiktokenUnavailable:
    """Cover line 34: tiktoken unavailable → None."""

    def test_no_tiktoken_returns_none(self, monkeypatch):
        from unittest.mock import patch as _patch

        from attune.models import token_estimator as mod

        # Clear lru_cache + patch flag
        mod._get_encoding.cache_clear()
        with _patch.object(mod, "TIKTOKEN_AVAILABLE", False):
            result = mod._get_encoding("any-model")
        assert result is None
        # Clear cache for subsequent tests
        mod._get_encoding.cache_clear()


class TestEstimateProjectTokensEdges:
    """Cover lines 184->183, 190-191, 193-194 in _estimate_file_tokens (or similar)."""

    def test_walks_directory_skipping_non_source_files(self, tmp_path):
        """Line 184->183: files without source extensions skipped."""
        from attune.models.token_estimator import _estimate_file_tokens

        # Create mix of files
        (tmp_path / "a.py").write_text("def f(): pass\n" * 10)
        (tmp_path / "b.txt").write_text("not source")  # skipped
        (tmp_path / "c.md").write_text("docs")  # skipped

        result = _estimate_file_tokens(str(tmp_path))
        assert result > 0

    def test_handles_unreadable_file(self, tmp_path, monkeypatch):
        """Lines 190-191: file open OSError → skip."""
        from attune.models.token_estimator import _estimate_file_tokens

        good = tmp_path / "good.py"
        good.write_text("x = 1\n")
        bad = tmp_path / "bad.py"
        bad.write_text("y = 2\n")

        # Patch open to raise OSError for bad.py
        original_open = open

        def fake_open(path, *args, **kwargs):
            if "bad.py" in str(path):
                raise OSError("permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", fake_open)
        # Should not raise — bad.py is skipped
        result = _estimate_file_tokens(str(tmp_path))
        assert result >= 0

    def test_invalid_path_returns_zero(self):
        """Lines 193-194: outer try/except returns 0."""
        from attune.models.token_estimator import _estimate_file_tokens

        # Path validation should fail or os calls should fail
        result = _estimate_file_tokens("/path/does/not/exist/at/all")
        assert result == 0


class TestCalculateStageCostsEdges:
    """Cover lines 222-223, 226."""

    def test_get_model_exception_falls_back(self):
        """Lines 222-223: get_model raises → falls back to capable."""
        from unittest.mock import MagicMock as _MagicMock
        from unittest.mock import patch as _patch

        from attune.models.token_estimator import _calculate_stage_costs

        stages = [{"name": "x", "tier": "weird-tier"}]

        with _patch("attune.models.registry.get_model") as mock_get:
            fake_model = _MagicMock()
            fake_model.input_cost_per_million = 1.0
            fake_model.output_cost_per_million = 2.0
            fake_model.id = "fallback"
            mock_get.side_effect = [RuntimeError("unknown tier"), fake_model]
            estimates, total_min, total_max = _calculate_stage_costs(
                stages, input_tokens=100, provider="anthropic"
            )
        assert len(estimates) == 1

    def test_model_info_none_skipped(self):
        """Line 226: model_info None → skip stage."""
        from unittest.mock import patch as _patch

        from attune.models.token_estimator import _calculate_stage_costs

        stages = [{"name": "skip-me", "tier": "cheap"}]

        with _patch("attune.models.registry.get_model", return_value=None):
            estimates, total_min, total_max = _calculate_stage_costs(
                stages, input_tokens=100, provider="anthropic"
            )
        assert estimates == []


class TestEstimateSingleCallCostNoModel:
    """Cover line 369: model_info None fallback path."""

    def test_no_model_returns_fallback(self):
        from unittest.mock import patch as _patch

        from attune.models.token_estimator import estimate_single_call_cost

        with _patch("attune.models.registry.get_model", return_value=None):
            result = estimate_single_call_cost("hello world", task_type="summarize")
        assert result["model"] == "unknown"
        assert result["estimated_cost"] == 0.0


class TestGetEncodingPaths:
    """Cover lines 40-43 in _get_encoding (tiktoken-installed path)."""

    def test_gpt4_encoding(self):
        from attune.models import token_estimator as mod

        mod._get_encoding.cache_clear()
        result = mod._get_encoding("gpt-4-turbo")
        assert result is not None
        mod._get_encoding.cache_clear()

    def test_o1_encoding(self):
        from attune.models import token_estimator as mod

        mod._get_encoding.cache_clear()
        result = mod._get_encoding("o1-preview")
        assert result is not None
        mod._get_encoding.cache_clear()

    def test_unknown_model_uses_default_encoding(self):
        from attune.models import token_estimator as mod

        mod._get_encoding.cache_clear()
        result = mod._get_encoding("unknown-model")
        assert result is not None
        mod._get_encoding.cache_clear()


class TestGetEncodingPathsNoTiktoken:
    """Cover lines 33-34 in _get_encoding (tiktoken-not-installed path).

    tiktoken is optional in production (heuristic fallback exists). These
    tests verify the no-tiktoken branch returns None so callers fall
    through to the heuristic. Pairs with TestGetEncodingPaths above which
    covers the tiktoken-installed branch.
    """

    def test_returns_none_when_tiktoken_unavailable(self):
        from unittest.mock import patch

        from attune.models import token_estimator as mod

        mod._get_encoding.cache_clear()
        with patch.object(mod, "TIKTOKEN_AVAILABLE", False):
            assert mod._get_encoding("gpt-4-turbo") is None
            assert mod._get_encoding("o1-preview") is None
            assert mod._get_encoding("unknown-model") is None
            assert mod._get_encoding("claude-sonnet-5") is None
        mod._get_encoding.cache_clear()


class TestEstimateFileTokensOuterError:
    """Cover lines 193-194: outer try/except in _estimate_file_tokens."""

    def test_path_validation_failure_returns_zero(self):
        """ValueError in path validation → outer except → 0."""
        from unittest.mock import patch as _patch

        from attune.models.token_estimator import _estimate_file_tokens

        with _patch(
            "attune.models.token_estimator._validate_file_path",
            side_effect=ValueError("invalid"),
        ):
            assert _estimate_file_tokens("/anything") == 0
