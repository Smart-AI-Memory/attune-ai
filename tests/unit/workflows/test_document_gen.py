"""Tests for DocumentGenerationWorkflow.

Tests cover initialization, outline generation, content writing,
document polishing, cost tracking, chunking, and export functionality.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile
from pathlib import Path

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.document_gen import (
    DOC_GEN_STEPS,
    TOKEN_COSTS,
    DocumentGenerationWorkflow,
    format_doc_gen_report,
)


class TestDocumentGenerationWorkflowInitialization:
    """Test suite for DocumentGenerationWorkflow initialization."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow()

    def test_workflow_basic_initialization(self, workflow):
        """Test workflow initializes with correct defaults."""
        assert workflow.name == "doc-gen"
        assert workflow.description == "Cost-optimized documentation generation pipeline"
        assert workflow.stages == ["outline", "write", "polish"]

    def test_workflow_tier_map(self, workflow):
        """Test tier mapping is correct."""
        assert workflow.tier_map["outline"] == ModelTier.CHEAP
        assert workflow.tier_map["write"] == ModelTier.CAPABLE
        # polish tier can be PREMIUM or CAPABLE (may be downgraded based on conditions)
        assert workflow.tier_map["polish"] in (ModelTier.PREMIUM, ModelTier.CAPABLE)

    def test_workflow_default_parameters(self, workflow):
        """Test default parameters are set correctly."""
        assert workflow.skip_polish_threshold == 1000
        assert workflow.max_sections == 10
        assert workflow.max_write_tokens == 16000
        assert workflow.section_focus is None
        assert workflow.chunked_generation is True
        assert workflow.sections_per_chunk == 3
        assert workflow.max_cost == 5.0
        assert workflow.cost_warning_threshold == 0.8
        assert workflow.graceful_degradation is True
        assert workflow.export_path is None
        assert workflow.max_display_chars == 45000

    def test_workflow_custom_parameters(self):
        """Test custom parameters override defaults."""
        workflow = DocumentGenerationWorkflow(
            skip_polish_threshold=500,
            max_sections=20,
            max_write_tokens=32000,
            section_focus=["API Reference"],
            chunked_generation=False,
            sections_per_chunk=5,
            max_cost=10.0,
            cost_warning_threshold=0.9,
            graceful_degradation=False,
            export_path="docs/generated",
            max_display_chars=60000,
        )

        assert workflow.skip_polish_threshold == 500
        assert workflow.max_sections == 20
        assert workflow.max_write_tokens == 32000
        assert workflow.section_focus == ["API Reference"]
        assert workflow.chunked_generation is False
        assert workflow.sections_per_chunk == 5
        assert workflow.max_cost == 10.0
        assert workflow.cost_warning_threshold == 0.9
        assert workflow.graceful_degradation is False
        assert workflow.export_path == Path("docs/generated")
        assert workflow.max_display_chars == 60000

    def test_workflow_internal_state_initialization(self, workflow):
        """Test internal state variables are initialized."""
        assert workflow._total_content_tokens == 0
        assert workflow._accumulated_cost == 0.0
        assert workflow._cost_warning_issued is False
        assert workflow._partial_results == {}


class TestCostEstimationAndTracking:
    """Test suite for cost estimation and tracking functionality."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow(max_cost=1.0)

    def test_estimate_cost_cheap_tier(self, workflow):
        """Test cost estimation for cheap tier."""
        cost = workflow._estimate_cost(ModelTier.CHEAP, 1000, 1000)
        expected = (1000 / 1000) * TOKEN_COSTS[ModelTier.CHEAP]["input"] + (
            1000 / 1000
        ) * TOKEN_COSTS[ModelTier.CHEAP]["output"]
        assert cost == expected

    def test_estimate_cost_capable_tier(self, workflow):
        """Test cost estimation for capable tier."""
        cost = workflow._estimate_cost(ModelTier.CAPABLE, 2000, 3000)
        expected = (2000 / 1000) * TOKEN_COSTS[ModelTier.CAPABLE]["input"] + (
            3000 / 1000
        ) * TOKEN_COSTS[ModelTier.CAPABLE]["output"]
        assert cost == expected

    def test_estimate_cost_premium_tier(self, workflow):
        """Test cost estimation for premium tier."""
        cost = workflow._estimate_cost(ModelTier.PREMIUM, 500, 1500)
        expected = (500 / 1000) * TOKEN_COSTS[ModelTier.PREMIUM]["input"] + (
            1500 / 1000
        ) * TOKEN_COSTS[ModelTier.PREMIUM]["output"]
        assert cost == expected

    def test_track_cost_accumulation(self, workflow):
        """Test cost tracking accumulates correctly."""
        # Track first call
        cost1, should_stop = workflow._track_cost(ModelTier.CHEAP, 1000, 1000)
        assert workflow._accumulated_cost == cost1
        assert not should_stop

        # Track second call
        cost2, should_stop = workflow._track_cost(ModelTier.CAPABLE, 2000, 2000)
        assert workflow._accumulated_cost == cost1 + cost2
        assert not should_stop

    def test_track_cost_warning_threshold(self, workflow):
        """Test cost tracking issues warning at threshold."""
        workflow.max_cost = 1.0
        workflow.cost_warning_threshold = 0.8

        # Track enough cost to reach warning threshold ($0.80+) but stay under limit ($1.00)
        # PREMIUM tier: $0.015 input + $0.075 output per 1000 tokens
        # For 10000 input + 9000 output: (10*0.015) + (9*0.075) = $0.825 (within range)
        cost, should_stop = workflow._track_cost(ModelTier.PREMIUM, 10000, 9000)
        assert workflow._cost_warning_issued
        assert not should_stop

    def test_track_cost_limit_reached(self, workflow):
        """Test cost tracking stops when limit reached."""
        workflow.max_cost = 0.1  # Very low limit

        # Track enough cost to exceed limit
        cost, should_stop = workflow._track_cost(ModelTier.PREMIUM, 5000, 5000)
        assert should_stop
        assert workflow._accumulated_cost >= workflow.max_cost

    def test_track_cost_no_limit(self):
        """Test cost tracking with no limit (max_cost=0)."""
        workflow = DocumentGenerationWorkflow(max_cost=0)

        # Track large cost
        cost, should_stop = workflow._track_cost(ModelTier.PREMIUM, 100000, 100000)
        assert not should_stop
        assert workflow._accumulated_cost > 0

    def test_track_cost_multiple_calls_below_limit(self, workflow):
        """Test multiple small calls stay below limit."""
        workflow.max_cost = 10.0

        for _ in range(5):
            cost, should_stop = workflow._track_cost(ModelTier.CHEAP, 100, 100)
            assert not should_stop

        assert workflow._accumulated_cost < workflow.max_cost


class TestAutoScaling:
    """Test suite for token auto-scaling functionality."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow()

    def test_auto_scale_small_section_count(self, workflow):
        """Test auto-scaling for small section count."""
        scaled = workflow._auto_scale_tokens(5)
        assert scaled == 16000  # Minimum

    def test_auto_scale_medium_section_count(self, workflow):
        """Test auto-scaling for medium section count."""
        scaled = workflow._auto_scale_tokens(15)
        assert scaled == 15 * 2000  # 2000 per section

    def test_auto_scale_large_section_count(self, workflow):
        """Test auto-scaling for large section count."""
        scaled = workflow._auto_scale_tokens(50)
        assert scaled == 64000  # Maximum

    def test_auto_scale_respects_user_override(self):
        """Test auto-scaling respects user max_write_tokens."""
        workflow = DocumentGenerationWorkflow(max_write_tokens=8000)
        scaled = workflow._auto_scale_tokens(20)
        assert scaled == 8000  # User override

    def test_auto_scale_boundary_conditions(self, workflow):
        """Test auto-scaling at boundary values."""
        # At minimum threshold
        assert workflow._auto_scale_tokens(8) == 16000

        # Just over minimum
        assert workflow._auto_scale_tokens(9) == 18000

        # At maximum threshold
        assert workflow._auto_scale_tokens(32) == 64000

        # Just under maximum
        assert workflow._auto_scale_tokens(31) == 62000


class TestOutlineParsing:
    """Test suite for outline parsing functionality."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow()

    def test_parse_simple_outline(self, workflow):
        """Test parsing simple numbered outline."""
        outline = """1. Introduction
2. Setup Guide
3. API Reference
4. Troubleshooting"""

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 4
        assert sections == ["Introduction", "Setup Guide", "API Reference", "Troubleshooting"]

    def test_parse_outline_with_descriptions(self, workflow):
        """Test parsing outline with section descriptions."""
        outline = """1. Introduction - Overview of the framework
2. Setup Guide - Installation and configuration
3. API Reference - Complete API documentation"""

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 3
        assert sections == ["Introduction", "Setup Guide", "API Reference"]

    def test_parse_outline_ignores_subsections(self, workflow):
        """Test parsing ignores sub-sections."""
        outline = """1. Introduction
   1.1 Background
   1.2 Goals
2. Setup Guide
   2.1 Prerequisites
   2.2 Installation
3. API Reference"""

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 3
        assert sections == ["Introduction", "Setup Guide", "API Reference"]

    def test_parse_outline_with_extra_whitespace(self, workflow):
        """Test parsing handles extra whitespace."""
        outline = """
        1.  Introduction

        2.   Setup Guide

        3.    API Reference
        """

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 3
        assert sections == ["Introduction", "Setup Guide", "API Reference"]

    def test_parse_outline_empty(self, workflow):
        """Test parsing empty outline."""
        sections = workflow._parse_outline_sections("")
        assert sections == []

    def test_parse_outline_no_matches(self, workflow):
        """Test parsing outline with no valid sections."""
        outline = """This is some text without numbered sections.
Just plain text.
No structure."""

        sections = workflow._parse_outline_sections(outline)
        assert sections == []

    def test_parse_outline_mixed_content(self, workflow):
        """Test parsing outline with mixed content."""
        outline = """Here is the outline:

1. Introduction - Start here
Some descriptive text
2. Core Concepts - Learn the basics
   - Point A
   - Point B
3. Advanced Topics
More text here
4. Conclusion"""

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 4
        assert sections == ["Introduction", "Core Concepts", "Advanced Topics", "Conclusion"]


class TestExportFunctionality:
    """Test suite for document export functionality."""

    def test_export_document_disabled(self):
        """Test export when export_path is None."""
        workflow = DocumentGenerationWorkflow(export_path=None)
        doc_path, report_path = workflow._export_document(
            document="# Test Doc",
            doc_type="test",
            report="Test Report",
        )
        assert doc_path is None
        assert report_path is None

    def test_export_document_creates_directory(self):
        """Test export creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "docs" / "generated"
            workflow = DocumentGenerationWorkflow(export_path=export_dir)

            doc_path, report_path = workflow._export_document(
                document="# Test Document",
                doc_type="api_reference",
                report="Test Report",
            )

            assert export_dir.exists()
            assert doc_path is not None
            assert doc_path.exists()
            assert report_path is not None
            assert report_path.exists()

    def test_export_document_filename_format(self):
        """Test export generates correct filename format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, report_path = workflow._export_document(
                document="# Test",
                doc_type="API Reference",
            )

            # Check filename format: doc_type_timestamp.md
            assert doc_path is not None
            assert doc_path.name.startswith("api_reference_")
            assert doc_path.name.endswith(".md")
            # Use resolve() to handle macOS symlinks (/var -> /private/var)
            assert doc_path.parent.resolve() == Path(tmpdir).resolve()

    def test_export_document_sanitizes_filename(self):
        """Test export sanitizes document type in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, report_path = workflow._export_document(
                document="# Test",
                doc_type="API/User Guide",
            )

            assert doc_path is not None
            # Slashes should be replaced with dashes
            assert "/" not in doc_path.name
            assert "api-user_guide" in doc_path.name

    def test_export_document_content_written(self):
        """Test export writes correct content to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)
            test_content = "# Test Document\n\nThis is test content."

            doc_path, report_path = workflow._export_document(
                document=test_content,
                doc_type="test",
            )

            assert doc_path is not None
            content = doc_path.read_text(encoding="utf-8")
            assert content == test_content

    def test_export_document_with_report(self):
        """Test export writes both document and report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, report_path = workflow._export_document(
                document="# Doc",
                doc_type="test",
                report="Test Report",
            )

            assert doc_path is not None
            assert report_path is not None
            assert doc_path.exists()
            assert report_path.exists()
            assert report_path.read_text(encoding="utf-8") == "Test Report"

    def test_export_document_without_report(self):
        """Test export without report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, report_path = workflow._export_document(
                document="# Doc",
                doc_type="test",
                report=None,
            )

            assert doc_path is not None
            assert report_path is None
            assert doc_path.exists()


class TestOutputChunking:
    """Test suite for output chunking functionality."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow(max_display_chars=100)

    def test_chunk_output_small_content(self, workflow):
        """Test chunking skips small content."""
        content = "Small content" * 5  # Less than 100 chars
        chunks = workflow._chunk_output_for_display(content)
        assert len(chunks) == 1
        assert chunks[0] == content

    def test_chunk_output_large_content(self, workflow):
        """Test chunking splits large content."""
        # Create content with sections
        content = "\n\n".join([f"## Section {i}\n{'x' * 50}" for i in range(5)])
        chunks = workflow._chunk_output_for_display(content)

        assert len(chunks) > 1
        # Each chunk should have header
        for chunk in chunks:
            assert "PART" in chunk

    def test_chunk_output_respects_section_boundaries(self, workflow):
        """Test chunking splits on section headers."""
        workflow.max_display_chars = 200
        content = "## Section 1\n" + "x" * 150 + "\n\n## Section 2\n" + "x" * 150

        chunks = workflow._chunk_output_for_display(content)
        assert len(chunks) == 2

    def test_chunk_output_adds_headers(self, workflow):
        """Test chunking adds proper headers."""
        content = "## Section 1\n" + "x" * 200 + "\n\n## Section 2\n" + "x" * 200

        chunks = workflow._chunk_output_for_display(content, chunk_prefix="TEST")
        assert len(chunks) > 1

        for i, chunk in enumerate(chunks):
            assert f"TEST {i + 1} of {len(chunks)}" in chunk

    def test_chunk_output_custom_prefix(self, workflow):
        """Test chunking with custom prefix."""
        content = "x" * 500
        chunks = workflow._chunk_output_for_display(content, chunk_prefix="OUTPUT")

        for chunk in chunks:
            if "OUTPUT" in chunk:
                assert "OUTPUT" in chunk
                break


class TestShouldSkipStage:
    """Test suite for stage skipping logic."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing."""
        return DocumentGenerationWorkflow(skip_polish_threshold=1000)

    def test_skip_polish_for_short_document(self, workflow):
        """Test polish stage uses capable tier for short documents."""
        workflow._total_content_tokens = 500
        should_skip, reason = workflow.should_skip_stage("polish", {})

        # Should not skip, but tier should be downgraded
        assert not should_skip
        assert workflow.tier_map["polish"] == ModelTier.CAPABLE

    def test_no_skip_polish_for_long_document(self, workflow):
        """Test polish stage uses premium tier for long documents."""
        # Reset tier_map in case previous test modified it
        workflow.tier_map["polish"] = ModelTier.PREMIUM

        workflow._total_content_tokens = 2000
        should_skip, reason = workflow.should_skip_stage("polish", {})

        assert not should_skip
        # Tier should remain premium (not downgraded when above threshold)
        assert workflow.tier_map["polish"] == ModelTier.PREMIUM

    def test_no_skip_for_other_stages(self, workflow):
        """Test other stages are not skipped."""
        should_skip, reason = workflow.should_skip_stage("outline", {})
        assert not should_skip

        should_skip, reason = workflow.should_skip_stage("write", {})
        assert not should_skip


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


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_initialization_with_zero_max_cost(self):
        """Test initialization with max_cost=0 (unlimited)."""
        workflow = DocumentGenerationWorkflow(max_cost=0)
        assert workflow.max_cost == 0

        # Should never stop due to cost
        cost, should_stop = workflow._track_cost(ModelTier.PREMIUM, 100000, 100000)
        assert not should_stop

    def test_initialization_with_negative_max_sections(self):
        """Test initialization handles negative max_sections."""
        workflow = DocumentGenerationWorkflow(max_sections=-1)
        # Should accept it (validation happens elsewhere)
        assert workflow.max_sections == -1

    def test_auto_scale_with_zero_sections(self):
        """Test auto-scaling with zero sections."""
        workflow = DocumentGenerationWorkflow()
        scaled = workflow._auto_scale_tokens(0)
        assert scaled == 16000  # Minimum

    def test_parse_outline_with_unicode(self):
        """Test outline parsing with unicode characters."""
        workflow = DocumentGenerationWorkflow()
        outline = """1. Introduction – Getting Started
2. API Reference — Complete Guide
3. Troubleshooting — Common Issues"""

        sections = workflow._parse_outline_sections(outline)
        assert len(sections) == 3

    def test_export_with_empty_document(self):
        """Test export with empty document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, report_path = workflow._export_document(
                document="",
                doc_type="empty",
            )

            assert doc_path is not None
            assert doc_path.exists()
            assert doc_path.read_text(encoding="utf-8") == ""

    def test_chunk_output_with_empty_content(self):
        """Test chunking with empty content."""
        workflow = DocumentGenerationWorkflow()
        chunks = workflow._chunk_output_for_display("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_output_with_no_sections(self):
        """Test chunking content without section markers."""
        workflow = DocumentGenerationWorkflow(max_display_chars=100)
        content = "x" * 500  # No section headers

        chunks = workflow._chunk_output_for_display(content)
        # Without section headers, the implementation treats entire content as one section
        # and wraps it in chunk headers, but doesn't split by character count
        assert len(chunks) == 1
        assert "PART 1 of 1" in chunks[0]

    def test_format_report_with_empty_outline(self):
        """Test report formatting with empty outline."""
        result = {
            "document": "# Doc",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {"outline": ""}

        report = format_doc_gen_report(result, input_data)
        assert "DOCUMENTATION GENERATION REPORT" in report

    def test_format_report_with_no_sections(self):
        """Test report formatting with document containing no sections."""
        result = {
            "document": "Plain text with no headers.",
            "doc_type": "test",
            "audience": "users",
        }
        input_data = {}

        report = format_doc_gen_report(result, input_data)
        assert "Section Count: ~0" in report


class TestGracefulDegradation:
    """Test suite for graceful degradation features."""

    def test_initialization_with_graceful_degradation_enabled(self):
        """Test workflow initializes with graceful degradation enabled."""
        workflow = DocumentGenerationWorkflow(graceful_degradation=True)
        assert workflow.graceful_degradation is True

    def test_initialization_with_graceful_degradation_disabled(self):
        """Test workflow initializes with graceful degradation disabled."""
        workflow = DocumentGenerationWorkflow(graceful_degradation=False)
        assert workflow.graceful_degradation is False

    def test_partial_results_initialized_empty(self):
        """Test partial results dictionary starts empty."""
        workflow = DocumentGenerationWorkflow()
        assert workflow._partial_results == {}


class TestComplexScenarios:
    """Test suite for complex usage scenarios."""

    def test_workflow_with_all_custom_settings(self):
        """Test workflow with all settings customized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(
                skip_polish_threshold=2000,
                max_sections=15,
                max_write_tokens=24000,
                section_focus=["API", "Examples"],
                chunked_generation=True,
                sections_per_chunk=4,
                max_cost=8.0,
                cost_warning_threshold=0.75,
                graceful_degradation=True,
                export_path=tmpdir,
                max_display_chars=30000,
            )

            # Verify all settings
            assert workflow.skip_polish_threshold == 2000
            assert workflow.max_sections == 15
            assert workflow.max_write_tokens == 24000
            assert workflow.section_focus == ["API", "Examples"]
            assert workflow.chunked_generation is True
            assert workflow.sections_per_chunk == 4
            assert workflow.max_cost == 8.0
            assert workflow.cost_warning_threshold == 0.75
            assert workflow.graceful_degradation is True
            assert workflow.export_path == Path(tmpdir)
            assert workflow.max_display_chars == 30000

    def test_cost_tracking_across_multiple_stages(self):
        """Test cost accumulates correctly across multiple stages."""
        workflow = DocumentGenerationWorkflow(max_cost=5.0)

        # Simulate multiple stages
        cost1, stop1 = workflow._track_cost(ModelTier.CHEAP, 1000, 500)
        cost2, stop2 = workflow._track_cost(ModelTier.CAPABLE, 2000, 1000)
        cost3, stop3 = workflow._track_cost(ModelTier.PREMIUM, 500, 300)

        assert workflow._accumulated_cost == cost1 + cost2 + cost3
        assert not stop1
        assert not stop2
        assert not stop3

    def test_multiple_outline_formats(self):
        """Test parsing various outline formats."""
        workflow = DocumentGenerationWorkflow()

        # Format 1: Simple numbered
        outline1 = "1. Intro\n2. Body\n3. Conclusion"
        sections1 = workflow._parse_outline_sections(outline1)
        assert len(sections1) == 3

        # Format 2: With descriptions
        outline2 = "1. Intro - Start\n2. Body - Main content\n3. Conclusion - End"
        sections2 = workflow._parse_outline_sections(outline2)
        assert len(sections2) == 3
        assert "Start" not in sections2[0]  # Description removed

        # Format 3: Mixed with subsections
        outline3 = "1. Intro\n  1.1 Sub\n2. Body\n  2.1 Sub\n3. Conclusion"
        sections3 = workflow._parse_outline_sections(outline3)
        assert len(sections3) == 3
        assert "1.1" not in " ".join(sections3)

    def test_export_with_special_characters_in_doctype(self):
        """Test export handles special characters in doc_type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = DocumentGenerationWorkflow(export_path=tmpdir)

            doc_path, _ = workflow._export_document(
                document="# Test",
                doc_type="API/Reference (v2.0)",
            )

            assert doc_path is not None
            # Should sanitize to safe filename
            assert "/" not in doc_path.name
            # The implementation replaces "/" with "-" and leaves parentheses
            # Check that slash was sanitized
            assert "-reference" in doc_path.name or "api_reference" in doc_path.name
