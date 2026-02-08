"""Structural workflow patterns.

How workflows are organized and structured.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from typing import Any

from .core import CodeSection, PatternCategory, WorkflowComplexity, WorkflowPattern


class SingleStagePattern(WorkflowPattern):
    """Single-stage workflow - simplest pattern.

    Use for: Quick tasks that don't need multiple steps.
    Examples: Simple text analysis, single API call, basic validation.
    """

    id: str = "single-stage"
    name: str = "Single Stage Workflow"
    category: PatternCategory = PatternCategory.STRUCTURAL
    description: str = "Simple one-stage workflow with single tier"
    complexity: WorkflowComplexity = WorkflowComplexity.SIMPLE
    use_cases: list[str] = [
        "Quick analysis tasks",
        "Single API calls",
        "Basic validation or formatting",
    ]
    examples: list[str] = []
    risk_weight: float = 1.0

    def generate_code_sections(self, context: dict[str, Any]) -> list[CodeSection]:
        """Generate code for single-stage workflow."""
        workflow_name = context.get("workflow_name", "MyWorkflow")
        context.get("class_name", "MyWorkflow")
        description = context.get("description", "Single-stage workflow")
        tier = context.get("tier", "CAPABLE")

        return [
            CodeSection(
                location="class_attributes",
                code=f"""    name = "{workflow_name}"
    description = "{description}"
    stages = ["process"]
    tier_map = {{
        "process": ModelTier.{tier},
    }}""",
                priority=1,
            ),
            CodeSection(
                location="methods",
                code='''    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute the single processing stage."""
        if stage_name == "process":
            return await self._process(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _process(
        self,
        input_data: Any,
        tier: ModelTier,
    ) -> tuple[Any, int, int]:
        """Process the input data.

        Args:
            input_data: Input data to process
            tier: Model tier to use

        Returns:
            Tuple of (result, input_tokens, output_tokens)

        """
        # TODO: Implement processing logic
        prompt = f"Process this input: {input_data}"

        # Use LLM executor if available
        if self.executor:
            result = await self.executor.execute(
                prompt=prompt,
                tier=tier.to_unified() if hasattr(tier, "to_unified") else tier,
            )
            return result.content, result.input_tokens, result.output_tokens

        # Fallback to basic processing
        return {"result": "Processed", "input": input_data}, 0, 0''',
                priority=2,
            ),
        ]


class MultiStagePattern(WorkflowPattern):
    """Multi-stage workflow with sequential execution.

    Use for: Complex tasks requiring multiple processing steps.
    Examples: Code review (classify → scan → recommend), bug prediction.
    """

    id: str = "multi-stage"
    name: str = "Multi-Stage Workflow"
    category: PatternCategory = PatternCategory.STRUCTURAL
    description: str = "Multiple sequential stages with different tiers"
    complexity: WorkflowComplexity = WorkflowComplexity.MODERATE
    use_cases: list[str] = [
        "Code analysis pipelines",
        "Multi-step processing",
        "Tiered cost optimization",
    ]
    examples: list[str] = ["bug-predict", "code-review", "pr-review"]
    risk_weight: float = 2.5

    def generate_code_sections(self, context: dict[str, Any]) -> list[CodeSection]:
        """Generate code for multi-stage workflow."""
        workflow_name = context.get("workflow_name", "my-workflow")
        context.get("class_name", "MyWorkflow")
        description = context.get("description", "Multi-stage workflow")
        stages = context.get("stages", ["analyze", "process", "report"])
        tier_map = context.get(
            "tier_map",
            {
                "analyze": "CHEAP",
                "process": "CAPABLE",
                "report": "PREMIUM",
            },
        )

        # Generate tier map code
        tier_map_code = "    tier_map = {\n"
        for stage, tier in tier_map.items():
            tier_map_code += f'        "{stage}": ModelTier.{tier},\n'
        tier_map_code += "    }"

        # Generate stage routing
        stage_routing = []
        for _i, stage in enumerate(stages):
            stage_routing.append(
                f"""        if stage_name == "{stage}":
            return await self._{stage}(input_data, tier)"""
            )

        stage_routing_code = "\n".join(stage_routing)

        # Generate stage method templates
        stage_methods = []
        for stage in stages:
            stage_methods.append(
                f'''    async def _{stage}(
        self,
        input_data: Any,
        tier: ModelTier,
    ) -> tuple[Any, int, int]:
        """{stage.replace("_", " ").title()} stage.

        Args:
            input_data: Input from previous stage
            tier: Model tier to use

        Returns:
            Tuple of (result, input_tokens, output_tokens)

        """
        # TODO: Implement {stage} logic
        prompt = f"{{stage}} stage: {{input_data}}"

        if self.executor:
            result = await self.executor.execute(
                prompt=prompt,
                tier=tier.to_unified() if hasattr(tier, "to_unified") else tier,
            )
            return result.content, result.input_tokens, result.output_tokens

        return {{"stage": "{stage}", "input": input_data}}, 0, 0'''
            )

        return [
            CodeSection(
                location="class_attributes",
                code=f"""    name = "{workflow_name}"
    description = "{description}"
    stages = {stages}
{tier_map_code}""",
                priority=1,
            ),
            CodeSection(
                location="methods",
                code=f'''    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation."""
{stage_routing_code}
        raise ValueError(f"Unknown stage: {{stage_name}}")

{chr(10).join(stage_methods)}''',
                priority=2,
            ),
        ]


class CrewBasedPattern(WorkflowPattern):
    """Workflow that wraps a CrewAI crew.

    Use for: Multi-agent collaboration tasks.
    Examples: Health check, security audit, code review.
    """

    id: str = "crew-based"
    name: str = "Crew-Based Workflow"
    category: PatternCategory = PatternCategory.INTEGRATION
    description: str = "Wraps CrewAI crew for multi-agent collaboration"
    complexity: WorkflowComplexity = WorkflowComplexity.COMPLEX
    use_cases: list[str] = [
        "Multi-agent tasks",
        "Complex analysis requiring specialized roles",
        "Collaborative problem solving",
    ]
    examples: list[str] = ["health-check", "security-audit"]
    conflicts_with: list[str] = ["single-stage"]
    risk_weight: float = 3.5

    def generate_code_sections(self, context: dict[str, Any]) -> list[CodeSection]:
        """Generate code for crew-based workflow."""
        workflow_name = context.get("workflow_name", "my-crew-workflow")
        context.get("class_name", "MyCrewWorkflow")
        description = context.get("description", "Crew-based workflow")
        crew_name = context.get("crew_name", "MyCrew")

        return [
            CodeSection(
                location="class_attributes",
                code=f"""    name = "{workflow_name}"
    description = "{description}"
    stages = ["analyze", "fix"]
    tier_map = {{
        "analyze": ModelTier.CAPABLE,
        "fix": ModelTier.CAPABLE,
    }}""",
                priority=1,
            ),
            CodeSection(
                location="init_method",
                code="""        self._crew: Any = None
        self._crew_available = False""",
                priority=1,
            ),
            CodeSection(
                location="methods",
                code=f'''    async def _initialize_crew(self) -> None:
        """Initialize the {crew_name}."""
        if self._crew is not None:
            return

        try:
            from attune_llm.agent_factory.crews import {crew_name}

            self._crew = {crew_name}()
            self._crew_available = True
            logger.info("{crew_name} initialized successfully")
        except ImportError as e:
            logger.warning(f"{crew_name} not available: {{e}}")
            self._crew_available = False

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to crew for execution."""
        await self._initialize_crew()

        if not self._crew_available:
            return {{"error": "Crew not available"}}, 0, 0

        # Execute crew task
        result = await self._crew.execute(stage_name, input_data)
        return result, 0, 0  # Crew handles token counting internally''',
                priority=2,
            ),
        ]
