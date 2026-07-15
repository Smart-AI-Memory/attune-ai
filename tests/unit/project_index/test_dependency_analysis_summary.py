"""Characterization pins for DependencyAnalysisMixin._build_summary.

Pins the CURRENT exact aggregation behavior (project_index/
dependency_analysis.py) so a follow-up refactor of the radon-F48
method can be proven behavior-preserving. Records are built
in-memory; the real ProjectScanner (which carries the mixin and a
real IndexConfig) runs the real method — no mocks.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.project_index.models import (
    FileCategory,
    FileRecord,
    ProjectSummary,
    TestRequirement,
)
from attune.project_index.scanner import ProjectScanner


def _rec(path: str, **kw) -> FileRecord:
    return FileRecord(path=path, name=path.split("/")[-1], **kw)


@pytest.fixture()
def scanner(tmp_path) -> ProjectScanner:
    """Real analyzer carrying the mixin, with the default IndexConfig."""
    return ProjectScanner(project_root=str(tmp_path))


def test_config_defaults_assumed_by_these_pins(scanner: ProjectScanner) -> None:
    """The pins below depend on the default high-impact threshold."""
    assert scanner.config.high_impact_threshold == 5.0


class TestEmptyRecords:
    def test_empty_records_leaves_all_defaults_untouched(self, scanner: ProjectScanner) -> None:
        summary = scanner._build_summary([])

        assert isinstance(summary, ProjectSummary)
        # Counts
        assert summary.total_files == 0
        assert summary.source_files == 0
        assert summary.test_files == 0
        assert summary.config_files == 0
        assert summary.doc_files == 0
        # Testing health
        assert summary.files_requiring_tests == 0
        assert summary.files_with_tests == 0
        assert summary.files_without_tests == 0
        assert summary.test_coverage_avg == 0.0
        assert summary.total_test_count == 0
        # Staleness (guards: untouched)
        assert summary.stale_file_count == 0
        assert summary.avg_staleness_days == 0.0
        assert summary.most_stale_files == []
        # Code metrics (guards: untouched)
        assert summary.total_lines_of_code == 0
        assert summary.total_lines_of_test == 0
        assert summary.test_to_code_ratio == 0.0
        assert summary.avg_complexity == 0.0
        # Quality (guards: untouched)
        assert summary.files_with_docstrings_pct == 0.0
        assert summary.files_with_type_hints_pct == 0.0
        assert summary.total_lint_issues == 0
        # Impact / attention
        assert summary.high_impact_files == []
        assert summary.critical_untested_files == []
        assert summary.files_needing_attention == 0
        assert summary.top_attention_files == []


class TestRichMixedRecords:
    """One rich fixture, every aggregation pinned to exact values."""

    @pytest.fixture()
    def records(self) -> list[FileRecord]:
        return [
            _rec(
                "src/s1.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=True,
                # test_count on a non-TEST record must NOT be summed:
                test_count=99,
                coverage_percent=80.0,
                lines_of_code=100,
                complexity_score=10.0,
                has_docstrings=True,
                has_type_hints=True,
                lint_issues=2,
                impact_score=20.0,
            ),
            _rec(
                "src/s2.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                coverage_percent=40.0,
                is_stale=True,
                staleness_days=30,
                lines_of_code=200,
                complexity_score=6.0,
                has_type_hints=True,
                lint_issues=1,
                impact_score=12.0,
                needs_attention=True,
            ),
            _rec(
                "src/s3.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                coverage_percent=0.0,  # excluded from coverage avg
                is_stale=True,
                staleness_days=5,
                lines_of_code=50,
                complexity_score=2.0,
                has_docstrings=True,
                impact_score=4.0,  # below high_impact_threshold
                needs_attention=True,
            ),
            _rec(
                "src/s4.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.OPTIONAL,
                tests_exist=False,
                lines_of_code=150,
                complexity_score=4.0,
                lint_issues=3,
                impact_score=7.0,  # high impact but OPTIONAL -> not critical
            ),
            _rec(
                "src/s5.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                lines_of_code=80,
                complexity_score=3.0,
                has_docstrings=True,
                has_type_hints=True,
                lint_issues=1,
                impact_score=6.0,
                needs_attention=True,
            ),
            _rec(
                "tests/test_s1.py",
                category=FileCategory.TEST,
                test_requirement=TestRequirement.NOT_APPLICABLE,
                test_count=12,
                lines_of_code=60,
                impact_score=1.0,
            ),
            _rec(
                "tests/test_s2.py",
                category=FileCategory.TEST,
                test_requirement=TestRequirement.NOT_APPLICABLE,
                test_count=8,
                lines_of_code=40,
                impact_score=0.5,
            ),
            _rec(
                "pyproject.toml",
                category=FileCategory.CONFIG,
                test_requirement=TestRequirement.NOT_APPLICABLE,
                lines_of_code=30,  # non-source LOC must not count
            ),
            _rec(
                "README.md",
                category=FileCategory.DOCS,
                test_requirement=TestRequirement.NOT_APPLICABLE,
                lines_of_code=25,  # non-source LOC must not count
            ),
        ]

    @pytest.fixture()
    def summary(self, scanner: ProjectScanner, records: list[FileRecord]) -> ProjectSummary:
        return scanner._build_summary(records)

    def test_category_counts(self, summary: ProjectSummary) -> None:
        assert summary.total_files == 9
        assert summary.source_files == 5
        assert summary.test_files == 2
        assert summary.config_files == 1
        assert summary.doc_files == 1

    def test_testing_health(self, summary: ProjectSummary) -> None:
        assert summary.files_requiring_tests == 4  # s1, s2, s3, s5
        assert summary.files_with_tests == 1  # s1 only
        assert summary.files_without_tests == 3  # derived difference
        # Only TEST-category records contribute; s1's test_count=99 ignored.
        assert summary.total_test_count == 20

    def test_coverage_average_only_over_covered_records(self, summary: ProjectSummary) -> None:
        # s1 (80.0) and s2 (40.0); s3's 0.0 excluded from the denominator.
        assert summary.test_coverage_avg == 60.0

    def test_staleness_aggregation_and_ordering(self, summary: ProjectSummary) -> None:
        assert summary.stale_file_count == 2
        assert summary.avg_staleness_days == 17.5  # (30 + 5) / 2
        assert summary.most_stale_files == ["src/s2.py", "src/s3.py"]

    def test_lines_of_code_totals_and_ratio(self, summary: ProjectSummary) -> None:
        # Source LOC only (100+200+50+150+80); config/docs LOC excluded.
        assert summary.total_lines_of_code == 580
        assert summary.total_lines_of_test == 100  # 60 + 40
        assert summary.test_to_code_ratio == 100 / 580

    def test_avg_complexity_over_source_records(self, summary: ProjectSummary) -> None:
        assert summary.avg_complexity == 5.0  # (10+6+2+4+3) / 5

    def test_quality_percentages_and_lint_total(self, summary: ProjectSummary) -> None:
        assert summary.files_with_docstrings_pct == 60.0  # s1, s3, s5 of 5
        assert summary.files_with_type_hints_pct == 60.0  # s1, s2, s5 of 5
        assert summary.total_lint_issues == 7  # 2+1+0+3+1 (all records)

    def test_high_impact_files_filtered_and_ordered(self, summary: ProjectSummary) -> None:
        # Top-10 by impact then filtered >= 5.0; s3 (4.0) is IN the top-10
        # but excluded by the threshold filter.
        assert summary.high_impact_files == [
            "src/s1.py",
            "src/s2.py",
            "src/s4.py",
            "src/s5.py",
        ]

    def test_critical_untested_files(self, summary: ProjectSummary) -> None:
        # High impact + no tests + REQUIRED, ordered by impact desc.
        # s1 excluded (has tests), s4 excluded (OPTIONAL), s3 (below threshold).
        assert summary.critical_untested_files == ["src/s2.py", "src/s5.py"]

    def test_attention_count_and_top_files(self, summary: ProjectSummary) -> None:
        assert summary.files_needing_attention == 3
        # Ordered by impact_score desc: s2 (12), s5 (6), s3 (4).
        assert summary.top_attention_files == ["src/s2.py", "src/s5.py", "src/s3.py"]


class TestGuardBranches:
    def test_coverage_avg_untouched_when_no_covered_records(self, scanner: ProjectScanner) -> None:
        records = [
            _rec("src/a.py", category=FileCategory.SOURCE, coverage_percent=0.0),
            _rec("src/b.py", category=FileCategory.SOURCE, coverage_percent=0.0),
        ]
        summary = scanner._build_summary(records)
        assert summary.test_coverage_avg == 0.0

    def test_staleness_untouched_when_no_stale_records(self, scanner: ProjectScanner) -> None:
        records = [
            _rec(
                "src/a.py",
                category=FileCategory.SOURCE,
                is_stale=False,
                staleness_days=99,  # ignored: not flagged stale
            ),
        ]
        summary = scanner._build_summary(records)
        assert summary.stale_file_count == 0
        assert summary.avg_staleness_days == 0.0
        assert summary.most_stale_files == []

    def test_most_stale_files_top_five_by_staleness_days(self, scanner: ProjectScanner) -> None:
        records = [
            _rec(
                f"src/f{i}.py",
                category=FileCategory.SOURCE,
                is_stale=True,
                staleness_days=days,
            )
            for i, days in enumerate([3, 40, 7, 25, 12, 31, 1])
        ]
        summary = scanner._build_summary(records)
        assert summary.stale_file_count == 7
        assert summary.avg_staleness_days == (3 + 40 + 7 + 25 + 12 + 31 + 1) / 7
        # Exactly 5, descending by staleness_days: 40, 31, 25, 12, 7.
        assert summary.most_stale_files == [
            "src/f1.py",
            "src/f5.py",
            "src/f3.py",
            "src/f4.py",
            "src/f2.py",
        ]

    def test_ratio_and_metrics_untouched_when_no_source_loc(self, scanner: ProjectScanner) -> None:
        # TEST-only records: total_lines_of_code == 0 -> the ratio,
        # avg_complexity, and quality percentages all stay at defaults
        # even though test lines exist.
        records = [
            _rec(
                "tests/test_x.py",
                category=FileCategory.TEST,
                lines_of_code=500,
                complexity_score=9.0,
                has_docstrings=True,
                has_type_hints=True,
                lint_issues=4,
            ),
        ]
        summary = scanner._build_summary(records)
        assert summary.total_lines_of_code == 0
        assert summary.total_lines_of_test == 500
        assert summary.test_to_code_ratio == 0.0
        assert summary.avg_complexity == 0.0
        assert summary.files_with_docstrings_pct == 0.0
        assert summary.files_with_type_hints_pct == 0.0
        # total_lint_issues sums ALL records (no source guard).
        assert summary.total_lint_issues == 4

    def test_source_with_zero_loc_still_gets_complexity_and_quality(
        self, scanner: ProjectScanner
    ) -> None:
        # source_records non-empty but total LOC 0: ratio guard holds,
        # avg_complexity and percentages DO compute.
        records = [
            _rec(
                "src/empty.py",
                category=FileCategory.SOURCE,
                lines_of_code=0,
                complexity_score=3.0,
                has_docstrings=True,
            ),
            _rec("tests/test_empty.py", category=FileCategory.TEST, lines_of_code=10),
        ]
        summary = scanner._build_summary(records)
        assert summary.total_lines_of_code == 0
        assert summary.total_lines_of_test == 10
        assert summary.test_to_code_ratio == 0.0  # guard: unchanged
        assert summary.avg_complexity == 3.0
        assert summary.files_with_docstrings_pct == 100.0
        assert summary.files_with_type_hints_pct == 0.0


class TestTopTenCaps:
    def test_high_impact_capped_at_ten_descending(self, scanner: ProjectScanner) -> None:
        # 12 records all above threshold -> only the top 10, descending.
        records = [
            _rec(
                f"src/m{i:02d}.py",
                category=FileCategory.SOURCE,
                impact_score=float(20 - i),  # 20, 19, ..., 9
            )
            for i in range(12)
        ]
        summary = scanner._build_summary(records)
        assert summary.high_impact_files == [f"src/m{i:02d}.py" for i in range(10)]

    def test_critical_untested_capped_at_ten_descending(self, scanner: ProjectScanner) -> None:
        records = [
            _rec(
                f"src/c{i:02d}.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                impact_score=float(30 - i),  # 30, 29, ..., 19
            )
            for i in range(12)
        ]
        summary = scanner._build_summary(records)
        assert summary.critical_untested_files == [f"src/c{i:02d}.py" for i in range(10)]

    def test_attention_count_uncapped_but_top_files_capped_at_ten(
        self, scanner: ProjectScanner
    ) -> None:
        records = [
            _rec(
                f"src/a{i:02d}.py",
                category=FileCategory.SOURCE,
                needs_attention=True,
                impact_score=float(12 - i),  # 12, 11, ..., 1
            )
            for i in range(12)
        ]
        summary = scanner._build_summary(records)
        assert summary.files_needing_attention == 12
        assert summary.top_attention_files == [f"src/a{i:02d}.py" for i in range(10)]


class TestCriticalUntestedExclusions:
    def test_each_exclusion_reason(self, scanner: ProjectScanner) -> None:
        records = [
            # Included: high impact, no tests, REQUIRED.
            _rec(
                "src/critical.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                impact_score=10.0,
            ),
            # Excluded: has tests.
            _rec(
                "src/tested.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=True,
                impact_score=11.0,
            ),
            # Excluded: not REQUIRED.
            _rec(
                "src/optional.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.OPTIONAL,
                tests_exist=False,
                impact_score=12.0,
            ),
            # Excluded: below high_impact_threshold.
            _rec(
                "src/low.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                impact_score=4.9,
            ),
        ]
        summary = scanner._build_summary(records)
        assert summary.critical_untested_files == ["src/critical.py"]

    def test_threshold_boundary_is_inclusive(self, scanner: ProjectScanner) -> None:
        # impact_score == threshold (5.0) counts as high impact (>=).
        records = [
            _rec(
                "src/edge.py",
                category=FileCategory.SOURCE,
                test_requirement=TestRequirement.REQUIRED,
                tests_exist=False,
                impact_score=5.0,
            ),
        ]
        summary = scanner._build_summary(records)
        assert summary.high_impact_files == ["src/edge.py"]
        assert summary.critical_untested_files == ["src/edge.py"]
