"""Risk-Driven Test Generator for Workflow Factory.

Generates comprehensive tests for workflows based on risk analysis and patterns.

Features:
- Risk-based test prioritization
- Pattern-driven test generation
- Jinja2 templates for unit/integration/E2E tests
- Fixture generation for common patterns
- CLI integration

Usage:
    from test_generator import TestGenerator

    generator = TestGenerator()
    tests = generator.generate_tests(
        workflow_id="soap_note",
        pattern_ids=["linear_flow", "approval", "structured_fields"]
    )

    # Write tests to file
    with open("test_soap_note.py", "w", encoding="utf-8") as f:
        f.write(tests["unit"])

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .generator import TestGenerator
from .risk_analyzer import RiskAnalysis, RiskAnalyzer

__all__ = [
    "RiskAnalysis",
    "RiskAnalyzer",
    "TestGenerator",
]

from attune import __version__
