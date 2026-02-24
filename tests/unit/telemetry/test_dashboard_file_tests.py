"""Tests for telemetry/commands/dashboard_file_tests.py.

Tests the HTML dashboard generation functions for file test status.
"""

from types import SimpleNamespace

from attune.telemetry.commands.dashboard_file_tests import (
    _build_file_test_html,
    _build_table_rows,
    _generate_empty_dashboard,
)


def _make_record(
    file_path: str = "src/foo.py",
    last_test_result: str = "passed",
    is_stale: bool = False,
    test_count: int = 5,
    passed: int = 5,
    failed: int = 0,
    errors: int = 0,
    duration_seconds: float = 1.2,
    timestamp: str = "2026-01-15T10:30:00Z",
) -> SimpleNamespace:
    """Create a mock file test record."""
    return SimpleNamespace(
        file_path=file_path,
        last_test_result=last_test_result,
        is_stale=is_stale,
        test_count=test_count,
        passed=passed,
        failed=failed,
        errors=errors,
        duration_seconds=duration_seconds,
        timestamp=timestamp,
    )


class TestBuildTableRows:
    """Tests for _build_table_rows()."""

    def test_passed_record(self):
        """Test that a passed record gets correct status class and icon."""
        record = _make_record(last_test_result="passed")
        html = _build_table_rows([record])
        assert 'class="passed"' in html
        assert "\u2705" in html
        assert "src/foo.py" in html

    def test_failed_record(self):
        """Test that a failed record gets correct status class and icon."""
        record = _make_record(last_test_result="failed", failed=2)
        html = _build_table_rows([record])
        assert 'class="failed"' in html
        assert "\u274c" in html

    def test_error_record(self):
        """Test that an error record uses the failed status class."""
        record = _make_record(last_test_result="error", errors=1)
        html = _build_table_rows([record])
        assert 'class="failed"' in html

    def test_no_tests_record(self):
        """Test that a no_tests record gets warning status."""
        record = _make_record(last_test_result="no_tests", test_count=0, passed=0)
        html = _build_table_rows([record])
        assert 'class="no-tests"' in html
        assert "\u26a0\ufe0f" in html

    def test_unknown_result_gets_skipped_class(self):
        """Test that an unknown result type gets skipped class."""
        record = _make_record(last_test_result="skipped")
        html = _build_table_rows([record])
        assert 'class="skipped"' in html

    def test_stale_badge_shown(self):
        """Test that stale records get a STALE badge."""
        record = _make_record(is_stale=True)
        html = _build_table_rows([record])
        assert "STALE" in html
        assert "badge stale" in html

    def test_stale_badge_absent_when_not_stale(self):
        """Test that non-stale records have no STALE badge."""
        record = _make_record(is_stale=False)
        html = _build_table_rows([record])
        assert "STALE" not in html

    def test_timestamp_formatting(self):
        """Test that ISO timestamps are formatted as YYYY-MM-DD HH:MM."""
        record = _make_record(timestamp="2026-01-15T10:30:00Z")
        html = _build_table_rows([record])
        assert "2026-01-15 10:30" in html

    def test_empty_records(self):
        """Test that empty records list returns empty string."""
        html = _build_table_rows([])
        assert html == ""


class TestGenerateEmptyDashboard:
    """Tests for _generate_empty_dashboard()."""

    def test_contains_title(self):
        """Test that empty dashboard contains expected title."""
        html = _generate_empty_dashboard()
        assert "File Test Status Dashboard" in html

    def test_contains_no_data_message(self):
        """Test that empty dashboard contains no-data message."""
        html = _generate_empty_dashboard()
        assert "No Test Data Available" in html

    def test_contains_scan_instruction(self):
        """Test that empty dashboard tells user how to populate data."""
        html = _generate_empty_dashboard()
        assert "file-tests --scan" in html


class TestBuildFileTestHtml:
    """Tests for _build_file_test_html()."""

    def test_stats_embedded(self):
        """Test that stats values are embedded in HTML."""
        html = _build_file_test_html(
            total=42, passed=30, failed=5, no_tests=4, stale=3, rows_html=""
        )
        assert ">42<" in html
        assert ">30<" in html
        assert ">5<" in html
        assert ">4<" in html
        assert ">3<" in html

    def test_rows_embedded(self):
        """Test that rows_html is included in the output."""
        sentinel = '<tr class="passed"><td>sentinel_file.py</td></tr>'
        html = _build_file_test_html(
            total=1, passed=1, failed=0, no_tests=0, stale=0, rows_html=sentinel
        )
        assert "sentinel_file.py" in html

    def test_contains_filter_buttons(self):
        """Test that the dashboard includes filter UI."""
        html = _build_file_test_html(total=1, passed=1, failed=0, no_tests=0, stale=0, rows_html="")
        assert "filter-btn" in html
        assert "searchInput" in html

    def test_contains_title(self):
        """Test that the full dashboard contains the title."""
        html = _build_file_test_html(total=0, passed=0, failed=0, no_tests=0, stale=0, rows_html="")
        assert "File Test Status Dashboard" in html
