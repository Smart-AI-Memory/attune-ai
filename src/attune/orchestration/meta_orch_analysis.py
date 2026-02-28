"""Meta-orchestrator Task Analysis.

Task analysis, classification, capability extraction, agent selection,
and composition pattern selection. Extracted from meta_orchestrator.py
for maintainability.

Contains:
- TaskAnalysisMixin: Task analysis, classification, agent selection,
  pattern selection

Expected attributes on the host class:
    (none - all state accessed via class constants and parameters)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_templates import AgentTemplate, get_template, get_templates_by_capability
from .meta_orchestrator import (
    CompositionPattern,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)

logger = logging.getLogger(__name__)


class TaskAnalysisMixin:
    """Mixin providing task analysis and agent selection for meta-orchestrator."""

    # Keyword patterns for task analysis
    COMPLEXITY_KEYWORDS = {
        TaskComplexity.SIMPLE: [
            "format",
            "lint",
            "check",
            "validate",
            "document",
        ],
        TaskComplexity.MODERATE: [
            "improve",
            "refactor",
            "optimize",
            "test",
            "review",
        ],
        TaskComplexity.COMPLEX: [
            "release",
            "migrate",
            "redesign",
            "architecture",
            "prepare",
        ],
    }

    DOMAIN_KEYWORDS = {
        TaskDomain.TESTING: [
            "test",
            "coverage",
            "pytest",
            "unit test",
            "integration test",
        ],
        TaskDomain.SECURITY: [
            "security",
            "vulnerability",
            "audit",
            "penetration",
            "threat",
        ],
        TaskDomain.CODE_QUALITY: [
            "quality",
            "code review",
            "lint",
            "best practices",
            "maintainability",
        ],
        TaskDomain.DOCUMENTATION: [
            "docs",
            "documentation",
            "readme",
            "guide",
            "tutorial",
        ],
        TaskDomain.PERFORMANCE: [
            "performance",
            "optimize",
            "speed",
            "benchmark",
            "profile",
        ],
        TaskDomain.ARCHITECTURE: [
            "architecture",
            "design",
            "structure",
            "pattern",
            "dependency",
        ],
        TaskDomain.REFACTORING: [
            "refactor",
            "cleanup",
            "simplify",
            "restructure",
            "debt",
        ],
    }

    # Capability mapping by domain
    DOMAIN_CAPABILITIES = {
        TaskDomain.TESTING: [
            "analyze_gaps",
            "suggest_tests",
            "validate_coverage",
        ],
        TaskDomain.SECURITY: [
            "vulnerability_scan",
            "threat_modeling",
            "compliance_check",
        ],
        TaskDomain.CODE_QUALITY: [
            "code_review",
            "quality_assessment",
            "best_practices_check",
        ],
        TaskDomain.DOCUMENTATION: [
            "generate_docs",
            "check_completeness",
            "update_examples",
        ],
        TaskDomain.PERFORMANCE: [
            "profile_code",
            "identify_bottlenecks",
            "suggest_optimizations",
        ],
        TaskDomain.ARCHITECTURE: [
            "analyze_architecture",
            "identify_patterns",
            "suggest_improvements",
        ],
        TaskDomain.REFACTORING: [
            "identify_code_smells",
            "suggest_refactorings",
            "validate_changes",
        ],
    }

    def _analyze_task(self, task: str, context: dict[str, Any]) -> TaskRequirements:
        """Analyze task to extract requirements.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            TaskRequirements with extracted information

        """
        task_lower = task.lower()

        # Determine complexity
        complexity = self._classify_complexity(task_lower)

        # Determine domain
        domain = self._classify_domain(task_lower)

        # Extract needed capabilities
        capabilities = self._extract_capabilities(domain, context)

        # Determine if parallelizable
        parallelizable = self._is_parallelizable(task_lower, complexity)

        # Extract quality gates from context
        quality_gates = context.get("quality_gates", {})

        return TaskRequirements(
            complexity=complexity,
            domain=domain,
            capabilities_needed=capabilities,
            parallelizable=parallelizable,
            quality_gates=quality_gates,
            context=context,
        )

    def _classify_complexity(self, task_lower: str) -> TaskComplexity:
        """Classify task complexity based on keywords.

        Args:
            task_lower: Lowercase task description

        Returns:
            TaskComplexity classification

        """
        # Check for complex keywords first (most specific)
        for keyword in self.COMPLEXITY_KEYWORDS[TaskComplexity.COMPLEX]:
            if keyword in task_lower:
                return TaskComplexity.COMPLEX

        # Check for moderate keywords
        for keyword in self.COMPLEXITY_KEYWORDS[TaskComplexity.MODERATE]:
            if keyword in task_lower:
                return TaskComplexity.MODERATE

        # Check for simple keywords
        for keyword in self.COMPLEXITY_KEYWORDS[TaskComplexity.SIMPLE]:
            if keyword in task_lower:
                return TaskComplexity.SIMPLE

        # Default to moderate if no keywords match
        return TaskComplexity.MODERATE

    def _classify_domain(self, task_lower: str) -> TaskDomain:
        """Classify task domain based on keywords.

        Args:
            task_lower: Lowercase task description

        Returns:
            TaskDomain classification

        """
        # Score each domain based on keyword matches
        domain_scores: dict[TaskDomain, int] = dict.fromkeys(TaskDomain, 0)

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    domain_scores[domain] += 1

        # Return domain with highest score
        max_score = max(domain_scores.values())
        if max_score > 0:
            for domain, score in domain_scores.items():
                if score == max_score:
                    return domain

        # Default to general if no keywords match
        return TaskDomain.GENERAL

    def _extract_capabilities(self, domain: TaskDomain, context: dict[str, Any]) -> list[str]:
        """Extract needed capabilities based on domain.

        Args:
            domain: Task domain
            context: Context dictionary

        Returns:
            List of capability names

        """
        # Get default capabilities for domain
        capabilities = self.DOMAIN_CAPABILITIES.get(domain, []).copy()

        # Add capabilities from context if provided
        if "capabilities" in context:
            additional = context["capabilities"]
            if isinstance(additional, list):
                capabilities.extend(additional)

        return capabilities

    def _is_parallelizable(self, task_lower: str, complexity: TaskComplexity) -> bool:
        """Determine if task can be parallelized.

        Args:
            task_lower: Lowercase task description
            complexity: Task complexity

        Returns:
            True if task can be parallelized

        """
        # Keywords indicating parallel execution
        parallel_keywords = [
            "release",
            "audit",
            "check",
            "validate",
            "review",
        ]

        # Keywords indicating sequential execution
        sequential_keywords = [
            "migrate",
            "refactor",
            "generate",
            "create",
        ]

        # Check for sequential keywords first (higher precedence)
        for keyword in sequential_keywords:
            if keyword in task_lower:
                return False

        # Check for parallel keywords
        for keyword in parallel_keywords:
            if keyword in task_lower:
                return True

        # Complex tasks often benefit from parallel execution
        return complexity == TaskComplexity.COMPLEX

    def _select_agents(self, requirements: TaskRequirements) -> list[AgentTemplate]:
        """Select appropriate agents based on requirements.

        Args:
            requirements: Task requirements

        Returns:
            List of agent templates

        Raises:
            ValueError: If no agents match requirements

        """
        agents: list[AgentTemplate] = []

        # Select agents based on needed capabilities
        for capability in requirements.capabilities_needed:
            templates = get_templates_by_capability(capability)
            if templates:
                # Pick the first template with this capability
                # In future: could rank by success rate, cost, etc.
                agent = templates[0]
                if agent not in agents:
                    agents.append(agent)

        # If no agents found, use domain-appropriate default
        if not agents:
            agents = self._get_default_agents(requirements.domain)

        if not agents:
            raise ValueError(f"No agents available for domain: {requirements.domain.value}")

        return agents

    def _get_default_agents(self, domain: TaskDomain) -> list[AgentTemplate]:
        """Get default agents for a domain.

        Args:
            domain: Task domain

        Returns:
            List of default agent templates

        """
        defaults = {
            TaskDomain.TESTING: ["test_coverage_analyzer"],
            TaskDomain.SECURITY: ["security_auditor"],
            TaskDomain.CODE_QUALITY: ["code_reviewer"],
            TaskDomain.DOCUMENTATION: ["documentation_writer"],
            TaskDomain.PERFORMANCE: ["performance_optimizer"],
            TaskDomain.ARCHITECTURE: ["architecture_analyst"],
            TaskDomain.REFACTORING: ["refactoring_specialist"],
        }

        template_ids = defaults.get(domain, ["code_reviewer"])
        agents = []
        for template_id in template_ids:
            template = get_template(template_id)
            if template:
                agents.append(template)

        return agents

    def _choose_composition_pattern(
        self,
        requirements: TaskRequirements,
        agents: list[AgentTemplate],
    ) -> CompositionPattern:
        """Choose optimal composition pattern.

        Args:
            requirements: Task requirements
            agents: Selected agents

        Returns:
            CompositionPattern to use

        """
        num_agents = len(agents)
        context = requirements.context

        # Anthropic Pattern 8: Tool-Enhanced (single agent + tools preferred)
        if num_agents == 1 and context.get("tools"):
            return CompositionPattern.TOOL_ENHANCED

        # Anthropic Pattern 10: Delegation Chain (hierarchical coordination)
        # Use when: Complex task + coordinator pattern + 2+ specialists
        has_coordinator = any("coordinator" in agent.role.lower() for agent in agents)
        if (
            requirements.complexity == TaskComplexity.COMPLEX
            and has_coordinator
            and num_agents >= 2
        ):
            return CompositionPattern.DELEGATION_CHAIN

        # Anthropic Pattern 9: Prompt-Cached Sequential (large shared context)
        # Use when: 3+ agents need same large context (>2000 tokens)
        large_context = context.get("cached_context") or context.get("shared_knowledge")
        if num_agents >= 3 and large_context and len(str(large_context)) > 2000:
            return CompositionPattern.PROMPT_CACHED_SEQUENTIAL

        # Parallelizable tasks: use parallel strategy (check before single agent)
        if requirements.parallelizable:
            return CompositionPattern.PARALLEL

        # Security/architecture: benefit from multiple perspectives (even with 1 agent)
        if requirements.domain in [TaskDomain.SECURITY, TaskDomain.ARCHITECTURE]:
            return CompositionPattern.PARALLEL

        # Documentation: teaching pattern (cheap → validate → expert if needed)
        if requirements.domain == TaskDomain.DOCUMENTATION:
            return CompositionPattern.TEACHING

        # Refactoring: refinement pattern (identify → refactor → validate)
        if requirements.domain == TaskDomain.REFACTORING:
            return CompositionPattern.REFINEMENT

        # Single agent: sequential (after domain-specific patterns)
        if num_agents == 1:
            return CompositionPattern.SEQUENTIAL

        # Multiple agents with same capability: debate/consensus
        capabilities = [cap for agent in agents for cap in agent.capabilities]
        if len(capabilities) != len(set(capabilities)):
            # Duplicate capabilities detected → debate
            return CompositionPattern.DEBATE

        # Testing domain: typically sequential (analyze → generate → validate)
        if requirements.domain == TaskDomain.TESTING:
            return CompositionPattern.SEQUENTIAL

        # Complex tasks: adaptive routing
        if requirements.complexity == TaskComplexity.COMPLEX:
            return CompositionPattern.ADAPTIVE

        # Default: sequential
        return CompositionPattern.SEQUENTIAL
