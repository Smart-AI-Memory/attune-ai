"""Documentation Orchestrator - Combined Scout + Writer Workflow

Combines ManageDocumentationCrew (scout/analyst) with DocumentGenerationWorkflow
(writer) to provide an end-to-end documentation management solution:

1. SCOUT Phase: ManageDocumentationCrew scans for stale docs and gaps
2. PRIORITIZE Phase: Filters and ranks items by severity and impact
3. GENERATE Phase: DocumentGenerationWorkflow creates/updates documentation
4. UPDATE Phase: ProjectIndex is updated with new documentation status

This orchestrator provides intelligent documentation maintenance:
- Detects when source code changes make docs stale
- Identifies undocumented files by priority (LOC, complexity)
- Generates documentation using cost-optimized 3-stage pipeline
- Tracks all costs and provides detailed reporting

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseWorkflow
from .compat import ModelTier
from .doc_orch_filters import DocOrchFilterMixin
from .doc_orch_report import DocOrchReportMixin
from .doc_orch_scout import DocOrchScoutMixin

logger = logging.getLogger(__name__)

# ManageDocumentationCrew was removed in v5.3.0 — scout
# phase now always uses ProjectIndex fallback.
HAS_SCOUT = False

# Import writer workflow
DocumentGenerationWorkflow = None
HAS_WRITER = False

try:
    from .document_gen import DocumentGenerationWorkflow as _DocumentGenerationWorkflow

    DocumentGenerationWorkflow = _DocumentGenerationWorkflow
    HAS_WRITER = True
except ImportError:
    pass

# Import ProjectIndex for tracking
ProjectIndex = None
HAS_PROJECT_INDEX = False

try:
    from attune.project_index import ProjectIndex as _ProjectIndex

    ProjectIndex = _ProjectIndex
    HAS_PROJECT_INDEX = True
except ImportError:
    pass


@dataclass
class DocumentationItem:
    """A single item that needs documentation work."""

    file_path: str
    issue_type: str  # "missing_docstring" | "stale_doc" | "no_documentation"
    severity: str  # "high" | "medium" | "low"
    priority: int  # 1-5, lower is higher priority
    details: str = ""
    related_source: list[str] = field(default_factory=list)
    days_stale: int = 0
    loc: int = 0


@dataclass
class OrchestratorResult:
    """Result from DocumentationOrchestrator execution."""

    success: bool
    phase: str  # "scout" | "prioritize" | "generate" | "complete"

    # Scout phase results
    items_found: int = 0
    stale_docs: int = 0
    missing_docs: int = 0

    # Generation phase results
    items_processed: int = 0
    docs_generated: list[str] = field(default_factory=list)
    docs_updated: list[str] = field(default_factory=list)
    docs_skipped: list[str] = field(default_factory=list)

    # Cost tracking
    scout_cost: float = 0.0
    generation_cost: float = 0.0
    total_cost: float = 0.0

    # Timing
    duration_ms: int = 0

    # Details
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "phase": self.phase,
            "items_found": self.items_found,
            "stale_docs": self.stale_docs,
            "missing_docs": self.missing_docs,
            "items_processed": self.items_processed,
            "docs_generated": self.docs_generated,
            "docs_updated": self.docs_updated,
            "docs_skipped": self.docs_skipped,
            "scout_cost": self.scout_cost,
            "generation_cost": self.generation_cost,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.summary,
        }


class DocumentationOrchestrator(
    DocOrchFilterMixin,
    DocOrchScoutMixin,
    DocOrchReportMixin,
    BaseWorkflow,
):
    """End-to-end documentation management orchestrator.

    Combines the ManageDocumentationCrew (scout) with DocumentGenerationWorkflow
    (writer) to provide intelligent, automated documentation maintenance.

    Phases:
    1. SCOUT: Analyze codebase for documentation gaps and staleness
    2. PRIORITIZE: Rank items by severity, LOC, and business impact
    3. GENERATE: Create/update documentation for priority items
    4. UPDATE: Update ProjectIndex with new documentation status

    Usage:
        orchestrator = DocumentationOrchestrator(
            project_root=".",
            max_items=5,           # Process top 5 priority items
            max_cost=2.0,          # Stop at $2 total cost
            auto_approve=False,    # Require approval before generation
        )
        result = await orchestrator.execute()
    """

    name = "documentation-orchestrator"
    description = "Coordinate doc-audit + doc-gen into end-to-end documentation maintenance"
    stages = ["scout", "prioritize", "generate", "update"]
    tier_map: dict[str, ModelTier] = {}

    # Patterns to exclude from SCANNING - things we don't want to analyze for documentation gaps
    # Note: The ALLOWED_OUTPUT_EXTENSIONS whitelist is the primary safety mechanism for writes
    DEFAULT_EXCLUDE_PATTERNS = [
        # Generated/build directories (would bloat results)
        "site/**",
        "dist/**",
        "build/**",
        "out/**",
        "node_modules/**",
        "__pycache__/**",
        ".git/**",
        "*.egg-info/**",
        # Framework internal/working directories
        ".attune/**",
        ".empathy_index/**",
        ".claude/**",
        # Book/large doc source folders
        "book/**",
        "docs/book/**",
        "docs/generated/**",
        "docs/word/**",
        "docs/pdf/**",
        # Dependency/config files (not source code - don't need documentation)
        "requirements*.txt",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "*.toml",
        "*.cfg",
        "*.ini",
        "*.env",
        ".env*",
        "Makefile",
        "Dockerfile",
        "docker-compose*.yml",
        "*.yaml",
        "*.yml",
        # Binary files (cannot be documented as code)
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.ico",
        "*.svg",
        "*.pdf",
        "*.woff",
        "*.woff2",
        "*.ttf",
        "*.eot",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dll",
        "*.exe",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.vsix",
        "*.docx",
        "*.doc",
    ]

    # ALLOWED file extensions for OUTPUT - documentation can ONLY create/modify these types
    # This is the PRIMARY safety mechanism - even if scanning includes wrong files,
    # only markdown documentation files can ever be written
    ALLOWED_OUTPUT_EXTENSIONS = [
        ".md",  # Markdown documentation
        ".mdx",  # MDX (Markdown with JSX)
        ".rst",  # reStructuredText
    ]

    def __init__(
        self,
        project_root: str = ".",
        max_items: int = 5,
        max_cost: float = 5.0,
        auto_approve: bool = False,
        export_path: str | Path | None = None,
        include_stale: bool = True,
        include_missing: bool = True,
        min_severity: str = "low",  # "high" | "medium" | "low"
        doc_type: str = "api_reference",
        audience: str = "developers",
        dry_run: bool = False,
        exclude_patterns: list[str] | None = None,
        **kwargs: Any,
    ):
        """Initialize the orchestrator.

        Args:
            project_root: Root directory of the project
            max_items: Maximum number of items to process (default 5)
            max_cost: Maximum total cost in USD (default $5)
            auto_approve: If True, generate docs without confirmation
            export_path: Directory to export generated docs
            include_stale: Include stale docs in processing
            include_missing: Include missing docs in processing
            min_severity: Minimum severity to include ("high", "medium", "low")
            doc_type: Type of documentation to generate
            audience: Target audience for documentation
            dry_run: If True, scout only without generating
            exclude_patterns: Additional patterns to exclude (merged with defaults)

        """
        super().__init__()
        self.project_root = Path(project_root)
        self.max_items = max_items
        self.max_cost = max_cost
        self.auto_approve = auto_approve

        # Merge default exclusions with any custom patterns
        self.exclude_patterns = list(self.DEFAULT_EXCLUDE_PATTERNS)
        if exclude_patterns:
            self.exclude_patterns.extend(exclude_patterns)
        self.export_path = (
            Path(export_path) if export_path else self.project_root / "docs" / "generated"
        )
        self._export_path_explicit = export_path is not None
        self.include_stale = include_stale
        self.include_missing = include_missing
        self.min_severity = min_severity
        self.doc_type = doc_type
        self.audience = audience
        self.dry_run = dry_run
        self.config = kwargs
        self._quiet = False  # Set to True for JSON output mode

        # Initialize components
        self._scout: Any = None
        self._writer: Any = None
        self._project_index: Any = None

        self._total_cost = 0.0
        self._items: list[DocumentationItem] = []
        self._excluded_files: list[dict] = []  # Track files excluded by patterns

        # Initialize writer if available
        if HAS_WRITER and DocumentGenerationWorkflow is not None:
            self._writer = DocumentGenerationWorkflow()

        # Initialize project index if available
        if HAS_PROJECT_INDEX and ProjectIndex is not None:
            try:
                self._project_index = ProjectIndex(str(self.project_root))
                if not self._project_index.load():
                    self._project_index.refresh()
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: ProjectIndex is optional enrichment
                logger.warning(f"Could not initialize ProjectIndex: {e}")

    def describe(self) -> str:
        """Get a human-readable description of the workflow."""
        lines = [
            f"Workflow: {self.name}",
            f"Description: {self.description}",
            "",
            "Phases:",
            "  1. SCOUT - Analyze codebase for documentation gaps and staleness",
            "  2. PRIORITIZE - Rank items by severity, LOC, and business impact",
            "  3. GENERATE - Create/update documentation for priority items",
            "  4. UPDATE - Update ProjectIndex with new documentation status",
            "",
            "Configuration:",
            f"  max_items: {self.max_items}",
            f"  max_cost: ${self.max_cost:.2f}",
            f"  auto_approve: {self.auto_approve}",
            f"  dry_run: {self.dry_run}",
            f"  include_stale: {self.include_stale}",
            f"  include_missing: {self.include_missing}",
            "",
            "Components:",
            f"  Scout (ManageDocumentationCrew): {'Available' if self._scout else 'Not available'}",
            f"  Writer (DocumentGenerationWorkflow): {'Available' if self._writer else 'Not available'}",
            f"  ProjectIndex: {'Available' if self._project_index else 'Not available'}",
        ]
        return "\n".join(lines)

    def _apply_scope_kwarg(self, kwargs: dict[str, Any]) -> None:
        """Resolve the `path=`/`project_root=` scope kwargs onto self.

        `path=` is the canonical kwarg (PATH_ARG_REGISTRY unification);
        `project_root=` is a deprecated alias, honored so the ops
        scope-picker can still re-scope a run.
        """
        scope = kwargs.get("path") or kwargs.get("project_root")
        if kwargs.get("project_root") and kwargs.get("path"):
            warnings.warn(
                "DocumentationOrchestrator.execute(): both `path=` and "
                "`project_root=` supplied; `path=` takes precedence and "
                "`project_root=` is deprecated.",
                DeprecationWarning,
                stacklevel=3,
            )
        elif kwargs.get("project_root"):
            warnings.warn(
                "DocumentationOrchestrator.execute(project_root=...) is "
                "deprecated; use execute(path=...) instead.",
                DeprecationWarning,
                stacklevel=3,
            )
        if scope:
            self.project_root = Path(scope).resolve()
            if not self._export_path_explicit:
                self.export_path = self.project_root / "docs" / "generated"

    def _check_dependencies(self, warning_msgs: list[str], errors: list[str]) -> bool:
        """Populate warning/error lists; return True if execution must abort."""
        if not HAS_SCOUT:
            warning_msgs.append(
                "ManageDocumentationCrew not available - using ProjectIndex fallback"
            )
        if not HAS_WRITER:
            errors.append("DocumentGenerationWorkflow not available - cannot generate docs")
            if not self.dry_run:
                return True
        if not HAS_PROJECT_INDEX:
            warning_msgs.append("ProjectIndex not available - limited file tracking")
        return False

    def _finalize_result(
        self,
        result: OrchestratorResult,
        started_at: datetime,
        phase: str,
        summary_items: list[DocumentationItem],
        docs_skipped: list[str] | None = None,
        warning_msgs: list[str] | None = None,
    ) -> OrchestratorResult:
        """Stamp the shared success/duration/cost/summary fields and return."""
        result.success = True
        result.phase = phase
        if docs_skipped is not None:
            result.docs_skipped = docs_skipped
        if warning_msgs is not None:
            result.warnings = warning_msgs
        result.duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        result.total_cost = self._total_cost
        result.summary = self._generate_summary(result, summary_items)
        return result

    async def execute(
        self,
        context: dict | None = None,
        **kwargs: Any,
    ) -> OrchestratorResult:
        """Execute the full documentation orchestration pipeline.

        Args:
            path: Project root to scope the run to. Canonical kwarg;
                replaces the deprecated `project_root=` alias.
            project_root: Deprecated alias for `path` (emits
                DeprecationWarning).
            context: Additional context for the workflows
            **kwargs: Additional arguments

        Returns:
            OrchestratorResult with full details

        """
        started_at = datetime.now()
        result = OrchestratorResult(success=False, phase="scout")
        errors: list[str] = []
        warning_msgs: list[str] = []

        self._apply_scope_kwarg(kwargs)

        if self._check_dependencies(warning_msgs, errors):
            result.errors = errors
            result.warnings = warning_msgs
            return result

        # Phase 1: Scout
        print("\n" + "=" * 60)
        print("DOCUMENTATION ORCHESTRATOR")
        print("=" * 60)

        items, scout_cost = await self._run_scout_phase()
        self._total_cost += scout_cost

        result.items_found = len(items)
        result.stale_docs = sum(1 for i in items if i.issue_type == "stale_doc")
        result.missing_docs = sum(1 for i in items if i.issue_type != "stale_doc")
        result.scout_cost = scout_cost
        result.phase = "prioritize"

        if not items:
            print("\n[✓] No documentation gaps found!")
            return self._finalize_result(result, started_at, "complete", items)

        # Phase 2: Prioritize
        print(f"\n[PRIORITIZE] Found {len(items)} items, selecting top {self.max_items}...")
        priority_items = self._prioritize_items(items)
        self._items = priority_items

        print("\nTop priority items:")
        for i, item in enumerate(priority_items):
            status = "STALE" if item.issue_type == "stale_doc" else "MISSING"
            print(f"  {i + 1}. [{status}] {item.file_path}")

        # Check for dry run
        if self.dry_run:
            print("\n[DRY RUN] Skipping generation phase")
            return self._finalize_result(
                result,
                started_at,
                "complete",
                priority_items,
                docs_skipped=[i.file_path for i in priority_items],
            )

        # Check for approval if not auto_approve
        if not self.auto_approve:
            print(f"\n[!] Ready to generate documentation for {len(priority_items)} items")
            print(f"    Estimated max cost: ${self.max_cost:.2f}")
            print("\n    Set auto_approve=True to proceed automatically")
            return self._finalize_result(
                result,
                started_at,
                "awaiting_approval",
                priority_items,
                docs_skipped=[i.file_path for i in priority_items],
                warning_msgs=warning_msgs,
            )

        # Phase 3: Generate
        result.phase = "generate"
        generated, updated, skipped, gen_cost = await self._run_generate_phase(priority_items)
        self._total_cost += gen_cost

        result.docs_generated = generated
        result.docs_updated = updated
        result.docs_skipped = skipped
        result.generation_cost = gen_cost
        result.items_processed = len(generated) + len(updated)

        # Phase 4: Update index
        result.phase = "update"
        self._update_project_index(generated, updated)

        # Finalize
        result.errors = errors
        self._finalize_result(
            result, started_at, "complete", priority_items, warning_msgs=warning_msgs
        )

        print(result.summary)

        return result

    async def scout_only(self) -> OrchestratorResult:
        """Run only the scout phase (equivalent to dry_run=True)."""
        self.dry_run = True
        return await self.execute()

    async def scout_as_json(self) -> dict:
        """Run scout phase and return JSON-serializable results.

        Used by VSCode extension to display results in Documentation Analysis panel.

        Returns:
            Dict with stats and items list ready for JSON serialization

        """
        import io
        import sys

        self.dry_run = True
        # Suppress console output during scout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = await self.execute()
        finally:
            sys.stdout = old_stdout

        return {
            "success": result.success,
            "stats": {
                "items_found": result.items_found,
                "stale_docs": result.stale_docs,
                "missing_docs": result.missing_docs,
                "scout_cost": result.scout_cost,
                "duration_ms": result.duration_ms,
                "excluded_count": len(self._excluded_files),
            },
            "items": [
                {
                    "id": f"{item.file_path}:{item.issue_type}",
                    "file_path": item.file_path,
                    "issue_type": item.issue_type,
                    "severity": item.severity,
                    "priority": item.priority,
                    "details": item.details,
                    "days_stale": item.days_stale,
                    "loc": item.loc,
                    "related_source": item.related_source[:3] if item.related_source else [],
                }
                for item in self._items
            ],
            "excluded": self._excluded_files,  # Files excluded from scanning
        }

    async def generate_for_files(
        self,
        file_paths: list[str],
        **kwargs: Any,
    ) -> dict:
        """Generate documentation for a list of specific files.

        Bypasses scout phase and generates directly for each file.

        Args:
            file_paths: List of file paths to document
            **kwargs: Additional arguments for DocumentGenerationWorkflow

        Returns:
            Dict with results for each file

        """
        generated: list[dict[str, str | float | None]] = []
        failed: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        total_cost = 0.0
        success = True

        for file_path in file_paths:
            # Skip excluded files (requirements.txt, package.json, etc.)
            if self._should_exclude(file_path):
                skipped.append(
                    {
                        "file": file_path,
                        "reason": "Excluded by pattern (dependency/config/binary file)",
                    },
                )
                continue

            try:
                result = await self.generate_for_file(file_path, **kwargs)
                if isinstance(result, dict) and result.get("error"):
                    failed.append({"file": file_path, "error": result["error"]})
                else:
                    export_path = result.get("export_path") if isinstance(result, dict) else None
                    cost = result.get("accumulated_cost", 0) if isinstance(result, dict) else 0
                    generated.append(
                        {
                            "file": file_path,
                            "export_path": export_path,
                            "cost": cost,
                        },
                    )
                    total_cost += cost
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Continue generating docs for remaining files
                failed.append({"file": file_path, "error": str(e)})
                success = False

        if failed:
            success = len(generated) > 0  # Partial success

        return {
            "success": success,
            "generated": generated,
            "failed": failed,
            "skipped": skipped,
            "total_cost": total_cost,
        }

    async def generate_for_file(
        self,
        file_path: str,
        **kwargs: Any,
    ) -> dict:
        """Generate documentation for a specific file.

        Bypasses scout phase and generates directly.

        Args:
            file_path: Path to the file to document
            **kwargs: Additional arguments for DocumentGenerationWorkflow

        Returns:
            Generation result dict

        """
        if self._writer is None:
            return {"error": "DocumentGenerationWorkflow not available"}

        source_path = self.project_root / file_path
        result = await self._writer.execute(
            path=str(source_path) if source_path.exists() else file_path,
        )

        # Update index on success (result may be WorkflowResult or dict from mocks)
        success = (
            result.get("document")
            if isinstance(result, dict)
            else getattr(result, "success", False)
        )
        if success:
            self._update_project_index([file_path], [])

        return result


# CLI entry point
if __name__ == "__main__":
    import json
    import sys

    async def main():
        """CLI entry point for the documentation orchestrator."""
        path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "."
        dry_run = "--dry-run" in sys.argv
        auto_approve = "--auto" in sys.argv
        scout_json = "--scout-json" in sys.argv

        # Parse --generate-files argument
        generate_files: list[str] | None = None
        for i, arg in enumerate(sys.argv):
            if arg == "--generate-files" and i + 1 < len(sys.argv):
                try:
                    generate_files = json.loads(sys.argv[i + 1])
                except json.JSONDecodeError:
                    print("Error: --generate-files must be valid JSON array", file=sys.stderr)
                    sys.exit(1)

        orchestrator = DocumentationOrchestrator(
            project_root=path,
            max_items=10,
            max_cost=5.0,
            dry_run=dry_run,
            auto_approve=auto_approve,
        )

        # JSON scout output for VSCode extension
        if scout_json:
            result = await orchestrator.scout_as_json()
            print(json.dumps(result))
            return

        # Generate specific files
        if generate_files:
            result = await orchestrator.generate_for_files(generate_files)
            print(json.dumps(result))
            return

        # Normal execution
        print("\nDocumentationOrchestrator")
        print(f"Project: {path}")
        print(f"Mode: {'DRY RUN' if dry_run else 'FULL' if auto_approve else 'SCOUT + AWAIT'}")

        print("\nComponents:")
        print(f"  Scout (ManageDocumentationCrew): {'✓' if orchestrator._scout else '✗'}")
        print(f"  Writer (DocumentGenerationWorkflow): {'✓' if orchestrator._writer else '✗'}")
        print(f"  ProjectIndex: {'✓' if orchestrator._project_index else '✗'}")

        result = await orchestrator.execute()

        if not result.summary:
            print(f"\nResult: {result.to_dict()}")

    asyncio.run(main())
