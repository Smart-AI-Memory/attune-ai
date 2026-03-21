"""Tests for orchestration/tools/__init__.py package exports.

Verifies that all public names are importable and the aggregated
REAL_TOOLS registry contains entries from all sub-modules.
"""

from attune.orchestration.tools import (
    PERFORMANCE_TOOLS,
    QUALITY_TOOLS,
    REAL_TOOLS,
    SECURITY_TOOLS,
    TESTING_TOOLS,
    ArchitectureReport,
    CoverageReport,
    DocumentationReport,
    PerformanceReport,
    QualityReport,
    RealArchitectureAnalyzer,
    RealCodeQualityAnalyzer,
    RealCoverageAnalyzer,
    RealDocumentationAnalyzer,
    RealPerformanceProfiler,
    RealSecurityAuditor,
    RealTestGenerator,
    RealTestValidator,
    SecurityReport,
    _validate_file_path,
)


class TestToolsPackageExports:
    """Verify all expected names are importable from the package."""

    def test_real_tools_is_dict(self):
        """REAL_TOOLS is a dict aggregating all sub-registries."""
        assert isinstance(REAL_TOOLS, dict)

    def test_real_tools_contains_sub_registries(self):
        """REAL_TOOLS merges TESTING, QUALITY, SECURITY, PERFORMANCE."""
        for key in TESTING_TOOLS:
            assert key in REAL_TOOLS
        for key in QUALITY_TOOLS:
            assert key in REAL_TOOLS
        for key in SECURITY_TOOLS:
            assert key in REAL_TOOLS
        for key in PERFORMANCE_TOOLS:
            assert key in REAL_TOOLS

    def test_real_tools_size_matches_sum(self):
        """REAL_TOOLS size equals sum of sub-registries (no collisions)."""
        expected = (
            len(TESTING_TOOLS) + len(QUALITY_TOOLS) + len(SECURITY_TOOLS) + len(PERFORMANCE_TOOLS)
        )
        assert len(REAL_TOOLS) == expected

    def test_sub_registries_are_dicts(self):
        """Each sub-registry is a dict."""
        assert isinstance(TESTING_TOOLS, dict)
        assert isinstance(QUALITY_TOOLS, dict)
        assert isinstance(SECURITY_TOOLS, dict)
        assert isinstance(PERFORMANCE_TOOLS, dict)

    def test_analyzer_classes_are_importable(self):
        """All analyzer/report classes are importable and are types."""
        classes = [
            RealArchitectureAnalyzer,
            RealCoverageAnalyzer,
            RealTestGenerator,
            RealTestValidator,
            RealSecurityAuditor,
            RealCodeQualityAnalyzer,
            RealDocumentationAnalyzer,
            RealPerformanceProfiler,
        ]
        for cls in classes:
            assert isinstance(cls, type), f"{cls} should be a class"

    def test_report_dataclasses_are_importable(self):
        """All report dataclasses are importable."""
        reports = [
            ArchitectureReport,
            CoverageReport,
            SecurityReport,
            QualityReport,
            DocumentationReport,
            PerformanceReport,
        ]
        for cls in reports:
            assert isinstance(cls, type), f"{cls} should be a class"

    def test_validate_file_path_is_callable(self):
        """_validate_file_path is re-exported and callable."""
        assert callable(_validate_file_path)

    def test_all_list_matches_exports(self):
        """__all__ in the package covers key exports."""
        import attune.orchestration.tools as pkg

        all_names = set(pkg.__all__)
        # Spot-check critical names
        assert "REAL_TOOLS" in all_names
        assert "RealSecurityAuditor" in all_names
        assert "RealCoverageAnalyzer" in all_names
        assert "_validate_file_path" in all_names
        assert "ArchitectureReport" in all_names
