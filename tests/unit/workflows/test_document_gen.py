"""Tests for DocumentGenerationWorkflow.

Tests cover report formatting, step configuration, and token cost constants.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.workflows.base import ModelTier
from attune.workflows.document_gen import (
    DOC_GEN_STEPS,
    TOKEN_COSTS,
    format_doc_gen_report,
)


class TestFormatDocGenReport:
    """Test suite for report formatting functionality."""

    def test_format_basic_report(self):
        """Test formatting basic report."""
        result = {
            "document": "# Test Doc\n\nContent here.",
            "doc_type": "api_reference",
            "audience": "developers",
            "model_tier_used": "capable",
        }
        input_data = {
            "outline": "1. Introduction\n2. API",
        }

        report = format_doc_gen_report(result, input_data)

        assert "DOCUMENTATION GENERATION REPORT" in report
        assert "Document Type: Api Reference" in report
        assert "Target Audience: Developers" in report
        assert "GENERATED DOCUMENTATION" in report
        assert "# Test Doc" in report

    def test_format_report_with_outline(self):
        """Test report includes outline summary."""
        result = {
            "document": "# Doc",
            "doc_type": "guide",
            "audience": "users",
        }
        input_data = {
            "outline": "1. Intro\n2. Setup\n3. Usage",
        }

        report = format_doc_gen_report(result, input_data)
        assert "DOCUMENT OUTLINE" in report
        assert "1. Intro" in report

    def test_format_report_with_statistics(self):
        """Test report includes statistics."""
        result = {
            "document": "## Section 1\nWord word word.\n## Section 2\nMore words.",
            "doc_type": "test",
            "audience": "testers",
        }
        input_data = {}

        report = format_doc_gen_report(result, input_data)
        assert "STATISTICS" in report
        assert "Word Count:" in report
        assert "Section Count:" in report

    def test_format_report_with_chunking(self):
        """Test report shows chunking information."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {
            "chunked": True,
            "chunk_count": 5,
            "chunks_completed": 5,
        }

        report = format_doc_gen_report(result, input_data)
        assert "Generation Mode: Chunked (5 chunks)" in report

    def test_format_report_with_partial_chunks(self):
        """Test report shows partial chunk completion."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {
            "chunked": True,
            "chunk_count": 5,
            "chunks_completed": 3,
            "stopped_early": True,
        }

        report = format_doc_gen_report(result, input_data)
        assert "Chunked (3/5 chunks completed)" in report

    def test_format_report_with_cost(self):
        """Test report includes cost information."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
            "accumulated_cost": 2.45,
        }
        input_data = {}

        report = format_doc_gen_report(result, input_data)
        assert "Estimated Cost: $2.45" in report

    def test_format_report_with_export_paths(self):
        """Test report includes export paths."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
            "export_path": "/path/to/doc.md",
            "report_path": "/path/to/report.txt",
        }
        input_data = {}

        report = format_doc_gen_report(result, input_data)
        assert "FILE EXPORT" in report
        assert "/path/to/doc.md" in report
        assert "/path/to/report.txt" in report

    def test_format_report_with_warnings(self):
        """Test report includes warnings."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {
            "warning": "Cost limit reached. Partial generation.",
        }

        report = format_doc_gen_report(result, input_data)
        assert "⚠️  WARNING" in report
        assert "Cost limit reached" in report

    def test_format_report_truncation_detection(self):
        """Test report detects truncated documents."""
        result = {
            "document": "## Section 1\nContent...",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {
            "outline": "1. Section 1\n2. Section 2\n3. Section 3\n4. Section 4",
        }

        report = format_doc_gen_report(result, input_data)
        assert "SCOPE NOTICE" in report
        assert "DOCUMENTATION MAY BE INCOMPLETE" in report

    def test_format_report_includes_model_tier(self):
        """Test report includes model tier used."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
            "model_tier_used": "premium",
        }
        input_data = {}

        report = format_doc_gen_report(result, input_data)
        assert "Generated using premium tier model" in report


class TestStepConfiguration:
    """Test suite for workflow step configuration."""

    def test_doc_gen_steps_defined(self):
        """Test DOC_GEN_STEPS is properly defined."""
        assert "polish" in DOC_GEN_STEPS
        step = DOC_GEN_STEPS["polish"]
        assert step.name == "polish"
        assert step.task_type == "final_review"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 20000

    def test_step_configuration_properties(self):
        """Test step configuration has required properties."""
        step = DOC_GEN_STEPS["polish"]
        assert hasattr(step, "name")
        assert hasattr(step, "task_type")
        assert hasattr(step, "tier_hint")
        assert hasattr(step, "description")
        assert hasattr(step, "max_tokens")


class TestTokenCosts:
    """Test suite for token cost constants."""

    def test_token_costs_defined(self):
        """Test TOKEN_COSTS constant is defined."""
        assert TOKEN_COSTS is not None
        assert len(TOKEN_COSTS) == 3

    def test_token_costs_has_all_tiers(self):
        """Test TOKEN_COSTS includes all model tiers."""
        assert ModelTier.CHEAP in TOKEN_COSTS
        assert ModelTier.CAPABLE in TOKEN_COSTS
        assert ModelTier.PREMIUM in TOKEN_COSTS

    def test_token_costs_structure(self):
        """Test TOKEN_COSTS has correct structure."""
        for tier in TOKEN_COSTS.values():
            assert "input" in tier
            assert "output" in tier
            assert isinstance(tier["input"], float)
            assert isinstance(tier["output"], float)

    def test_token_costs_relative_pricing(self):
        """Test token costs follow expected price hierarchy."""
        # Cheap should be cheapest
        assert TOKEN_COSTS[ModelTier.CHEAP]["input"] < TOKEN_COSTS[ModelTier.CAPABLE]["input"]
        assert TOKEN_COSTS[ModelTier.CHEAP]["output"] < TOKEN_COSTS[ModelTier.CAPABLE]["output"]

        # Premium should be most expensive
        assert TOKEN_COSTS[ModelTier.CAPABLE]["input"] < TOKEN_COSTS[ModelTier.PREMIUM]["input"]
        assert TOKEN_COSTS[ModelTier.CAPABLE]["output"] < TOKEN_COSTS[ModelTier.PREMIUM]["output"]
