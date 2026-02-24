"""Built-in agent template definitions.

Provides 13 pre-built agent templates covering common roles:
test analysis, security auditing, code review, documentation,
performance optimization, architecture analysis, refactoring,
test generation/validation, reporting, documentation analysis,
synthesis, and general-purpose agents.

Templates are registered into the global registry on import.

Example:
    >>> from attune.orchestration.agent_templates import get_all_templates
    >>> templates = get_all_templates()
    >>> len(templates) >= 13
    True
"""

import logging

from .models import AgentTemplate, ResourceRequirements
from .registry import _register_template

logger = logging.getLogger(__name__)


# Template 1: Test Coverage Analyzer
_TEST_COVERAGE_ANALYZER = AgentTemplate(
    id="test_coverage_analyzer",
    role="Test Coverage Expert",
    capabilities=["analyze_gaps", "suggest_tests", "validate_coverage"],
    tier_preference="CAPABLE",
    tools=["coverage_analyzer", "ast_parser"],
    default_instructions=(
        "You are a test coverage expert. Analyze the codebase to:\n"
        "1. Identify test coverage gaps\n"
        "2. Suggest specific tests to improve coverage\n"
        "3. Validate that coverage meets quality gates\n"
        "Focus on high-value test cases that improve code quality."
    ),
    quality_gates={"min_coverage": 80, "min_quality_score": 7},
    resource_requirements=ResourceRequirements(
        min_tokens=2000,
        max_tokens=15000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)

# Template 2: Security Auditor
_SECURITY_AUDITOR = AgentTemplate(
    id="security_auditor",
    role="Security Auditor",
    capabilities=[
        "vulnerability_scan",
        "threat_modeling",
        "compliance_check",
    ],
    tier_preference="PREMIUM",
    tools=["security_scanner", "bandit", "dependency_checker"],
    default_instructions=(
        "You are a security auditor. Perform comprehensive security analysis:\n"
        "1. Scan for common vulnerabilities (OWASP Top 10)\n"
        "2. Perform threat modeling for critical components\n"
        "3. Verify compliance with security standards\n"
        "4. Generate remediation plan for findings\n"
        "Prioritize critical and high-severity issues."
    ),
    quality_gates={
        "max_critical_issues": 0,
        "max_high_issues": 0,
        "min_compliance_score": 90,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=5000,
        max_tokens=30000,
        timeout_seconds=900,
        memory_mb=2048,
    ),
)

# Template 3: Code Reviewer
_CODE_REVIEWER = AgentTemplate(
    id="code_reviewer",
    role="Code Quality Reviewer",
    capabilities=[
        "code_review",
        "quality_assessment",
        "best_practices_check",
    ],
    tier_preference="CAPABLE",
    tools=["ast_parser", "complexity_analyzer", "style_checker"],
    default_instructions=(
        "You are a code quality reviewer. Review code for:\n"
        "1. Code quality and maintainability\n"
        "2. Adherence to best practices\n"
        "3. Potential bugs and edge cases\n"
        "4. Performance considerations\n"
        "Provide actionable feedback with specific examples."
    ),
    quality_gates={
        "min_quality_score": 7,
        "max_complexity": 15,
        "min_test_coverage": 80,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=3000,
        max_tokens=20000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)

# Template 4: Documentation Writer
_DOCUMENTATION_WRITER = AgentTemplate(
    id="documentation_writer",
    role="Documentation Writer",
    capabilities=[
        "generate_docs",
        "check_completeness",
        "update_examples",
    ],
    tier_preference="CHEAP",
    tools=["ast_parser", "doc_generator"],
    default_instructions=(
        "You are a documentation writer. Create clear, comprehensive docs:\n"
        "1. Generate API documentation from code\n"
        "2. Write usage examples and tutorials\n"
        "3. Update existing documentation for consistency\n"
        "4. Verify all public APIs are documented\n"
        "Focus on clarity and usefulness for developers."
    ),
    quality_gates={
        "min_doc_coverage": 100,
        "min_example_count": 3,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=1000,
        max_tokens=10000,
        timeout_seconds=300,
        memory_mb=512,
    ),
)

# Template 5: Performance Optimizer
_PERFORMANCE_OPTIMIZER = AgentTemplate(
    id="performance_optimizer",
    role="Performance Optimizer",
    capabilities=[
        "profile_code",
        "identify_bottlenecks",
        "suggest_optimizations",
    ],
    tier_preference="CAPABLE",
    tools=["profiler", "complexity_analyzer", "benchmark_runner"],
    default_instructions=(
        "You are a performance optimizer. Analyze and improve performance:\n"
        "1. Profile code to identify bottlenecks\n"
        "2. Analyze time and space complexity\n"
        "3. Suggest specific optimizations\n"
        "4. Validate improvements with benchmarks\n"
        "Focus on high-impact optimizations with measurable results."
    ),
    quality_gates={
        "min_performance_improvement": 20,
        "max_regression_percent": 5,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=2000,
        max_tokens=15000,
        timeout_seconds=900,
        memory_mb=2048,
    ),
)

# Template 6: Architecture Analyst
_ARCHITECTURE_ANALYST = AgentTemplate(
    id="architecture_analyst",
    role="Architecture Analyst",
    capabilities=[
        "analyze_architecture",
        "identify_patterns",
        "suggest_improvements",
    ],
    tier_preference="PREMIUM",
    tools=["dependency_analyzer", "pattern_detector", "metrics_collector"],
    default_instructions=(
        "You are an architecture analyst. Analyze system architecture:\n"
        "1. Map dependencies and component relationships\n"
        "2. Identify architectural patterns and anti-patterns\n"
        "3. Assess scalability and maintainability\n"
        "4. Suggest architectural improvements\n"
        "Focus on long-term maintainability and system evolution."
    ),
    quality_gates={
        "max_circular_dependencies": 0,
        "min_modularity_score": 7,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=5000,
        max_tokens=30000,
        timeout_seconds=900,
        memory_mb=2048,
    ),
)

# Template 7: Refactoring Specialist
_REFACTORING_SPECIALIST = AgentTemplate(
    id="refactoring_specialist",
    role="Refactoring Specialist",
    capabilities=[
        "identify_code_smells",
        "suggest_refactorings",
        "validate_changes",
    ],
    tier_preference="CAPABLE",
    tools=[
        "ast_parser",
        "complexity_analyzer",
        "duplication_detector",
    ],
    default_instructions=(
        "You are a refactoring specialist. Improve code structure:\n"
        "1. Identify code smells and technical debt\n"
        "2. Suggest specific refactorings\n"
        "3. Ensure behavior preservation\n"
        "4. Validate improvements with tests\n"
        "Focus on improving maintainability without changing behavior."
    ),
    quality_gates={
        "max_duplication_percent": 5,
        "max_complexity": 10,
        "min_test_coverage": 90,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=2000,
        max_tokens=15000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)

# Template 8: Test Generator
_TEST_GENERATOR = AgentTemplate(
    id="test_generator",
    role="Test Generator",
    capabilities=[
        "generate_unit_tests",
        "generate_integration_tests",
        "create_test_fixtures",
    ],
    tier_preference="CAPABLE",
    tools=["ast_parser", "pytest", "test_framework"],
    default_instructions=(
        "You are a test generator. Create comprehensive tests:\n"
        "1. Generate unit tests for uncovered code paths\n"
        "2. Create integration tests for component interactions\n"
        "3. Include edge cases and boundary conditions\n"
        "4. Use appropriate assertions and fixtures\n"
        "Focus on high-value tests that catch real bugs."
    ),
    quality_gates={
        "min_assertions_per_test": 1,
        "max_test_complexity": 10,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=2000,
        max_tokens=20000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)

# Template 9: Test Validator
_TEST_VALIDATOR = AgentTemplate(
    id="test_validator",
    role="Test Validator",
    capabilities=[
        "validate_tests",
        "run_tests",
        "verify_coverage",
    ],
    tier_preference="CHEAP",
    tools=["pytest", "coverage_analyzer"],
    default_instructions=(
        "You are a test validator. Verify test quality:\n"
        "1. Run generated tests to verify they pass\n"
        "2. Check that tests actually test the intended behavior\n"
        "3. Verify coverage improvements\n"
        "4. Identify flaky or unreliable tests\n"
        "Focus on ensuring test reliability and correctness."
    ),
    quality_gates={
        "min_pass_rate": 100,
        "max_flaky_tests": 0,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=1000,
        max_tokens=8000,
        timeout_seconds=300,
        memory_mb=512,
    ),
)

# Template 10: Report Generator
_REPORT_GENERATOR = AgentTemplate(
    id="report_generator",
    role="Report Generator",
    capabilities=[
        "generate_reports",
        "summarize_findings",
        "create_recommendations",
    ],
    tier_preference="CHEAP",
    tools=["markdown_writer"],
    default_instructions=(
        "You are a report generator. Create clear, actionable reports:\n"
        "1. Summarize key findings from analysis\n"
        "2. Prioritize issues by severity and impact\n"
        "3. Provide specific recommendations\n"
        "4. Include metrics and progress indicators\n"
        "Focus on clarity and actionability for the reader."
    ),
    quality_gates={
        "min_sections": 3,
        "max_report_length": 5000,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=500,
        max_tokens=5000,
        timeout_seconds=180,
        memory_mb=256,
    ),
)

# Template 11: Documentation Analyst
_DOCUMENTATION_ANALYST = AgentTemplate(
    id="documentation_analyst",
    role="Documentation Analyst",
    capabilities=[
        "analyze_docs",
        "find_gaps",
        "check_freshness",
    ],
    tier_preference="CAPABLE",
    tools=["ast_parser", "doc_analyzer", "pydocstyle"],
    default_instructions=(
        "You are a documentation analyst. Analyze documentation quality:\n"
        "1. Identify missing docstrings and documentation\n"
        "2. Find outdated documentation that needs updates\n"
        "3. Check documentation completeness for public APIs\n"
        "4. Verify README and guides are current\n"
        "Focus on finding gaps that impact developer experience."
    ),
    quality_gates={
        "min_doc_coverage": 80,
        "max_stale_docs": 5,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=1500,
        max_tokens=12000,
        timeout_seconds=450,
        memory_mb=768,
    ),
)

# Template 12: Synthesizer
_SYNTHESIZER = AgentTemplate(
    id="synthesizer",
    role="Information Synthesizer",
    capabilities=[
        "synthesize_findings",
        "create_action_plans",
        "prioritize_work",
    ],
    tier_preference="CAPABLE",
    tools=["markdown_writer"],
    default_instructions=(
        "You are an information synthesizer. Combine and prioritize findings:\n"
        "1. Consolidate findings from multiple analyses\n"
        "2. Identify patterns and common themes\n"
        "3. Create prioritized action plans\n"
        "4. Provide clear next steps with owners\n"
        "Focus on actionable synthesis that drives improvements."
    ),
    quality_gates={
        "min_action_items": 3,
        "max_priority_levels": 3,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=1500,
        max_tokens=10000,
        timeout_seconds=400,
        memory_mb=512,
    ),
)

# Template 13: Code Simplifier
_CODE_SIMPLIFIER = AgentTemplate(
    id="code_simplifier",
    role="Code Simplification Specialist",
    capabilities=[
        "complexity_analysis",
        "simplification",
        "dead_code_removal",
    ],
    tier_preference="CAPABLE",
    tools=["ast_parser", "code_metrics"],
    default_instructions=(
        "You are a code simplification specialist. "
        "Your job is to reduce unnecessary complexity:\n"
        "1. Flatten deeply nested conditionals\n"
        "2. Inline trivial helper functions\n"
        "3. Remove dead code paths\n"
        "4. Replace complex patterns with simpler stdlib alternatives\n"
        "5. Reduce unnecessary abstraction layers\n"
        "Preserve all behavior. Simpler is better."
    ),
    quality_gates={
        "min_simplification_score": 5,
        "max_complexity_increase": 0,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=2000,
        max_tokens=15000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)

# Template 14: Generic Agent
_GENERIC_AGENT = AgentTemplate(
    id="generic_agent",
    role="General Purpose Agent",
    capabilities=[
        "analyze",
        "generate",
        "review",
    ],
    tier_preference="CAPABLE",
    tools=["read", "write", "grep"],
    default_instructions=(
        "You are a general purpose agent. Complete the assigned task:\n"
        "1. Understand the task requirements thoroughly\n"
        "2. Gather necessary information and context\n"
        "3. Execute the task systematically\n"
        "4. Verify the results meet success criteria\n"
        "Focus on quality and completeness."
    ),
    quality_gates={
        "min_quality_score": 7,
    },
    resource_requirements=ResourceRequirements(
        min_tokens=1000,
        max_tokens=15000,
        timeout_seconds=600,
        memory_mb=1024,
    ),
)


def _register_all_builtin_templates() -> None:
    """Register all built-in templates into the global registry."""
    templates = [
        _TEST_COVERAGE_ANALYZER,
        _SECURITY_AUDITOR,
        _CODE_REVIEWER,
        _DOCUMENTATION_WRITER,
        _PERFORMANCE_OPTIMIZER,
        _ARCHITECTURE_ANALYST,
        _REFACTORING_SPECIALIST,
        _TEST_GENERATOR,
        _TEST_VALIDATOR,
        _REPORT_GENERATOR,
        _DOCUMENTATION_ANALYST,
        _SYNTHESIZER,
        _CODE_SIMPLIFIER,
        _GENERIC_AGENT,
    ]
    for template in templates:
        _register_template(template)

    logger.info(f"Registered {len(templates)} agent templates")


# Register on import
_register_all_builtin_templates()
