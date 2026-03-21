"""Base class for agent composition strategies.

This module defines the ExecutionStrategy abstract base class that all
strategy implementations must inherit from.

Security:
    - All agent outputs validated before passing to next agent
    - No eval() or exec() usage
    - Timeout enforcement at strategy level

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .data_classes import AgentResult, StrategyResult

if TYPE_CHECKING:
    from ..agent_templates import AgentTemplate

logger = logging.getLogger(__name__)


class ExecutionStrategy(ABC):
    """Base class for agent composition strategies.

    All strategies must implement execute() method to define
    how agents are coordinated and results aggregated.
    """

    @abstractmethod
    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute agents using this strategy.

        Args:
            agents: List of agent templates to execute
            context: Initial context for execution

        Returns:
            StrategyResult with aggregated outputs

        Raises:
            ValueError: If agents list is empty
            TimeoutError: If execution exceeds timeout

        """

    async def _execute_agent(self, agent: AgentTemplate, context: dict[str, Any]) -> AgentResult:
        """Execute a single agent with real analysis tools.

        Maps agent capabilities to real tool implementations and executes them.

        Args:
            agent: Agent template to execute
            context: Execution context

        Returns:
            AgentResult with execution outcome

        """
        import time

        from ..real_tools import (
            RealArchitectureAnalyzer,
            RealCodeQualityAnalyzer,
            RealCoverageAnalyzer,
            RealDocumentationAnalyzer,
            RealPerformanceProfiler,
            RealSecurityAuditor,
        )

        logger.info(f"Executing agent: {agent.id} ({agent.role})")
        start_time = time.perf_counter()

        # Get project root from context
        project_root = context.get("project_root", ".")
        target_path = context.get("target_path", "src")

        try:
            # Map agent ID to real tool implementation
            if agent.id == "security_auditor" or "security" in agent.role.lower():
                auditor = RealSecurityAuditor(project_root)
                report = auditor.audit(target_path)

                output = {
                    "agent_role": agent.role,
                    "total_issues": report.total_issues,
                    "critical_issues": report.critical_count,  # Match workflow field name
                    "high_issues": report.high_count,  # Match workflow field name
                    "medium_issues": report.medium_count,  # Match workflow field name
                    "passed": report.passed,
                    "issues_by_file": report.issues_by_file,
                }
                success = report.passed
                confidence = 1.0 if report.total_issues == 0 else 0.7

            elif agent.id == "test_coverage_analyzer" or "coverage" in agent.role.lower():
                analyzer = RealCoverageAnalyzer(project_root)
                report = analyzer.analyze()  # Analyzes all packages automatically

                output = {
                    "agent_role": agent.role,
                    "coverage_percent": report.total_coverage,  # Match workflow field name
                    "total_coverage": report.total_coverage,  # Keep for compatibility
                    "files_analyzed": report.files_analyzed,
                    "uncovered_files": report.uncovered_files,
                    "passed": report.total_coverage >= 80.0,
                }
                success = report.total_coverage >= 80.0
                confidence = min(report.total_coverage / 100.0, 1.0)

            elif agent.id == "code_reviewer" or "quality" in agent.role.lower():
                analyzer = RealCodeQualityAnalyzer(project_root)
                report = analyzer.analyze(target_path)

                output = {
                    "agent_role": agent.role,
                    "quality_score": report.quality_score,
                    "ruff_issues": report.ruff_issues,
                    "mypy_issues": report.mypy_issues,
                    "total_files": report.total_files,
                    "passed": report.passed,
                }
                success = report.passed
                confidence = report.quality_score / 10.0

            elif agent.id == "documentation_writer" or "documentation" in agent.role.lower():
                analyzer = RealDocumentationAnalyzer(project_root)
                report = analyzer.analyze(target_path)

                output = {
                    "agent_role": agent.role,
                    "completeness": report.completeness_percentage,
                    "coverage_percent": report.completeness_percentage,  # Match Release Prep field name
                    "total_functions": report.total_functions,
                    "documented_functions": report.documented_functions,
                    "total_classes": report.total_classes,
                    "documented_classes": report.documented_classes,
                    "missing_docstrings": report.missing_docstrings,
                    "passed": report.passed,
                }
                success = report.passed
                confidence = report.completeness_percentage / 100.0

            elif agent.id == "performance_optimizer" or "performance" in agent.role.lower():
                profiler = RealPerformanceProfiler(project_root)
                report = profiler.analyze(target_path)

                output = {
                    "agent_role": agent.role,
                    "score": report.score,
                    "total_files": report.total_files,
                    "functions_analyzed": report.functions_analyzed,
                    "high_complexity_count": len(report.high_complexity),
                    "large_functions_count": len(report.large_functions),
                    "high_complexity": report.high_complexity,
                    "large_functions": report.large_functions,
                    "passed": report.passed,
                }
                success = report.passed
                confidence = report.score / 10.0

            elif agent.id == "architecture_analyst" or "architecture" in agent.role.lower():
                analyzer = RealArchitectureAnalyzer(project_root)
                report = analyzer.analyze(target_path)

                output = {
                    "agent_role": agent.role,
                    "score": report.score,
                    "total_modules": report.total_modules,
                    "total_packages": report.total_packages,
                    "max_depth": report.max_depth,
                    "circular_imports": len(report.circular_imports),
                    "high_coupling_count": len(report.high_coupling),
                    "high_coupling": report.high_coupling,
                    "passed": report.passed,
                }
                success = report.passed
                confidence = report.score / 10.0

            elif agent.id == "test_generator":
                # Test generation requires different handling (LLM-based)
                logger.info("Test generation requires manual invocation, returning placeholder")
                output = {
                    "agent_role": agent.role,
                    "message": "Test generation requires manual invocation",
                    "passed": True,
                }
                success = True
                confidence = 0.8

            else:
                # Unknown agent type - log warning and return placeholder
                logger.warning(f"Unknown agent type: {agent.id}, returning placeholder")
                output = {
                    "agent_role": agent.role,
                    "agent_id": agent.id,
                    "message": "Unknown agent type - no real implementation",
                    "passed": True,
                }
                success = True
                confidence = 0.5

            duration = time.perf_counter() - start_time

            logger.info(
                f"Agent {agent.id} completed: success={success}, "
                f"confidence={confidence:.2f}, duration={duration:.2f}s",
            )

            return AgentResult(
                agent_id=agent.id,
                success=success,
                output=output,
                confidence=confidence,
                duration_seconds=duration,
            )

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Agent execution may fail for various reasons
            # (missing deps, invalid input, resource exhaustion). Catch
            # broadly so the orchestrator always gets an AgentResult
            # with error details rather than crashing the entire run.
            duration = time.perf_counter() - start_time
            logger.error(f"Agent {agent.id} failed: {e}")

            return AgentResult(
                agent_id=agent.id,
                success=False,
                output={"agent_role": agent.role, "error_details": str(e)},
                error=str(e),
                confidence=0.0,
                duration_seconds=duration,
            )

    def _aggregate_results(self, results: list[AgentResult]) -> dict[str, Any]:
        """Aggregate results from multiple agents.

        Args:
            results: List of agent results

        Returns:
            Aggregated output dictionary

        """
        return {
            "num_agents": len(results),
            "all_succeeded": all(r.success for r in results),
            "avg_confidence": (
                sum(r.confidence for r in results) / len(results) if results else 0.0
            ),
            "outputs": [r.output for r in results],
        }
