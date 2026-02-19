"""Code Review Crew

Multi-agent crew that performs comprehensive code reviews using
hierarchical collaboration with 5 specialized agents.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging

from ..base import CrewBase
from .config import XML_PROMPT_TEMPLATES, CodeReviewConfig
from .models import (
    CodeReviewReport,
    ReviewFinding,
    Verdict,
)
from .parser import (
    determine_verdict,
    generate_summary,
    parse_findings,
)

logger = logging.getLogger(__name__)


class CodeReviewCrew(CrewBase):
    """Multi-agent crew for comprehensive code reviews.

    The crew consists of 5 specialized agents:
    Review Lead, Security Analyst, Architecture Reviewer,
    Quality Analyst, and Performance Reviewer.

    Example:
        crew = CodeReviewCrew(api_key="...")
        report = await crew.review(
            diff="...",
            files_changed=["src/api.py"],
        )

        if report.verdict == Verdict.APPROVE:
            print("Code is ready to merge!")

        print(f"Quality Score: {report.quality_score}/100")

    """

    config_class = CodeReviewConfig
    XML_PROMPT_TEMPLATES = XML_PROMPT_TEMPLATES

    async def _create_agents(self) -> None:
        """Create the 5 specialized code review agents with XML-enhanced prompts."""
        # Fallback prompts for when XML is disabled
        lead_fallback = """You are the Review Lead, a senior engineer with 15+ years.

Your responsibilities:
1. Coordinate the code review team
2. Synthesize findings from all reviewers
3. Prioritize issues by impact
4. Make final verdict decision (approve, request_changes, reject)
5. Generate actionable summary

You delegate to your team:
- Security Analyst: Security vulnerabilities and risks
- Architecture Reviewer: Design patterns and structure
- Quality Analyst: Code quality and maintainability
- Performance Reviewer: Performance issues and optimizations

For verdict decisions:
- APPROVE: No issues or only minor suggestions
- APPROVE_WITH_SUGGESTIONS: Good overall, some improvements recommended
- REQUEST_CHANGES: Issues that must be addressed before merge
- REJECT: Fundamental problems requiring significant rework

Be constructive and specific in feedback."""

        # 1. Review Lead (Coordinator)
        self._agents["lead"] = self._factory.create_agent(
            name="review_lead",
            role="coordinator",
            description="Senior engineer who orchestrates the code review team",
            system_prompt=self._get_system_prompt("review_lead", lead_fallback),
            model_tier=self.config.lead_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
            resilience_enabled=self.config.resilience_enabled,
        )

        # Fallback prompts for remaining agents
        security_fallback = """You are the Security Analyst, a security-focused reviewer.

Your focus areas:
1. OWASP Top 10 vulnerabilities
2. SQL Injection, XSS, Command Injection
3. Hardcoded secrets, API keys, passwords
4. Authentication and authorization flaws
5. Input validation issues
6. Insecure dependencies
7. Cryptographic weaknesses

For each finding, provide:
- Clear description of the security risk
- File and line number
- Severity (critical/high/medium/low)
- Specific remediation with code example

Be thorough but minimize false positives. Focus on exploitable issues."""

        architecture_fallback = """You are the Architecture Reviewer, a software architect.

Your evaluation criteria:
1. SOLID Principles
   - Single Responsibility
   - Open/Closed
   - Liskov Substitution
   - Interface Segregation
   - Dependency Inversion

2. Design Patterns
   - Appropriate pattern usage
   - Anti-patterns to avoid
   - Missing patterns where beneficial

3. Code Structure
   - Module boundaries
   - Coupling and cohesion
   - Dependency direction
   - Layering violations

4. Scalability
   - Extensibility points
   - Future maintenance burden
   - Breaking changes

Provide specific refactoring suggestions with before/after examples."""

        quality_fallback = """You are the Quality Analyst, a code quality expert.

Your focus areas:
1. Code Smells
   - Long methods/functions
   - Large classes
   - Duplicate code
   - Dead code
   - Magic numbers/strings

2. Maintainability
   - Clear naming
   - Appropriate comments
   - Consistent formatting
   - Error handling
   - Logging

3. Testing
   - Test coverage gaps
   - Edge cases
   - Error scenarios
   - Integration points

4. Complexity
   - Cyclomatic complexity
   - Nesting depth
   - Parameter counts
   - Cognitive load

Prioritize issues that affect long-term maintainability."""

        # 2. Security Analyst
        self._agents["security"] = self._factory.create_agent(
            name="security_analyst",
            role="security",
            description="Expert at identifying security vulnerabilities",
            system_prompt=self._get_system_prompt("security_analyst", security_fallback),
            model_tier=self.config.security_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 3. Architecture Reviewer
        self._agents["architecture"] = self._factory.create_agent(
            name="architecture_reviewer",
            role="architect",
            description="Evaluates code design and architecture",
            system_prompt=self._get_system_prompt("architecture_reviewer", architecture_fallback),
            model_tier=self.config.architecture_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # 4. Quality Analyst
        self._agents["quality"] = self._factory.create_agent(
            name="quality_analyst",
            role="analyst",
            description="Identifies code quality and maintainability issues",
            system_prompt=self._get_system_prompt("quality_analyst", quality_fallback),
            model_tier=self.config.quality_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

        # Performance fallback
        performance_fallback = """You are the Performance Reviewer, a performance engineer.

Your focus areas:
1. Algorithm Efficiency
   - Time complexity (Big O)
   - Space complexity
   - Unnecessary iterations
   - Inefficient data structures

2. Resource Usage
   - Memory leaks
   - Connection leaks
   - File handle management
   - Cache misuse

3. Common Anti-patterns
   - N+1 queries
   - Sync operations in async code
   - Blocking main thread
   - Unoptimized regex
   - String concatenation in loops

4. Database Performance
   - Missing indexes
   - Expensive queries
   - Over-fetching
   - Transaction scope

Provide optimization suggestions with expected impact."""

        # 5. Performance Reviewer
        self._agents["performance"] = self._factory.create_agent(
            name="performance_reviewer",
            role="analyst",
            description="Identifies performance issues and optimizations",
            system_prompt=self._get_system_prompt("performance_reviewer", performance_fallback),
            model_tier=self.config.performance_tier,
            memory_graph_enabled=self.config.memory_graph_enabled,
            memory_graph_path=self.config.memory_graph_path,
        )

    async def _create_workflow(self) -> None:
        """Create hierarchical workflow with Review Lead as manager."""
        agents = list(self._agents.values())

        self._workflow = self._factory.create_workflow(
            name="code_review_workflow",
            agents=agents,
            mode="hierarchical",  # Review Lead delegates to others
            description="Comprehensive code review with coordinated analysis",
        )

    async def review(
        self,
        diff: str = "",
        files_changed: list[str] | None = None,
        target: str = "",
        context: dict | None = None,
    ) -> CodeReviewReport:
        """Perform a comprehensive code review.

        Args:
            diff: Git diff or code changes to review
            files_changed: List of changed file paths
            target: Description of review target
            context: Optional context (previous findings, focus areas, etc.)

        Returns:
            CodeReviewReport with findings and verdict

        """
        import time

        start_time = time.time()

        # Initialize if needed
        await self._initialize()

        context = context or {}
        files_changed = files_changed or []
        findings: list[ReviewFinding] = []
        memory_hits = 0

        # Build target description
        if not target:
            target = f"Review of {len(files_changed)} files"

        # Check Memory Graph for similar past reviews
        if self._graph and self.config.memory_graph_enabled:
            try:
                similar = self._graph.find_similar(
                    {"name": f"code_review:{target}", "description": target},
                    threshold=0.4,
                    limit=10,
                )
                if similar:
                    memory_hits = len(similar)
                    context["similar_reviews"] = [
                        {
                            "name": node.name,
                            "verdict": node.metadata.get("verdict", "unknown"),
                            "quality_score": node.metadata.get("quality_score", 0),
                        }
                        for node, score in similar
                    ]
                    logger.info(f"Found {memory_hits} similar past reviews")
            except Exception as e:
                logger.warning(f"Error querying Memory Graph: {e}")

        # Build review task for the crew
        review_task = self._build_review_task(diff, files_changed, context)

        # Execute the workflow
        verdict = Verdict.APPROVE
        try:
            result = await self._workflow.run(review_task, initial_state=context)

            # Parse findings from result
            findings = parse_findings(result)

            # Determine verdict
            verdict = determine_verdict(findings)

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            # Return partial report with error
            return CodeReviewReport(
                target=target,
                findings=findings,
                verdict=Verdict.REQUEST_CHANGES,
                summary=f"Review failed with error: {e}",
                review_duration_seconds=time.time() - start_time,
                agents_used=list(self._agents.keys()),
                memory_graph_hits=memory_hits,
                metadata={"error": str(e)},
            )

        # Build the report
        duration = time.time() - start_time
        report = CodeReviewReport(
            target=target,
            findings=findings,
            verdict=verdict,
            summary=generate_summary(findings, verdict),
            review_duration_seconds=duration,
            agents_used=list(self._agents.keys()),
            memory_graph_hits=memory_hits,
            metadata={
                "review_depth": self.config.review_depth,
                "framework": str(self._factory.framework.value),
                "files_changed": files_changed,
            },
        )

        # Store review in Memory Graph
        if self._graph and self.config.memory_graph_enabled:
            try:
                self._graph.add_finding(
                    "code_review_crew",
                    {
                        "type": "code_review",
                        "name": f"review:{target}",
                        "description": report.summary,
                        "verdict": verdict.value,
                        "quality_score": report.quality_score,
                        "findings_count": len(findings),
                    },
                )
                self._graph._save()
            except Exception as e:
                logger.warning(f"Error storing review in Memory Graph: {e}")

        return report

    def _build_review_task(self, diff: str, files_changed: list[str], context: dict) -> str:
        """Build the review task description for the crew."""
        depth_instructions = {
            "quick": "Focus on critical issues only. Skip style and minor issues.",
            "standard": "Cover security, architecture, quality, and performance.",
            "thorough": "Deep review including edge cases, testing, and docs.",
        }

        focus_list = ", ".join(self.config.focus_areas)

        task = f"""Perform a comprehensive code review.

Review Depth: {self.config.review_depth}
Instructions: {depth_instructions.get(self.config.review_depth, "standard")}
Focus Areas: {focus_list}

Files Changed ({len(files_changed)}):
{chr(10).join(f"  - {f}" for f in files_changed[:20])}

Diff/Code to Review:
```
{diff[:15000]}
```

Workflow:
1. Review Lead coordinates the overall review strategy
2. Security Analyst checks for security vulnerabilities
3. Architecture Reviewer evaluates design and structure
4. Quality Analyst identifies code quality issues
5. Performance Reviewer spots performance problems

For each finding, provide:
- Title and description
- Severity (critical/high/medium/low/info)
- Category (security/architecture/quality/performance/etc.)
- File path and line number
- Specific suggestion with code example if applicable

Final Verdict Options:
- APPROVE: No issues or only minor suggestions
- APPROVE_WITH_SUGGESTIONS: Good overall, improvements recommended
- REQUEST_CHANGES: Issues must be addressed before merge
- REJECT: Fundamental problems requiring rework

"""
        if context.get("similar_reviews"):
            task += f"""
Similar Past Reviews Found: {len(context["similar_reviews"])}
Consider patterns from past reviews.
"""

        return task
