"""Code analysis configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field


@dataclass
class AnalysisConfig:
    """Code analysis and scanning configuration.

    Controls thresholds, patterns, and features for code analysis
    workflows like security scanning, bug prediction, and performance audits.

    Attributes:
        complexity_threshold: Cyclomatic complexity threshold for warnings.
        max_file_size_kb: Maximum file size to analyze (in KB).
        exclude_patterns: Glob patterns for files/dirs to exclude.
        include_patterns: Glob patterns for files to include.
        security_scan_enabled: Enable security vulnerability scanning.
        bug_prediction_enabled: Enable bug prediction analysis.
        performance_audit_enabled: Enable performance audit analysis.
        doc_coverage_check: Check documentation coverage.
        type_hint_check: Check for missing type hints.
        test_coverage_target: Target test coverage percentage.
        max_function_length: Maximum recommended function length (lines).

    """

    complexity_threshold: int = 10
    max_file_size_kb: int = 500
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["*.pyc", "__pycache__", ".git", "node_modules", ".venv"],
    )
    include_patterns: list[str] = field(default_factory=lambda: ["*.py"])
    security_scan_enabled: bool = True
    bug_prediction_enabled: bool = True
    performance_audit_enabled: bool = True
    doc_coverage_check: bool = True
    type_hint_check: bool = True
    test_coverage_target: int = 80
    max_function_length: int = 50

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "complexity_threshold": self.complexity_threshold,
            "max_file_size_kb": self.max_file_size_kb,
            "exclude_patterns": self.exclude_patterns,
            "include_patterns": self.include_patterns,
            "security_scan_enabled": self.security_scan_enabled,
            "bug_prediction_enabled": self.bug_prediction_enabled,
            "performance_audit_enabled": self.performance_audit_enabled,
            "doc_coverage_check": self.doc_coverage_check,
            "type_hint_check": self.type_hint_check,
            "test_coverage_target": self.test_coverage_target,
            "max_function_length": self.max_function_length,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisConfig":
        """Create from dictionary."""
        return cls(
            complexity_threshold=data.get("complexity_threshold", 10),
            max_file_size_kb=data.get("max_file_size_kb", 500),
            exclude_patterns=data.get(
                "exclude_patterns",
                ["*.pyc", "__pycache__", ".git", "node_modules", ".venv"],
            ),
            include_patterns=data.get("include_patterns", ["*.py"]),
            security_scan_enabled=data.get("security_scan_enabled", True),
            bug_prediction_enabled=data.get("bug_prediction_enabled", True),
            performance_audit_enabled=data.get("performance_audit_enabled", True),
            doc_coverage_check=data.get("doc_coverage_check", True),
            type_hint_check=data.get("type_hint_check", True),
            test_coverage_target=data.get("test_coverage_target", 80),
            max_function_length=data.get("max_function_length", 50),
        )
