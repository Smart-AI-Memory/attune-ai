"""Project Scanner - Scans codebase to build file index.

Facade that composes file analysis, code metrics, and dependency analysis
mixins into a single ProjectScanner class.  All public APIs are preserved;
internal logic is delegated to focused modules:

- file_analysis.py   -- categorization, glob matching, test mapping
- code_metrics.py    -- AST parsing, complexity, caching
- dependency_analysis.py -- import graph, impact scores, summary

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import re
from datetime import datetime
from pathlib import Path

from .code_metrics import CodeMetricsMixin
from .dependency_analysis import DependencyAnalysisMixin
from .file_analysis import FileAnalysisMixin
from .models import (
    FileCategory,  # noqa: F401 - re-exported
    FileRecord,
    IndexConfig,
    ProjectSummary,
)


class ProjectScanner(FileAnalysisMixin, CodeMetricsMixin, DependencyAnalysisMixin):
    """Scans a project directory and builds file metadata.

    Used by ProjectIndex to populate and update the index.

    Composes three mixins:
        - FileAnalysisMixin: file discovery, categorization, test mapping
        - CodeMetricsMixin: AST analysis, complexity scoring, caching
        - DependencyAnalysisMixin: dependency graph, impact scores, summary
    """

    # Re-export class-level frozensets so existing attribute access still works.
    # The canonical definitions live in FileAnalysisMixin; these aliases keep
    # backward compatibility for any code that references ProjectScanner.XYZ.
    CONFIG_SUFFIXES = FileAnalysisMixin.CONFIG_SUFFIXES
    DOC_SUFFIXES = FileAnalysisMixin.DOC_SUFFIXES
    DOC_NAMES = FileAnalysisMixin.DOC_NAMES
    ASSET_SUFFIXES = FileAnalysisMixin.ASSET_SUFFIXES
    SOURCE_SUFFIXES = FileAnalysisMixin.SOURCE_SUFFIXES

    def __init__(self, project_root: str, config: IndexConfig | None = None):
        """Initialize the project scanner.

        Args:
            project_root: Root directory of the project to scan.
            config: Optional index configuration overrides.
        """
        self.project_root = Path(project_root)
        self.config = config or IndexConfig()
        self._test_file_map: dict[str, str] = {}  # source -> test mapping
        # Pre-compile glob patterns for O(1) matching (vs recompiling on every call)
        # This optimization reduces _matches_glob_pattern() time by ~70%
        self._compiled_patterns: dict[str, tuple[re.Pattern, str | None]] = {}
        self._compile_glob_patterns()

    def scan(self, analyze_dependencies: bool = True) -> tuple[list[FileRecord], ProjectSummary]:
        """Scan the entire project and return file records and summary.

        Args:
            analyze_dependencies: Whether to analyze import dependencies.
                Set to False to skip expensive dependency graph analysis (saves ~2s).
                Default: True for backwards compatibility.

        Returns:
            Tuple of (list of FileRecords, ProjectSummary)

        """
        records: list[FileRecord] = []

        # First pass: discover all files
        all_files = self._discover_files()

        # Build test file mapping
        self._build_test_mapping(all_files)

        # Second pass: analyze each file
        for file_path in all_files:
            record = self._analyze_file(file_path)
            if record:
                records.append(record)

        # Third pass: build dependency graph (optional - saves ~2s when skipped)
        if analyze_dependencies:
            self._analyze_dependencies(records)

            # Calculate impact scores (depends on dependency graph)
            self._calculate_impact_scores(records)

        # Determine attention needs
        self._determine_attention_needs(records)

        # Build summary
        summary = self._build_summary(records)

        return records, summary

    def _analyze_file(self, file_path: Path) -> FileRecord | None:
        """Analyze a single file and create its record."""
        rel_path = str(file_path.relative_to(self.project_root))

        # Determine category
        category = self._determine_category(file_path)

        # Determine language
        language = self._determine_language(file_path)

        # Get file stats
        try:
            stat = file_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            last_modified = None

        # Determine test requirement
        test_requirement = self._determine_test_requirement(file_path, category)

        # Find associated test file
        test_file_path = self._test_file_map.get(rel_path)
        tests_exist = test_file_path is not None

        # Get test file modification time
        tests_last_modified = None
        if test_file_path:
            test_full_path = self.project_root / test_file_path
            if test_full_path.exists():
                try:
                    tests_last_modified = datetime.fromtimestamp(test_full_path.stat().st_mtime)
                except OSError:
                    pass

        # Calculate staleness
        staleness_days = 0
        is_stale = False
        if last_modified and tests_last_modified:
            if last_modified > tests_last_modified:
                staleness_days = (last_modified - tests_last_modified).days
                is_stale = staleness_days >= self.config.staleness_threshold_days

        # Analyze code metrics (skip expensive AST analysis for test files)
        metrics = self._analyze_code_metrics(file_path, language, category)

        return FileRecord(
            path=rel_path,
            name=file_path.name,
            category=category,
            language=language,
            test_requirement=test_requirement,
            test_file_path=test_file_path,
            tests_exist=tests_exist,
            test_count=metrics.get("test_count", 0),
            coverage_percent=0.0,  # Will be populated from coverage data
            last_modified=last_modified,
            tests_last_modified=tests_last_modified,
            last_indexed=datetime.now(),
            staleness_days=staleness_days,
            is_stale=is_stale,
            lines_of_code=metrics.get("lines_of_code", 0),
            lines_of_test=metrics.get("lines_of_test", 0),
            complexity_score=metrics.get("complexity", 0.0),
            has_docstrings=metrics.get("has_docstrings", False),
            has_type_hints=metrics.get("has_type_hints", False),
            lint_issues=0,  # Will be populated from linter
            imports=metrics.get("imports", []),
            imported_by=[],  # Populated in dependency analysis
            import_count=len(metrics.get("imports", [])),
            imported_by_count=0,
            impact_score=0.0,  # Calculated later
            metadata={},
            needs_attention=False,
            attention_reasons=[],
        )
