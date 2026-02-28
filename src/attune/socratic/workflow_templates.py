"""Pre-configured workflow template instances.

Workflow templates define multi-stage agent pipelines for specific
domains including code review, security auditing, testing,
performance analysis, and CI/CD optimization.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .domain_models import Domain, WorkflowTemplate

# =============================================================================
# SOFTWARE DEVELOPMENT WORKFLOWS
# =============================================================================

CODE_REVIEW_WORKFLOW = WorkflowTemplate(
    template_id="code_review_standard",
    name="Standard Code Review",
    description=("Comprehensive code review covering quality, security, and tests"),
    domain=Domain.CODE_REVIEW,
    agents=["code_reviewer", "security_scanner", "result_synthesizer"],
    stages=[
        {
            "stage_id": "analysis",
            "name": "Code Analysis",
            "agents": ["code_reviewer", "security_scanner"],
            "parallel": True,
        },
        {
            "stage_id": "synthesis",
            "name": "Result Synthesis",
            "agents": ["result_synthesizer"],
            "parallel": False,
            "dependencies": ["analysis"],
        },
    ],
    success_metrics=[
        {
            "metric_id": "issues_found",
            "name": "Issues Identified",
            "type": "count",
            "direction": "higher_is_better",
        },
        {
            "metric_id": "critical_issues",
            "name": "Critical Issues",
            "type": "count",
            "target": 0,
            "direction": "lower_is_better",
        },
    ],
    estimated_duration="moderate",
    estimated_cost="moderate",
    tags=["code_review", "quality"],
)

TESTING_WORKFLOW = WorkflowTemplate(
    template_id="test_generation_comprehensive",
    name="Comprehensive Test Generation",
    description="Generate unit tests with high coverage",
    domain=Domain.TESTING,
    agents=[
        "test_generator",
        "code_reviewer",
        "result_synthesizer",
    ],
    stages=[
        {
            "stage_id": "generation",
            "name": "Test Generation",
            "agents": ["test_generator"],
            "parallel": False,
        },
        {
            "stage_id": "review",
            "name": "Test Review",
            "agents": ["code_reviewer"],
            "parallel": False,
            "dependencies": ["generation"],
        },
        {
            "stage_id": "synthesis",
            "name": "Summary",
            "agents": ["result_synthesizer"],
            "parallel": False,
            "dependencies": ["review"],
        },
    ],
    success_metrics=[
        {
            "metric_id": "tests_generated",
            "name": "Tests Generated",
            "type": "count",
            "direction": "higher_is_better",
        },
        {
            "metric_id": "coverage_improvement",
            "name": "Coverage Improvement",
            "type": "percentage",
            "target": 80,
            "direction": "higher_is_better",
        },
    ],
    estimated_duration="moderate",
    estimated_cost="moderate",
    tags=["testing", "coverage", "quality"],
)

PERFORMANCE_WORKFLOW = WorkflowTemplate(
    template_id="performance_analysis",
    name="Performance Analysis",
    description="Analyze and optimize code performance",
    domain=Domain.PERFORMANCE,
    agents=[
        "performance_analyzer",
        "refactoring_advisor",
        "result_synthesizer",
    ],
    stages=[
        {
            "stage_id": "analysis",
            "name": "Performance Analysis",
            "agents": ["performance_analyzer"],
            "parallel": False,
        },
        {
            "stage_id": "optimization",
            "name": "Optimization Recommendations",
            "agents": ["refactoring_advisor"],
            "parallel": False,
            "dependencies": ["analysis"],
        },
        {
            "stage_id": "synthesis",
            "name": "Summary",
            "agents": ["result_synthesizer"],
            "parallel": False,
            "dependencies": ["optimization"],
        },
    ],
    success_metrics=[
        {
            "metric_id": "bottlenecks_found",
            "name": "Bottlenecks Identified",
            "type": "count",
        },
        {
            "metric_id": "optimization_potential",
            "name": "Optimization Potential",
            "type": "percentage",
        },
    ],
    estimated_duration="moderate",
    estimated_cost="moderate",
    tags=["performance", "optimization"],
)

# =============================================================================
# SECURITY WORKFLOWS
# =============================================================================

SECURITY_AUDIT_WORKFLOW = WorkflowTemplate(
    template_id="security_audit_comprehensive",
    name="Comprehensive Security Audit",
    description=("Full security audit including vulnerability scanning and compliance"),
    domain=Domain.SECURITY_AUDIT,
    agents=[
        "security_scanner",
        "compliance_auditor",
        "result_synthesizer",
    ],
    stages=[
        {
            "stage_id": "scanning",
            "name": "Security Scanning",
            "agents": ["security_scanner"],
            "parallel": False,
        },
        {
            "stage_id": "compliance",
            "name": "Compliance Check",
            "agents": ["compliance_auditor"],
            "parallel": False,
            "dependencies": ["scanning"],
        },
        {
            "stage_id": "synthesis",
            "name": "Report Generation",
            "agents": ["result_synthesizer"],
            "parallel": False,
            "dependencies": ["scanning", "compliance"],
        },
    ],
    success_metrics=[
        {
            "metric_id": "vulnerabilities_found",
            "name": "Vulnerabilities Found",
            "type": "count",
        },
        {
            "metric_id": "compliance_score",
            "name": "Compliance Score",
            "type": "percentage",
            "target": 90,
            "direction": "higher_is_better",
        },
    ],
    estimated_duration="slow",
    estimated_cost="expensive",
    tags=["security", "compliance", "audit"],
)

# =============================================================================
# DEVOPS WORKFLOWS
# =============================================================================

DEVOPS_CI_CD_WORKFLOW = WorkflowTemplate(
    template_id="ci_cd_optimization",
    name="CI/CD Pipeline Optimization",
    description="Analyze and optimize CI/CD pipelines",
    domain=Domain.CI_CD,
    agents=[
        "ci_cd_analyzer",
        "security_scanner",
        "result_synthesizer",
    ],
    stages=[
        {
            "stage_id": "pipeline_analysis",
            "name": "Pipeline Analysis",
            "agents": ["ci_cd_analyzer"],
            "parallel": False,
        },
        {
            "stage_id": "security_check",
            "name": "Security Check",
            "agents": ["security_scanner"],
            "parallel": False,
            "dependencies": ["pipeline_analysis"],
        },
        {
            "stage_id": "synthesis",
            "name": "Recommendations",
            "agents": ["result_synthesizer"],
            "parallel": False,
            "dependencies": ["security_check"],
        },
    ],
    success_metrics=[
        {
            "metric_id": "pipeline_time_reduction",
            "name": "Time Reduction Potential",
            "type": "percentage",
        },
        {
            "metric_id": "security_issues",
            "name": "Security Issues",
            "type": "count",
            "target": 0,
        },
    ],
    estimated_duration="moderate",
    estimated_cost="moderate",
    tags=["devops", "ci_cd", "pipeline"],
)

# Convenience list of all built-in workflow templates
ALL_WORKFLOW_TEMPLATES = [
    CODE_REVIEW_WORKFLOW,
    SECURITY_AUDIT_WORKFLOW,
    TESTING_WORKFLOW,
    PERFORMANCE_WORKFLOW,
    DEVOPS_CI_CD_WORKFLOW,
]
