"""Plan Generator for Meta-Workflows.

Generates execution plans from meta-workflow templates that can be executed
by Claude Code instead of making direct API calls.

This enables users to leverage their Claude Max subscription instead of
paying per-API-call costs.

Output formats:
- Markdown: Human-readable plan for interactive use
- Claude Code Skill: .claude/commands/ compatible format
- JSON: Programmatic consumption

Created: 2026-01-20
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from attune.meta_workflows.models import (
    AgentCompositionRule,
    MetaWorkflowTemplate,
    TierStrategy,
)
from attune.orchestration.agent_templates import get_template


@dataclass
class AgentStep:
    """A single step in the execution plan."""

    order: int
    role: str
    tier_recommendation: str
    tools: list[str]
    prompt: str
    success_criteria: list[str]
    config: dict


@dataclass
class ExecutionPlan:
    """Complete execution plan for a meta-workflow."""

    template_id: str
    template_name: str
    generated_at: str
    form_responses: dict
    steps: list[AgentStep]
    synthesis_prompt: str


class PlanGenerator:
    """Generates execution plans from meta-workflow templates."""

    # Map tier strategies to Claude Code model recommendations
    TIER_TO_MODEL = {
        TierStrategy.CHEAP_ONLY: "haiku",
        TierStrategy.PROGRESSIVE: "sonnet (escalate to opus if needed)",
        TierStrategy.CAPABLE_FIRST: "sonnet",
        TierStrategy.PREMIUM_ONLY: "opus",
    }

    def __init__(self, template: MetaWorkflowTemplate):
        """Initialize with a template.

        Args:
            template: The meta-workflow template to generate a plan from
        """
        self.template = template

    def generate(
        self,
        form_responses: dict | None = None,
        use_defaults: bool = True,
    ) -> ExecutionPlan:
        """Generate an execution plan.

        Args:
            form_responses: User responses to form questions
            use_defaults: Whether to use default values for missing responses

        Returns:
            ExecutionPlan ready for execution
        """
        # Collect form responses
        responses = self._collect_responses(form_responses, use_defaults)

        # Build steps from composition rules
        steps = self._build_steps(responses)

        # Generate synthesis prompt
        synthesis = self._build_synthesis_prompt(steps)

        return ExecutionPlan(
            template_id=self.template.template_id,
            template_name=self.template.name,
            generated_at=datetime.now().isoformat(),
            form_responses=responses,
            steps=steps,
            synthesis_prompt=synthesis,
        )

    def _collect_responses(
        self,
        provided: dict | None,
        use_defaults: bool,
    ) -> dict:
        """Collect form responses with defaults."""
        responses = {}
        provided = provided or {}

        for question in self.template.form_schema.questions:
            if question.id in provided:
                responses[question.id] = provided[question.id]
            elif use_defaults and question.default:
                responses[question.id] = question.default
            elif question.required:
                raise ValueError(f"Missing required response: {question.id}")

        return responses

    def _build_steps(self, responses: dict) -> list[AgentStep]:
        """Build execution steps from composition rules."""
        steps = []
        order = 1

        for rule in self.template.agent_composition_rules:
            # Check if this agent should be included based on responses
            if not self._should_include_agent(rule, responses):
                continue

            # Get base template for additional context
            base_template = get_template(rule.base_template)

            # Build the prompt
            prompt = self._build_agent_prompt(rule, base_template, responses)

            # Map config from responses
            config = {}
            for response_key, config_key in rule.config_mapping.items():
                if response_key in responses:
                    config[config_key] = responses[response_key]

            steps.append(
                AgentStep(
                    order=order,
                    role=rule.role,
                    tier_recommendation=self.TIER_TO_MODEL.get(rule.tier_strategy, "sonnet"),
                    tools=rule.tools,
                    prompt=prompt,
                    success_criteria=rule.success_criteria,
                    config=config,
                )
            )
            order += 1

        return steps

    def _should_include_agent(
        self,
        rule: AgentCompositionRule,
        responses: dict,
    ) -> bool:
        """Check if agent should be included based on required responses."""
        for key, required_value in rule.required_responses.items():
            if responses.get(key) != required_value:
                return False
        return True

    def _build_agent_prompt(
        self,
        rule: AgentCompositionRule,
        base_template,
        responses: dict,
    ) -> str:
        """Build the prompt for an agent."""
        # Start with base template instructions
        base_instructions = ""
        if base_template:
            base_instructions = base_template.default_instructions

        # Build context from responses
        context_lines = []
        for key, value in rule.config_mapping.items():
            if key in responses:
                context_lines.append(f"- {value}: {responses[key]}")

        context = "\n".join(context_lines) if context_lines else "Using default configuration."

        # Build success criteria checklist
        criteria = "\n".join(f"- [ ] {c}" for c in rule.success_criteria)

        return f"""You are a {rule.role} analyzing this codebase.

{base_instructions}

Configuration:
{context}

Success Criteria:
{criteria}

Tools available: {", ".join(rule.tools)}

Provide a structured report with findings, issues by severity, and recommendations.
"""

    def _build_synthesis_prompt(self, steps: list[AgentStep]) -> str:
        """Build the synthesis prompt that combines all agent outputs."""
        roles = [f"- {step.role}" for step in steps]
        roles_list = "\n".join(roles)

        return f"""You are synthesizing the results from multiple agents.

Combine the outputs from:
{roles_list}

Create a comprehensive report:

## Summary
Overall assessment of the analysis.

## Critical Issues (must address)
List any blockers or critical problems.

## Recommendations (should address)
List improvements and fixes.

## Action Items
Prioritized list of next steps.

## Risk Assessment
What risks exist? What's the recommended path forward?
"""

    def to_markdown(self, plan: ExecutionPlan) -> str:
        """Convert plan to markdown format."""
        lines = [
            f"# Execution Plan: {plan.template_name}",
            "",
            "> Generated by Empathy Framework",
            f"> Template: {plan.template_id}",
            f"> Generated: {plan.generated_at}",
            "",
            "## Configuration",
            "",
        ]

        for key, value in plan.form_responses.items():
            lines.append(f"- **{key}**: {value}")

        lines.extend(["", "---", "", "## Execution Steps", ""])

        for step in plan.steps:
            lines.extend(
                [
                    f"### Step {step.order}: {step.role}",
                    "",
                    f"**Tier Recommendation**: {step.tier_recommendation}",
                    f"**Tools**: {', '.join(step.tools)}",
                    "",
                    "**Prompt:**",
                    "```",
                    step.prompt,
                    "```",
                    "",
                    "**Success Criteria:**",
                ]
            )
            for criterion in step.success_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.extend(["", "---", ""])

        lines.extend(
            [
                "## Synthesis",
                "",
                "After all steps complete, run this synthesis:",
                "",
                "```",
                plan.synthesis_prompt,
                "```",
            ]
        )

        return "\n".join(lines)

    def to_claude_code_skill(self, plan: ExecutionPlan) -> str:
        """Convert plan to Claude Code skill format.

        This generates content for .claude/commands/<template-id>.md
        """
        steps_text = []
        for step in plan.steps:
            steps_text.append(
                f"""
### {step.role}
Use the Task tool with subagent_type="Explore" to:
{step.prompt}
"""
            )

        return f"""# {plan.template_name}

Execute the {plan.template_name} workflow for this codebase.

## Steps

{"".join(steps_text)}

## Synthesis

After completing all steps, synthesize the findings:
{plan.synthesis_prompt}

## Output

Provide a final report with:
1. Overall status (READY / NEEDS WORK / BLOCKED)
2. Critical issues found
3. Recommendations
4. Next steps
"""


def generate_plan(
    template_id: str,
    form_responses: dict | None = None,
    use_defaults: bool = True,
    output_format: Literal["markdown", "skill", "json"] = "markdown",
) -> str:
    """Generate an execution plan for a meta-workflow.

    Args:
        template_id: ID of the template to use
        form_responses: Optional form responses
        use_defaults: Whether to use default values
        output_format: Output format (markdown, skill, or json)

    Returns:
        Plan in the requested format
    """
    from attune.meta_workflows.registry import get_template as get_workflow_template

    template = get_workflow_template(template_id)
    if not template:
        raise ValueError(f"Template not found: {template_id}")

    generator = PlanGenerator(template)
    plan = generator.generate(form_responses, use_defaults)

    if output_format == "markdown":
        return generator.to_markdown(plan)
    elif output_format == "skill":
        return generator.to_claude_code_skill(plan)
    elif output_format == "json":
        import json

        return json.dumps(
            {
                "template_id": plan.template_id,
                "template_name": plan.template_name,
                "generated_at": plan.generated_at,
                "form_responses": plan.form_responses,
                "steps": [
                    {
                        "order": s.order,
                        "role": s.role,
                        "tier_recommendation": s.tier_recommendation,
                        "tools": s.tools,
                        "prompt": s.prompt,
                        "success_criteria": s.success_criteria,
                        "config": s.config,
                    }
                    for s in plan.steps
                ],
                "synthesis_prompt": plan.synthesis_prompt,
            },
            indent=2,
        )
    else:
        raise ValueError(f"Unknown format: {output_format}")
