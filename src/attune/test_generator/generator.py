"""Test generator core implementation.

Generates comprehensive tests for workflows using Jinja2 templates
and risk-based prioritization.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from patterns import get_pattern_registry
from patterns.structural import LinearFlowPattern, PhasedProcessingPattern

from .risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)


def _get_default_template_dir() -> Path:
    """Get default template directory.

    Returns:
        Path to templates directory

    Note:
        Uses multiple fallback strategies to avoid __file__ AttributeError
        in pytest environments.

    """
    try:
        # Try __file__ first (works in most cases)
        return Path(__file__).parent / "templates"
    except (AttributeError, NameError):
        # Fallback: Use module __spec__ if available
        import importlib.util
        import sys

        spec = importlib.util.find_spec("attune.test_generator")
        if spec and spec.origin:
            return Path(spec.origin).parent / "templates"

        # Last resort: Try to find from sys.modules
        this_module = sys.modules.get(__name__)
        if this_module and hasattr(this_module, "__file__") and this_module.__file__:
            return Path(this_module.__file__).parent / "templates"

        # Final fallback: Use current working directory
        return Path.cwd() / "src" / "attune" / "test_generator" / "templates"


class TestGenerator:
    """Generates tests for workflows based on patterns and risk analysis.

    Uses Jinja2 templates to generate:
    - Unit tests with risk-prioritized coverage
    - Integration tests for multi-step workflows
    - E2E tests for critical paths
    - Test fixtures for common patterns
    """

    def __init__(self, template_dir: Path | None = None):
        """Initialize test generator.

        Args:
            template_dir: Directory containing Jinja2 templates
                         (defaults to test_generator/templates/)

        """
        if template_dir is None:
            template_dir = _get_default_template_dir()

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,  # Enable autoescape for security (test gen templates should be safe)
        )

        self.risk_analyzer = RiskAnalyzer()
        self.registry = get_pattern_registry()

    def generate_tests(
        self,
        workflow_id: str,
        pattern_ids: list[str],
        workflow_module: str | None = None,
        workflow_class: str | None = None,
    ) -> dict[str, str | None]:
        """Generate tests for a workflow.

        Args:
            workflow_id: Workflow identifier
            pattern_ids: List of pattern IDs used by workflow
            workflow_module: Python module path (e.g., "workflows.soap_note")
            workflow_class: Workflow class name (e.g., "SOAPNoteWorkflow")

        Returns:
            Dictionary with test types:
                {
                    "unit": "...",  # Unit test code
                    "integration": "...",  # Integration test code (if applicable)
                    "fixtures": "...",  # Test fixtures
                }

        """
        logger.info(f"Generating tests for workflow: {workflow_id}")

        # Perform risk analysis
        risk_analysis = self.risk_analyzer.analyze(workflow_id, pattern_ids)

        # Infer module and class if not provided
        if not workflow_module:
            workflow_module = self._infer_module(workflow_id)

        if not workflow_class:
            workflow_class = self._infer_class_name(workflow_id)

        # Gather template context
        context = self._build_template_context(
            workflow_id=workflow_id,
            pattern_ids=pattern_ids,
            workflow_module=workflow_module,
            workflow_class=workflow_class,
            risk_analysis=risk_analysis,
        )

        # Generate unit tests (always)
        unit_tests = self._generate_unit_tests(context)

        # Generate integration tests (for multi-step workflows)
        integration_tests = None
        if self._needs_integration_tests(pattern_ids):
            integration_tests = self._generate_integration_tests(context)

        # Generate test fixtures
        fixtures = self._generate_fixtures(context)

        logger.info(
            f"Generated tests for {workflow_id}: "
            f"unit={len(unit_tests)} chars, "
            f"integration={'yes' if integration_tests else 'no'}, "
            f"fixtures={len(fixtures)} chars",
        )

        return {
            "unit": unit_tests,
            "integration": integration_tests,
            "fixtures": fixtures,
        }

    def _build_template_context(
        self,
        workflow_id: str,
        pattern_ids: list[str],
        workflow_module: str,
        workflow_class: str,
        risk_analysis: Any,
    ) -> dict:
        """Build Jinja2 template context.

        Args:
            workflow_id: Workflow identifier
            pattern_ids: Pattern IDs
            workflow_module: Module path
            workflow_class: Class name
            risk_analysis: RiskAnalysis object

        Returns:
            Context dictionary for templates

        """
        # Get pattern details
        patterns = [self.registry.get(pid) for pid in pattern_ids if self.registry.get(pid)]

        # Check for specific patterns
        has_linear_flow = "linear_flow" in pattern_ids
        has_phased = "phased_processing" in pattern_ids
        has_approval = "approval" in pattern_ids
        has_async = True  # Assume async by default for modern workflows

        # Get linear flow details if present
        total_steps = None
        if has_linear_flow:
            linear_pattern = self.registry.get("linear_flow")
            if isinstance(linear_pattern, LinearFlowPattern):
                total_steps = linear_pattern.total_steps

        # Get phases if present
        phases = []
        if has_phased:
            phased_pattern = self.registry.get("phased_processing")
            if isinstance(phased_pattern, PhasedProcessingPattern):
                phases = phased_pattern.phases

        return {
            "workflow_id": workflow_id,
            "workflow_module": workflow_module,
            "workflow_class": workflow_class,
            "pattern_ids": pattern_ids,
            "patterns": patterns,
            "risk_analysis": risk_analysis,
            "has_async": has_async,
            "has_linear_flow": has_linear_flow,
            "has_phased": has_phased,
            "has_approval": has_approval,
            "total_steps": total_steps,
            "phases": phases,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_unit_tests(self, context: dict) -> str:
        """Generate unit tests from template.

        Args:
            context: Template context

        Returns:
            Generated unit test code

        """
        template = self.env.get_template("unit_test.py.jinja2")
        return template.render(**context)

    def _generate_integration_tests(self, context: dict) -> str:
        """Generate integration tests.

        Args:
            context: Template context

        Returns:
            Generated integration test code

        """
        # For now, return a simple integration test template
        # In full implementation, would use integration_test.py.jinja2
        return f'''"""Integration tests for {context["workflow_id"]} workflow.

Auto-generated by Attune AI Test Generator
Tests end-to-end workflow workflows.
"""

import pytest
from {context["workflow_module"]} import {context["workflow_class"]}


class TestIntegration{context["workflow_class"]}:
    """Integration tests for {context["workflow_id"]} workflow."""

    @pytest.fixture
    async def workflow(self):
        """Create workflow instance."""
        return {context["workflow_class"]}()

    @pytest.mark.asyncio
    async def test_complete_workflow_workflow(self, workflow):
        """Test complete workflow workflow end-to-end."""
        # Start workflow
        session = await workflow.start()
        workflow_id = session["workflow_id"]

        # Complete all steps with valid data
        # TODO: Add step completion logic

        # Verify final state
        assert session.get("completed", False) is True
'''

    def _generate_fixtures(self, context: dict) -> str:
        """Generate test fixtures.

        Args:
            context: Template context

        Returns:
            Generated fixture code

        """
        return f'''"""Test fixtures for {context["workflow_id"]} workflow.

Auto-generated by Attune AI Test Generator
Provides common test data and mocks.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def sample_{context["workflow_id"]}_data():
    """Sample data for {context["workflow_id"]} workflow."""
    return {{
        "field1": "test value 1",
        "field2": "test value 2",
    }}


@pytest.fixture
def mock_{context["workflow_id"]}_dependencies():
    """Mock dependencies for {context["workflow_id"]} workflow."""
    return {{
        "database": MagicMock(),
        "api_client": MagicMock(),
    }}
'''

    def _needs_integration_tests(self, pattern_ids: list[str]) -> bool:
        """Determine if integration tests are needed.

        Args:
            pattern_ids: Pattern IDs

        Returns:
            True if integration tests recommended

        """
        # Integration tests for multi-step or phased workflows
        return "linear_flow" in pattern_ids or "phased_processing" in pattern_ids

    def _infer_module(self, workflow_id: str) -> str:
        """Infer module path from workflow ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Inferred module path

        """
        # Try to determine workflow location
        # This is a simple heuristic - can be improved
        if workflow_id in ["soap_note", "sbar", "care_plan"]:
            return f"workflows.{workflow_id}"
        return f"workflows.{workflow_id}_workflow"

    def _infer_class_name(self, workflow_id: str) -> str:
        """Infer workflow class name from ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Inferred class name

        """
        # Convert snake_case to PascalCase and add "Workflow"
        parts = workflow_id.split("_")
        class_name = "".join(part.capitalize() for part in parts)
        return f"{class_name}Workflow"
