"""Agent and Workflow Generator

Generates concrete agents and workflows from blueprints.

This module transforms abstract blueprints (from Socratic questioning)
into runnable agent instances and workflow configurations.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .blueprint import (
    AgentBlueprint,
    AgentRole,
    AgentSpec,
    StageSpec,
    WorkflowBlueprint,
)
from .generated_workflow import GeneratedWorkflow
from .generator_registry import AGENT_TEMPLATES, TOOL_REGISTRY, AgentTemplate
from .success import SuccessCriteria

if TYPE_CHECKING:
    from ..workflows.xml_enhanced_crew import XMLAgent

logger = logging.getLogger(__name__)


class AgentGenerator:
    """Generates agents and workflows from blueprints.

    Example:
        >>> generator = AgentGenerator()
        >>>
        >>> # Generate from blueprint
        >>> blueprint = WorkflowBlueprint(...)
        >>> workflow = generator.generate_workflow(blueprint)
        >>>
        >>> # Generate from template
        >>> agent = generator.generate_agent_from_template(
        ...     "security_reviewer",
        ...     customizations={"languages": ["python"]}
        ... )
    """

    def __init__(self):
        """Initialize the generator."""
        self.templates = AGENT_TEMPLATES.copy()
        self.tools = TOOL_REGISTRY.copy()

    def register_template(self, template: AgentTemplate) -> None:
        """Register a custom agent template."""
        self.templates[template.id] = template

    def register_tool(self, tool: Any) -> None:
        """Register a custom tool."""
        self.tools[tool.id] = tool

    def generate_agent_from_template(
        self,
        template_id: str,
        customizations: dict[str, Any] | None = None,
    ) -> AgentBlueprint:
        """Generate an agent blueprint from a template.

        Args:
            template_id: ID of the template to use
            customizations: Override template defaults

        Returns:
            AgentBlueprint ready for instantiation

        Raises:
            ValueError: If template not found
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")

        spec = template.create_spec(customizations)

        return AgentBlueprint(
            spec=spec,
            generated_from="template",
            template_id=template_id,
            customizations=customizations or {},
        )

    def generate_agents_for_requirements(
        self,
        requirements: dict[str, Any],
    ) -> list[AgentBlueprint]:
        """Generate appropriate agents based on requirements.

        This is the core intelligent generation that maps requirements
        (from Socratic questioning) to agent configurations.

        Args:
            requirements: Requirements gathered from Socratic session
                - quality_focus: list of quality attributes
                - languages: list of programming languages
                - automation_level: advisory/semi_auto/fully_auto
                - domain: domain (e.g., "code_review", "testing")

        Returns:
            List of AgentBlueprints for a complete team
        """
        agents: list[AgentBlueprint] = []
        quality_focus = requirements.get("quality_focus", [])
        languages = requirements.get("languages", [])
        automation = requirements.get("automation_level", "semi_auto")

        # Map quality focus to agent templates
        quality_to_templates = {
            "security": ["security_reviewer"],
            "performance": ["performance_analyzer"],
            "maintainability": ["code_quality_reviewer", "documentation_writer"],
            "reliability": ["code_quality_reviewer", "test_generator"],
            "testability": ["test_generator"],
        }

        # Collect needed templates
        needed_templates: set[str] = set()
        for quality in quality_focus:
            templates = quality_to_templates.get(quality, [])
            needed_templates.update(templates)

        # Default to basic code review if no specific focus
        if not needed_templates:
            needed_templates.add("code_quality_reviewer")

        # Add synthesizer for results aggregation
        if len(needed_templates) > 1:
            needed_templates.add("result_synthesizer")

        # Generate agent for each template
        for template_id in needed_templates:
            customizations = {
                "languages": languages,
                "quality_focus": quality_focus,
            }

            # Adjust for automation level
            if automation == "fully_auto":
                customizations["instructions"] = [
                    "Apply fixes automatically where safe",
                    "Minimize human review requirements",
                ]
            elif automation == "advisory":
                customizations["instructions"] = [
                    "Provide recommendations only",
                    "Do not modify any files",
                ]

            try:
                agent = self.generate_agent_from_template(template_id, customizations)
                agents.append(agent)
            except ValueError:
                logger.warning(f"Template not found: {template_id}")

        return agents

    def generate_workflow(
        self,
        blueprint: WorkflowBlueprint,
    ) -> GeneratedWorkflow:
        """Generate a complete workflow from a blueprint.

        Args:
            blueprint: The workflow blueprint to generate from

        Returns:
            GeneratedWorkflow ready for execution
        """
        # Validate blueprint
        is_valid, errors = blueprint.validate()
        if not is_valid:
            raise ValueError(f"Invalid blueprint: {'; '.join(errors)}")

        # Generate XML agents from blueprints
        xml_agents = []
        for agent_bp in blueprint.agents:
            xml_agent = self._create_xml_agent(agent_bp.spec)
            xml_agents.append(xml_agent)

        # Build stage configuration
        stages_config = []
        for stage in blueprint.stages:
            stages_config.append(
                {
                    "id": stage.id,
                    "name": stage.name,
                    "agents": stage.agent_ids,
                    "parallel": stage.parallel,
                    "depends_on": stage.depends_on,
                    "timeout": stage.timeout,
                }
            )

        return GeneratedWorkflow(
            blueprint=blueprint,
            agents=xml_agents,
            stages=stages_config,
            generated_at=datetime.now().isoformat(),
        )

    def _create_xml_agent(self, spec: AgentSpec) -> XMLAgent:
        """Create an XMLAgent from a spec."""
        from ..workflows.xml_enhanced_crew import XMLAgent

        return XMLAgent(
            role=spec.name,
            goal=spec.goal,
            backstory=spec.backstory,
            expertise_level="expert" if spec.model_tier != "cheap" else "competent",
            custom_instructions=spec.custom_instructions,
        )

    def create_workflow_blueprint(
        self,
        name: str,
        description: str,
        agents: list[AgentBlueprint],
        quality_focus: list[str],
        automation_level: str,
        success_criteria: SuccessCriteria | None = None,
    ) -> WorkflowBlueprint:
        """Create a workflow blueprint with automatic staging.

        Args:
            name: Workflow name
            description: Workflow description
            agents: Agent blueprints to include
            quality_focus: Quality attributes to optimize for
            automation_level: Level of automation
            success_criteria: Optional success criteria

        Returns:
            Complete WorkflowBlueprint
        """
        # Group agents by role for staging
        analyzers = [
            a
            for a in agents
            if a.spec.role in (AgentRole.ANALYZER, AgentRole.REVIEWER, AgentRole.AUDITOR)
        ]
        generators = [a for a in agents if a.spec.role == AgentRole.GENERATOR]
        reporters = [a for a in agents if a.spec.role == AgentRole.REPORTER]

        stages = []

        # Stage 1: Analysis (parallel)
        if analyzers:
            stages.append(
                StageSpec(
                    id="analysis",
                    name="Analysis",
                    description="Analyze code and identify issues",
                    agent_ids=[a.spec.id for a in analyzers],
                    parallel=True,
                    output_aggregation="merge",
                )
            )

        # Stage 2: Generation (sequential, depends on analysis)
        if generators:
            stages.append(
                StageSpec(
                    id="generation",
                    name="Generation",
                    description="Generate fixes and improvements",
                    agent_ids=[a.spec.id for a in generators],
                    parallel=False,
                    depends_on=["analysis"] if analyzers else [],
                )
            )

        # Stage 3: Synthesis (always last)
        if reporters:
            depends = []
            if analyzers:
                depends.append("analysis")
            if generators:
                depends.append("generation")

            stages.append(
                StageSpec(
                    id="synthesis",
                    name="Synthesis",
                    description="Synthesize findings into report",
                    agent_ids=[a.spec.id for a in reporters],
                    parallel=False,
                    depends_on=depends,
                )
            )

        return WorkflowBlueprint(
            name=name,
            description=description,
            agents=agents,
            stages=stages,
            quality_focus=quality_focus,
            automation_level=automation_level,
            success_criteria=success_criteria,
            generated_at=datetime.now().isoformat(),
        )
