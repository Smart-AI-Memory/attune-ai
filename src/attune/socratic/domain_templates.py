"""Domain-Specific Agent Templates (backward-compatible re-exports).

This module re-exports all public symbols from the refactored
sub-modules so that existing imports like:

    from attune.socratic.domain_templates import Domain
    from attune.socratic.domain_templates import DomainTemplateRegistry

continue to work without modification.

Actual implementations live in:
- domain_models.py    (Domain, AgentTemplate, WorkflowTemplate,
                       DomainTemplate)
- agent_templates.py  (agent template instances)
- workflow_templates.py (workflow template instances)
- domain_registry.py  (DomainTemplateRegistry, get_registry)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# Agent template instances
from .agent_templates import (
    CI_CD_ANALYZER,
    CODE_REVIEWER,
    COMPLIANCE_AUDITOR,
    DATA_VALIDATOR,
    DOCUMENTATION_WRITER,
    INCIDENT_RESPONDER,
    INFRASTRUCTURE_REVIEWER,
    MODEL_EVALUATOR,
    PENETRATION_TESTER,
    PERFORMANCE_ANALYZER,
    REFACTORING_ADVISOR,
    RESULT_SYNTHESIZER,
    SECURITY_SCANNER,
    TEST_GENERATOR,
)

# Core data structures
from .domain_models import (
    AgentTemplate,
    Domain,
    DomainTemplate,
    WorkflowTemplate,
)

# Registry
from .domain_registry import (
    REGISTRY,
    DomainTemplateRegistry,
    get_registry,
)

# Workflow template instances
from .workflow_templates import (
    CODE_REVIEW_WORKFLOW,
    DEVOPS_CI_CD_WORKFLOW,
    PERFORMANCE_WORKFLOW,
    SECURITY_AUDIT_WORKFLOW,
    TESTING_WORKFLOW,
)

__all__ = [
    # Domain enum and dataclasses
    "Domain",
    "AgentTemplate",
    "WorkflowTemplate",
    "DomainTemplate",
    # Agent template instances
    "CODE_REVIEWER",
    "SECURITY_SCANNER",
    "TEST_GENERATOR",
    "PERFORMANCE_ANALYZER",
    "DOCUMENTATION_WRITER",
    "REFACTORING_ADVISOR",
    "COMPLIANCE_AUDITOR",
    "PENETRATION_TESTER",
    "DATA_VALIDATOR",
    "MODEL_EVALUATOR",
    "CI_CD_ANALYZER",
    "INFRASTRUCTURE_REVIEWER",
    "INCIDENT_RESPONDER",
    "RESULT_SYNTHESIZER",
    # Workflow template instances
    "CODE_REVIEW_WORKFLOW",
    "SECURITY_AUDIT_WORKFLOW",
    "TESTING_WORKFLOW",
    "PERFORMANCE_WORKFLOW",
    "DEVOPS_CI_CD_WORKFLOW",
    # Registry
    "DomainTemplateRegistry",
    "REGISTRY",
    "get_registry",
]
