"""Unit tests for memory graph Node and NodeType.

This test suite provides comprehensive coverage for the memory graph node
implementation, including NodeType enum, Node dataclass, specialized node types,
and serialization.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime

import pytest

from attune.memory.nodes import (
    BugNode,
    Node,
    NodeType,
    PatternNode,
    PerformanceNode,
    VulnerabilityNode,
)


@pytest.mark.unit
class TestNodeTypeEnum:
    """Test suite for NodeType enum."""

    def test_node_type_enum_has_code_entities(self):
        """Test that NodeType enum includes code entity types."""
        assert NodeType.FILE.value == "file"
        assert NodeType.FUNCTION.value == "function"
        assert NodeType.CLASS.value == "class"
        assert NodeType.MODULE.value == "module"

    def test_node_type_enum_has_issues_and_findings(self):
        """Test that NodeType enum includes issue types."""
        assert NodeType.BUG.value == "bug"
        assert NodeType.VULNERABILITY.value == "vulnerability"
        assert NodeType.PERFORMANCE_ISSUE.value == "performance_issue"
        assert NodeType.CODE_SMELL.value == "code_smell"
        assert NodeType.TECH_DEBT.value == "tech_debt"

    def test_node_type_enum_has_solutions_and_patterns(self):
        """Test that NodeType enum includes solution types."""
        assert NodeType.PATTERN.value == "pattern"
        assert NodeType.FIX.value == "fix"
        assert NodeType.REFACTOR.value == "refactor"

    def test_node_type_enum_has_testing_types(self):
        """Test that NodeType enum includes testing types."""
        assert NodeType.TEST.value == "test"
        assert NodeType.TEST_CASE.value == "test_case"
        assert NodeType.COVERAGE_GAP.value == "coverage_gap"

    def test_node_type_enum_has_documentation_types(self):
        """Test that NodeType enum includes documentation types."""
        assert NodeType.DOC.value == "doc"
        assert NodeType.API_ENDPOINT.value == "api_endpoint"

    def test_node_type_enum_has_dependency_types(self):
        """Test that NodeType enum includes dependency types."""
        assert NodeType.DEPENDENCY.value == "dependency"
        assert NodeType.LICENSE.value == "license"

    def test_node_type_enum_has_curated_memory_types(self):
        """Test that NodeType enum includes curated cross-session memory
        types (not workflow findings - see module docstring)."""
        assert NodeType.USER_CONTEXT.value == "user_context"
        assert NodeType.FEEDBACK.value == "feedback"
        assert NodeType.PROJECT_CONTEXT.value == "project_context"
        assert NodeType.REFERENCE.value == "reference"

    def test_node_type_can_be_created_from_string_value(self):
        """Test that NodeType can be created from string value."""
        node_type = NodeType("bug")
        assert node_type == NodeType.BUG


@pytest.mark.unit
class TestNodeDataclass:
    """Test suite for Node dataclass."""

    def test_node_creation_with_required_fields(self):
        """Test creating node with only required fields."""
        node = Node(
            id="node-1",
            type=NodeType.BUG,
            name="Test Bug",
        )

        assert node.id == "node-1"
        assert node.type == NodeType.BUG
        assert node.name == "Test Bug"

    def test_node_creation_with_default_values(self):
        """Test that node uses correct default values."""
        node = Node(
            id="node-1",
            type=NodeType.BUG,
            name="Test Bug",
        )

        assert node.description == ""
        assert node.source_workflow == ""
        assert node.source_file == ""
        assert node.source_line is None
        assert node.severity == ""
        assert node.confidence == 1.0
        assert node.metadata == {}
        assert node.tags == []
        assert isinstance(node.created_at, datetime)
        assert isinstance(node.updated_at, datetime)
        assert node.status == "open"

    def test_node_creation_with_custom_values(self):
        """Test creating node with custom values."""
        custom_time = datetime(2025, 1, 15, 12, 0, 0)
        node = Node(
            id="node-1",
            type=NodeType.BUG,
            name="Test Bug",
            description="A test bug",
            source_workflow="bug-predict",
            source_file="test.py",
            source_line=42,
            severity="high",
            confidence=0.85,
            metadata={"priority": 1},
            tags=["critical", "security"],
            created_at=custom_time,
            updated_at=custom_time,
            status="investigating",
        )

        assert node.description == "A test bug"
        assert node.source_workflow == "bug-predict"
        assert node.source_file == "test.py"
        assert node.source_line == 42
        assert node.severity == "high"
        assert node.confidence == 0.85
        assert node.metadata == {"priority": 1}
        assert node.tags == ["critical", "security"]
        assert node.created_at == custom_time
        assert node.updated_at == custom_time
        assert node.status == "investigating"

    def test_node_severity_levels(self):
        """Test that node accepts different severity levels."""
        severities = ["critical", "high", "medium", "low", "info"]

        for severity in severities:
            node = Node(id="node", type=NodeType.BUG, name="Bug", severity=severity)
            assert node.severity == severity

    def test_node_status_values(self):
        """Test that node accepts different status values."""
        statuses = ["open", "investigating", "resolved", "wontfix"]

        for status in statuses:
            node = Node(id="node", type=NodeType.BUG, name="Bug", status=status)
            assert node.status == status

    def test_node_confidence_range(self):
        """Test that node confidence can be set to different values."""
        node_low = Node(id="node", type=NodeType.BUG, name="Bug", confidence=0.1)
        node_high = Node(id="node", type=NodeType.BUG, name="Bug", confidence=1.0)

        assert node_low.confidence == 0.1
        assert node_high.confidence == 1.0


@pytest.mark.unit
class TestNodeSerialization:
    """Test suite for Node serialization and deserialization."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all node fields."""
        custom_time = datetime(2025, 1, 15, 12, 0, 0)
        node = Node(
            id="node-1",
            type=NodeType.BUG,
            name="Test Bug",
            description="A test bug",
            source_workflow="bug-predict",
            source_file="test.py",
            source_line=42,
            severity="high",
            confidence=0.85,
            metadata={"key": "value"},
            tags=["tag1", "tag2"],
            created_at=custom_time,
            updated_at=custom_time,
            status="open",
        )

        node_dict = node.to_dict()

        assert node_dict["id"] == "node-1"
        assert node_dict["type"] == "bug"
        assert node_dict["name"] == "Test Bug"
        assert node_dict["description"] == "A test bug"
        assert node_dict["source_workflow"] == "bug-predict"
        assert node_dict["source_file"] == "test.py"
        assert node_dict["source_line"] == 42
        assert node_dict["severity"] == "high"
        assert node_dict["confidence"] == 0.85
        assert node_dict["metadata"] == {"key": "value"}
        assert node_dict["tags"] == ["tag1", "tag2"]
        assert node_dict["created_at"] == "2025-01-15T12:00:00"
        assert node_dict["updated_at"] == "2025-01-15T12:00:00"
        assert node_dict["status"] == "open"

    def test_to_dict_converts_enum_to_string(self):
        """Test that to_dict converts NodeType enum to string value."""
        node = Node(id="node", type=NodeType.VULNERABILITY, name="Test")
        node_dict = node.to_dict()

        assert node_dict["type"] == "vulnerability"
        assert isinstance(node_dict["type"], str)

    def test_to_dict_converts_datetime_to_isoformat(self):
        """Test that to_dict converts datetime to ISO format string."""
        custom_time = datetime(2025, 1, 15, 12, 30, 45)
        node = Node(
            id="node",
            type=NodeType.BUG,
            name="Test",
            created_at=custom_time,
            updated_at=custom_time,
        )
        node_dict = node.to_dict()

        assert node_dict["created_at"] == "2025-01-15T12:30:45"
        assert node_dict["updated_at"] == "2025-01-15T12:30:45"
        assert isinstance(node_dict["created_at"], str)

    def test_from_dict_creates_node_with_all_fields(self):
        """Test that from_dict creates node from dictionary."""
        node_dict = {
            "id": "node-1",
            "type": "bug",
            "name": "Test Bug",
            "description": "A test bug",
            "source_workflow": "bug-predict",
            "source_file": "test.py",
            "source_line": 42,
            "severity": "high",
            "confidence": 0.85,
            "metadata": {"key": "value"},
            "tags": ["tag1", "tag2"],
            "created_at": "2025-01-15T12:00:00",
            "updated_at": "2025-01-15T12:30:00",
            "status": "investigating",
        }

        node = Node.from_dict(node_dict)

        assert node.id == "node-1"
        assert node.type == NodeType.BUG
        assert node.name == "Test Bug"
        assert node.description == "A test bug"
        assert node.source_workflow == "bug-predict"
        assert node.source_file == "test.py"
        assert node.source_line == 42
        assert node.severity == "high"
        assert node.confidence == 0.85
        assert node.metadata == {"key": "value"}
        assert node.tags == ["tag1", "tag2"]
        assert node.created_at == datetime(2025, 1, 15, 12, 0, 0)
        assert node.updated_at == datetime(2025, 1, 15, 12, 30, 0)
        assert node.status == "investigating"

    def test_from_dict_uses_defaults_for_missing_optional_fields(self):
        """Test that from_dict uses defaults for missing optional fields."""
        node_dict = {
            "id": "node-1",
            "type": "bug",
            "name": "Test Bug",
        }

        node = Node.from_dict(node_dict)

        assert node.description == ""
        assert node.source_workflow == ""
        assert node.source_file == ""
        assert node.source_line is None
        assert node.severity == ""
        assert node.confidence == 1.0
        assert node.metadata == {}
        assert node.tags == []
        assert isinstance(node.created_at, datetime)
        assert isinstance(node.updated_at, datetime)
        assert node.status == "open"

    def test_from_dict_handles_legacy_source_wizard_field(self):
        """Test that from_dict handles legacy 'source_wizard' field."""
        node_dict = {
            "id": "node-1",
            "type": "bug",
            "name": "Test Bug",
            "source_wizard": "legacy-wizard",  # Old field name
        }

        node = Node.from_dict(node_dict)

        # Should use source_wizard as fallback for source_workflow
        assert node.source_workflow == "legacy-wizard"

    def test_from_dict_prefers_source_workflow_over_source_wizard(self):
        """Test that from_dict prefers source_workflow when both present."""
        node_dict = {
            "id": "node-1",
            "type": "bug",
            "name": "Test Bug",
            "source_workflow": "new-workflow",
            "source_wizard": "old-wizard",
        }

        node = Node.from_dict(node_dict)

        assert node.source_workflow == "new-workflow"

    def test_roundtrip_serialization(self):
        """Test that node survives to_dict -> from_dict round trip."""
        original = Node(
            id="node-1",
            type=NodeType.VULNERABILITY,
            name="SQL Injection",
            description="SQL injection vulnerability in login form",
            source_workflow="security-audit",
            source_file="auth.py",
            source_line=123,
            severity="critical",
            confidence=0.95,
            metadata={"cwe": "CWE-89", "cvss": 9.8},
            tags=["sql", "injection", "critical"],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
            updated_at=datetime(2025, 1, 15, 11, 0, 0),
            status="investigating",
        )

        # Round trip
        node_dict = original.to_dict()
        restored = Node.from_dict(node_dict)

        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.source_workflow == original.source_workflow
        assert restored.source_file == original.source_file
        assert restored.source_line == original.source_line
        assert restored.severity == original.severity
        assert restored.confidence == original.confidence
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
        assert restored.status == original.status

    def test_curated_memory_node_roundtrip_serialization(self):
        """Regression guard: before the curated-memory NodeType members
        existed, Node.from_dict(node.to_dict()) on a FEEDBACK/USER_CONTEXT/
        PROJECT_CONTEXT/REFERENCE node raised
        ``ValueError: '<value>' is not a valid NodeType`` at reload time
        (from_dict calls NodeType(data["type"]) against whatever the enum
        actually contains). severity stays unset and status is
        reinterpreted (active, not open/resolved) for these node types -
        see the module docstring."""
        original = Node(
            id="feedback_my_commitments_to_patrick",
            type=NodeType.FEEDBACK,
            name="Standing commitments to Patrick",
            description="Neutral curiosity, full attention, correction without ego.",
            source_file="/memory/feedback_my_commitments_to_patrick.md",
            severity="",
            status="active",
            tags=["relationship", "standing-commitment"],
        )

        restored = Node.from_dict(original.to_dict())

        assert restored.type == NodeType.FEEDBACK
        assert restored.severity == ""
        assert restored.status == "active"
        assert restored.source_workflow == ""


@pytest.mark.unit
class TestBugNode:
    """Test suite for BugNode specialized node type."""

    def test_bug_node_creation_with_required_fields(self):
        """Test creating BugNode with required fields."""
        node = BugNode(
            id="bug-1",
            type=NodeType.BUG,  # Will be overridden by __post_init__
            name="Null Pointer Exception",
        )

        assert node.id == "bug-1"
        assert node.type == NodeType.BUG
        assert node.name == "Null Pointer Exception"

    def test_bug_node_post_init_sets_type_to_bug(self):
        """Test that BugNode.__post_init__ sets type to BUG."""
        node = BugNode(
            id="bug-1",
            type=NodeType.FILE,  # Wrong type - should be overridden
            name="Test Bug",
        )

        # __post_init__ should force type to BUG
        assert node.type == NodeType.BUG

    def test_bug_node_creation_with_custom_fields(self):
        """Test creating BugNode with bug-specific fields."""
        node = BugNode(
            id="bug-1",
            type=NodeType.BUG,
            name="Memory Leak",
            root_cause="Unclosed file handle",
            fix_suggestion="Add context manager",
            reproduction_steps=[
                "Open file without context manager",
                "Run for 1000 iterations",
                "Check memory usage",
            ],
        )

        assert node.root_cause == "Unclosed file handle"
        assert node.fix_suggestion == "Add context manager"
        assert len(node.reproduction_steps) == 3
        assert node.reproduction_steps[0] == "Open file without context manager"

    def test_bug_node_default_values(self):
        """Test BugNode default values for specialized fields."""
        node = BugNode(id="bug-1", type=NodeType.BUG, name="Test Bug")

        assert node.root_cause == ""
        assert node.fix_suggestion == ""
        assert node.reproduction_steps == []


@pytest.mark.unit
class TestVulnerabilityNode:
    """Test suite for VulnerabilityNode specialized node type."""

    def test_vulnerability_node_creation_with_required_fields(self):
        """Test creating VulnerabilityNode with required fields."""
        node = VulnerabilityNode(
            id="vuln-1",
            type=NodeType.VULNERABILITY,
            name="SQL Injection",
        )

        assert node.id == "vuln-1"
        assert node.type == NodeType.VULNERABILITY
        assert node.name == "SQL Injection"

    def test_vulnerability_node_post_init_sets_type(self):
        """Test that VulnerabilityNode.__post_init__ sets type to VULNERABILITY."""
        node = VulnerabilityNode(
            id="vuln-1",
            type=NodeType.BUG,  # Wrong type - should be overridden
            name="Test Vulnerability",
        )

        # __post_init__ should force type to VULNERABILITY
        assert node.type == NodeType.VULNERABILITY

    def test_vulnerability_node_creation_with_custom_fields(self):
        """Test creating VulnerabilityNode with vulnerability-specific fields."""
        node = VulnerabilityNode(
            id="vuln-1",
            type=NodeType.VULNERABILITY,
            name="SQL Injection in Login",
            cwe_id="CWE-89",
            cvss_score=9.8,
            attack_vector="Network",
            remediation="Use parameterized queries",
        )

        assert node.cwe_id == "CWE-89"
        assert node.cvss_score == 9.8
        assert node.attack_vector == "Network"
        assert node.remediation == "Use parameterized queries"

    def test_vulnerability_node_default_values(self):
        """Test VulnerabilityNode default values for specialized fields."""
        node = VulnerabilityNode(
            id="vuln-1",
            type=NodeType.VULNERABILITY,
            name="Test Vulnerability",
        )

        assert node.cwe_id == ""
        assert node.cvss_score == 0.0
        assert node.attack_vector == ""
        assert node.remediation == ""


@pytest.mark.unit
class TestPerformanceNode:
    """Test suite for PerformanceNode specialized node type."""

    def test_performance_node_creation_with_required_fields(self):
        """Test creating PerformanceNode with required fields."""
        node = PerformanceNode(
            id="perf-1",
            type=NodeType.PERFORMANCE_ISSUE,
            name="Slow Query",
        )

        assert node.id == "perf-1"
        assert node.type == NodeType.PERFORMANCE_ISSUE
        assert node.name == "Slow Query"

    def test_performance_node_post_init_sets_type(self):
        """Test that PerformanceNode.__post_init__ sets type to PERFORMANCE_ISSUE."""
        node = PerformanceNode(
            id="perf-1",
            type=NodeType.BUG,  # Wrong type - should be overridden
            name="Test Performance Issue",
        )

        # __post_init__ should force type to PERFORMANCE_ISSUE
        assert node.type == NodeType.PERFORMANCE_ISSUE

    def test_performance_node_creation_with_custom_fields(self):
        """Test creating PerformanceNode with performance-specific fields."""
        node = PerformanceNode(
            id="perf-1",
            type=NodeType.PERFORMANCE_ISSUE,
            name="High Latency",
            metric="latency",
            current_value=2500.0,
            target_value=200.0,
            optimization_suggestion="Add database index",
        )

        assert node.metric == "latency"
        assert node.current_value == 2500.0
        assert node.target_value == 200.0
        assert node.optimization_suggestion == "Add database index"

    def test_performance_node_default_values(self):
        """Test PerformanceNode default values for specialized fields."""
        node = PerformanceNode(
            id="perf-1",
            type=NodeType.PERFORMANCE_ISSUE,
            name="Test Performance Issue",
        )

        assert node.metric == ""
        assert node.current_value == 0.0
        assert node.target_value == 0.0
        assert node.optimization_suggestion == ""


@pytest.mark.unit
class TestPatternNode:
    """Test suite for PatternNode specialized node type."""

    def test_pattern_node_creation_with_required_fields(self):
        """Test creating PatternNode with required fields."""
        node = PatternNode(
            id="pattern-1",
            type=NodeType.PATTERN,
            name="Singleton Pattern",
        )

        assert node.id == "pattern-1"
        assert node.type == NodeType.PATTERN
        assert node.name == "Singleton Pattern"

    def test_pattern_node_post_init_sets_type(self):
        """Test that PatternNode.__post_init__ sets type to PATTERN."""
        node = PatternNode(
            id="pattern-1",
            type=NodeType.BUG,  # Wrong type - should be overridden
            name="Test Pattern",
        )

        # __post_init__ should force type to PATTERN
        assert node.type == NodeType.PATTERN

    def test_pattern_node_creation_with_custom_fields(self):
        """Test creating PatternNode with pattern-specific fields."""
        node = PatternNode(
            id="pattern-1",
            type=NodeType.PATTERN,
            name="Factory Method",
            pattern_type="best-practice",
            language="python",
            example_code="class Factory:\n    def create(self): pass",
            applies_to=["object-creation", "dependency-injection"],
        )

        assert node.pattern_type == "best-practice"
        assert node.language == "python"
        assert "class Factory" in node.example_code
        assert node.applies_to == ["object-creation", "dependency-injection"]

    def test_pattern_node_default_values(self):
        """Test PatternNode default values for specialized fields."""
        node = PatternNode(id="pattern-1", type=NodeType.PATTERN, name="Test Pattern")

        assert node.pattern_type == ""
        assert node.language == ""
        assert node.example_code == ""
        assert node.applies_to == []


@pytest.mark.unit
class TestNodeEdgeCases:
    """Test suite for Node edge cases."""

    def test_node_with_empty_metadata(self):
        """Test that node handles empty metadata dictionary."""
        node = Node(id="node", type=NodeType.BUG, name="Test", metadata={})

        assert node.metadata == {}
        node_dict = node.to_dict()
        assert node_dict["metadata"] == {}

    def test_node_with_empty_tags(self):
        """Test that node handles empty tags list."""
        node = Node(id="node", type=NodeType.BUG, name="Test", tags=[])

        assert node.tags == []
        node_dict = node.to_dict()
        assert node_dict["tags"] == []

    def test_node_with_none_source_line(self):
        """Test that node handles None source_line."""
        node = Node(id="node", type=NodeType.BUG, name="Test", source_line=None)

        assert node.source_line is None
        node_dict = node.to_dict()
        assert node_dict["source_line"] is None

    def test_node_with_special_characters_in_name(self):
        """Test that node handles special characters in name."""
        node = Node(id="node", type=NodeType.BUG, name="Bug: SQL Injection (CWE-89)")

        assert node.name == "Bug: SQL Injection (CWE-89)"

    def test_node_with_very_long_description(self):
        """Test that node handles very long description strings."""
        long_desc = "x" * 10000
        node = Node(id="node", type=NodeType.BUG, name="Test", description=long_desc)

        assert node.description == long_desc
        assert len(node.description) == 10000

    def test_node_with_complex_metadata(self):
        """Test that node handles complex nested metadata."""
        metadata = {
            "nested": {"key": "value", "number": 42},
            "list": [1, 2, 3],
            "mixed": {"data": [{"a": 1}, {"b": 2}]},
        }
        node = Node(id="node", type=NodeType.BUG, name="Test", metadata=metadata)

        node_dict = node.to_dict()
        restored = Node.from_dict(node_dict)
        assert restored.metadata == metadata

    def test_node_with_unicode_in_fields(self):
        """Test that node handles unicode characters."""
        node = Node(
            id="node-1",
            type=NodeType.BUG,
            name="バグ",  # Japanese
            description="Erreur de syntaxe",  # French
            tags=["テスト", "тест"],  # Japanese, Russian
        )

        node_dict = node.to_dict()
        restored = Node.from_dict(node_dict)
        assert restored.name == "バグ"
        assert restored.description == "Erreur de syntaxe"
        assert restored.tags == ["テスト", "тест"]
