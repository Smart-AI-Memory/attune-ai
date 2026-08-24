"""Documentation Orchestrator Scout Phase.

Scout phase execution, ProjectIndex item extraction, findings parsing,
and prioritization. Extracted from documentation_orchestrator.py for
maintainability.

Contains:
- DocOrchScoutMixin: Scout phase, index querying, findings parsing,
  item prioritization

Expected attributes on the host class:
    _scout: Any (ManageDocumentationCrew instance or None)
    _project_index: Any (ProjectIndex instance or None)
    include_stale: bool
    include_missing: bool
    min_severity: str
    max_items: int
    project_root: Path
    _should_exclude: method (from DocOrchFilterMixin)
    _should_include_severity: method (from DocOrchFilterMixin)
    _severity_to_priority: method (from DocOrchFilterMixin)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DocOrchScoutMixin:
    """Mixin providing scout phase for documentation orchestrator."""

    # Class-level defaults for expected attributes
    include_stale: bool = True
    include_missing: bool = True
    max_items: int = 5
    project_root: Path = Path()
    # True only after a scan (scout or ProjectIndex fallback) actually
    # ran — zero items with no scan is "not assessed", never "no gaps".
    _scan_performed: bool = False

    async def _run_scout_phase(self) -> tuple[list, float]:
        """Run the scout phase to identify documentation gaps.

        Sets ``self._scan_performed`` so the caller can distinguish an
        empty result from a scan that never happened.

        Returns:
            Tuple of (items found, cost)

        """
        from .documentation_orchestrator import DocumentationItem

        items: list[DocumentationItem] = []
        cost = 0.0
        self._scan_performed = False

        if self._scout is None:
            logger.warning("Scout (ManageDocumentationCrew) not available")
            # Fall back to ProjectIndex if available. The index read
            # counts as a performed scan ONLY when it actually carried
            # doc-coverage data (#2220) — an empty/errored/capability-
            # less read is "not assessed", never "no gaps found".
            if self._project_index is not None:
                items, assessed = self._items_from_index()
                self._scan_performed = assessed
            return items, cost

        logger.info("Starting scout phase...")
        print("\n[SCOUT PHASE] Analyzing codebase for documentation gaps...")

        result = await self._scout.execute(path=str(self.project_root))
        cost = result.cost

        if not result.success:
            logger.error("Scout phase failed")
            return items, cost
        self._scan_performed = True

        # Parse scout findings into DocumentationItems
        items = self._parse_scout_findings(result)

        # Supplement with ProjectIndex data if available
        if self._project_index is not None:
            index_items, _ = self._items_from_index()
            # Merge, preferring scout items but adding unique index items
            existing_paths = {item.file_path for item in items}
            for idx_item in index_items:
                if idx_item.file_path not in existing_paths:
                    items.append(idx_item)

        logger.info("Scout phase found %s items (cost: $%.4f)", len(items), cost)
        return items, cost

    def _items_from_index(self) -> tuple[list, bool]:
        """Extract documentation items from ProjectIndex.

        Returns:
            Tuple of (items, assessed). ``assessed`` is True only when
            the index context actually carried doc-coverage data
            (``files_without_docstrings``) — for years no index branch
            produced that key, every read defaulted empty, and zero
            items rendered as "no documentation gaps found" (#2220).
            A capability-less or errored read is NOT an assessment.
        """
        from .documentation_orchestrator import DocumentationItem

        items: list[DocumentationItem] = []

        if self._project_index is None:
            return items, False

        try:
            context = self._project_index.get_context_for_workflow("documentation")
            if "files_without_docstrings" not in context:
                return items, False

            # Get files without docstrings
            if self.include_missing:
                files_without_docs = context.get("files_without_docstrings", [])
                for f in files_without_docs[:20]:  # Limit
                    file_path = f.get("path", "")
                    if self._should_exclude(file_path, track=True):
                        continue
                    items.append(
                        DocumentationItem(
                            file_path=file_path,
                            issue_type="missing_docstring",
                            severity="medium",
                            priority=2,
                            details=f"Missing docstring - {f.get('loc', 0)} LOC",
                            loc=f.get("loc", 0),
                        ),
                    )

            # Get stale docs
            if self.include_stale:
                docs_needing_review = context.get("docs_needing_review", [])
                for d in docs_needing_review[:10]:
                    if d.get("source_modified_after_doc"):
                        file_path = d.get("doc_file", "")
                        if self._should_exclude(file_path, track=True):
                            continue
                        items.append(
                            DocumentationItem(
                                file_path=file_path,
                                issue_type="stale_doc",
                                severity="high",
                                priority=1,
                                details="Source modified after doc update",
                                related_source=d.get("related_source_files", [])[:3],
                                days_stale=d.get("days_since_doc_update", 0),
                            ),
                        )
        except Exception as e:  # noqa: BLE001
            logger.warning("Error extracting items from index: %s", e)
            return items, False

        return items, True

    def _parse_scout_findings(self, result: Any) -> list:
        """Parse scout result into DocumentationItems."""
        from .documentation_orchestrator import DocumentationItem

        items: list[DocumentationItem] = []

        # Scout returns findings as list of dicts with agent responses
        for finding in result.findings:
            response = finding.get("response", "")
            agent = finding.get("agent", "")

            # Try to extract structured data from analyst response
            if "Analyst" in agent:
                # Find file paths mentioned
                file_pattern = r'"file_path":\s*"([^"]+)"'
                issue_pattern = r'"issue_type":\s*"([^"]+)"'
                severity_pattern = r'"severity":\s*"([^"]+)"'

                file_matches = re.findall(file_pattern, response)
                issue_matches = re.findall(issue_pattern, response)
                severity_matches = re.findall(severity_pattern, response)

                for i, file_path in enumerate(file_matches):
                    issue_type = issue_matches[i] if i < len(issue_matches) else "unknown"
                    severity = severity_matches[i] if i < len(severity_matches) else "medium"

                    # Filter by settings
                    if issue_type == "stale_doc" and not self.include_stale:
                        continue
                    if (
                        issue_type in ("missing_docstring", "no_documentation")
                        and not self.include_missing
                    ):
                        continue
                    if not self._should_include_severity(severity):
                        continue
                    # Skip excluded files (requirements.txt, package.json, etc.)
                    if self._should_exclude(file_path):
                        continue

                    items.append(
                        DocumentationItem(
                            file_path=file_path,
                            issue_type=issue_type,
                            severity=severity,
                            priority=self._severity_to_priority(severity),
                            details=f"Found by {agent}",
                        ),
                    )

        return items

    def _prioritize_items(self, items: list) -> list:
        """Prioritize items for generation.

        Priority order:
        1. Stale docs (source changed) - highest urgency
        2. High-severity missing docs
        3. Files with most LOC
        4. Medium/low severity
        """
        # Sort by: priority (asc), days_stale (desc), loc (desc)
        sorted_items = sorted(
            items,
            key=lambda x: (
                x.priority,
                -x.days_stale,
                -x.loc,
            ),
        )

        return sorted_items[: self.max_items]
