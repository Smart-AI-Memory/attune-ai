"""Execution mixin for ManageDocumentationCrew.

Encapsulates the context-building and agent task execution
logic so that manage_documentation.py stays under 500 lines.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .doc_crew_models import (
    ManageDocumentationCrewResult,
    Task,
    parse_xml_response,
)
from .doc_crew_report import format_manage_docs_report


class DocCrewExecutionMixin:
    """Mixin that implements the execute() method for the crew.

    Expects the host class to provide:
    - self.manager: Agent
    - self.define_tasks() -> list[Task]
    - self._call_llm(agent, task, context, task_type)
    - self._scan_directory(path) -> dict
    - self._get_index_context() -> dict
    - self._executor: executor or None
    - self._total_cost: float
    - self._total_input_tokens: int
    - self._total_output_tokens: int
    """

    async def execute(
        self,
        path: str = ".",
        context: dict | None = None,
        **kwargs: Any,
    ) -> ManageDocumentationCrewResult:
        """Execute the documentation management crew.

        Args:
            path: Path to analyze for documentation gaps
            context: Additional context for agents
            **kwargs: Additional arguments

        Returns:
            ManageDocumentationCrewResult with findings and
            recommendations

        """
        started_at = datetime.now()
        context = context or {}

        scan_results, agent_context = self._build_context(path, context)

        if "error" in scan_results:
            return ManageDocumentationCrewResult(
                success=False,
                findings=[{"error": scan_results["error"]}],
                recommendations=["Fix the path and try again"],
            )

        all_findings, all_responses = await self._run_agent_tasks(agent_context)

        await self._run_manager_synthesis(path, all_responses)

        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)

        result = self._build_result(
            path,
            scan_results,
            all_findings,
            all_responses,
            duration_ms,
        )

        result.formatted_report = format_manage_docs_report(result, path)
        return result

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_context(self, path: str, context: dict) -> tuple[dict, dict]:
        """Build scan_results and agent_context dicts.

        Args:
            path: Path to analyze.
            context: User-supplied context.

        Returns:
            Tuple of (scan_results, agent_context).

        """
        index_context = self._get_index_context()

        if index_context:
            return self._context_from_index(path, context, index_context)

        print("  [Fallback] Scanning directory manually")
        scan_results = self._scan_directory(path)
        if "error" in scan_results:
            return scan_results, {}

        agent_context = {
            "path": path,
            "python_files": (f"{scan_results['python_file_count']} files found"),
            "sample_files": ", ".join(scan_results["python_files"][:10]),
            "doc_files": (f"{scan_results['doc_file_count']} doc files found"),
            **context,
        }
        return scan_results, agent_context

    def _context_from_index(
        self,
        path: str,
        context: dict,
        index_context: dict,
    ) -> tuple[dict, dict]:
        """Build context from ProjectIndex data.

        Args:
            path: Path being analyzed.
            context: User-supplied context.
            index_context: Data from ProjectIndex.

        Returns:
            Tuple of (scan_results, agent_context).

        """
        print("  [ProjectIndex] Using indexed file data")
        doc_stats = index_context.get("documentation_stats", {})

        agent_context: dict[str, Any] = {
            "path": path,
            "python_files": (f"{doc_stats.get('total_python_files', 0)} " "Python files indexed"),
            "files_with_docstrings": (
                f"{doc_stats.get('files_with_docstrings', 0)} files "
                f"({doc_stats.get('docstring_coverage_pct', 0):.1f}"
                "% coverage)"
            ),
            "files_without_docstrings": (
                f"{doc_stats.get('files_without_docstrings', 0)} " "files need docstrings"
            ),
            "type_hint_coverage": (f"{doc_stats.get('type_hint_coverage_pct', 0):.1f}%"),
            "high_impact_undocumented": doc_stats.get("priority_files", []),
            "doc_files": (f"{doc_stats.get('doc_file_count', 0)} " "documentation files"),
            "total_loc_undocumented": doc_stats.get("loc_undocumented", 0),
            "recently_modified_source_count": doc_stats.get("recently_modified_source_count", 0),
            "stale_docs_count": doc_stats.get("stale_docs_count", 0),
            **context,
        }

        files_without_docs = index_context.get("files_without_docstrings", [])
        if files_without_docs:
            agent_context["sample_undocumented"] = [f["path"] for f in files_without_docs[:10]]

        recent_source = index_context.get("recently_modified_source", [])
        if recent_source:
            agent_context["recently_modified_source_files"] = [
                {
                    "path": f["path"],
                    "modified": f.get("last_modified"),
                }
                for f in recent_source[:10]
            ]

        docs_needing_review = index_context.get("docs_needing_review", [])
        if docs_needing_review:
            stale_docs = [d for d in docs_needing_review if d.get("source_modified_after_doc")]
            agent_context["stale_docs"] = [
                {
                    "doc": d["doc_file"],
                    "related_source": (d["related_source_files"][:3]),
                    "days_since_update": d["days_since_doc_update"],
                }
                for d in stale_docs[:5]
            ]

        scan_results = {
            "python_file_count": doc_stats.get("total_python_files", 0),
            "doc_file_count": doc_stats.get("doc_file_count", 0),
            "python_files": [f["path"] for f in files_without_docs[:50]],
            "doc_files": [f["path"] for f in index_context.get("doc_files", [])[:20]],
            "recently_modified_count": doc_stats.get("recently_modified_source_count", 0),
            "stale_docs_count": doc_stats.get("stale_docs_count", 0),
        }

        return scan_results, agent_context

    # ------------------------------------------------------------------
    # Agent task runners
    # ------------------------------------------------------------------

    async def _run_agent_tasks(self, agent_context: dict) -> tuple[list[dict], list[str]]:
        """Execute the three agent tasks sequentially.

        Args:
            agent_context: Context dict to pass to each agent.

        Returns:
            Tuple of (all_findings, all_responses).

        """
        tasks = self.define_tasks()
        all_findings: list[dict] = []
        all_responses: list[str] = []

        for i, task in enumerate(tasks):
            print(f"  [{i + 1}/{len(tasks)}] {task.agent.role}: {task.description[:50]}...")

            if all_responses:
                agent_context["previous_analysis"] = all_responses[-1][:2000]

            task_type = "code_analysis"
            if "review" in task.agent.role.lower():
                task_type = "code_analysis"
            elif "synth" in task.agent.role.lower():
                task_type = "summarize"

            response, in_tokens, out_tokens, cost = await self._call_llm(
                agent=task.agent,
                task=task,
                context=agent_context,
                task_type=task_type,
            )

            self._total_input_tokens += in_tokens
            self._total_output_tokens += out_tokens
            self._total_cost += cost

            parsed = parse_xml_response(response)
            all_responses.append(response)

            all_findings.append(
                {
                    "agent": task.agent.role,
                    "task": task.description[:100],
                    "response": response[:1000],
                    "thinking": (parsed["thinking"][:500] if parsed["thinking"] else ""),
                    "answer": (parsed["answer"][:500] if parsed["answer"] else response[:500]),
                    "has_xml_structure": parsed["has_structure"],
                    "tokens": {
                        "input": in_tokens,
                        "output": out_tokens,
                    },
                    "cost": cost,
                },
            )

        return all_findings, all_responses

    async def _run_manager_synthesis(self, path: str, all_responses: list[str]) -> None:
        """Run the manager agent for final synthesis.

        Args:
            path: Path that was analyzed.
            all_responses: Responses from the previous agents.

        """
        manager_context = {
            "path": path,
            "analyst_findings": (all_responses[0][:1500] if len(all_responses) > 0 else ""),
            "reviewer_validation": (all_responses[1][:1500] if len(all_responses) > 1 else ""),
            "synthesizer_plan": (all_responses[2][:1500] if len(all_responses) > 2 else ""),
        }

        print(f"  [Final] {self.manager.role}: " "Coordinating final output...")

        manager_task = Task(
            description=(
                "Review all agent outputs and create a final "
                "executive summary with the top 3-5 prioritized "
                "actions for improving documentation."
            ),
            expected_output=(
                "Executive summary with: "
                "1) Overall documentation health score (0-100), "
                "2) Top priorities, 3) Quick wins, "
                "4) Estimated total effort"
            ),
            agent=self.manager,
        )

        _, in_tokens, out_tokens, cost = await self._call_llm(
            agent=self.manager,
            task=manager_task,
            context=manager_context,
            task_type="summarize",
        )

        self._total_input_tokens += in_tokens
        self._total_output_tokens += out_tokens
        self._total_cost += cost

    # ------------------------------------------------------------------
    # Result building
    # ------------------------------------------------------------------

    def _build_result(
        self,
        path: str,
        scan_results: dict,
        all_findings: list[dict],
        all_responses: list[str],
        duration_ms: int,
    ) -> ManageDocumentationCrewResult:
        """Build the final ManageDocumentationCrewResult.

        Args:
            path: Path that was analyzed.
            scan_results: Scan results dict.
            all_findings: Findings from agent tasks.
            all_responses: Raw responses from agents.
            duration_ms: Total execution time in milliseconds.

        Returns:
            ManageDocumentationCrewResult.

        """
        recommendations = [
            f"Documentation analysis complete for {path}",
            (f"Analyzed {scan_results['python_file_count']} " "Python files"),
            (f"Found {scan_results['doc_file_count']} " "documentation files"),
        ]

        if len(all_responses) > 2:
            recommendations.append("See synthesizer output for prioritized action plan")

        return ManageDocumentationCrewResult(
            success=True,
            findings=all_findings,
            recommendations=recommendations,
            files_analyzed=scan_results["python_file_count"],
            docs_needing_update=0,
            new_docs_needed=0,
            confidence=0.75 if self._executor else 0.3,
            cost=self._total_cost,
            duration_ms=duration_ms,
        )
