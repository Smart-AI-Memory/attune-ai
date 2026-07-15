"""Dependency Analysis - Import graph, impact scores, and project summary.

Builds the inter-file dependency graph from import statements, calculates
impact scores, determines which files need attention, and aggregates all
file records into a ProjectSummary.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import heapq

from .models import FileCategory, FileRecord, ProjectSummary, TestRequirement


class DependencyAnalysisMixin:
    """Mixin providing dependency analysis, scoring, and summary generation.

    Expects the consuming class to provide:
        - self.config: IndexConfig (for thresholds)
    """

    def _analyze_dependencies(self, records: list[FileRecord]) -> None:
        """Build dependency graph between files.

        Optimized from O(n^3) to O(n*m) where n=records, m=avg imports per file.
        Uses dict lookups instead of nested loops for finding modules and records.
        """
        # Build record lookup by path for O(1) access (eliminates innermost loop)
        records_by_path: dict[str, FileRecord] = {r.path: r for r in records}

        # Build multiple module indexes for flexible matching
        # Key: module name or suffix -> Value: path
        module_to_path: dict[str, str] = {}
        module_suffix_to_path: dict[str, str] = {}  # For "endswith" matching

        for record in records:
            if record.language == "python":
                # Convert path to module name: src/attune/core.py -> src.attune.core
                module_name = record.path.replace("/", ".").replace("\\", ".")
                module_name = module_name.removesuffix(".py")

                module_to_path[module_name] = record.path

                # Also index by module suffix parts for partial matching
                # e.g., "attune.core" and "core" for "src.attune.core"
                parts = module_name.split(".")
                for i in range(len(parts)):
                    suffix = ".".join(parts[i:])
                    if suffix not in module_suffix_to_path:
                        module_suffix_to_path[suffix] = record.path

        # Track which records have been updated (for imported_by deduplication)
        imported_by_sets: dict[str, set[str]] = {r.path: set() for r in records}

        # Update imported_by relationships with O(1) lookups
        for record in records:
            for imp in record.imports:
                # Try exact match first
                target_path = module_to_path.get(imp)

                # Try suffix match if no exact match
                if not target_path:
                    target_path = module_suffix_to_path.get(imp)

                # Try partial suffix matching as fallback
                if not target_path:
                    # Check if import is a suffix of any module
                    for suffix, path in module_suffix_to_path.items():
                        if suffix.endswith(imp) or imp in suffix:
                            target_path = path
                            break

                if target_path and target_path in records_by_path:
                    # Use set for O(1) deduplication check
                    if record.path not in imported_by_sets[target_path]:
                        imported_by_sets[target_path].add(record.path)
                        target_record = records_by_path[target_path]
                        target_record.imported_by.append(record.path)
                        target_record.imported_by_count = len(target_record.imported_by)

    def _calculate_impact_scores(self, records: list[FileRecord]) -> None:
        """Calculate impact score for each file."""
        for record in records:
            # Impact = imported_by_count * 2 + complexity * 0.5 + lines_of_code * 0.01
            record.impact_score = (
                record.imported_by_count * 2.0
                + record.complexity_score * 0.5
                + record.lines_of_code * 0.01
            )

    def _determine_attention_needs(self, records: list[FileRecord]) -> None:
        """Determine which files need attention."""
        for record in records:
            reasons = []

            # Stale tests
            if record.is_stale:
                reasons.append(f"Tests are {record.staleness_days} days stale")

            # No tests but required
            if record.test_requirement == TestRequirement.REQUIRED and not record.tests_exist:
                reasons.append("Missing tests")

            # Low coverage (if we have coverage data)
            if (
                record.coverage_percent > 0
                and record.coverage_percent < self.config.low_coverage_threshold
            ):
                reasons.append(f"Low coverage ({record.coverage_percent:.1f}%)")

            # High impact but no tests
            if record.impact_score >= self.config.high_impact_threshold:
                if not record.tests_exist and record.test_requirement == TestRequirement.REQUIRED:
                    reasons.append(f"High impact ({record.impact_score:.1f}) without tests")

            record.attention_reasons = reasons
            record.needs_attention = len(reasons) > 0

    def _build_summary(self, records: list[FileRecord]) -> ProjectSummary:
        """Build project summary from records."""
        summary = ProjectSummary()
        _summarize_categories(summary, records)
        _summarize_testing(summary, records)
        _summarize_staleness(summary, records)
        _summarize_code_metrics(summary, records)
        _summarize_impact(summary, records, self.config.high_impact_threshold)
        return summary


def _summarize_categories(summary: ProjectSummary, records: list[FileRecord]) -> None:
    """File counts per category."""
    summary.total_files = len(records)
    summary.source_files = sum(1 for r in records if r.category == FileCategory.SOURCE)
    summary.test_files = sum(1 for r in records if r.category == FileCategory.TEST)
    summary.config_files = sum(1 for r in records if r.category == FileCategory.CONFIG)
    summary.doc_files = sum(1 for r in records if r.category == FileCategory.DOCS)


def _summarize_testing(summary: ProjectSummary, records: list[FileRecord]) -> None:
    """Testing health: requirement counts, test totals, coverage average."""
    requiring_tests = [r for r in records if r.test_requirement == TestRequirement.REQUIRED]
    summary.files_requiring_tests = len(requiring_tests)
    summary.files_with_tests = sum(1 for r in requiring_tests if r.tests_exist)
    summary.files_without_tests = summary.files_requiring_tests - summary.files_with_tests
    summary.total_test_count = sum(r.test_count for r in records if r.category == FileCategory.TEST)

    # Coverage average — only over records that carry coverage data.
    covered = [r for r in records if r.coverage_percent > 0]
    if covered:
        summary.test_coverage_avg = sum(r.coverage_percent for r in covered) / len(covered)


def _summarize_staleness(summary: ProjectSummary, records: list[FileRecord]) -> None:
    """Stale-test counts, average staleness, top-5 most stale."""
    stale = [r for r in records if r.is_stale]
    summary.stale_file_count = len(stale)
    if stale:
        summary.avg_staleness_days = sum(r.staleness_days for r in stale) / len(stale)
        top_stale = heapq.nlargest(5, stale, key=lambda r: r.staleness_days)
        summary.most_stale_files = [r.path for r in top_stale]


def _summarize_code_metrics(summary: ProjectSummary, records: list[FileRecord]) -> None:
    """LOC totals, test-to-code ratio, complexity, quality percentages."""
    source_records = [r for r in records if r.category == FileCategory.SOURCE]
    summary.total_lines_of_code = sum(r.lines_of_code for r in source_records)
    summary.total_lines_of_test = sum(
        r.lines_of_code for r in records if r.category == FileCategory.TEST
    )
    if summary.total_lines_of_code > 0:
        summary.test_to_code_ratio = summary.total_lines_of_test / summary.total_lines_of_code
    if source_records:
        summary.avg_complexity = sum(r.complexity_score for r in source_records) / len(
            source_records,
        )
        summary.files_with_docstrings_pct = (
            sum(1 for r in source_records if r.has_docstrings) / len(source_records) * 100
        )
        summary.files_with_type_hints_pct = (
            sum(1 for r in source_records if r.has_type_hints) / len(source_records) * 100
        )
    summary.total_lint_issues = sum(r.lint_issues for r in records)


def _summarize_impact(
    summary: ProjectSummary, records: list[FileRecord], high_impact_threshold: float
) -> None:
    """High-impact, critical-untested, and needs-attention rankings."""
    high_impact = heapq.nlargest(10, records, key=lambda r: r.impact_score)
    summary.high_impact_files = [
        r.path for r in high_impact if r.impact_score >= high_impact_threshold
    ]

    # Critical untested files (high impact + no tests)
    critical = [
        r
        for r in records
        if r.impact_score >= high_impact_threshold
        and not r.tests_exist
        and r.test_requirement == TestRequirement.REQUIRED
    ]
    summary.critical_untested_files = [
        r.path for r in heapq.nlargest(10, critical, key=lambda r: r.impact_score)
    ]

    needing_attention = [r for r in records if r.needs_attention]
    summary.files_needing_attention = len(needing_attention)
    summary.top_attention_files = [
        r.path for r in heapq.nlargest(10, needing_attention, key=lambda r: r.impact_score)
    ]
