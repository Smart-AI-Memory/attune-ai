"""Domain model definitions for agent templates.

Core data structures used across the domain template system:
- Domain enum (supported knowledge domains)
- AgentTemplate (agent configuration)
- WorkflowTemplate (workflow configuration)
- DomainTemplate (complete domain configuration)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .blueprint import AgentRole


class Domain(Enum):
    """Supported knowledge domains."""

    # Software Development
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"

    # Security
    SECURITY_AUDIT = "security_audit"
    VULNERABILITY_SCAN = "vulnerability_scan"
    COMPLIANCE = "compliance"
    PENETRATION_TESTING = "penetration_testing"

    # Data Science
    DATA_VALIDATION = "data_validation"
    MODEL_EVALUATION = "model_evaluation"
    DATA_PIPELINE = "data_pipeline"
    REPORTING = "reporting"

    # DevOps
    CI_CD = "ci_cd"
    INFRASTRUCTURE = "infrastructure"
    MONITORING = "monitoring"
    INCIDENT_RESPONSE = "incident_response"

    # Legal
    CONTRACT_REVIEW = "contract_review"
    LEGAL_COMPLIANCE = "legal_compliance"
    IP_ANALYSIS = "ip_analysis"

    # Healthcare
    CLINICAL_NOTES = "clinical_notes"
    HIPAA_COMPLIANCE = "hipaa_compliance"
    MEDICAL_CODING = "medical_coding"

    # Financial
    RISK_ANALYSIS = "risk_analysis"
    FRAUD_DETECTION = "fraud_detection"
    FINANCIAL_REPORTING = "financial_reporting"

    # General
    GENERAL = "general"


@dataclass
class AgentTemplate:
    """Template for configuring an agent."""

    template_id: str
    name: str
    description: str
    role: AgentRole
    tools: list[str]
    model_tier: str = "capable"  # cheap, capable, premium
    system_prompt: str = ""
    example_prompts: list[str] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class WorkflowTemplate:
    """Template for configuring a workflow."""

    template_id: str
    name: str
    description: str
    domain: Domain
    agents: list[str]  # Agent template IDs
    stages: list[dict[str, Any]]
    success_metrics: list[dict[str, Any]]
    estimated_duration: str  # fast, moderate, slow
    estimated_cost: str  # cheap, moderate, expensive
    configuration: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class DomainTemplate:
    """Complete template for a domain."""

    domain: Domain
    name: str
    description: str
    agents: list[AgentTemplate]
    workflows: list[WorkflowTemplate]
    default_workflow: str  # Default workflow template ID
    keywords: list[str]  # Keywords for domain detection
    required_tools: list[str]
    optional_tools: list[str]
