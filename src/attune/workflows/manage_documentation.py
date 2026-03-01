"""Manage_Documentation - Multi-Agent Workflow (Facade)

.. deprecated:: 4.3.0
    Use ``empathy meta-workflow run manage-docs`` instead.

Facade re-exporting public names from doc_crew_models,
doc_crew_report, and doc_crew_execution.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import os
import warnings
from pathlib import Path
from typing import Any

from .doc_crew_execution import DocCrewExecutionMixin

# Re-export public data models so every existing import path works.
from .doc_crew_models import (  # noqa: F401
    Agent,
    ManageDocumentationCrewResult,
    Task,
    parse_xml_response,
)
from .doc_crew_report import format_manage_docs_report  # noqa: F401

# ------------------------------------------------------------------
# Optional dependency imports (fail-open)
# ------------------------------------------------------------------

EmpathyLLMExecutor = None
ExecutionContext = None
HAS_EXECUTOR = False

try:
    from attune.models import ExecutionContext as _ExecutionContext
    from attune.models.empathy_executor import (
        EmpathyLLMExecutor as _EmpathyLLMExecutor,
    )

    EmpathyLLMExecutor = _EmpathyLLMExecutor
    ExecutionContext = _ExecutionContext
    HAS_EXECUTOR = True
except ImportError:
    pass

ProjectIndex = None
HAS_PROJECT_INDEX = False

try:
    from attune.project_index import ProjectIndex as _ProjectIndex

    ProjectIndex = _ProjectIndex
    HAS_PROJECT_INDEX = True
except ImportError:
    pass


# ------------------------------------------------------------------
# Main crew class
# ------------------------------------------------------------------


class ManageDocumentationCrew(DocCrewExecutionMixin):
    """Manage_Documentation - Documentation management crew.

    Makes sure that new program files are fully documented and
    existing documents are updated when associated program files
    are changed.

    Process Type: sequential

    Agents:
    - Analyst: Scans codebase to identify documentation gaps
    - Reviewer: Cross-checks findings and validates accuracy
    - Synthesizer: Combines findings into actionable recs
    - Manager: Coordinates actions and prioritizes work

    Usage:
        crew = ManageDocumentationCrew()
        result = await crew.execute(path="./src", context={})
    """

    name = "Manage_Documentation"
    description = (
        "Makes sure that new program files are fully documented "
        "and existing documents are updated when associated "
        "program files are changed."
    )
    process_type = "sequential"

    def __init__(self, project_root: str = ".", **kwargs: Any):
        """Initialize the crew with configured agents.

        Args:
            project_root: Root directory of the project.
            **kwargs: Additional configuration options.

        .. deprecated:: 4.3.0
            Use meta-workflow system instead.

        """
        warnings.warn(
            "ManageDocumentationCrew is deprecated since v4.3.0. "
            "Use meta-workflow system instead: "
            "empathy meta-workflow run manage-docs. "
            "See docs/CREWAI_MIGRATION.md for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = kwargs
        self.project_root = project_root
        self._executor = None
        self._project_index = None
        self._total_cost = 0.0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        self._init_executor()
        self._init_project_index(project_root)
        self._init_agents()

    # ----------------------------------------------------------
    # Initialization helpers
    # ----------------------------------------------------------

    def _init_executor(self) -> None:
        """Initialize the LLM executor if available."""
        if HAS_EXECUTOR and EmpathyLLMExecutor is not None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self._executor = EmpathyLLMExecutor(
                        provider="anthropic",
                        api_key=api_key,
                    )
                except Exception:
                    # INTENTIONAL: executor init is best-effort
                    pass

    def _init_project_index(self, project_root: str) -> None:
        """Initialize the ProjectIndex if available."""
        if HAS_PROJECT_INDEX and ProjectIndex is not None:
            try:
                self._project_index = ProjectIndex(project_root)
                if not self._project_index.load():
                    print("  [ProjectIndex] Building index (first run)...")
                    self._project_index.refresh()
            except Exception as e:
                # INTENTIONAL: index init is best-effort
                print(f"  [ProjectIndex] Warning: Could not load index: {e}")

    def _init_agents(self) -> None:
        """Define the four crew agents."""
        self.analyst = Agent(
            role="Documentation Analyst",
            goal=("Scan the codebase to identify files lacking documentation and find stale docs"),
            backstory=(
                "Expert analyst who understands code structure, "
                "docstrings, and documentation best practices. "
                "Skilled at identifying gaps between code and "
                "documentation."
            ),
            expertise_level="expert",
        )
        self.reviewer = Agent(
            role="Documentation Reviewer",
            goal=("Cross-check findings and validate accuracy of the analysis"),
            backstory=(
                "Experienced technical writer and reviewer "
                "focused on quality, correctness, and ensuring "
                "documentation matches actual code behavior."
            ),
            expertise_level="expert",
        )
        self.synthesizer = Agent(
            role="Documentation Synthesizer",
            goal=("Combine findings into actionable, prioritized recommendations"),
            backstory=(
                "Strategic thinker who excels at synthesis and "
                "prioritization. Creates clear action plans that "
                "developers can follow."
            ),
            expertise_level="expert",
        )
        self.manager = Agent(
            role="Documentation Manager",
            goal=("Coordinate actions of other agents and prioritize documentation work"),
            backstory=(
                "Understands the documentation needs of the "
                "project and the capability of other agents. "
                "Makes decisions about what to document first "
                "based on impact and effort."
            ),
            expertise_level="world-class",
        )
        self.agents = [
            self.analyst,
            self.reviewer,
            self.synthesizer,
            self.manager,
        ]

    # ----------------------------------------------------------
    # Task definitions
    # ----------------------------------------------------------

    def define_tasks(self) -> list[Task]:
        """Define the tasks for this crew.

        Returns:
            List of Task objects for analyst, reviewer,
            and synthesizer.

        """
        return [
            Task(
                description=(
                    "Analyze the codebase to identify: "
                    "1) Python files without docstrings, "
                    "2) Functions/classes missing documentation, "
                    "3) README files that may be outdated, "
                    "4) Missing API documentation"
                ),
                expected_output=(
                    "JSON list of findings with: file_path, "
                    "issue_type (missing_docstring|stale_doc|"
                    "no_readme), severity (high|medium|low), "
                    "details"
                ),
                agent=self.analyst,
            ),
            Task(
                description=(
                    "Review and validate the analysis findings. "
                    "Check if flagged files truly need "
                    "documentation updates. Identify any "
                    "false positives."
                ),
                expected_output=(
                    "Validated findings with confidence scores "
                    "(0-1) and notes on any false positives "
                    "removed"
                ),
                agent=self.reviewer,
            ),
            Task(
                description=(
                    "Synthesize validated findings into a "
                    "prioritized action plan. Group by "
                    "module/area, estimate effort, and create "
                    "clear next steps."
                ),
                expected_output=(
                    "Prioritized list of documentation tasks "
                    "with: priority (1-5), task description, "
                    "estimated effort (small|medium|large), "
                    "files involved"
                ),
                agent=self.synthesizer,
            ),
        ]

    # ----------------------------------------------------------
    # LLM interaction
    # ----------------------------------------------------------

    async def _call_llm(
        self,
        agent: Agent,
        task: Task,
        context: dict,
        task_type: str = "code_analysis",
    ) -> tuple[str, int, int, float]:
        """Call the LLM with agent/task configuration.

        Args:
            agent: The Agent whose system prompt to use.
            task: The Task whose user prompt to use.
            context: Context dict passed to the user prompt.
            task_type: LLM task type for routing.

        Returns:
            Tuple of (response_text, input_tokens,
            output_tokens, cost).

        """
        system_prompt = agent.get_system_prompt()
        user_prompt = task.get_user_prompt(context)

        if self._executor is not None and ExecutionContext is not None:
            try:
                exec_context = ExecutionContext(
                    workflow_name=self.name,
                    step_name=agent.role.lower().replace(" ", "_"),
                    task_type=task_type,
                )
                response = await self._executor.run(
                    task_type=task_type,
                    prompt=user_prompt,
                    system=system_prompt,
                    context=exec_context,
                )
                return (
                    response.content,
                    response.tokens_input,
                    response.tokens_output,
                    response.cost_estimate or 0.0,
                )
            except Exception as e:
                # INTENTIONAL: fallback to mock on LLM error
                return self._mock_response(agent, task, context, str(e))
        else:
            return self._mock_response(
                agent,
                task,
                context,
                "No LLM executor configured",
            )

    def _mock_response(
        self,
        agent: Agent,
        task: Task,
        context: dict,
        reason: str,
    ) -> tuple[str, int, int, float]:
        """Generate a mock response when LLM is unavailable.

        Args:
            agent: The Agent to mock for.
            task: The current Task.
            context: Context dict.
            reason: Why the mock is being used.

        Returns:
            Tuple of (response, in_tokens, out_tokens, cost).

        """
        mock_findings = {
            "Documentation Analyst": (
                f"[Mock Analysis - {reason}]\n\n"
                f"Based on scanning the path: "
                f"{context.get('path', '.')}\n\n"
                "Findings:\n"
                '1. {{\n   "file_path": "src/example.py",\n'
                '   "issue_type": "missing_docstring",\n'
                '   "severity": "medium",\n'
                '   "details": "Module lacks module-level '
                'docstring"\n}}\n'
                '2. {{\n   "file_path": "README.md",\n'
                '   "issue_type": "stale_doc",\n'
                '   "severity": "low",\n'
                '   "details": "README may not reflect recent '
                'changes"\n}}\n\n'
                "Note: This is a mock response. Configure "
                "ANTHROPIC_API_KEY for real analysis."
            ),
            "Documentation Reviewer": (
                f"[Mock Review - {reason}]\n\n"
                "Validated Findings:\n"
                "- Finding 1: VALID (confidence: 0.8) - "
                "Missing docstrings are a real issue\n"
                "- Finding 2: NEEDS_VERIFICATION "
                "(confidence: 0.5) - "
                "Stale docs need manual check\n\n"
                "False Positives Removed: 0\n\n"
                "Note: This is a mock response. Configure "
                "ANTHROPIC_API_KEY for real analysis."
            ),
            "Documentation Synthesizer": (
                f"[Mock Synthesis - {reason}]\n\n"
                "Prioritized Action Plan:\n\n"
                "1. Priority 1 (High) - Add module docstrings\n"
                "   - Effort: small\n"
                "   - Files: src/example.py\n\n"
                "2. Priority 3 (Medium) - Review README "
                "accuracy\n"
                "   - Effort: medium\n"
                "   - Files: README.md\n\n"
                "Note: This is a mock response. Configure "
                "ANTHROPIC_API_KEY for real analysis."
            ),
        }
        response = mock_findings.get(agent.role, f"Mock response for {agent.role}")
        return (response, 0, 0, 0.0)

    # ----------------------------------------------------------
    # Directory scanning
    # ----------------------------------------------------------

    def _scan_directory(self, path: str) -> dict:
        """Scan directory for Python files and documentation.

        Args:
            path: Directory path to scan.

        Returns:
            Dict with file counts/lists, or an error key.

        """
        path_obj = Path(path)
        if not path_obj.exists():
            return {"error": f"Path does not exist: {path}"}

        python_files: list[str] = []
        doc_files: list[str] = []

        for py_file in path_obj.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                python_files.append(str(py_file))

        for pattern in ["*.md", "*.rst", "*.txt"]:
            for doc_file in path_obj.rglob(pattern):
                doc_files.append(str(doc_file))

        return {
            "python_files": python_files[:50],
            "python_file_count": len(python_files),
            "doc_files": doc_files[:20],
            "doc_file_count": len(doc_files),
        }

    def _get_index_context(self) -> dict[str, Any]:
        """Get documentation context from ProjectIndex.

        Returns:
            Context dict, or empty dict if unavailable.

        """
        if self._project_index is None:
            return {}
        try:
            return self._project_index.get_context_for_workflow("documentation")
        except Exception as e:
            # INTENTIONAL: index query is best-effort
            print(f"  [ProjectIndex] Warning: Could not get context: {e}")
            return {}


# ------------------------------------------------------------------
# CLI entry point for testing
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def main() -> None:
        """Run the crew from the command line."""
        path = sys.argv[1] if len(sys.argv) > 1 else "."
        print(f"ManageDocumentationCrew - Analyzing: {path}\n")

        crew = ManageDocumentationCrew()
        print(f"Crew: {crew.name}")
        print(f"Agents: {len(crew.agents)}")
        executor_status = "Available" if crew._executor else "Not configured (using mocks)"
        print(f"LLM Executor: {executor_status}")
        print()

        result = await crew.execute(path=path)
        print("\n" + result.formatted_report)

    asyncio.run(main())
