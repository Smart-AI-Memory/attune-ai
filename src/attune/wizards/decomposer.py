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

CRITICAL OUTPUT RULES — follow exactly:
- Output ONLY the XML document. No prose, no markdown, no headings, no
  code fences, no commentary before or after the XML.
- Your response MUST begin with the literal characters `<tasks>` and end
  with `</tasks>`.
- Do NOT ask clarifying questions. If details are missing or ambiguous,
  make reasonable assumptions and proceed.

Use exactly this XML format:

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
        """Initialize the task decomposer.

        Args:
            workflow: Workflow instance providing LLM access.
        """
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

        # The schema and the problem go together in the user message: the
        # EmpathyLLM interaction layer builds its own level-based system
        # prompt and ignores the ``system`` argument, so the decomposition
        # schema must travel in the user turn to actually reach the model.
        user_parts = [DECOMPOSITION_SYSTEM_PROMPT, "", f"Problem: {problem_description}", ""]

        if codebase_context:
            user_parts.append(f"Codebase context:\n{codebase_context}")
            user_parts.append("")

        if constraints:
            user_parts.append("Constraints:")
            for c in constraints:
                user_parts.append(f"- {c}")

        user_message = "\n".join(user_parts)

        # _call_llm(tier, system, user_message, ...) -> (text, in_tokens, out_tokens).
        try:
            response_text, _in_tokens, _out_tokens = await self._workflow._call_llm(
                tier=ModelTier.CAPABLE,
                system="",
                user_message=user_message,
                stage_name="decompose",
            )
        except Exception as e:  # noqa: BLE001
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

            self._warn_on_dropped_fields(
                task_id,
                body,
                len(files_to_create) + len(files_to_modify),
                len(validation_checks),
                len(risks),
                len(dependencies),
            )

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
        # Runs even when nothing parsed: a response whose only task carries a
        # single-quoted attribute is exactly the case this warning exists for.
        self._warn_on_dropped_task_content(xml_content, task_pattern)

        return tasks

    #: Opening tags that only appear inside a <task> body. Finding one in the
    #: text between task blocks means a task lost its wrapper and was dropped.
    #: ``[\s>]`` after the name admits attributes and stray whitespace
    #: (``<file path=``, ``<objective >``) without matching ``<files-to-…>``.
    _ORPHAN_TAG = re.compile(r"<(objective|file|check|risk|dep)[\s>]")

    def _warn_on_dropped_task_content(self, xml_content: str, task_pattern: re.Pattern) -> None:
        """Warn when task-shaped content sits outside every ``<task>`` block.

        The parser is regex-based, so anything it does not match is discarded
        in silence. A single-quoted attribute, a missing ``path=``, or a
        mistyped closing tag drops a whole task and still returns a plausible
        list. The caller has no way to tell a two-task plan from a three-task
        plan whose third task was malformed.
        """
        leftovers: list[str] = []
        cursor = 0
        for match in task_pattern.finditer(xml_content):
            leftovers.append(xml_content[cursor : match.start()])
            cursor = match.end()
        leftovers.append(xml_content[cursor:])

        orphaned = sorted(
            {f"<{m.group(1)}>" for chunk in leftovers for m in self._ORPHAN_TAG.finditer(chunk)}
        )
        if orphaned:
            logger.warning(
                "Found task content outside any <task> block (%s) - "
                "%d task(s) parsed; check for a malformed or unclosed <task> tag",
                ", ".join(orphaned),
                len(task_pattern.findall(xml_content)),
            )

    def _warn_on_dropped_fields(
        self,
        task_id: str,
        body: str,
        files: int,
        checks: int,
        risks: int,
        deps: int,
    ) -> None:
        """Warn when a tag appears in a task body but no value came out of it.

        The sub-extractors are regexes too. ``<file>`` without ``path=`` and
        ``<risk>`` without ``severity=`` match nothing and are dropped without
        a word, so a task can parse "successfully" while losing every file it
        named. Counting raw opening tags against extracted values catches that
        without re-parsing.
        """
        for tag, extracted in (
            ("<file", files),
            ("<check", checks),
            ("<risk", risks),
            ("<dep", deps),
        ):
            # Require a space or '>' after the tag name, so the section
            # wrappers are not miscounted as their own children:
            # '<files-to-modify>' is not a '<file>', '<risks>' is not a
            # '<risk>', '<dependencies>' is not a '<dep>'.
            seen = len(re.findall(re.escape(tag) + r"[\s>]", body))
            if seen > extracted:
                logger.warning(
                    "Task %s: %d %s tag(s) present but %d parsed - "
                    "check for a missing or single-quoted attribute",
                    task_id,
                    seen,
                    tag,
                    extracted,
                )

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
