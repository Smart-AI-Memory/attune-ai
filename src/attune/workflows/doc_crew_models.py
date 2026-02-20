"""Data models for the ManageDocumentation crew workflow.

Contains the dataclasses used by ManageDocumentationCrew:
- ManageDocumentationCrewResult: Result from crew execution
- Agent: Agent configuration with XML-enhanced prompting
- Task: Task configuration with XML-enhanced prompting
- parse_xml_response: Parse XML-structured agent responses

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re
from dataclasses import dataclass, field


@dataclass
class ManageDocumentationCrewResult:
    """Result from ManageDocumentationCrew execution."""

    success: bool
    findings: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    files_analyzed: int = 0
    docs_needing_update: int = 0
    new_docs_needed: int = 0
    confidence: float = 0.0
    cost: float = 0.0
    duration_ms: int = 0
    formatted_report: str = ""

    def to_dict(self) -> dict:
        """Serialize result to a dictionary.

        Returns:
            Dictionary representation of the result.
        """
        return {
            "success": self.success,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "files_analyzed": self.files_analyzed,
            "docs_needing_update": self.docs_needing_update,
            "new_docs_needed": self.new_docs_needed,
            "confidence": self.confidence,
            "cost": self.cost,
            "duration_ms": self.duration_ms,
            "formatted_report": self.formatted_report,
        }


@dataclass
class Agent:
    """Agent configuration for the crew with XML-enhanced prompting."""

    role: str
    goal: str
    backstory: str
    expertise_level: str = "expert"
    use_xml_structure: bool = True  # Enable XML-enhanced prompting by default

    def get_system_prompt(self) -> str:
        """Generate XML-enhanced system prompt for this agent.

        Returns:
            Formatted system prompt string (XML or legacy format).
        """
        if not self.use_xml_structure:
            # Legacy format for backward compatibility
            return (
                f"You are a {self.role} with "
                f"{self.expertise_level}-level expertise.\n\n"
                f"Goal: {self.goal}\n\n"
                f"Background: {self.backstory}\n\n"
                "Provide thorough, actionable analysis. "
                "Be specific and cite file paths when relevant."
            )

        # XML-enhanced format (Anthropic best practice)
        return f"""<agent_role>
You are a {self.role} with {self.expertise_level}-level expertise.
</agent_role>

<agent_goal>
{self.goal}
</agent_goal>

<agent_backstory>
{self.backstory}
</agent_backstory>

<instructions>
1. Carefully review all provided context data
2. Think through your analysis step-by-step
3. Provide thorough, actionable analysis
4. Be specific and cite file paths when relevant
5. Structure your output according to the requested format
</instructions>

<output_structure>
Always structure your response as:

<thinking>
[Your step-by-step reasoning process]
- What you observe in the context
- How you analyze the situation
- What conclusions you draw
</thinking>

<answer>
[Your final output in the requested format]
</answer>
</output_structure>"""


@dataclass
class Task:
    """Task configuration for the crew with XML-enhanced prompting."""

    description: str
    expected_output: str
    agent: Agent

    def get_user_prompt(self, context: dict) -> str:
        """Generate XML-enhanced user prompt for this task with context.

        Args:
            context: Dictionary of context data for the task.

        Returns:
            Formatted user prompt string (XML or legacy format).
        """
        if not self.agent.use_xml_structure:
            # Legacy format for backward compatibility
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items() if v)
            return (
                f"{self.description}\n\n"
                f"Context:\n{context_str}\n\n"
                f"Expected output format: {self.expected_output}"
            )

        # XML-enhanced format (Anthropic best practice)
        # Build structured context with proper XML tags
        context_sections = []
        for key, value in context.items():
            if value:
                # Use underscores for tag names
                tag_name = key.replace(" ", "_").replace("-", "_").lower()
                # Wrap in appropriate tags
                context_sections.append(f"<{tag_name}>\n{value}\n</{tag_name}>")

        context_xml = "\n".join(context_sections)

        return f"""<task_description>
{self.description}
</task_description>

<context>
{context_xml}
</context>

<expected_output>
{self.expected_output}
</expected_output>

<instructions>
1. Review all context data in the <context> tags above
2. Structure your response using <thinking> and <answer> tags as defined in your system prompt
3. Match the expected output format exactly
4. Be thorough and specific in your analysis
</instructions>"""


def parse_xml_response(response: str) -> dict:
    """Parse XML-structured agent response.

    Args:
        response: Raw agent response potentially containing XML tags

    Returns:
        Dictionary with 'thinking', 'answer', and 'raw' keys
    """
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", response, re.DOTALL)
    answer_match = re.search(r"<answer>(.*?)</answer>", response, re.DOTALL)

    return {
        "thinking": (thinking_match.group(1).strip() if thinking_match else ""),
        "answer": (answer_match.group(1).strip() if answer_match else response.strip()),
        "raw": response,
        "has_structure": bool(thinking_match and answer_match),
    }
