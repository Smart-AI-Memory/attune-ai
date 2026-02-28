"""Health Check Crew

A multi-agent crew that diagnoses and fixes project health issues.
Uses XML-enhanced prompts for structured, consistent output.

Agents:
1. Health Lead (Coordinator) - Orchestrates checks, prioritizes fixes
2. Lint Fixer - Runs ruff, generates auto-fix patches
3. Type Resolver - Runs mypy, suggests type annotations
4. Test Doctor - Runs pytest, diagnoses and fixes test failures
5. Dep Auditor - Checks outdated/vulnerable dependencies

Usage:
    from attune.agent_factory.crews import HealthCheckCrew

    crew = HealthCheckCrew(api_key="...")
    report = await crew.check(path=".", auto_fix=True)

    print(f"Health Score: {report.health_score}")
    for fix in report.applied_fixes:
        print(f"  Fixed: {fix.title}")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging

from ..base import CrewBase
from .analyzers import apply_fixes, build_check_task, calculate_health_score, parse_fixes
from .checkers import run_dep_check, run_lint_check, run_test_check, run_type_check
from .config import XML_PROMPT_TEMPLATES, HealthCheckConfig
from .models import HealthCheckReport, HealthFix, HealthIssue

logger = logging.getLogger(__name__)


class HealthCheckCrew(CrewBase):
    """Multi-agent crew for project health diagnosis and fixing.

    Uses 5 specialized agents (Health Lead, Lint Fixer, Type Resolver,
    Test Doctor, Dep Auditor) with XML-enhanced prompts.

    Example:
        crew = HealthCheckCrew(api_key="...")
        report = await crew.check(path=".", auto_fix=True)

        if report.is_healthy:
            print("Project is healthy!")
        else:
            print(f"Health Score: {report.health_score}/100")
            for issue in report.critical_issues:
                print(f"  - {issue.title}")

    """

    config_class = HealthCheckConfig
    XML_PROMPT_TEMPLATES = XML_PROMPT_TEMPLATES

    async def _create_agents(self) -> None:
        """Create the 5 specialized health check agents with XML prompts."""
        # 1. Health Lead (Coordinator)
        self._agents["lead"] = self._factory.create_agent(
            name="health_lead",
            role="coordinator",
            description="Senior engineer who orchestrates the health check team",
            system_prompt=self._get_system_prompt(
                "health_lead",
                """You are the Health Lead, coordinating project health checks.

Your responsibilities:
1. Coordinate the health check team
2. Synthesize findings from all checkers
3. Prioritize issues by severity and impact
4. Calculate overall health score (0-100)
5. Generate actionable fix plan

Health Score calculation:
- Start at 100
- Deduct 25 per critical issue
- Deduct 10 per high issue
- Deduct 3 per medium issue
- Deduct 1 per low issue

Be constructive and prioritize quick wins.""",
            ),
            model_tier=self.config.lead_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
            resilience_enabled=self.config.resilience_enabled,
        )

        # 2. Lint Fixer
        self._agents["lint"] = self._factory.create_agent(
            name="lint_fixer",
            role="analyst",
            description="Expert at identifying and fixing lint issues",
            system_prompt=self._get_system_prompt(
                "lint_fixer",
                """You are the Lint Fixer, a code quality expert.

Your focus:
1. Parse ruff output for lint violations
2. Categorize by type (style, error, security)
3. Identify auto-fixable issues
4. Generate patches for complex fixes
5. Explain each fix

Rules:
- Only auto-fix safe style issues
- Flag security-related issues as high priority
- Never change code behavior
- Respect noqa comments""",
            ),
            model_tier=self.config.lint_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 3. Type Resolver
        self._agents["types"] = self._factory.create_agent(
            name="type_resolver",
            role="analyst",
            description="Expert at resolving type errors",
            system_prompt=self._get_system_prompt(
                "type_resolver",
                """You are the Type Resolver, a typing expert.

Your focus:
1. Parse mypy output for type errors
2. Categorize errors by type
3. Infer correct types from context
4. Generate type annotations
5. Suggest typing strategy

Rules:
- Prefer simple types over complex generics
- Use | union syntax (Python 3.10+)
- Suggest Any only as last resort
- Consider runtime implications""",
            ),
            model_tier=self.config.types_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 4. Test Doctor
        self._agents["tests"] = self._factory.create_agent(
            name="test_doctor",
            role="analyst",
            description="Expert at diagnosing test failures",
            system_prompt=self._get_system_prompt(
                "test_doctor",
                """You are the Test Doctor, a testing expert.

Your focus:
1. Parse pytest output for failures
2. Analyze failure type (assertion, exception, timeout)
3. Determine root cause (test bug vs code bug)
4. Generate fixes for test issues
5. Identify flaky tests

Rules:
- Distinguish test bugs from code bugs
- Never remove assertions to fix tests
- Prefer fixing setup over mocking
- Flag implementation-coupled tests""",
            ),
            model_tier=self.config.tests_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 5. Dep Auditor
        self._agents["deps"] = self._factory.create_agent(
            name="dep_auditor",
            role="analyst",
            description="Expert at auditing dependencies",
            system_prompt=self._get_system_prompt(
                "dep_auditor",
                """You are the Dep Auditor, a dependency expert.

Your focus:
1. Check for security vulnerabilities
2. Identify outdated packages
3. Assess update risk
4. Check for conflicts
5. Suggest safe update paths

Rules:
- Prioritize security over outdated
- Be conservative with major upgrades
- Check changelogs for breaking changes
- Consider transitive impacts""",
            ),
            model_tier=self.config.deps_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

    async def _create_workflow(self) -> None:
        """Create hierarchical workflow with Health Lead as manager."""
        agents = list(self._agents.values())

        self._workflow = self._factory.create_workflow(
            name="health_check_workflow",
            agents=agents,
            mode="hierarchical",
            description="Comprehensive health check with coordinated diagnosis and fixes",
        )

    async def check(
        self,
        path: str = ".",
        auto_fix: bool | None = None,
        context: dict | None = None,
    ) -> HealthCheckReport:
        """Perform a comprehensive health check.

        Args:
            path: Path to check (default: current directory)
            auto_fix: Override config auto_fix setting
            context: Optional context (focus areas, previous checks, etc.)

        Returns:
            HealthCheckReport with issues, fixes, and health score

        """
        import time

        start_time = time.time()

        # Initialize if needed
        await self._initialize()

        context = context or {}
        auto_fix = auto_fix if auto_fix is not None else self.config.auto_fix
        issues: list[HealthIssue] = []
        fixes: list[HealthFix] = []
        checks_run: dict[str, dict] = {}
        memory_hits = 0

        # Run the individual checks first to gather data
        if self.config.check_lint:
            lint_result = await run_lint_check(path)
            checks_run["lint"] = lint_result
            issues.extend(lint_result.get("issues", []))

        if self.config.check_types:
            types_result = await run_type_check(path)
            checks_run["types"] = types_result
            issues.extend(types_result.get("issues", []))

        if self.config.check_tests:
            tests_result = await run_test_check(path)
            checks_run["tests"] = tests_result
            issues.extend(tests_result.get("issues", []))

        if self.config.check_deps:
            deps_result = await run_dep_check(path)
            checks_run["deps"] = deps_result
            issues.extend(deps_result.get("issues", []))

        # Check Memory Graph for similar past issues
        if self._graph and self.config.memory_graph_enabled:
            try:
                similar = self._graph.find_similar(
                    {"name": f"health_check:{path}", "description": f"Health check of {path}"},
                    threshold=0.4,
                    limit=10,
                )
                if similar:
                    memory_hits = len(similar)
                    context["past_checks"] = [
                        {
                            "name": node.name,
                            "health_score": node.metadata.get("health_score", 0),
                            "issues_found": node.metadata.get("issues_found", 0),
                        }
                        for node, score in similar
                    ]
                    logger.info(f"Found {memory_hits} similar past health checks")
            except Exception as e:
                # INTENTIONAL: Memory Graph is optional - continue health check if unavailable
                logger.warning(f"Error querying Memory Graph: {e}")

        # Build task for the crew to analyze and generate fixes
        check_task = build_check_task(path, checks_run, issues, auto_fix, context)

        # Execute the workflow for analysis
        try:
            result = await self._workflow.run(check_task, initial_state=context)

            # Parse fixes from result
            fixes = parse_fixes(result, issues)

            # Apply auto-fixes if enabled
            if auto_fix:
                fixes = await apply_fixes(fixes, path, self.config.fix_safe_only)

        except Exception as e:
            # INTENTIONAL: Analysis failure shouldn't crash - return partial results
            logger.error(f"Health check analysis failed: {e}")

        # Calculate health score
        health_score = calculate_health_score(issues)

        # Build the report
        duration = time.time() - start_time
        report = HealthCheckReport(
            target=path,
            issues=issues,
            fixes=fixes,
            health_score=health_score,
            check_duration_seconds=duration,
            agents_used=list(self._agents.keys()),
            memory_graph_hits=memory_hits,
            checks_run={k: {"passed": v.get("passed", False)} for k, v in checks_run.items()},
            metadata={
                "auto_fix": auto_fix,
                "framework": str(self._factory.framework.value) if self._factory else "unknown",
                "xml_prompts": self.config.xml_prompts_enabled,
            },
        )

        # Store check in Memory Graph
        if self._graph and self.config.memory_graph_enabled:
            try:
                self._graph.add_finding(
                    "health_check_crew",
                    {
                        "type": "health_check",
                        "name": f"check:{path}",
                        "description": f"Health score: {health_score}/100",
                        "health_score": health_score,
                        "issues_found": len(issues),
                        "fixes_applied": len(report.applied_fixes),
                    },
                )
                self._graph._save()
            except Exception as e:
                # INTENTIONAL: Memory Graph storage is optional - continue without it
                logger.warning(f"Error storing check in Memory Graph: {e}")

        return report

    # Delegate methods - thin wrappers that call standalone functions.
    # Preserves backward compatibility for callers using self._method().

    async def _run_lint_check(self, path: str) -> dict:
        """Run ruff lint check. Delegates to checkers.run_lint_check."""
        return await run_lint_check(path)

    async def _run_type_check(self, path: str) -> dict:
        """Run mypy type check. Delegates to checkers.run_type_check."""
        return await run_type_check(path)

    async def _run_test_check(self, path: str) -> dict:
        """Run pytest test check. Delegates to checkers.run_test_check."""
        return await run_test_check(path)

    async def _run_dep_check(self, path: str) -> dict:
        """Run dependency security check. Delegates to checkers.run_dep_check."""
        return await run_dep_check(path)

    def _build_check_task(
        self,
        path: str,
        checks_run: dict,
        issues: list[HealthIssue],
        auto_fix: bool,
        context: dict,
    ) -> str:
        """Build the check task description. Delegates to analyzers.build_check_task."""
        return build_check_task(path, checks_run, issues, auto_fix, context)

    def _parse_fixes(self, result: dict, issues: list[HealthIssue]) -> list[HealthFix]:
        """Parse fixes from workflow result. Delegates to analyzers.parse_fixes."""
        return parse_fixes(result, issues)

    async def _apply_fixes(self, fixes: list[HealthFix], path: str) -> list[HealthFix]:
        """Apply safe auto-fixes. Delegates to analyzers.apply_fixes."""
        return await apply_fixes(fixes, path, self.config.fix_safe_only)

    def _calculate_health_score(self, issues: list[HealthIssue]) -> float:
        """Calculate health score from issues. Delegates to analyzers.calculate_health_score."""
        return calculate_health_score(issues)
