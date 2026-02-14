"""Real tool implementations for meta-orchestration agents.

This package provides actual tool integrations for agents to interact with
real systems instead of returning mock data.

Security:
    - All file operations validated with _validate_file_path()
    - Subprocess calls sanitized
    - Output size limited to prevent memory issues

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from ._shared import _validate_file_path
from .performance import PERFORMANCE_TOOLS, PerformanceReport, RealPerformanceProfiler
from .quality import (
    QUALITY_TOOLS,
    DocumentationReport,
    QualityReport,
    RealCodeQualityAnalyzer,
    RealDocumentationAnalyzer,
)
from .security import SECURITY_TOOLS, RealSecurityAuditor, SecurityReport
from .testing import (
    TESTING_TOOLS,
    CoverageReport,
    RealCoverageAnalyzer,
    RealTestGenerator,
    RealTestValidator,
)

REAL_TOOLS = {**TESTING_TOOLS, **QUALITY_TOOLS, **SECURITY_TOOLS, **PERFORMANCE_TOOLS}

__all__ = [
    # Aggregated registry
    "REAL_TOOLS",
    # Sub-registries
    "TESTING_TOOLS",
    "QUALITY_TOOLS",
    "SECURITY_TOOLS",
    "PERFORMANCE_TOOLS",
    # Shared
    "_validate_file_path",
    # Dataclasses
    "CoverageReport",
    "SecurityReport",
    "QualityReport",
    "DocumentationReport",
    "PerformanceReport",
    # Classes
    "RealCoverageAnalyzer",
    "RealTestGenerator",
    "RealTestValidator",
    "RealSecurityAuditor",
    "RealCodeQualityAnalyzer",
    "RealDocumentationAnalyzer",
    "RealPerformanceProfiler",
]
