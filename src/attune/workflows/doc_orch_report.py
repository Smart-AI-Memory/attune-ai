"""Documentation Orchestrator Report & Generation Phase.

Generation phase execution, ProjectIndex updates, and summary report
generation. Extracted from documentation_orchestrator.py for
maintainability.

Contains:
- DocOrchReportMixin: Generation phase, index updates, summary reporting

Expected attributes on the host class:
    _writer: Any (DocumentGenerationWorkflow instance or None)
    _project_index: Any (ProjectIndex instance or None)
    _total_cost: float
    max_cost: float
    doc_type: str
    audience: str
    project_root: Path
    export_path: Path
    dry_run: bool

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .documentation_orchestrator import DocumentationItem, OrchestratorResult

logger = logging.getLogger(__name__)


class DocOrchReportMixin:
    """Mixin providing generation phase and reporting for documentation orchestrator."""

    # Class-level defaults for expected attributes
    _total_cost: float = 0.0
    max_cost: float = 5.0
    doc_type: str = "api_reference"
    audience: str = "developers"
    project_root: Path = Path()
    export_path: Path = Path("docs/generated")
    dry_run: bool = False

    async def _run_generate_phase(
        self,
        items: list[DocumentationItem],
    ) -> tuple[list[str], list[str], list[str], float]:
        """Run the generation phase for prioritized items.

        Returns:
            Tuple of (generated, updated, skipped, cost)

        """
        generated: list[str] = []
        updated: list[str] = []
        skipped: list[str] = []
        cost = 0.0

        if self._writer is None:
            logger.warning("Writer (DocumentGenerationWorkflow) not available")
            return generated, updated, [item.file_path for item in items], cost

        logger.info(f"Starting generation phase for {len(items)} items...")
        print(f"\n[GENERATE PHASE] Processing {len(items)} documentation items...")

        for i, item in enumerate(items):
            # Check cost limit
            if self._total_cost + cost >= self.max_cost:
                remaining = items[i:]
                skipped.extend([r.file_path for r in remaining])
                logger.warning(f"Cost limit reached. Skipping {len(remaining)} items.")
                print(f"  [!] Cost limit ${self.max_cost:.2f} reached. Skipping remaining items.")
                break

            print(f"  [{i + 1}/{len(items)}] {item.issue_type}: {item.file_path}")

            try:
                source_path = self.project_root / item.file_path
                file_path_arg = str(source_path) if source_path.exists() else item.file_path
                result = await self._writer.execute(path=file_path_arg)

                # Track cost from result (handles both WorkflowResult and dict)
                if isinstance(result, dict):
                    step_cost = result.get("accumulated_cost", 0.0)
                    result_ok = bool(result.get("document") or result.get("success"))
                else:
                    step_cost = getattr(getattr(result, "cost_report", None), "total_cost", 0.0)
                    result_ok = getattr(result, "success", False)
                cost += step_cost

                if result_ok:
                    # Categorize result
                    if item.issue_type == "stale_doc":
                        updated.append(item.file_path)
                    else:
                        generated.append(item.file_path)
                else:
                    skipped.append(item.file_path)

            except Exception as e:  # noqa: BLE001
                logger.error(f"Error generating docs for {item.file_path}: {e}")
                skipped.append(item.file_path)

        logger.info(
            f"Generation phase: {len(generated)} generated, "
            f"{len(updated)} updated, {len(skipped)} skipped",
        )
        return generated, updated, skipped, cost

    def _update_project_index(self, generated: list[str], updated: list[str]) -> None:
        """Update ProjectIndex with newly documented files."""
        if self._project_index is None:
            return

        try:
            # Mark files as documented
            for file_path in generated + updated:
                # Update record if it exists
                record = self._project_index.get_record(file_path)
                if record:
                    record.has_docstring = True
                    record.last_modified = datetime.now()

            # Save index
            self._project_index.save()
            logger.info(
                f"ProjectIndex updated with {len(generated) + len(updated)} documented files",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not update ProjectIndex: {e}")

    def _generate_summary(
        self,
        result: OrchestratorResult,
        items: list[DocumentationItem],
    ) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            "DOCUMENTATION ORCHESTRATOR REPORT",
            "=" * 60,
            "",
            f"Project: {self.project_root}",
            "Status: "
            + (
                "DEGRADED (scan did not run — gaps not assessed)"
                if result.degraded
                else ("SUCCESS" if result.success else "PARTIAL")
            ),
            "",
            "-" * 60,
            "SCOUT PHASE",
            "-" * 60,
            f"  Items found: {result.items_found}",
            f"  Stale docs: {result.stale_docs}",
            f"  Missing docs: {result.missing_docs}",
            f"  Cost: ${result.scout_cost:.4f}",
            "",
        ]

        if items:
            lines.extend(
                [
                    "Priority Items:",
                ],
            )
            for i, item in enumerate(items[:10]):
                lines.append(f"  {i + 1}. [{item.severity.upper()}] {item.file_path}")
                lines.append(f"     Type: {item.issue_type}")
                if item.days_stale:
                    lines.append(f"     Days stale: {item.days_stale}")
            lines.append("")

        if not self.dry_run:
            lines.extend(
                [
                    "-" * 60,
                    "GENERATION PHASE",
                    "-" * 60,
                    f"  Items processed: {result.items_processed}",
                    f"  Docs generated: {len(result.docs_generated)}",
                    f"  Docs updated: {len(result.docs_updated)}",
                    f"  Skipped: {len(result.docs_skipped)}",
                    f"  Cost: ${result.generation_cost:.4f}",
                    "",
                ],
            )

            if result.docs_generated:
                lines.append("Generated:")
                for doc in result.docs_generated[:5]:
                    lines.append(f"  + {doc}")
                if len(result.docs_generated) > 5:
                    lines.append(f"  ... and {len(result.docs_generated) - 5} more")
                lines.append("")

            if result.docs_updated:
                lines.append("Updated:")
                for doc in result.docs_updated[:5]:
                    lines.append(f"  ~ {doc}")
                lines.append("")

        if result.errors:
            lines.extend(
                [
                    "-" * 60,
                    "ERRORS",
                    "-" * 60,
                ],
            )
            for error in result.errors:
                lines.append(f"  ! {error}")
            lines.append("")

        if result.warnings:
            lines.extend(
                [
                    "-" * 60,
                    "WARNINGS",
                    "-" * 60,
                ],
            )
            for warning in result.warnings:
                lines.append(f"  * {warning}")
            lines.append("")

        lines.extend(
            [
                "-" * 60,
                "TOTALS",
                "-" * 60,
                f"  Total cost: ${result.total_cost:.4f}",
                f"  Duration: {result.duration_ms}ms",
                f"  Export path: {self.export_path}",
                "",
                "=" * 60,
            ],
        )

        return "\n".join(lines)
