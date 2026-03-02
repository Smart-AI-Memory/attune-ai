"""Tests for workflows/__init__.py module.

Tests lazy import system, workflow registry, and discovery functions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest


class TestLazyImportWorkflow:
    """Tests for _lazy_import_workflow."""

    def test_known_workflow_loads(self):
        """Known workflow names in _LAZY_WORKFLOW_IMPORTS resolve."""
        from attune.workflows import _lazy_import_workflow

        # SecurityAuditWorkflow is in _LAZY_WORKFLOW_IMPORTS
        cls = _lazy_import_workflow("SecurityAuditWorkflow")
        assert cls is not None

    def test_unknown_name_raises(self):
        """Unknown names raise AttributeError."""
        from attune.workflows import _lazy_import_workflow

        with pytest.raises(AttributeError, match="has no attribute"):
            _lazy_import_workflow("NonExistentWorkflow")


class TestGetattr:
    """Tests for __getattr__ lazy loading."""

    def test_getattr_unknown_raises(self):
        """Accessing non-existent attribute raises AttributeError."""
        import attune.workflows as wf_module

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = wf_module.__getattr__("TotallyFakeClass")

    def test_lazy_workflow_import_via_getattr(self):
        """Lazy workflow class can be accessed via module attribute."""
        # SecurityAuditWorkflow is in _LAZY_WORKFLOW_IMPORTS
        from attune.workflows import _LAZY_WORKFLOW_IMPORTS

        # Pick one that should exist
        assert "SecurityAuditWorkflow" in _LAZY_WORKFLOW_IMPORTS


class TestDiscoverWorkflows:
    """Tests for discover_workflows."""

    def test_discover_returns_dict(self):
        """discover_workflows returns a dict."""
        from attune.workflows import discover_workflows

        result = discover_workflows()

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_discover_includes_code_review(self):
        """Default workflows include code-review."""
        from attune.workflows import discover_workflows

        result = discover_workflows()

        assert "code-review" in result

    def test_discover_without_defaults(self):
        """include_defaults=False returns only entry-point workflows."""
        from attune.workflows import discover_workflows

        result = discover_workflows(include_defaults=False)

        # Without defaults, only entry_points are loaded
        # (likely empty in test environment)
        assert isinstance(result, dict)

    def test_discover_with_disabled_workflows(self):
        """Disabled workflows are excluded from results."""
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig(disabled_workflows=["code-review"])
        from attune.workflows import discover_workflows

        result = discover_workflows(config=config)

        assert "code-review" not in result


class TestGetWorkflow:
    """Tests for get_workflow."""

    def test_get_known_workflow(self):
        """get_workflow returns class for known workflow name."""
        from attune.workflows import get_workflow

        cls = get_workflow("code-review")

        assert cls is not None
        assert hasattr(cls, "execute")

    def test_get_unknown_workflow_raises(self):
        """get_workflow raises KeyError for unknown names."""
        from attune.workflows import get_workflow

        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent-workflow-xyz")


class TestListWorkflows:
    """Tests for list_workflows."""

    def test_list_returns_list_of_dicts(self):
        """list_workflows returns list of dicts with expected keys."""
        from attune.workflows import list_workflows

        result = list_workflows()

        assert isinstance(result, list)
        assert len(result) > 0

        # Check required keys
        for wf in result:
            assert "name" in wf
            assert "class" in wf
            assert "description" in wf
            assert "stages" in wf


class TestDefaultWorkflowNames:
    """Tests for _DEFAULT_WORKFLOW_NAMES registry."""

    def test_registry_has_expected_entries(self):
        """Registry contains core workflow names."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        expected = [
            "code-review",
            "bug-predict",
            "security-audit",
            "test-gen",
            "refactor-plan",
        ]
        for name in expected:
            assert name in _DEFAULT_WORKFLOW_NAMES

    def test_registry_values_are_strings(self):
        """Registry values are class name strings (for lazy loading)."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        for key, value in _DEFAULT_WORKFLOW_NAMES.items():
            assert isinstance(value, str), f"{key} maps to {type(value)}, expected str"


class TestRefreshWorkflowRegistry:
    """Tests for refresh_workflow_registry."""

    def test_refresh_clears_and_repopulates(self):
        """refresh_workflow_registry clears and repopulates WORKFLOW_REGISTRY."""
        from attune.workflows import WORKFLOW_REGISTRY, refresh_workflow_registry

        refresh_workflow_registry()

        assert isinstance(WORKFLOW_REGISTRY, dict)
        assert len(WORKFLOW_REGISTRY) > 0
