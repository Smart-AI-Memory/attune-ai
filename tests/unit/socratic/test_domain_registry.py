"""Tests for the Socratic domain template registry.

Covers branches not exercised by other tests: domain-filtered listing,
default-workflow fallback, and custom domain registration.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.socratic.domain_models import Domain, DomainTemplate
from attune.socratic.domain_registry import (
    DomainTemplateRegistry,
    get_registry,
)


@pytest.fixture
def registry() -> DomainTemplateRegistry:
    """Fresh registry instance to avoid cross-test pollution from the global one."""
    return DomainTemplateRegistry()


class TestListAgentsByDomain:
    def test_list_agents_with_domain_returns_domain_agents(self, registry):
        """Lookup with a known domain returns that domain's agents (lines 201-203)."""
        agents = registry.list_agents(domain=Domain.CODE_REVIEW)
        assert len(agents) > 0
        # Each entry should be an AgentTemplate
        for a in agents:
            assert hasattr(a, "template_id")

    def test_list_agents_with_unknown_domain_returns_empty(self, registry):
        """Unknown domain key (e.g. GENERAL — not registered) returns [] (line 204)."""
        # Domain.GENERAL is not registered in built-ins
        result = registry.list_agents(domain=Domain.GENERAL)
        assert result == []


class TestListWorkflowsByDomain:
    def test_list_workflows_with_domain_returns_domain_workflows(self, registry):
        """Lookup with a known domain returns that domain's workflows (lines 211-213)."""
        workflows = registry.list_workflows(domain=Domain.CODE_REVIEW)
        assert len(workflows) > 0
        for w in workflows:
            assert hasattr(w, "template_id")

    def test_list_workflows_with_unknown_domain_returns_empty(self, registry):
        """Unknown domain returns [] (line 214)."""
        result = registry.list_workflows(domain=Domain.GENERAL)
        assert result == []


class TestGetDefaultWorkflow:
    def test_get_default_workflow_for_unknown_domain_returns_none(self, registry):
        """Unknown domain has no default workflow → returns None (line 259)."""
        result = registry.get_default_workflow(Domain.GENERAL)
        assert result is None

    def test_get_default_workflow_known_domain(self, registry):
        """Known domain returns its default WorkflowTemplate."""
        result = registry.get_default_workflow(Domain.CODE_REVIEW)
        assert result is not None
        assert result.template_id == "code_review_standard"


class TestRegisterDomain:
    def test_register_domain_adds_custom_template(self, registry):
        """register_domain stores a custom DomainTemplate (line 271)."""
        custom = DomainTemplate(
            domain=Domain.GENERAL,
            name="Custom General",
            description="custom",
            agents=[],
            workflows=[],
            default_workflow="",
            keywords=["custom"],
            required_tools=[],
            optional_tools=[],
        )

        registry.register_domain(custom)

        retrieved = registry.get_domain(Domain.GENERAL)
        assert retrieved is custom


class TestGetRegistrySingleton:
    def test_get_registry_returns_global_singleton(self):
        """get_registry() returns the same instance on repeated calls."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
