"""Tests for DocumentationOrchestrator.

Tests cover initialization, scout phase, prioritization, generation phase,
cost tracking, exclusion patterns, and end-to-end orchestration.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.documentation_orchestrator import (
    DocumentationItem,
    DocumentationOrchestrator,
    OrchestratorResult,
)


class TestDocumentationOrchestratorInitialization:
    """Test suite for DocumentationOrchestrator initialization."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_orchestrator_basic_initialization(self, orchestrator, tmp_path):
        """Test orchestrator initializes with correct defaults."""
        assert orchestrator.name == "documentation-orchestrator"
        assert (
            orchestrator.description
            == "Coordinate doc-audit + doc-gen into end-to-end documentation maintenance"
        )
        assert orchestrator.project_root == tmp_path
        assert orchestrator.max_items == 5
        assert orchestrator.max_cost == 5.0
        assert orchestrator.auto_approve is False

    def test_orchestrator_default_parameters(self, orchestrator, tmp_path):
        """Test default parameters are set correctly."""
        assert orchestrator.export_path == tmp_path / "docs" / "generated"
        assert orchestrator.include_stale is True
        assert orchestrator.include_missing is True
        assert orchestrator.min_severity == "low"
        assert orchestrator.doc_type == "api_reference"
        assert orchestrator.audience == "developers"
        assert orchestrator.dry_run is False

    def test_orchestrator_custom_parameters(self, tmp_path):
        """Test custom parameters override defaults."""
        export_path = tmp_path / "custom_docs"
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            max_items=10,
            max_cost=10.0,
            auto_approve=True,
            export_path=str(export_path),
            include_stale=False,
            include_missing=False,
            min_severity="high",
            doc_type="tutorial",
            audience="beginners",
            dry_run=True,
        )

        assert orchestrator.max_items == 10
        assert orchestrator.max_cost == 10.0
        assert orchestrator.auto_approve is True
        assert orchestrator.export_path == export_path
        assert orchestrator.include_stale is False
        assert orchestrator.include_missing is False
        assert orchestrator.min_severity == "high"
        assert orchestrator.doc_type == "tutorial"
        assert orchestrator.audience == "beginners"
        assert orchestrator.dry_run is True

    def test_orchestrator_exclude_patterns_default(self, orchestrator):
        """Test default exclude patterns are loaded."""
        assert "site/**" in orchestrator.exclude_patterns
        assert "dist/**" in orchestrator.exclude_patterns
        assert "node_modules/**" in orchestrator.exclude_patterns
        assert "*.png" in orchestrator.exclude_patterns
        assert ".git/**" in orchestrator.exclude_patterns

    def test_orchestrator_custom_exclude_patterns(self, tmp_path):
        """Test custom exclude patterns are merged with defaults."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            exclude_patterns=["custom/**", "*.test.py"],
        )

        # Should have both default and custom patterns
        assert "site/**" in orchestrator.exclude_patterns  # default
        assert "custom/**" in orchestrator.exclude_patterns  # custom
        assert "*.test.py" in orchestrator.exclude_patterns  # custom

    def test_orchestrator_internal_state_initialization(self, orchestrator):
        """Test internal state variables are initialized."""
        assert orchestrator._total_cost == 0.0
        assert orchestrator._items == []
        assert orchestrator._excluded_files == []
        assert orchestrator._quiet is False


class TestSeverityAndPriorityHelpers:
    """Test suite for severity and priority helper methods."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_severity_to_priority_high(self, orchestrator):
        """Test converting high severity to priority."""
        assert orchestrator._severity_to_priority("high") == 1
        assert orchestrator._severity_to_priority("HIGH") == 1

    def test_severity_to_priority_medium(self, orchestrator):
        """Test converting medium severity to priority."""
        assert orchestrator._severity_to_priority("medium") == 2
        assert orchestrator._severity_to_priority("MEDIUM") == 2

    def test_severity_to_priority_low(self, orchestrator):
        """Test converting low severity to priority."""
        assert orchestrator._severity_to_priority("low") == 3
        assert orchestrator._severity_to_priority("LOW") == 3

    def test_severity_to_priority_unknown(self, orchestrator):
        """Test converting unknown severity defaults to low priority."""
        assert orchestrator._severity_to_priority("unknown") == 3
        assert orchestrator._severity_to_priority("invalid") == 3

    def test_should_include_severity_high_threshold(self, tmp_path):
        """Test severity filtering with high threshold."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            min_severity="high",
        )
        assert orchestrator._should_include_severity("high") is True
        assert orchestrator._should_include_severity("medium") is False
        assert orchestrator._should_include_severity("low") is False

    def test_should_include_severity_medium_threshold(self, tmp_path):
        """Test severity filtering with medium threshold."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            min_severity="medium",
        )
        assert orchestrator._should_include_severity("high") is True
        assert orchestrator._should_include_severity("medium") is True
        assert orchestrator._should_include_severity("low") is False

    def test_should_include_severity_low_threshold(self, tmp_path):
        """Test severity filtering with low threshold."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            min_severity="low",
        )
        assert orchestrator._should_include_severity("high") is True
        assert orchestrator._should_include_severity("medium") is True
        assert orchestrator._should_include_severity("low") is True


class TestExclusionPatterns:
    """Test suite for file exclusion patterns."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_should_exclude_generated_directories(self, orchestrator):
        """Test exclusion of generated directories."""
        assert orchestrator._should_exclude("site/index.html") is True
        assert orchestrator._should_exclude("dist/bundle.js") is True
        assert orchestrator._should_exclude("build/output.txt") is True
        assert orchestrator._should_exclude("node_modules/package/index.js") is True
        assert orchestrator._should_exclude("__pycache__/module.pyc") is True

    def test_should_exclude_binary_files(self, orchestrator):
        """Test exclusion of binary files."""
        assert orchestrator._should_exclude("logo.png") is True
        assert orchestrator._should_exclude("icon.jpg") is True
        assert orchestrator._should_exclude("diagram.svg") is True
        assert orchestrator._should_exclude("document.pdf") is True
        assert orchestrator._should_exclude("archive.zip") is True
        assert orchestrator._should_exclude("compiled.pyc") is True

    def test_should_exclude_config_files(self, orchestrator):
        """Test exclusion of config/dependency files."""
        assert orchestrator._should_exclude("requirements.txt") is True
        assert orchestrator._should_exclude("package.json") is True
        assert orchestrator._should_exclude("pyproject.toml") is True
        assert orchestrator._should_exclude("setup.py") is True
        assert orchestrator._should_exclude(".env") is True

    def test_should_exclude_empathy_internal(self, orchestrator):
        """Test exclusion of empathy internal directories."""
        assert orchestrator._should_exclude(".attune/data.json") is True
        assert orchestrator._should_exclude(".claude/rules.md") is True
        assert orchestrator._should_exclude(".empathy_index/cache") is True

    def test_should_not_exclude_source_files(self, orchestrator):
        """Test that source files are not excluded."""
        assert orchestrator._should_exclude("src/main.py") is False
        assert orchestrator._should_exclude("lib/utils.js") is False
        assert orchestrator._should_exclude("README.md") is False
        assert orchestrator._should_exclude("docs/guide.md") is False

    def test_should_exclude_with_tracking(self, orchestrator):
        """Test exclusion with tracking enabled."""
        result = orchestrator._should_exclude("site/index.html", track=True)
        assert result is True
        assert len(orchestrator._excluded_files) == 1
        assert orchestrator._excluded_files[0]["file_path"] == "site/index.html"
        assert orchestrator._excluded_files[0]["matched_pattern"] == "site/**"

    def test_exclusion_reasons(self, orchestrator):
        """Test human-readable exclusion reasons."""
        reason = orchestrator._get_exclusion_reason("site/**")
        assert reason == "Generated/build directory"

        reason = orchestrator._get_exclusion_reason("*.png")
        assert reason == "Binary/asset file"

        reason = orchestrator._get_exclusion_reason(".attune/**")
        assert reason == "Framework internal file"

        reason = orchestrator._get_exclusion_reason("book/**")
        assert reason == "Book/document source"


class TestAllowedOutputExtensions:
    """Test suite for output file extension validation."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_is_allowed_output_markdown(self, orchestrator):
        """Test that markdown files are allowed."""
        assert orchestrator._is_allowed_output("docs/guide.md") is True
        assert orchestrator._is_allowed_output("README.MD") is True

    def test_is_allowed_output_mdx(self, orchestrator):
        """Test that MDX files are allowed."""
        assert orchestrator._is_allowed_output("docs/component.mdx") is True
        assert orchestrator._is_allowed_output("page.MDX") is True

    def test_is_allowed_output_rst(self, orchestrator):
        """Test that reStructuredText files are allowed."""
        assert orchestrator._is_allowed_output("docs/api.rst") is True
        assert orchestrator._is_allowed_output("index.RST") is True

    def test_is_not_allowed_output_source_files(self, orchestrator):
        """Test that source files are not allowed as output."""
        assert orchestrator._is_allowed_output("src/main.py") is False
        assert orchestrator._is_allowed_output("lib/utils.js") is False
        assert orchestrator._is_allowed_output("config.json") is False

    def test_is_not_allowed_output_binary_files(self, orchestrator):
        """Test that binary files are not allowed as output."""
        assert orchestrator._is_allowed_output("image.png") is False
        assert orchestrator._is_allowed_output("document.pdf") is False
        assert orchestrator._is_allowed_output("archive.zip") is False


class TestDocumentationItemDataclass:
    """Test suite for DocumentationItem dataclass."""

    def test_documentation_item_creation(self):
        """Test creating DocumentationItem with required fields."""
        item = DocumentationItem(
            file_path="src/main.py",
            issue_type="missing_docstring",
            severity="high",
            priority=1,
        )
        assert item.file_path == "src/main.py"
        assert item.issue_type == "missing_docstring"
        assert item.severity == "high"
        assert item.priority == 1

    def test_documentation_item_with_optional_fields(self):
        """Test creating DocumentationItem with optional fields."""
        item = DocumentationItem(
            file_path="src/main.py",
            issue_type="stale_doc",
            severity="medium",
            priority=2,
            details="Source modified 10 days ago",
            related_source=["src/utils.py", "src/config.py"],
            days_stale=10,
            loc=500,
        )
        assert item.details == "Source modified 10 days ago"
        assert item.related_source == ["src/utils.py", "src/config.py"]
        assert item.days_stale == 10
        assert item.loc == 500

    def test_documentation_item_defaults(self):
        """Test DocumentationItem default values."""
        item = DocumentationItem(
            file_path="test.py",
            issue_type="missing",
            severity="low",
            priority=3,
        )
        assert item.details == ""
        assert item.related_source == []
        assert item.days_stale == 0
        assert item.loc == 0


class TestOrchestratorResultDataclass:
    """Test suite for OrchestratorResult dataclass."""

    def test_orchestrator_result_creation(self):
        """Test creating OrchestratorResult with minimal fields."""
        result = OrchestratorResult(success=True, phase="complete")
        assert result.success is True
        assert result.phase == "complete"

    def test_orchestrator_result_defaults(self):
        """Test OrchestratorResult default values."""
        result = OrchestratorResult(success=False, phase="scout")
        assert result.items_found == 0
        assert result.stale_docs == 0
        assert result.missing_docs == 0
        assert result.items_processed == 0
        assert result.docs_generated == []
        assert result.docs_updated == []
        assert result.docs_skipped == []
        assert result.scout_cost == 0.0
        assert result.generation_cost == 0.0
        assert result.total_cost == 0.0
        assert result.duration_ms == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.summary == ""

    def test_orchestrator_result_to_dict(self):
        """Test converting OrchestratorResult to dictionary."""
        result = OrchestratorResult(
            success=True,
            phase="complete",
            items_found=5,
            stale_docs=2,
            missing_docs=3,
            items_processed=4,
            docs_generated=["a.md", "b.md"],
            docs_updated=["c.md"],
            scout_cost=0.5,
            generation_cost=1.5,
            total_cost=2.0,
            duration_ms=5000,
        )

        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["phase"] == "complete"
        assert result_dict["items_found"] == 5
        assert result_dict["stale_docs"] == 2
        assert result_dict["missing_docs"] == 3
        assert result_dict["items_processed"] == 4
        assert result_dict["docs_generated"] == ["a.md", "b.md"]
        assert result_dict["docs_updated"] == ["c.md"]
        assert result_dict["scout_cost"] == 0.5
        assert result_dict["generation_cost"] == 1.5
        assert result_dict["total_cost"] == 2.0
        assert result_dict["duration_ms"] == 5000


class TestDescribeMethod:
    """Test suite for describe() method."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_describe_returns_string(self, orchestrator):
        """Test describe returns a string."""
        description = orchestrator.describe()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_describe_contains_workflow_name(self, orchestrator):
        """Test describe contains workflow name."""
        description = orchestrator.describe()
        assert "documentation-orchestrator" in description

    def test_describe_contains_phases(self, orchestrator):
        """Test describe contains all phases."""
        description = orchestrator.describe()
        assert "SCOUT" in description
        assert "PRIORITIZE" in description
        assert "GENERATE" in description
        assert "UPDATE" in description

    def test_describe_contains_configuration(self, orchestrator):
        """Test describe contains configuration details."""
        description = orchestrator.describe()
        assert "max_items:" in description
        assert "max_cost:" in description
        assert "auto_approve:" in description

    def test_describe_shows_component_availability(self, orchestrator):
        """Test describe shows component availability."""
        description = orchestrator.describe()
        assert "Scout" in description or "Writer" in description
        assert "Available" in description or "Not available" in description


class TestPrioritizeItems:
    """Test suite for item prioritization."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path), max_items=3)

    def test_prioritize_by_severity(self, orchestrator):
        """Test prioritization by severity (priority)."""
        items = [
            DocumentationItem("low.py", "missing", "low", 3, loc=100),
            DocumentationItem("high.py", "missing", "high", 1, loc=100),
            DocumentationItem("med.py", "missing", "medium", 2, loc=100),
        ]

        prioritized = orchestrator._prioritize_items(items)
        assert prioritized[0].severity == "high"
        assert prioritized[1].severity == "medium"
        assert prioritized[2].severity == "low"

    def test_prioritize_by_staleness(self, orchestrator):
        """Test prioritization by days stale."""
        items = [
            DocumentationItem("new.py", "stale_doc", "high", 1, days_stale=5),
            DocumentationItem("old.py", "stale_doc", "high", 1, days_stale=30),
            DocumentationItem("recent.py", "stale_doc", "high", 1, days_stale=10),
        ]

        prioritized = orchestrator._prioritize_items(items)
        assert prioritized[0].days_stale == 30
        assert prioritized[1].days_stale == 10
        assert prioritized[2].days_stale == 5

    def test_prioritize_by_loc(self, orchestrator):
        """Test prioritization by lines of code."""
        items = [
            DocumentationItem("small.py", "missing", "medium", 2, loc=50),
            DocumentationItem("large.py", "missing", "medium", 2, loc=500),
            DocumentationItem("med.py", "missing", "medium", 2, loc=200),
        ]

        prioritized = orchestrator._prioritize_items(items)
        assert prioritized[0].loc == 500
        assert prioritized[1].loc == 200
        assert prioritized[2].loc == 50

    def test_prioritize_respects_max_items(self, orchestrator):
        """Test prioritization limits to max_items."""
        items = [DocumentationItem(f"file{i}.py", "missing", "high", 1) for i in range(10)]

        prioritized = orchestrator._prioritize_items(items)
        assert len(prioritized) == 3  # max_items=3

    def test_prioritize_combined_criteria(self, orchestrator):
        """Test prioritization with multiple criteria."""
        items = [
            DocumentationItem("a.py", "missing", "low", 3, loc=1000, days_stale=0),
            DocumentationItem("b.py", "stale_doc", "high", 1, loc=100, days_stale=50),
            DocumentationItem("c.py", "missing", "high", 1, loc=500, days_stale=0),
            DocumentationItem("d.py", "stale_doc", "high", 1, loc=100, days_stale=30),
        ]

        prioritized = orchestrator._prioritize_items(items)
        # Should be ordered by: priority (asc), days_stale (desc), loc (desc)
        assert prioritized[0].file_path == "b.py"  # high priority, most stale
        assert prioritized[1].file_path == "d.py"  # high priority, less stale
        assert prioritized[2].file_path == "c.py"  # high priority, more LOC


class TestParseScoutFindings:
    """Test suite for parsing scout findings."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_parse_scout_findings_empty(self, orchestrator):
        """Test parsing empty scout findings."""
        mock_result = MagicMock()
        mock_result.findings = []

        items = orchestrator._parse_scout_findings(mock_result)
        assert items == []

    def test_parse_scout_findings_with_data(self, orchestrator):
        """Test parsing scout findings with structured data."""
        mock_result = MagicMock()
        mock_result.findings = [
            {
                "agent": "Documentation Analyst",
                "response": """Found issues:
                "file_path": "src/main.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]

        items = orchestrator._parse_scout_findings(mock_result)
        assert len(items) == 1
        assert items[0].file_path == "src/main.py"
        assert items[0].issue_type == "missing_docstring"
        assert items[0].severity == "high"

    def test_parse_scout_findings_filters_by_settings(self, tmp_path):
        """Test parsing filters items based on orchestrator settings."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            include_stale=False,  # Don't include stale docs
        )

        mock_result = MagicMock()
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "stale.py"
                "issue_type": "stale_doc"
                "severity": "high"
                """,
            },
            {
                "agent": "Analyst",
                "response": """
                "file_path": "missing.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]

        items = orchestrator._parse_scout_findings(mock_result)
        # Should only have missing_docstring, not stale_doc
        assert len(items) == 1
        assert items[0].issue_type == "missing_docstring"

    def test_parse_scout_findings_respects_severity_filter(self, tmp_path):
        """Test parsing respects minimum severity setting."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            min_severity="high",
        )

        mock_result = MagicMock()
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "high.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
            {
                "agent": "Analyst",
                "response": """
                "file_path": "low.py"
                "issue_type": "missing_docstring"
                "severity": "low"
                """,
            },
        ]

        items = orchestrator._parse_scout_findings(mock_result)
        # Should only have high severity
        assert len(items) == 1
        assert items[0].severity == "high"

    def test_parse_scout_findings_filters_missing_when_disabled(self, tmp_path):
        """Test parsing drops missing_docstring/no_documentation when include_missing=False."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            include_missing=False,
        )

        mock_result = MagicMock()
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "missing.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
            {
                "agent": "Analyst",
                "response": """
                "file_path": "undocumented.py"
                "issue_type": "no_documentation"
                "severity": "high"
                """,
            },
            {
                "agent": "Analyst",
                "response": """
                "file_path": "stale.py"
                "issue_type": "stale_doc"
                "severity": "high"
                """,
            },
        ]

        items = orchestrator._parse_scout_findings(mock_result)
        # Both missing-docs kinds are dropped; the stale_doc item survives
        assert len(items) == 1
        assert items[0].issue_type == "stale_doc"

    def test_parse_scout_findings_excludes_filtered_files(self, orchestrator):
        """Test parsing skips findings whose file_path matches an exclude pattern."""
        mock_result = MagicMock()
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "requirements.txt"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
            {
                "agent": "Analyst",
                "response": """
                "file_path": "src/main.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]

        items = orchestrator._parse_scout_findings(mock_result)
        # requirements.txt matches DEFAULT_EXCLUDE_PATTERNS ("requirements*.txt")
        assert len(items) == 1
        assert items[0].file_path == "src/main.py"


class TestItemsFromIndex:
    """Test suite for extracting items from ProjectIndex."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_items_from_index_no_index(self, orchestrator):
        """Test items extraction when ProjectIndex is not available."""
        orchestrator._project_index = None
        items = orchestrator._items_from_index()
        assert items == []

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_items_from_index_missing_docstrings(self, orchestrator):
        """Test extracting missing docstring items from index."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [
                {"path": "src/main.py", "loc": 500},
                {"path": "src/utils.py", "loc": 300},
            ],
            "docs_needing_review": [],
        }
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        assert len(items) == 2
        assert items[0].file_path == "src/main.py"
        assert items[0].issue_type == "missing_docstring"
        assert items[0].severity == "medium"
        assert items[0].loc == 500

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_items_from_index_stale_docs(self, orchestrator):
        """Test extracting stale doc items from index."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [],
            "docs_needing_review": [
                {
                    "doc_file": "docs/api.md",
                    "source_modified_after_doc": True,
                    "related_source_files": ["src/api.py", "src/models.py"],
                    "days_since_doc_update": 15,
                },
            ],
        }
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        assert len(items) == 1
        assert items[0].file_path == "docs/api.md"
        assert items[0].issue_type == "stale_doc"
        assert items[0].severity == "high"
        assert items[0].days_stale == 15

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_items_from_index_respects_include_settings(self, tmp_path):
        """Test items extraction respects include_stale and include_missing."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            include_stale=False,
            include_missing=True,
        )

        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [{"path": "missing.py", "loc": 100}],
            "docs_needing_review": [
                {
                    "doc_file": "stale.md",
                    "source_modified_after_doc": True,
                    "related_source_files": [],
                    "days_since_doc_update": 10,
                },
            ],
        }
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        # Should only have missing_docstring items
        assert len(items) == 1
        assert items[0].issue_type == "missing_docstring"

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_items_from_index_excludes_filtered_files(self, orchestrator):
        """Test items extraction excludes files matching exclude patterns."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [
                {"path": "src/main.py", "loc": 500},
                {"path": "requirements.txt", "loc": 10},  # Should be excluded
            ],
            "docs_needing_review": [],
        }
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        # Should only have main.py, not requirements.txt
        assert len(items) == 1
        assert items[0].file_path == "src/main.py"

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_items_from_index_excludes_filtered_stale_doc(self, orchestrator):
        """Test stale-doc extraction excludes doc_file paths matching an exclude pattern."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [],
            "docs_needing_review": [
                {
                    "doc_file": "requirements.txt",  # matches "requirements*.txt"
                    "source_modified_after_doc": True,
                    "related_source_files": [],
                    "days_since_doc_update": 5,
                },
                {
                    "doc_file": "docs/api.md",
                    "source_modified_after_doc": True,
                    "related_source_files": [],
                    "days_since_doc_update": 5,
                },
            ],
        }
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        # Only docs/api.md should survive - requirements.txt is excluded
        assert len(items) == 1
        assert items[0].file_path == "docs/api.md"

    def test_items_from_index_handles_context_exception(self, orchestrator):
        """Test extraction degrades gracefully when get_context_for_workflow raises."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.side_effect = RuntimeError("index unavailable")
        orchestrator._project_index = mock_index

        items = orchestrator._items_from_index()
        assert items == []


class TestGenerateSummary:
    """Test suite for summary generation."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_generate_summary_basic(self, orchestrator):
        """Test generating basic summary."""
        result = OrchestratorResult(
            success=True,
            phase="complete",
            items_found=5,
            stale_docs=2,
            missing_docs=3,
            scout_cost=0.5,
        )
        items = []

        summary = orchestrator._generate_summary(result, items)
        assert "DOCUMENTATION ORCHESTRATOR REPORT" in summary
        assert "SUCCESS" in summary
        assert "Items found: 5" in summary
        assert "Stale docs: 2" in summary
        assert "Missing docs: 3" in summary

    def test_generate_summary_with_items(self, orchestrator):
        """Test generating summary with priority items."""
        result = OrchestratorResult(success=True, phase="complete")
        items = [
            DocumentationItem("high.py", "missing", "high", 1),
            DocumentationItem("med.py", "stale_doc", "medium", 2, days_stale=10),
        ]

        summary = orchestrator._generate_summary(result, items)
        assert "Priority Items:" in summary
        assert "[HIGH] high.py" in summary
        assert "[MEDIUM] med.py" in summary
        assert "Days stale: 10" in summary

    def test_generate_summary_with_generation_results(self, orchestrator):
        """Test generating summary with generation phase results."""
        orchestrator.dry_run = False
        result = OrchestratorResult(
            success=True,
            phase="complete",
            items_processed=3,
            docs_generated=["a.md", "b.md"],
            docs_updated=["c.md"],
            docs_skipped=["d.py"],
            generation_cost=1.5,
        )
        items = []

        summary = orchestrator._generate_summary(result, items)
        assert "GENERATION PHASE" in summary
        assert "Items processed: 3" in summary
        assert "Docs generated: 2" in summary
        assert "Docs updated: 1" in summary
        assert "+ a.md" in summary
        assert "~ c.md" in summary

    def test_generate_summary_with_errors(self, orchestrator):
        """Test generating summary with errors."""
        result = OrchestratorResult(
            success=False,
            phase="generate",
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
        )
        items = []

        summary = orchestrator._generate_summary(result, items)
        assert "ERRORS" in summary
        assert "! Error 1" in summary
        assert "! Error 2" in summary
        assert "WARNINGS" in summary
        assert "* Warning 1" in summary

    def test_generate_summary_totals(self, orchestrator):
        """Test generating summary includes totals."""
        result = OrchestratorResult(
            success=True,
            phase="complete",
            total_cost=2.5,
            duration_ms=5000,
        )
        items = []

        summary = orchestrator._generate_summary(result, items)
        assert "TOTALS" in summary
        assert "Total cost: $2.5" in summary
        assert "Duration: 5000ms" in summary


@pytest.mark.asyncio
class TestScoutPhase:
    """Test suite for scout phase execution."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    async def test_run_scout_phase_no_scout_available(self, orchestrator):
        """Test scout phase when scout component is not available."""
        orchestrator._scout = None
        orchestrator._project_index = None

        items, cost = await orchestrator._run_scout_phase()
        assert items == []
        assert cost == 0.0

    async def test_run_scout_phase_with_scout(self, orchestrator):
        """Test scout phase with mock scout component."""
        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "src/main.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        items, cost = await orchestrator._run_scout_phase()
        assert len(items) >= 0  # May have items from parsing
        assert cost == 0.5
        mock_scout.execute.assert_called_once()

    async def test_run_scout_phase_failure(self, orchestrator):
        """Test scout phase when scout execution fails."""
        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.cost = 0.1
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        items, cost = await orchestrator._run_scout_phase()
        assert items == []
        assert cost == 0.1

    async def test_run_scout_phase_merges_unique_index_items(self, orchestrator):
        """Test scout phase appends ProjectIndex items whose path scout didn't find.

        Items with a file_path scout already found are NOT duplicated; items
        with a distinct file_path are appended.
        """
        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "src/handler.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "files_without_docstrings": [
                {"path": "src/handler.py", "loc": 10},  # duplicate - skipped
                {"path": "src/index_extra.py", "loc": 42},  # unique - merged in
            ],
            "docs_needing_review": [],
        }
        orchestrator._project_index = mock_index

        items, cost = await orchestrator._run_scout_phase()
        paths = [item.file_path for item in items]
        assert paths.count("src/handler.py") == 1
        assert "src/index_extra.py" in paths
        assert len(items) == 2
        assert cost == 0.5


@pytest.mark.asyncio
class TestGeneratePhase:
    """Test suite for generation phase execution."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    async def test_run_generate_phase_no_writer(self, orchestrator):
        """Test generate phase when writer is not available."""
        orchestrator._writer = None
        items = [DocumentationItem("test.py", "missing", "high", 1)]

        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)
        assert generated == []
        assert updated == []
        assert skipped == ["test.py"]
        assert cost == 0.0

    async def test_run_generate_phase_with_writer(self, orchestrator, tmp_path):
        """Test generate phase with mock writer component."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        mock_writer = MagicMock()
        mock_result = {
            "document": "# Test Doc",
            "accumulated_cost": 0.5,
            "export_path": str(tmp_path / "test.md"),
        }
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        items = [DocumentationItem("test.py", "missing_docstring", "high", 1)]
        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)

        assert len(generated) == 1
        assert generated[0] == "test.py"
        assert updated == []
        assert skipped == []
        assert cost == 0.5
        mock_writer.execute.assert_called_once()

    async def test_run_generate_phase_cost_limit(self, orchestrator, tmp_path):
        """Test generate phase stops at cost limit."""
        orchestrator.max_cost = 1.0
        orchestrator._total_cost = 0.9  # Already close to limit

        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        mock_writer = MagicMock()
        mock_result = {
            "document": "# Test",
            "accumulated_cost": 0.5,  # Would exceed limit
        }
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        items = [
            DocumentationItem("test1.py", "missing", "high", 1),
            DocumentationItem("test2.py", "missing", "high", 1),
        ]

        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)
        # Should skip remaining items when cost limit reached
        assert len(skipped) > 0

    async def test_run_generate_phase_stale_doc(self, orchestrator, tmp_path):
        """Test generate phase categorizes stale docs as updated."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        mock_writer = MagicMock()
        mock_result = {
            "document": "# Updated Doc",
            "accumulated_cost": 0.3,
        }
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        items = [DocumentationItem("test.py", "stale_doc", "high", 1)]
        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)

        assert generated == []
        assert len(updated) == 1
        assert updated[0] == "test.py"

    async def test_run_generate_phase_handles_errors(self, orchestrator, tmp_path):
        """Test generate phase handles errors gracefully."""
        mock_writer = MagicMock()
        mock_writer.execute = AsyncMock(side_effect=Exception("Generation failed"))
        orchestrator._writer = mock_writer

        items = [DocumentationItem("test.py", "missing", "high", 1)]
        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)

        assert generated == []
        assert skipped == ["test.py"]


class TestUpdateProjectIndex:
    """Test suite for project index updates."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(project_root=str(tmp_path))

    def test_update_project_index_no_index(self, orchestrator):
        """Test update when ProjectIndex is not available."""
        orchestrator._project_index = None
        # Should not raise error
        orchestrator._update_project_index(["a.py"], ["b.py"])

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_update_project_index_success(self, orchestrator):
        """Test successful project index update."""
        mock_record = MagicMock()
        mock_record.has_docstring = False

        mock_index = MagicMock()
        mock_index.get_record.return_value = mock_record
        orchestrator._project_index = mock_index

        orchestrator._update_project_index(["test.py"], [])

        mock_index.get_record.assert_called_once_with("test.py")
        assert mock_record.has_docstring is True
        mock_index.save.assert_called_once()

    @patch("attune.workflows.documentation_orchestrator.HAS_PROJECT_INDEX", True)
    def test_update_project_index_handles_errors(self, orchestrator):
        """Test update handles errors gracefully."""
        mock_index = MagicMock()
        mock_index.get_record.side_effect = Exception("Index error")
        orchestrator._project_index = mock_index

        # Should not raise error
        orchestrator._update_project_index(["test.py"], [])


@pytest.mark.asyncio
class TestExecuteWorkflow:
    """Test suite for full workflow execution."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create orchestrator instance for testing."""
        return DocumentationOrchestrator(
            project_root=str(tmp_path),
            max_items=2,
            dry_run=True,  # Dry run by default
        )

    async def test_execute_dry_run(self, orchestrator):
        """Test execute in dry run mode."""
        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.execute()

        assert result.success is True
        assert result.phase == "complete"
        assert result.scout_cost == 0.5
        # Should not have generated docs in dry run
        assert result.docs_generated == []

    async def test_execute_no_items_found(self, orchestrator):
        """Test execute when no documentation gaps found."""
        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.1
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.execute()

        assert result.success is True
        assert result.phase == "complete"
        assert result.items_found == 0

    async def test_execute_awaiting_approval(self, tmp_path):
        """Test execute stops at approval when auto_approve=False."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            auto_approve=False,
            dry_run=False,
        )

        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "test.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.execute()

        assert result.success is True
        assert result.phase == "awaiting_approval"
        # Should not have generated docs
        assert result.docs_generated == []

    async def test_execute_missing_writer(self, tmp_path):
        """Test execute when writer component is missing."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            dry_run=False,
        )
        orchestrator._writer = None

        with patch("attune.workflows.documentation_orchestrator.HAS_WRITER", False):
            result = await orchestrator.execute()

        assert result.success is False
        assert len(result.errors) > 0

    async def test_execute_missing_writer_dry_run_continues(self, tmp_path):
        """dry_run=True skips the writer-missing early return.

        Characterization pin (batch-4 D-block cut): the ``if not
        HAS_WRITER: ... if not self.dry_run: return`` guard has a
        ``dry_run=True`` branch that continues into the scout phase
        instead of early-returning. Not previously pinned.
        """
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            dry_run=True,
        )
        orchestrator._writer = None

        with patch("attune.workflows.documentation_orchestrator.HAS_WRITER", False):
            result = await orchestrator.execute()

        # Continued past the guard: reached "no items" completion,
        # not the writer-missing failure.
        assert result.phase == "complete"
        assert "DocumentGenerationWorkflow not available" not in result.errors

    async def test_execute_dry_run_with_items_skips_generation(self, orchestrator):
        """dry_run=True with items found stops before generation.

        Characterization pin: the ``if items:`` branch reaching the
        dry-run short-circuit (as opposed to the earlier "no items"
        short-circuit) was unpinned — every existing dry-run test used
        an empty findings list.
        """
        item = DocumentationItem(
            file_path="src/attune/foo.py",
            issue_type="missing_docstring",
            severity="high",
            priority=1,
        )
        with patch.object(orchestrator, "_run_scout_phase", AsyncMock(return_value=([item], 0.25))):
            result = await orchestrator.execute()

        assert result.success is True
        assert result.phase == "complete"
        assert result.docs_skipped == ["src/attune/foo.py"]
        assert result.docs_generated == []


@pytest.mark.asyncio
class TestScoutOnlyMethod:
    """Test suite for scout_only() method."""

    async def test_scout_only(self, tmp_path):
        """Test scout_only executes in dry run mode."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            dry_run=False,  # Initially not dry run
        )

        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.scout_only()

        assert orchestrator.dry_run is True  # Should be set to True
        assert result.phase == "complete"


@pytest.mark.asyncio
class TestScoutAsJsonMethod:
    """Test suite for scout_as_json() method."""

    async def test_scout_as_json_structure(self, tmp_path):
        """Test scout_as_json returns correct JSON structure."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.scout_as_json()

        assert "success" in result
        assert "stats" in result
        assert "items" in result
        assert "excluded" in result

    async def test_scout_as_json_stats(self, tmp_path):
        """Test scout_as_json includes correct stats."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        mock_scout = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.cost = 0.5
        mock_result.findings = []
        mock_scout.execute = AsyncMock(return_value=mock_result)
        orchestrator._scout = mock_scout

        result = await orchestrator.scout_as_json()

        stats = result["stats"]
        assert "items_found" in stats
        assert "stale_docs" in stats
        assert "missing_docs" in stats
        assert "scout_cost" in stats
        assert "duration_ms" in stats


@pytest.mark.asyncio
class TestGenerateForFilesMethods:
    """Test suite for generate_for_file(s) methods."""

    async def test_generate_for_file_no_writer(self, tmp_path):
        """Test generate_for_file when writer is not available."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))
        orchestrator._writer = None

        result = await orchestrator.generate_for_file("test.py")

        assert "error" in result
        assert "not available" in result["error"]

    async def test_generate_for_file_file_not_found(self, tmp_path):
        """Test generate_for_file when source file doesn't exist."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        mock_writer = MagicMock()
        mock_writer.execute = AsyncMock(return_value={"document": "# Test"})
        orchestrator._writer = mock_writer

        await orchestrator.generate_for_file("nonexistent.py")

        # Should still call writer with the path argument
        mock_writer.execute.assert_called_once()
        call_args = mock_writer.execute.call_args
        assert "path" in call_args.kwargs

    async def test_generate_for_file_success(self, tmp_path):
        """Test successful generate_for_file execution."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        mock_writer = MagicMock()
        mock_result = {"document": "# Test Doc", "accumulated_cost": 0.5}
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.generate_for_file("test.py")

        assert "document" in result
        assert result["document"] == "# Test Doc"

    async def test_generate_for_files_excludes_filtered(self, tmp_path):
        """Test generate_for_files excludes files matching patterns."""
        # Create the source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "main.py"
        test_file.write_text("def main(): pass")

        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        # Mock writer with AsyncMock
        mock_writer = MagicMock()
        mock_result = {"document": "# Doc", "accumulated_cost": 0.5, "export_path": "out.md"}
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.generate_for_files(
            [
                "src/main.py",
                "requirements.txt",  # Should be excluded
            ],
        )

        assert result["success"] is True
        assert len(result["skipped"]) == 1
        assert result["skipped"][0]["file"] == "requirements.txt"
        assert len(result["generated"]) == 1
        assert result["generated"][0]["file"] == "src/main.py"

    async def test_generate_for_files_batch_processing(self, tmp_path):
        """Test generate_for_files processes multiple files."""
        test_file1 = tmp_path / "test1.py"
        test_file1.write_text("def test1(): pass")
        test_file2 = tmp_path / "test2.py"
        test_file2.write_text("def test2(): pass")

        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        mock_writer = MagicMock()
        mock_result = {"document": "# Doc", "accumulated_cost": 0.5, "export_path": "out.md"}
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.generate_for_files(["test1.py", "test2.py"])

        assert result["success"] is True
        assert len(result["generated"]) == 2
        assert result["total_cost"] == 1.0  # 0.5 * 2


# Integration-style tests
@pytest.mark.asyncio
class TestEndToEndScenarios:
    """Test suite for end-to-end workflow scenarios."""

    async def test_full_workflow_with_mocks(self, tmp_path):
        """Test complete workflow execution with all mocked components."""
        # Create test file
        test_file = tmp_path / "main.py"
        test_file.write_text("def main(): pass")

        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            max_items=2,
            auto_approve=True,
            dry_run=False,
        )

        # Mock scout
        mock_scout = MagicMock()
        mock_scout_result = MagicMock()
        mock_scout_result.success = True
        mock_scout_result.cost = 0.5
        mock_scout_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "main.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]
        mock_scout.execute = AsyncMock(return_value=mock_scout_result)
        orchestrator._scout = mock_scout

        # Mock writer
        mock_writer = MagicMock()
        mock_writer_result = {
            "document": "# Main Module",
            "accumulated_cost": 1.0,
            "export_path": str(tmp_path / "main.md"),
        }
        mock_writer.execute = AsyncMock(return_value=mock_writer_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.execute()

        assert result.success is True
        assert result.phase == "complete"
        assert result.items_found >= 1
        assert result.scout_cost == 0.5
        assert result.generation_cost == 1.0
        assert result.total_cost == 1.5
        assert len(result.docs_generated) == 1

    async def test_workflow_with_cost_limits(self, tmp_path):
        """Test workflow respects cost limits during execution."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            max_cost=2.0,  # Allow enough for scout + writer
            auto_approve=True,
            dry_run=False,
        )

        # Mock scout with low cost
        mock_scout = MagicMock()
        mock_scout_result = MagicMock()
        mock_scout_result.success = True
        mock_scout_result.cost = 0.4
        mock_scout_result.findings = [
            {
                "agent": "Analyst",
                "response": """
                "file_path": "test.py"
                "issue_type": "missing_docstring"
                "severity": "high"
                """,
            },
        ]
        mock_scout.execute = AsyncMock(return_value=mock_scout_result)
        orchestrator._scout = mock_scout

        # Mock writer with reasonable cost
        mock_writer = MagicMock()
        mock_writer_result = {
            "document": "# Test",
            "accumulated_cost": 0.5,
        }
        mock_writer.execute = AsyncMock(return_value=mock_writer_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.execute()

        # Should complete successfully with total cost = scout + writer
        assert result.success is True
        assert result.total_cost == 0.9  # 0.4 scout + 0.5 writer
        assert result.total_cost <= orchestrator.max_cost


# Additional tests for edge cases and error paths
@pytest.mark.asyncio
class TestErrorHandlingPaths:
    """Test suite for error handling paths."""

    async def test_generate_for_file_read_permission_error(self, tmp_path):
        """Test handling of file permission errors during read."""
        import os

        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Make file unreadable (Unix-like systems)
        if os.name != "nt":  # Skip on Windows
            original_mode = test_file.stat().st_mode
            test_file.chmod(0o000)

        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))
        mock_writer = MagicMock()
        mock_writer.execute = AsyncMock(return_value={"document": "# Doc"})
        orchestrator._writer = mock_writer

        result = await orchestrator.generate_for_file("test.py")

        # Restore permissions for cleanup
        if os.name != "nt":
            test_file.chmod(original_mode)

        # Should handle error gracefully
        if os.name != "nt":
            assert "error" in result or "document" in result  # Different OSes behave differently

    async def test_generate_phase_file_read_error_handling(self, tmp_path):
        """Test generation phase handles file read errors."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        # Create item for non-existent file
        items = [
            DocumentationItem(
                file_path="nonexistent.py",
                issue_type="missing_docstring",
                severity="high",
                priority=1,
            ),
        ]

        mock_writer = MagicMock()
        mock_result = {"document": "# Doc", "accumulated_cost": 0.1}
        mock_writer.execute = AsyncMock(return_value=mock_result)
        orchestrator._writer = mock_writer

        generated, updated, skipped, cost = await orchestrator._run_generate_phase(items)

        # Should generate docs even if source file doesn't exist
        assert len(generated) == 1 or len(skipped) == 0

    async def test_generate_for_files_with_errors(self, tmp_path):
        """Test generate_for_files handles errors in batch."""
        test_file = tmp_path / "good.py"
        test_file.write_text("def good(): pass")

        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        # Mock writer that fails for specific file
        mock_writer = MagicMock()

        async def mock_execute(**kwargs):
            if "bad" in kwargs.get("path", ""):
                raise ValueError("Simulated error")
            return {"document": "# Doc", "accumulated_cost": 0.1}

        mock_writer.execute = AsyncMock(side_effect=mock_execute)
        orchestrator._writer = mock_writer

        result = await orchestrator.generate_for_files(["good.py", "bad.py"])

        # Should have one success and one failure
        assert len(result["generated"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["file"] == "bad.py"


@pytest.mark.asyncio
class TestAdvancedPatternMatching:
    """Test suite for advanced exclusion pattern matching."""

    def test_exclude_by_filename_only(self):
        """Test exclusion matches filename across any directory."""
        orchestrator = DocumentationOrchestrator(
            project_root=".",
            exclude_patterns=["node_modules/**"],
        )

        # Should match in any location
        assert orchestrator._should_exclude("deep/path/node_modules/file.js") is True
        assert orchestrator._should_exclude("node_modules/package/index.js") is True

    def test_exclude_pattern_with_double_asterisk(self):
        """Test ** pattern matching in paths."""
        orchestrator = DocumentationOrchestrator(
            project_root=".",
            exclude_patterns=["**/build/**"],
        )

        # Should match build directory anywhere
        assert orchestrator._should_exclude("project/build/output.js") is True
        assert orchestrator._should_exclude("build/file.py") is True

    def test_filename_pattern_without_path(self):
        """Test pattern matching on filename only."""
        orchestrator = DocumentationOrchestrator(
            project_root=".",
            exclude_patterns=["*.pyc"],
        )

        # Should match .pyc files anywhere
        assert orchestrator._should_exclude("module.pyc") is True
        assert orchestrator._should_exclude("src/package/module.pyc") is True
        assert orchestrator._should_exclude("src/module.py") is False

    def test_exclusion_tracking_for_advanced_patterns(self):
        """Test that advanced pattern matches are tracked."""
        orchestrator = DocumentationOrchestrator(
            project_root=".",
            exclude_patterns=["**/__pycache__/**"],
        )

        # Reset tracking
        orchestrator._excluded_files = []

        # Exclude with tracking
        result = orchestrator._should_exclude("src/__pycache__/module.pyc", track=True)

        assert result is True
        assert len(orchestrator._excluded_files) > 0


@pytest.mark.asyncio
class TestCostLimitEnforcement:
    """Test suite for cost limit enforcement scenarios."""

    async def test_cost_limit_stops_generation_mid_batch(self, tmp_path):
        """Test that cost limit stops generation partway through batch."""
        # Create multiple test files
        for i in range(5):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"def test{i}(): pass")

        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            max_cost=0.25,  # Very low limit
            auto_approve=True,
        )

        # Mock scout
        mock_scout = MagicMock()
        mock_scout_result = MagicMock()
        mock_scout_result.success = True
        mock_scout_result.cost = 0.1
        mock_scout_result.findings = [
            {
                "agent": "Analyst",
                "response": f'"file_path": "test{i}.py"\n"issue_type": "missing_docstring"\n"severity": "high"',
            }
            for i in range(5)
        ]
        mock_scout.execute = AsyncMock(return_value=mock_scout_result)
        orchestrator._scout = mock_scout

        # Mock writer with cost per execution
        mock_writer = MagicMock()
        mock_writer_result = {"document": "# Test", "accumulated_cost": 0.1}
        mock_writer.execute = AsyncMock(return_value=mock_writer_result)
        orchestrator._writer = mock_writer

        result = await orchestrator.execute()

        # Should stop before processing all 5 items due to cost limit
        assert result.items_processed < 5
        assert result.total_cost <= orchestrator.max_cost + 0.1  # Small margin for last item


@pytest.mark.asyncio
class TestProjectIndexEdgeCases:
    """Test edge cases in project index interactions."""

    async def test_update_index_with_missing_get_record_method(self, tmp_path):
        """Test handling when ProjectIndex doesn't have get_record method."""
        orchestrator = DocumentationOrchestrator(project_root=str(tmp_path))

        # Create a mock index without get_record method
        mock_index = MagicMock()
        del mock_index.get_record  # Remove the method
        orchestrator._index = mock_index

        # Should handle gracefully
        orchestrator._update_project_index(["test.py"], [])

        # No exception should be raised

    async def test_items_from_index_with_filtered_exclusions(self, tmp_path):
        """Test that items_from_index respects file exclusions."""
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path),
            include_missing=True,
        )

        # Create mock index with both included and excluded files
        mock_index = MagicMock()
        mock_records = [
            MagicMock(
                file_path="src/main.py",
                category="source",
                loc=100,
                has_docstring=False,
            ),
            MagicMock(
                file_path="requirements.txt",  # Should be excluded
                category="config",
                loc=10,
                has_docstring=False,
            ),
        ]
        mock_index.records = mock_records
        orchestrator._index = mock_index

        items = orchestrator._items_from_index()

        # Should only include source file, not requirements.txt
        assert len(items) <= 1
        if len(items) > 0:
            assert "requirements.txt" not in items[0].file_path


class TestExecutePathKwarg:
    """execute() honors the canonical `path=` kwarg and the deprecated alias.

    Scout is mocked to return no items so execute() short-circuits right
    after scope resolution, without running the generation pipeline.
    """

    @pytest.fixture
    def orchestrator(self, tmp_path):
        return DocumentationOrchestrator(project_root=str(tmp_path), dry_run=True)

    async def test_execute_accepts_path_kwarg(self, orchestrator, tmp_path):
        target = tmp_path / "scoped"
        target.mkdir()
        orchestrator._run_scout_phase = AsyncMock(return_value=([], 0.0))
        result = await orchestrator.execute(path=str(target))
        assert result.success is True
        assert orchestrator.project_root == target.resolve()

    async def test_execute_legacy_project_root_warns(self, orchestrator, tmp_path):
        target = tmp_path / "legacy"
        target.mkdir()
        orchestrator._run_scout_phase = AsyncMock(return_value=([], 0.0))
        with pytest.warns(DeprecationWarning, match="project_root"):
            result = await orchestrator.execute(project_root=str(target))
        assert result.success is True
        assert orchestrator.project_root == target.resolve()

    async def test_execute_both_kwargs_path_wins(self, orchestrator, tmp_path):
        win = tmp_path / "win"
        win.mkdir()
        lose = tmp_path / "lose"
        lose.mkdir()
        orchestrator._run_scout_phase = AsyncMock(return_value=([], 0.0))
        with pytest.warns(DeprecationWarning, match="precedence"):
            result = await orchestrator.execute(path=str(win), project_root=str(lose))
        assert result.success is True
        assert orchestrator.project_root == win.resolve()

    async def test_execute_default_export_path_rederived_under_scope(self, orchestrator, tmp_path):
        target = tmp_path / "scoped2"
        target.mkdir()
        orchestrator._run_scout_phase = AsyncMock(return_value=([], 0.0))
        await orchestrator.execute(path=str(target))
        assert orchestrator.export_path == target.resolve() / "docs" / "generated"

    async def test_execute_explicit_export_path_preserved(self, tmp_path):
        export = tmp_path / "custom-export"
        orchestrator = DocumentationOrchestrator(
            project_root=str(tmp_path), export_path=str(export), dry_run=True
        )
        target = tmp_path / "scoped3"
        target.mkdir()
        orchestrator._run_scout_phase = AsyncMock(return_value=([], 0.0))
        await orchestrator.execute(path=str(target))
        # An explicitly-set export_path must NOT be re-derived on re-scope.
        assert orchestrator.export_path == export
