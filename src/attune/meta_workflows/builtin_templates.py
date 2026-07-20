"""Built-in meta-workflow templates.

These templates replace the deprecated Crew-based workflows with equivalent
functionality using the meta-workflow system.

Migration replacements:
- ReleasePreparationCrew → release-prep template
- TestCoverageBoostCrew → test-coverage-boost template
- TestMaintenanceCrew → test-maintenance template
- ManageDocumentationCrew → manage-docs template

Created: 2026-01-18
Purpose: Provide drop-in replacements for deprecated Crew workflows
"""

from attune.meta_workflows.models import (
    AgentCompositionRule,
    FormQuestion,
    FormSchema,
    MetaWorkflowTemplate,
    QuestionType,
    TierStrategy,
)

# =============================================================================
# Release Preparation Template
# =============================================================================

RELEASE_PREP_TEMPLATE = MetaWorkflowTemplate(
    template_id="release-prep",
    name="Release Preparation",
    description="Comprehensive release readiness assessment using multi-agent collaboration",
    version="1.0.0",
    tags=["release", "quality", "security", "testing", "documentation"],
    author="attune-ai",
    estimated_cost_range=(0.10, 0.75),
    estimated_duration_minutes=10,
    form_schema=FormSchema(
        title="Release Preparation Configuration",
        description="Configure release readiness checks for your project",
        questions=[
            FormQuestion(
                id="security_scan",
                text="Run security vulnerability scan?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Scan for OWASP Top 10 vulnerabilities and dependency issues",
            ),
            FormQuestion(
                id="test_coverage_check",
                text="Verify test coverage meets threshold?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Check that test coverage meets minimum requirements",
            ),
            FormQuestion(
                id="coverage_threshold",
                text="Minimum coverage threshold (%)",
                type=QuestionType.SINGLE_SELECT,
                options=["70%", "80%", "85%", "90%"],
                default="80%",
                help_text="Tests must meet this coverage percentage",
            ),
            FormQuestion(
                id="quality_review",
                text="Run code quality review?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Check for code smells, complexity issues, and best practices",
            ),
            FormQuestion(
                id="doc_verification",
                text="Verify documentation completeness?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Check that all public APIs are documented",
            ),
        ],
    ),
    agent_composition_rules=[
        AgentCompositionRule(
            role="Security Auditor",
            base_template="security_auditor",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["grep", "bandit", "safety"],
            required_responses={"security_scan": "Yes"},
            config_mapping={},
            success_criteria=[
                "No critical vulnerabilities found",
                "All dependencies are secure",
            ],
        ),
        AgentCompositionRule(
            role="Test Coverage Analyst",
            base_template="test_coverage_analyzer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["pytest", "coverage"],
            required_responses={"test_coverage_check": "Yes"},
            config_mapping={"coverage_threshold": "min_coverage"},
            success_criteria=[
                "Coverage meets threshold",
                "All tests pass",
            ],
        ),
        AgentCompositionRule(
            role="Code Quality Reviewer",
            base_template="code_reviewer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["ruff", "mypy"],
            required_responses={"quality_review": "Yes"},
            config_mapping={},
            success_criteria=[
                "No high-severity issues",
                "Complexity within bounds",
            ],
        ),
        AgentCompositionRule(
            role="Documentation Specialist",
            base_template="documentation_writer",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["pydocstyle"],
            required_responses={"doc_verification": "Yes"},
            config_mapping={},
            success_criteria=[
                "All public APIs documented",
                "README is current",
            ],
        ),
    ],
)

# =============================================================================
# Test Coverage Boost Template
# =============================================================================

TEST_COVERAGE_BOOST_TEMPLATE = MetaWorkflowTemplate(
    template_id="test-coverage-boost",
    name="Test Coverage Boost",
    description="Multi-agent test generation with gap analysis and validation",
    version="1.0.0",
    tags=["testing", "coverage", "test-generation"],
    author="attune-ai",
    estimated_cost_range=(0.15, 1.00),
    estimated_duration_minutes=15,
    form_schema=FormSchema(
        title="Test Coverage Boost Configuration",
        description="Configure test generation to improve coverage",
        questions=[
            FormQuestion(
                id="target_coverage",
                text="Target coverage percentage",
                type=QuestionType.SINGLE_SELECT,
                options=["70%", "75%", "80%", "85%", "90%"],
                default="80%",
                help_text="Generate tests until this coverage is reached",
            ),
            FormQuestion(
                id="test_style",
                text="Test style preference",
                type=QuestionType.SINGLE_SELECT,
                options=["pytest", "unittest", "auto-detect"],
                default="auto-detect",
                help_text="Test framework style to use",
            ),
            FormQuestion(
                id="prioritize_high_impact",
                text="Prioritize high-impact files?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Focus on complex, frequently-used code first",
            ),
            FormQuestion(
                id="include_edge_cases",
                text="Include edge case tests?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Generate tests for boundary conditions",
            ),
        ],
    ),
    agent_composition_rules=[
        AgentCompositionRule(
            role="Gap Analyzer",
            base_template="test_coverage_analyzer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["pytest-cov", "coverage"],
            required_responses={},
            config_mapping={"target_coverage": "target_coverage"},
            success_criteria=[
                "Identified coverage gaps",
                "Prioritized files by impact",
            ],
        ),
        AgentCompositionRule(
            role="Test Generator",
            base_template="test_generator",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["ast", "pytest"],
            required_responses={},
            config_mapping={
                "test_style": "test_style",
                "include_edge_cases": "edge_cases",
            },
            success_criteria=[
                "Tests are syntactically correct",
                "Tests cover identified gaps",
            ],
        ),
        AgentCompositionRule(
            role="Test Validator",
            base_template="test_validator",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["pytest"],
            required_responses={},
            config_mapping={},
            success_criteria=[
                "Generated tests pass",
                "Coverage improved",
            ],
        ),
    ],
)

# =============================================================================
# Test Maintenance Template
# =============================================================================

TEST_MAINTENANCE_TEMPLATE = MetaWorkflowTemplate(
    template_id="test-maintenance",
    name="Test Maintenance",
    description="Automated test lifecycle management with gap analysis and validation",
    version="1.0.0",
    tags=["testing", "maintenance", "automation"],
    author="attune-ai",
    estimated_cost_range=(0.10, 0.80),
    estimated_duration_minutes=12,
    form_schema=FormSchema(
        title="Test Maintenance Configuration",
        description="Configure test maintenance and generation",
        questions=[
            FormQuestion(
                id="mode",
                text="Maintenance mode",
                type=QuestionType.SINGLE_SELECT,
                options=["full", "analyze", "generate", "validate", "report"],
                default="full",
                help_text="Full runs all agents; other modes run specific phases",
            ),
            FormQuestion(
                id="max_files",
                text="Maximum files to process",
                type=QuestionType.SINGLE_SELECT,
                options=["5", "10", "20", "30", "50"],
                default="30",
                help_text="Limit number of files to process per run",
            ),
            FormQuestion(
                id="staleness_threshold",
                text="Staleness threshold (days)",
                type=QuestionType.SINGLE_SELECT,
                options=["3", "7", "14", "30"],
                default="7",
                help_text="Tests older than this are considered stale",
            ),
            FormQuestion(
                id="auto_validation",
                text="Enable auto-validation?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Automatically run generated tests to verify they work",
            ),
        ],
    ),
    agent_composition_rules=[
        AgentCompositionRule(
            role="Test Analyst",
            base_template="test_coverage_analyzer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["pytest-cov", "coverage"],
            required_responses={"mode": ["full", "analyze"]},
            config_mapping={
                "max_files": "max_files_per_run",
                "staleness_threshold": "staleness_days",
            },
            success_criteria=[
                "Coverage gaps identified",
                "Stale tests detected",
            ],
        ),
        AgentCompositionRule(
            role="Test Generator",
            base_template="test_generator",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["ast", "pytest"],
            required_responses={"mode": ["full", "generate"]},
            config_mapping={},
            success_criteria=[
                "Tests generated for priority files",
            ],
        ),
        AgentCompositionRule(
            role="Test Validator",
            base_template="test_validator",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["pytest"],
            required_responses={"mode": ["full", "validate"], "auto_validation": "Yes"},
            config_mapping={},
            success_criteria=[
                "Generated tests pass",
            ],
        ),
        AgentCompositionRule(
            role="Test Reporter",
            base_template="report_generator",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=[],
            required_responses={},
            config_mapping={},
            success_criteria=[
                "Status report generated",
            ],
        ),
    ],
)

# =============================================================================
# Documentation Management Template
# =============================================================================

MANAGE_DOCS_TEMPLATE = MetaWorkflowTemplate(
    template_id="manage-docs",
    name="Documentation Management",
    description="Ensure program files are documented and docs stay in sync with code",
    version="1.0.0",
    tags=["documentation", "docstrings", "readme"],
    author="attune-ai",
    estimated_cost_range=(0.08, 0.50),
    estimated_duration_minutes=8,
    form_schema=FormSchema(
        title="Documentation Management Configuration",
        description="Configure documentation sync and gap detection",
        questions=[
            FormQuestion(
                id="check_docstrings",
                text="Check for missing docstrings?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Identify functions and classes without docstrings",
            ),
            FormQuestion(
                id="check_readme",
                text="Check README freshness?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Verify README reflects recent code changes",
            ),
            FormQuestion(
                id="check_api_docs",
                text="Check API documentation?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Verify all public APIs are documented",
            ),
            FormQuestion(
                id="suggest_updates",
                text="Generate update suggestions?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Provide specific recommendations for documentation improvements",
            ),
        ],
    ),
    agent_composition_rules=[
        AgentCompositionRule(
            role="Documentation Analyst",
            base_template="documentation_analyst",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["ast", "pydocstyle"],
            required_responses={},
            config_mapping={
                "check_docstrings": "analyze_docstrings",
                "check_readme": "analyze_readme",
                "check_api_docs": "analyze_api_docs",
            },
            success_criteria=[
                "Documentation gaps identified",
            ],
        ),
        AgentCompositionRule(
            role="Documentation Reviewer",
            base_template="documentation_writer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=[],
            required_responses={},
            config_mapping={},
            success_criteria=[
                "Findings validated",
                "False positives removed",
            ],
        ),
        AgentCompositionRule(
            role="Documentation Synthesizer",
            base_template="synthesizer",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=[],
            required_responses={"suggest_updates": "Yes"},
            config_mapping={},
            success_criteria=[
                "Prioritized action plan created",
            ],
        ),
    ],
)

# =============================================================================
# Feature Overview Template
# =============================================================================

FEATURE_OVERVIEW_TEMPLATE = MetaWorkflowTemplate(
    template_id="feature-overview",
    name="Feature Overview Generator",
    description="Generate comprehensive technical documentation for code modules, suitable for architects, engineers, and content creators",
    version="1.0.0",
    tags=["documentation", "architecture", "insights", "blog"],
    author="attune-ai",
    estimated_cost_range=(0.40, 0.80),
    estimated_duration_minutes=15,
    form_schema=FormSchema(
        title="Feature Overview Configuration",
        description="Configure technical documentation generation",
        questions=[
            FormQuestion(
                id="target_path",
                text="Which module or directory to analyze?",
                type=QuestionType.TEXT_INPUT,
                default="src/",
                help_text="Path to the code you want to document",
            ),
            FormQuestion(
                id="target_audience",
                text="Who is the primary audience?",
                type=QuestionType.SINGLE_SELECT,
                options=["Architects", "Engineers", "Technical Writers", "All"],
                default="Architects",
                help_text="Tailors the depth and focus of documentation",
            ),
            FormQuestion(
                id="include_blog_summary",
                text="Include blog-ready summary?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Generate a summary suitable for technical blog posts",
            ),
            FormQuestion(
                id="include_diagrams",
                text="Include architecture diagrams?",
                type=QuestionType.BOOLEAN,
                default="Yes",
                help_text="Generate ASCII diagrams showing component relationships",
            ),
        ],
    ),
    agent_composition_rules=[
        AgentCompositionRule(
            role="Code Scanner",
            base_template="generic_agent",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["read", "grep", "glob"],
            required_responses={},
            config_mapping={"target_path": "path"},
            success_criteria=[
                "modules_identified",
                "structure_mapped",
            ],
        ),
        AgentCompositionRule(
            role="Insights Reporter",
            base_template="generic_agent",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["read"],
            required_responses={},
            config_mapping={"target_audience": "audience"},
            success_criteria=[
                "patterns_identified",
                "insights_generated",
            ],
        ),
        AgentCompositionRule(
            role="Architecture Analyst",
            base_template="architecture_analyst",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["read"],
            required_responses={"include_diagrams": "Yes"},
            config_mapping={},
            success_criteria=[
                "diagrams_created",
                "relationships_mapped",
            ],
        ),
        AgentCompositionRule(
            role="Quality Reviewer",
            base_template="code_reviewer",
            tier_strategy=TierStrategy.PREMIUM_ONLY,
            tools=["read"],
            required_responses={},
            config_mapping={},
            success_criteria=[
                "accuracy_validated",
                "completeness_checked",
            ],
        ),
        AgentCompositionRule(
            role="Blog Content Creator",
            base_template="generic_agent",
            tier_strategy=TierStrategy.PREMIUM_ONLY,
            tools=["write"],
            required_responses={"include_blog_summary": "Yes"},
            config_mapping={"target_audience": "audience"},
            success_criteria=[
                "blog_summary_created",
                "audience_appropriate",
            ],
        ),
    ],
)

# =============================================================================
# Template Registry
# =============================================================================

BUILTIN_TEMPLATES = {
    "release-prep": RELEASE_PREP_TEMPLATE,
    "test-coverage-boost": TEST_COVERAGE_BOOST_TEMPLATE,
    "test-maintenance": TEST_MAINTENANCE_TEMPLATE,
    "manage-docs": MANAGE_DOCS_TEMPLATE,
    "feature-overview": FEATURE_OVERVIEW_TEMPLATE,
}


def get_builtin_template(template_id: str) -> MetaWorkflowTemplate | None:
    """Get a built-in template by ID.

    Args:
        template_id: ID of the template to retrieve

    Returns:
        MetaWorkflowTemplate if found, None otherwise

    """
    return BUILTIN_TEMPLATES.get(template_id)


def list_builtin_templates() -> list[str]:
    """List all built-in template IDs.

    Returns:
        List of template IDs

    """
    return list(BUILTIN_TEMPLATES.keys())


def get_all_builtin_templates() -> dict[str, MetaWorkflowTemplate]:
    """Get all built-in templates.

    Returns:
        Dictionary mapping template_id → MetaWorkflowTemplate

    """
    return BUILTIN_TEMPLATES.copy()
