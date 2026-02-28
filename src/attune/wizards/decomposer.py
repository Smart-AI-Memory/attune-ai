"""XML task decomposition engine.

Breaks complex problems into structured XML sub-tasks following
the ``<task>`` schema from ``docs/implementation/TASK_PROMPTS.md``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from attune.workflows.compat import ModelTier

logger = logging.getLogger(__name__)

# =========================================================================
# Decomposition prompt template
# =========================================================================

DECOMPOSITION_SYSTEM_PROMPT = """\
You are a task decomposition specialist. Given a problem description and
codebase context, break the work into self-contained sub-tasks.

Respond ONLY with XML in this format (no other text):

<tasks>
  <task id="1" name="short-name">
    <objective>What this task accomplishes (1-2 sentences)</objective>
    <files-to-create>
      <file path="path/to/new.py">Brief description of contents</file>
    </files-to-create>
    <files-to-modify>
      <file path="path/to/existing.py">What changes to make</file>
    </files-to-modify>
    <validation>
      <check>How to verify this task is done correctly</check>
    </validation>
    <risks>
      <risk severity="low|medium|high">Risk description and mitigation</risk>
    </risks>
    <dependencies>
      <dep>task-id that must complete first</dep>
    </dependencies>
  </task>
</tasks>

Rules:
- Each task should be self-contained and independently executable
- Include ALL files that need to be created or modified
- Validation checks should be specific and testable
- Order tasks by dependency (independent tasks first)
- Keep tasks small: ideally 1-3 files each
"""


# =========================================================================
# Data classes
# =========================================================================


@dataclass
class DecomposedTask:
    """A single task extracted from XML decomposition.

    Args:
        task_id: Unique task identifier.
        name: Short task name.
        objective: What the task accomplishes.
        files_to_create: List of ``{path, description}`` dicts.
        files_to_modify: List of ``{path, description}`` dicts.
        validation_checks: How to verify correctness.
        risks: List of ``{severity, description}`` dicts.
        dependencies: Task IDs that must complete first.

    """

    task_id: str
    name: str
    objective: str
    files_to_create: list[dict[str, str]] = field(default_factory=list)
    files_to_modify: list[dict[str, str]] = field(default_factory=list)
    validation_checks: list[str] = field(default_factory=list)
    risks: list[dict[str, str]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation of this task.

        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "objective": self.objective,
            "files_to_create": self.files_to_create,
            "files_to_modify": self.files_to_modify,
            "validation_checks": self.validation_checks,
            "risks": self.risks,
            "dependencies": self.dependencies,
        }

    def to_xml(self) -> str:
        """Render this task as XML.

        Returns:
            XML string following the task prompt schema.

        """
        parts = [f'<task id="{self.task_id}" name="{self.name}">']
        parts.append(f"  <objective>{self.objective}</objective>")

        if self.files_to_create:
            parts.append("  <files-to-create>")
            for f in self.files_to_create:
                parts.append(f'    <file path="{f["path"]}">{f.get("description", "")}</file>')
            parts.append("  </files-to-create>")

        if self.files_to_modify:
            parts.append("  <files-to-modify>")
            for f in self.files_to_modify:
                parts.append(f'    <file path="{f["path"]}">{f.get("description", "")}</file>')
            parts.append("  </files-to-modify>")

        if self.validation_checks:
            parts.append("  <validation>")
            for check in self.validation_checks:
                parts.append(f"    <check>{check}</check>")
            parts.append("  </validation>")

        if self.risks:
            parts.append("  <risks>")
            for risk in self.risks:
                severity = risk.get("severity", "medium")
                desc = risk.get("description", "")
                parts.append(f'    <risk severity="{severity}">{desc}</risk>')
            parts.append("  </risks>")

        if self.dependencies:
            parts.append("  <dependencies>")
            for dep in self.dependencies:
                parts.append(f"    <dep>{dep}</dep>")
            parts.append("  </dependencies>")

        parts.append("</task>")
        return "\n".join(parts)


# =========================================================================
# Task Decomposer
# =========================================================================


class TaskDecomposer:
    """Decomposes complex problems into structured XML tasks.

    Uses an LLM to analyze a problem description and produce a list
    of ``DecomposedTask`` objects following the XML task schema.

    Args:
        workflow: ``WizardInternalWorkflow`` for LLM access.

    Example:
        >>> decomposer = TaskDecomposer(workflow)
        >>> tasks = await decomposer.decompose(
        ...     problem_description="Add user authentication",
        ...     codebase_context="Flask app with SQLAlchemy",
        ...     constraints=["Use JWT tokens", "Add tests"],
        ... )

    """

    def __init__(self, workflow: Any) -> None:
        self._workflow = workflow

    async def decompose(
        self,
        problem_description: str,
        codebase_context: str,
        constraints: list[str] | None = None,
    ) -> list[DecomposedTask]:
        """Decompose a problem into sub-tasks using LLM.

        Args:
            problem_description: What needs to be accomplished.
            codebase_context: Relevant code or file structure.
            constraints: Rules the decomposition must follow.

        Returns:
            Ordered list of ``DecomposedTask`` objects.

        """
        constraints = constraints or []

        prompt_parts = [
            DECOMPOSITION_SYSTEM_PROMPT,
            "",
            f"Problem: {problem_description}",
            "",
        ]

        if codebase_context:
            prompt_parts.append(f"Codebase context:\n{codebase_context}")
            prompt_parts.append("")

        if constraints:
            prompt_parts.append("Constraints:")
            for c in constraints:
                prompt_parts.append(f"- {c}")

        prompt = "\n".join(prompt_parts)

        try:
            result = await self._workflow._call_llm(prompt, ModelTier.CAPABLE, "decompose")
            if isinstance(result, tuple):
                response_text = result[0]
            else:
                response_text = str(result)
        except Exception as e:
            logger.error("Task decomposition LLM call failed: %s", e)
            return []

        return self._parse_tasks_from_xml(response_text)

    def _parse_tasks_from_xml(self, xml_content: str) -> list[DecomposedTask]:
        """Parse ``<task>`` elements from XML response.

        Uses regex extraction for robustness -- LLM responses may include
        markdown fences or extra text around the XML.

        Args:
            xml_content: Raw LLM response text.

        Returns:
            List of ``DecomposedTask`` objects.

        """
        tasks: list[DecomposedTask] = []

        # Extract individual <task> blocks
        task_pattern = re.compile(
            r'<task\s+id="([^"]*)"(?:\s+name="([^"]*)")?\s*>(.*?)</task>',
            re.DOTALL,
        )

        for match in task_pattern.finditer(xml_content):
            task_id = match.group(1)
            name = match.group(2) or task_id
            body = match.group(3)

            objective = self._extract_tag(body, "objective")
            files_to_create = self._extract_files(body, "files-to-create")
            files_to_modify = self._extract_files(body, "files-to-modify")
            validation_checks = self._extract_list(body, "validation", "check")
            risks = self._extract_risks(body)
            dependencies = self._extract_list(body, "dependencies", "dep")

            tasks.append(
                DecomposedTask(
                    task_id=task_id,
                    name=name,
                    objective=objective,
                    files_to_create=files_to_create,
                    files_to_modify=files_to_modify,
                    validation_checks=validation_checks,
                    risks=risks,
                    dependencies=dependencies,
                ),
            )

        if not tasks:
            logger.warning("No <task> elements found in decomposition response")

        return tasks

    # -----------------------------------------------------------------
    # XML extraction helpers
    # -----------------------------------------------------------------

    def _extract_tag(self, xml: str, tag: str) -> str:
        """Extract text content of a single tag.

        Args:
            xml: XML fragment to search.
            tag: Tag name.

        Returns:
            Tag text content, or empty string if not found.

        """
        match = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_files(self, xml: str, section_tag: str) -> list[dict[str, str]]:
        """Extract file entries from a section.

        Args:
            xml: XML fragment.
            section_tag: Parent tag (e.g. ``"files-to-create"``).

        Returns:
            List of ``{path, description}`` dicts.

        """
        section_match = re.search(
            rf"<{section_tag}>(.*?)</{section_tag}>",
            xml,
            re.DOTALL,
        )
        if not section_match:
            return []

        section = section_match.group(1)
        files: list[dict[str, str]] = []
        file_pattern = re.compile(r'<file\s+path="([^"]*)">(.*?)</file>', re.DOTALL)
        for match in file_pattern.finditer(section):
            files.append({"path": match.group(1), "description": match.group(2).strip()})

        return files

    def _extract_list(self, xml: str, section_tag: str, item_tag: str) -> list[str]:
        """Extract a list of text items from a section.

        Args:
            xml: XML fragment.
            section_tag: Parent tag.
            item_tag: Child tag for each item.

        Returns:
            List of text strings.

        """
        section_match = re.search(
            rf"<{section_tag}>(.*?)</{section_tag}>",
            xml,
            re.DOTALL,
        )
        if not section_match:
            return []

        section = section_match.group(1)
        items: list[str] = []
        item_pattern = re.compile(rf"<{item_tag}>(.*?)</{item_tag}>", re.DOTALL)
        for match in item_pattern.finditer(section):
            items.append(match.group(1).strip())

        return items

    def _extract_risks(self, xml: str) -> list[dict[str, str]]:
        """Extract risk entries with severity.

        Args:
            xml: XML fragment.

        Returns:
            List of ``{severity, description}`` dicts.

        """
        section_match = re.search(r"<risks>(.*?)</risks>", xml, re.DOTALL)
        if not section_match:
            return []

        section = section_match.group(1)
        risks: list[dict[str, str]] = []
        risk_pattern = re.compile(r'<risk\s+severity="([^"]*)">(.*?)</risk>', re.DOTALL)
        for match in risk_pattern.finditer(section):
            risks.append({"severity": match.group(1), "description": match.group(2).strip()})

        return risks
