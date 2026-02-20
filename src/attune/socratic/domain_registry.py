"""Domain template registry.

Provides the DomainTemplateRegistry class that manages agent templates,
workflow templates, and domain configurations. Includes domain detection
from goal text and a global singleton instance.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .agent_templates import (
    ALL_AGENT_TEMPLATES,
    CI_CD_ANALYZER,
    CODE_REVIEWER,
    COMPLIANCE_AUDITOR,
    PERFORMANCE_ANALYZER,
    REFACTORING_ADVISOR,
    RESULT_SYNTHESIZER,
    SECURITY_SCANNER,
    TEST_GENERATOR,
)
from .domain_models import (
    AgentTemplate,
    Domain,
    DomainTemplate,
    WorkflowTemplate,
)
from .workflow_templates import (
    ALL_WORKFLOW_TEMPLATES,
    CODE_REVIEW_WORKFLOW,
    DEVOPS_CI_CD_WORKFLOW,
    PERFORMANCE_WORKFLOW,
    SECURITY_AUDIT_WORKFLOW,
    TESTING_WORKFLOW,
)


class DomainTemplateRegistry:
    """Registry of domain templates."""

    def __init__(self) -> None:
        """Initialize registry with built-in templates."""
        self._agents: dict[str, AgentTemplate] = {}
        self._workflows: dict[str, WorkflowTemplate] = {}
        self._domains: dict[Domain, DomainTemplate] = {}

        # Register built-in templates
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in agent and workflow templates."""
        # Register agent templates
        for agent in ALL_AGENT_TEMPLATES:
            self._agents[agent.template_id] = agent

        # Register workflow templates
        for workflow in ALL_WORKFLOW_TEMPLATES:
            self._workflows[workflow.template_id] = workflow

        # Create domain templates
        self._domains[Domain.CODE_REVIEW] = DomainTemplate(
            domain=Domain.CODE_REVIEW,
            name="Code Review",
            description="Automated code review and quality analysis",
            agents=[
                CODE_REVIEWER,
                SECURITY_SCANNER,
                RESULT_SYNTHESIZER,
            ],
            workflows=[CODE_REVIEW_WORKFLOW],
            default_workflow="code_review_standard",
            keywords=[
                "review",
                "quality",
                "lint",
                "style",
                "clean",
                "readable",
            ],
            required_tools=["read_file", "grep_code"],
            optional_tools=["analyze_ast", "run_linter"],
        )

        self._domains[Domain.SECURITY_AUDIT] = DomainTemplate(
            domain=Domain.SECURITY_AUDIT,
            name="Security Audit",
            description=("Security vulnerability scanning and compliance " "auditing"),
            agents=[
                SECURITY_SCANNER,
                COMPLIANCE_AUDITOR,
                RESULT_SYNTHESIZER,
            ],
            workflows=[SECURITY_AUDIT_WORKFLOW],
            default_workflow="security_audit_comprehensive",
            keywords=[
                "security",
                "vulnerability",
                "audit",
                "compliance",
                "penetration",
                "CVE",
                "OWASP",
            ],
            required_tools=["read_file", "security_scan"],
            optional_tools=["grep_code", "analyze_ast"],
        )

        self._domains[Domain.TESTING] = DomainTemplate(
            domain=Domain.TESTING,
            name="Testing",
            description=("Automated test generation and coverage improvement"),
            agents=[
                TEST_GENERATOR,
                CODE_REVIEWER,
                RESULT_SYNTHESIZER,
            ],
            workflows=[TESTING_WORKFLOW],
            default_workflow="test_generation_comprehensive",
            keywords=[
                "test",
                "coverage",
                "unit",
                "integration",
                "e2e",
                "pytest",
                "jest",
            ],
            required_tools=[
                "read_file",
                "run_tests",
                "write_file",
            ],
            optional_tools=["analyze_ast"],
        )

        self._domains[Domain.PERFORMANCE] = DomainTemplate(
            domain=Domain.PERFORMANCE,
            name="Performance",
            description="Performance analysis and optimization",
            agents=[
                PERFORMANCE_ANALYZER,
                REFACTORING_ADVISOR,
                RESULT_SYNTHESIZER,
            ],
            workflows=[PERFORMANCE_WORKFLOW],
            default_workflow="performance_analysis",
            keywords=[
                "performance",
                "optimize",
                "speed",
                "memory",
                "profile",
                "bottleneck",
            ],
            required_tools=["read_file", "analyze_ast"],
            optional_tools=["run_profiler"],
        )

        self._domains[Domain.CI_CD] = DomainTemplate(
            domain=Domain.CI_CD,
            name="CI/CD",
            description=("CI/CD pipeline analysis and optimization"),
            agents=[
                CI_CD_ANALYZER,
                SECURITY_SCANNER,
                RESULT_SYNTHESIZER,
            ],
            workflows=[DEVOPS_CI_CD_WORKFLOW],
            default_workflow="ci_cd_optimization",
            keywords=[
                "ci",
                "cd",
                "pipeline",
                "github actions",
                "jenkins",
                "deployment",
            ],
            required_tools=["read_file", "grep_code"],
            optional_tools=["run_script"],
        )

    def get_agent(self, template_id: str) -> AgentTemplate | None:
        """Get agent template by ID."""
        return self._agents.get(template_id)

    def get_workflow(self, template_id: str) -> WorkflowTemplate | None:
        """Get workflow template by ID."""
        return self._workflows.get(template_id)

    def get_domain(self, domain: Domain) -> DomainTemplate | None:
        """Get domain template."""
        return self._domains.get(domain)

    def list_agents(self, domain: Domain | None = None) -> list[AgentTemplate]:
        """List agent templates, optionally filtered by domain."""
        if domain is None:
            return list(self._agents.values())

        domain_template = self._domains.get(domain)
        if domain_template:
            return domain_template.agents
        return []

    def list_workflows(self, domain: Domain | None = None) -> list[WorkflowTemplate]:
        """List workflow templates, optionally filtered by domain."""
        if domain is None:
            return list(self._workflows.values())

        domain_template = self._domains.get(domain)
        if domain_template:
            return domain_template.workflows
        return []

    def list_domains(self) -> list[Domain]:
        """List all supported domains."""
        return list(self._domains.keys())

    def detect_domain(self, goal: str) -> tuple[Domain, float]:
        """Detect domain from goal text.

        Args:
            goal: Goal text

        Returns:
            (domain, confidence) tuple
        """
        goal_lower = goal.lower()
        scores: dict[Domain, float] = {}

        for domain, template in self._domains.items():
            score = 0.0
            for keyword in template.keywords:
                if keyword in goal_lower:
                    score += 1.0
                    # Bonus for word boundary match
                    if f" {keyword} " in f" {goal_lower} ":
                        score += 0.5

            if score > 0:
                # Normalize by number of keywords
                scores[domain] = score / len(template.keywords)

        if not scores:
            return Domain.GENERAL, 0.3

        best_domain = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = min(scores[best_domain] * 2, 1.0)  # Scale up, cap at 1.0

        return best_domain, confidence

    def get_default_workflow(self, domain: Domain) -> WorkflowTemplate | None:
        """Get default workflow for a domain."""
        domain_template = self._domains.get(domain)
        if domain_template:
            return self._workflows.get(domain_template.default_workflow)
        return None

    def register_agent(self, template: AgentTemplate) -> None:
        """Register a custom agent template."""
        self._agents[template.template_id] = template

    def register_workflow(self, template: WorkflowTemplate) -> None:
        """Register a custom workflow template."""
        self._workflows[template.template_id] = template

    def register_domain(self, template: DomainTemplate) -> None:
        """Register a custom domain template."""
        self._domains[template.domain] = template


# Global registry instance
REGISTRY = DomainTemplateRegistry()


def get_registry() -> DomainTemplateRegistry:
    """Get the global domain template registry."""
    return REGISTRY
