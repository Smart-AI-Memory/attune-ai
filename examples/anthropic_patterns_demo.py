"""
Anthropic Agent Patterns - Practical Examples

Demonstrates how to implement Anthropic's three core agent patterns
in the Attune AI:
1. Workflows (Sequential)
2. Orchestrator (Dynamic Routing)
3. Evaluator (Self-Correction)

Usage:
    python examples/anthropic_patterns_demo.py

Requirements:
    pip install attune-ai[developer]
"""

import asyncio
from typing import Any

from attune.workflows import BaseWorkflow
from attune.models import LLMClient

# ============================================================================
# Pattern 1: Sequential Workflow (Anthropic Pattern)
# ============================================================================


class CodeAnalysisPipeline(BaseWorkflow):
    """Sequential code analysis workflow.

    Follows Anthropic's workflow pattern: predefined sequence of agents
    with clear input/output contracts.

    Stages:
    1. Parse (cheap tier) - Extract structure
    2. Analyze (capable tier) - Deep analysis
    3. Recommend (premium tier) - Strategic recommendations
    """

    def __init__(self):
        super().__init__(workflow_id="code-analysis-pipeline")

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute three-stage analysis pipeline.

        Args:
            inputs: {"code": str} - Source code to analyze

        Returns:
            {
                "parsed": dict,  # Structure extraction
                "analysis": dict,  # Deep analysis
                "recommendations": dict,  # Improvements
                "stages_completed": int
            }
        """
        code = inputs["code"]

        # Stage 1: Parse code structure (cheap tier)
        parsed = await self._parse_code(code)
        print("✓ Stage 1: Parsed code structure")

        # Stage 2: Analyze patterns (capable tier)
        analysis = await self._analyze_patterns(parsed, code)
        print("✓ Stage 2: Analyzed patterns")

        # Stage 3: Generate recommendations (premium tier)
        recommendations = await self._generate_recommendations(analysis, code)
        print("✓ Stage 3: Generated recommendations")

        return {
            "parsed": parsed,
            "analysis": analysis,
            "recommendations": recommendations,
            "stages_completed": 3,
        }

    async def _parse_code(self, code: str) -> dict[str, Any]:
        """Stage 1: Parse code structure (cheap tier)."""
        prompt = f"""Extract the structure of this code:
{code}

Return JSON with: functions, classes, imports, complexity"""

        response = await self.llm_client.call(
            prompt=prompt,
            tier="cheap",  # Fast, inexpensive parsing
            workflow_id=f"{self.workflow_id}:parse",
        )

        return {"structure": response["content"]}

    async def _analyze_patterns(self, parsed: dict, code: str) -> dict[str, Any]:
        """Stage 2: Analyze code patterns (capable tier)."""
        prompt = f"""Analyze this code for patterns and issues:

Structure: {parsed['structure']}

Code:
{code}

Identify: anti-patterns, bugs, security issues"""

        response = await self.llm_client.call(
            prompt=prompt,
            tier="capable",  # More thorough analysis
            workflow_id=f"{self.workflow_id}:analyze",
        )

        return {"findings": response["content"]}

    async def _generate_recommendations(self, analysis: dict, code: str) -> dict[str, Any]:
        """Stage 3: Generate strategic recommendations (premium tier)."""
        prompt = f"""Given this analysis, provide strategic recommendations:

Analysis: {analysis['findings']}

Original Code:
{code}

Recommend: architectural improvements, refactoring, best practices"""

        response = await self.llm_client.call(
            prompt=prompt,
            tier="premium",  # High-quality strategic thinking
            workflow_id=f"{self.workflow_id}:recommend",
        )

        return {"recommendations": response["content"]}


# ============================================================================
# Pattern 2: Orchestrator (Dynamic Routing)
# ============================================================================


class SimpleOrchestrator:
    """Routes tasks to specialist workflows.

    Follows Anthropic's orchestrator pattern: single coordinator
    that delegates to domain specialists.
    """

    def __init__(self):
        # Define specialists upfront (Anthropic pattern)
        self.specialists = {
            "security": self._create_security_specialist(),
            "performance": self._create_performance_specialist(),
            "quality": self._create_quality_specialist(),
        }

    def _create_security_specialist(self):
        """Security analysis specialist."""

        async def specialist(code: str) -> dict:
            client = LLMClient()
            response = await client.call(
                prompt=f"Find security vulnerabilities:\n{code}",
                tier="capable",
                workflow_id="security-specialist",
            )
            return {"type": "security", "findings": response["content"]}

        return specialist

    def _create_performance_specialist(self):
        """Performance analysis specialist."""

        async def specialist(code: str) -> dict:
            client = LLMClient()
            response = await client.call(
                prompt=f"Find performance issues:\n{code}",
                tier="capable",
                workflow_id="performance-specialist",
            )
            return {"type": "performance", "findings": response["content"]}

        return specialist

    def _create_quality_specialist(self):
        """Code quality specialist."""

        async def specialist(code: str) -> dict:
            client = LLMClient()
            response = await client.call(
                prompt=f"Review code quality:\n{code}",
                tier="capable",
                workflow_id="quality-specialist",
            )
            return {"type": "quality", "findings": response["content"]}

        return specialist

    async def route(self, task: str, code: str) -> dict:
        """Route task to appropriate specialist.

        Args:
            task: Natural language task description
            code: Code to analyze

        Returns:
            Specialist analysis result
        """
        task_lower = task.lower()

        # Keyword-based routing (Anthropic pattern)
        if any(word in task_lower for word in ["security", "vuln", "hack"]):
            print("→ Routing to security specialist")
            return await self.specialists["security"](code)

        elif any(word in task_lower for word in ["slow", "perf", "bottleneck"]):
            print("→ Routing to performance specialist")
            return await self.specialists["performance"](code)

        elif any(word in task_lower for word in ["quality", "review", "improve"]):
            print("→ Routing to quality specialist")
            return await self.specialists["quality"](code)

        else:
            # Default to quality review
            print("→ Routing to quality specialist (default)")
            return await self.specialists["quality"](code)


# ============================================================================
# Pattern 3: Evaluator (Self-Correction)
# ============================================================================


class SelfCorrectingCodeGenerator(BaseWorkflow):
    """Code generator with self-evaluation loop.

    Follows Anthropic's evaluator pattern: worker agent generates,
    evaluator agent assesses quality, loop until good enough.
    """

    def __init__(self):
        super().__init__(workflow_id="self-correcting-generator")

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Generate code with self-correction.

        Args:
            inputs: {
                "task": str,  # What to generate
                "requirements": str,  # Requirements
            }

        Returns:
            {
                "code": str,  # Generated code
                "quality_score": int,  # 0-100
                "attempts": int,  # Number of iterations
                "status": str,  # success or max_attempts
            }
        """
        task = inputs["task"]
        requirements = inputs.get("requirements", "")

        max_attempts = 3
        best_code = None
        best_score = 0

        for attempt in range(max_attempts):
            print(f"\n--- Attempt {attempt + 1} ---")

            # Worker: Generate code
            code = await self._generate_code(
                task=task,
                requirements=requirements,
                previous_code=best_code,
                attempt=attempt,
            )

            # Evaluator: Assess quality
            evaluation = await self._evaluate_code(code, requirements)
            score = evaluation["score"]

            print(f"Quality score: {score}/100")

            # Check if good enough
            if score >= 85:
                print("✓ Quality threshold met!")
                return {
                    "code": code,
                    "quality_score": score,
                    "attempts": attempt + 1,
                    "status": "success",
                }

            # Track best attempt
            if score > best_score:
                best_score = score
                best_code = code

        # Return best after max attempts
        print("⚠ Max attempts reached, returning best")
        return {
            "code": best_code,
            "quality_score": best_score,
            "attempts": max_attempts,
            "status": "max_attempts_reached",
        }

    async def _generate_code(
        self,
        task: str,
        requirements: str,
        previous_code: str | None,
        attempt: int,
    ) -> str:
        """Worker agent: Generate code."""
        if attempt == 0:
            prompt = f"Generate code for: {task}\n\nRequirements: {requirements}"
        else:
            prompt = f"""Improve this code:
{previous_code}

Task: {task}
Requirements: {requirements}
Make it better."""

        response = await self.llm_client.call(
            prompt=prompt,
            tier="capable",
            workflow_id=f"{self.workflow_id}:generate",
        )

        return response["content"]

    async def _evaluate_code(self, code: str, requirements: str) -> dict:
        """Evaluator agent: Assess code quality."""
        prompt = f"""Evaluate this code on a scale of 0-100:

Code:
{code}

Requirements:
{requirements}

Criteria: correctness, readability, efficiency, best practices

Return JSON: {{"score": <number>, "feedback": "<string>"}}"""

        response = await self.llm_client.call(
            prompt=prompt,
            tier="cheap",  # Evaluation can be cheaper
            workflow_id=f"{self.workflow_id}:evaluate",
        )

        # Parse score (simple extraction)
        content = response["content"]
        try:
            import json

            data = json.loads(content)
            return {"score": data["score"], "feedback": data["feedback"]}
        except Exception:
            # Fallback parsing
            score = 50  # Default
            if "score" in content:
                import re

                match = re.search(r'"score":\s*(\d+)', content)
                if match:
                    score = int(match.group(1))
            return {"score": score, "feedback": content}


# ============================================================================
# Demo Runner
# ============================================================================


async def demo_pattern_1():
    """Demo: Sequential workflow."""
    print("\n" + "=" * 60)
    print("PATTERN 1: SEQUENTIAL WORKFLOW")
    print("=" * 60)

    sample_code = """
def calculate_total(prices):
    total = 0
    for price in prices:
        total = total + price
    return total
"""

    pipeline = CodeAnalysisPipeline()
    result = await pipeline.execute({"code": sample_code})

    print("\n--- Results ---")
    print(f"Stages completed: {result['stages_completed']}")
    print(f"Parsed: {result['parsed']}")
    print(f"Analysis: {result['analysis']}")
    print(f"Recommendations: {result['recommendations']}")


async def demo_pattern_2():
    """Demo: Orchestrator (dynamic routing)."""
    print("\n" + "=" * 60)
    print("PATTERN 2: ORCHESTRATOR (DYNAMIC ROUTING)")
    print("=" * 60)

    sample_code = """
def login(username, password):
    query = "SELECT * FROM users WHERE username='" + username + "'"
    return execute_query(query)
"""

    orchestrator = SimpleOrchestrator()

    # Route different tasks
    tasks = [
        "Check for security vulnerabilities",
        "Find performance bottlenecks",
        "Review code quality",
    ]

    for task in tasks:
        print(f"\nTask: {task}")
        result = await orchestrator.route(task, sample_code)
        print(f"Result: {result['type']} specialist found issues")


async def demo_pattern_3():
    """Demo: Self-correcting agent."""
    print("\n" + "=" * 60)
    print("PATTERN 3: SELF-CORRECTING AGENT")
    print("=" * 60)

    generator = SelfCorrectingCodeGenerator()
    result = await generator.execute(
        {
            "task": "Write a function to validate email addresses",
            "requirements": "Must handle edge cases and use regex",
        }
    )

    print("\n--- Final Result ---")
    print(f"Status: {result['status']}")
    print(f"Quality: {result['quality_score']}/100")
    print(f"Attempts: {result['attempts']}")
    print(f"Code:\n{result['code']}")


async def main():
    """Run all pattern demonstrations."""
    print("\n🚀 ANTHROPIC AGENT PATTERNS DEMO")
    print("Demonstrating the three core patterns in Attune AI\n")

    try:
        # Pattern 1: Sequential Workflow
        await demo_pattern_1()

        # Pattern 2: Orchestrator
        await demo_pattern_2()

        # Pattern 3: Self-Correcting
        await demo_pattern_3()

        print("\n" + "=" * 60)
        print("✅ ALL PATTERNS DEMONSTRATED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
