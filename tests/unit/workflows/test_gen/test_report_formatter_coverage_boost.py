"""Comprehensive coverage tests for Test Generation Report Formatter.

Tests report formatting, XML parsing, path truncation, and all report sections.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

import attune.workflows.test_gen.report_formatter as formatter_module

format_test_gen_report = formatter_module.format_test_gen_report


@pytest.mark.unit
class TestReportFormatterBasics:
    """Test basic report structure and headers."""

    def test_minimal_report(self):
        """Test report with minimal data."""
        result = {"total_tests": 0, "files_covered": 0}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "TEST GAP ANALYSIS REPORT" in report
        assert "SUMMARY" in report
        assert "Tests Generated:     0" in report
        assert "Files Covered:       0" in report

    def test_report_has_header_footer(self):
        """Test that report includes header and footer."""
        result = {"total_tests": 5, "files_covered": 2, "model_tier_used": "cheap"}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "=" * 60 in report
        assert "Review completed using cheap tier model" in report

    def test_summary_section_with_all_stats(self):
        """Test summary section with all statistics."""
        result = {"total_tests": 10, "files_covered": 5}
        input_data = {
            "total_candidates": 20,
            "hotspot_count": 3,
            "untested_count": 7,
        }

        report = format_test_gen_report(result, input_data)

        assert "Tests Generated:     10" in report
        assert "Files Covered:       5" in report
        assert "Total Candidates:    20" in report
        assert "Bug Hotspots Found:  3" in report
        assert "Untested Files:      7" in report


@pytest.mark.unit
class TestReportFormatterStatusIndicators:
    """Test status indicator logic based on test count."""

    def test_zero_tests_warning(self):
        """Test warning when no tests generated."""
        result = {"total_tests": 0, "files_covered": 0}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "⚠️  No tests were generated" in report

    def test_few_tests_yellow_status(self):
        """Test yellow status for 1-4 tests."""
        result = {"total_tests": 3, "files_covered": 2}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "🟡 Generated 3 test(s) - consider adding more coverage" in report

    def test_moderate_tests_green_status(self):
        """Test green status for 5-19 tests."""
        result = {"total_tests": 10, "files_covered": 5}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "🟢 Generated 10 tests - good coverage" in report

    def test_many_tests_excellent_status(self):
        """Test excellent status for 20+ tests."""
        result = {"total_tests": 25, "files_covered": 10}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "✅ Generated 25 tests - excellent coverage" in report


@pytest.mark.unit
class TestReportFormatterScopeNotice:
    """Test scope notice section for large projects."""

    def test_scope_notice_shown_with_source_files(self):
        """Test that scope notice appears when source files are present."""
        result = {"total_tests": 5, "files_covered": 3}
        input_data = {
            "total_source_files": 100,
            "existing_test_files": 50,
        }

        report = format_test_gen_report(result, input_data)

        assert "SCOPE NOTICE" in report
        assert "Source Files Found:   100" in report
        assert "Existing Test Files:  50" in report
        assert "Files Analyzed:       3" in report

    def test_large_project_warning(self):
        """Test large project warning display."""
        result = {"total_tests": 5, "files_covered": 3}
        input_data = {
            "total_source_files": 500,
            "large_project_warning": True,
            "analysis_coverage_percent": 30,
        }

        report = format_test_gen_report(result, input_data)

        assert "⚠️  LARGE PROJECT: Only high-priority files analyzed" in report
        assert "Coverage: 30% of candidate files" in report

    def test_existing_tests_note(self):
        """Test note about existing tests."""
        result = {"total_tests": 5, "files_covered": 3}
        input_data = {
            "total_source_files": 50,
            "existing_test_files": 25,
        }

        report = format_test_gen_report(result, input_data)

        assert "Note: This report identifies gaps in untested files." in report
        assert "Run 'pytest --co -q' for full test suite statistics." in report


@pytest.mark.unit
class TestReportFormatterXMLParsing:
    """Test XML review feedback parsing."""

    def test_xml_summary_extraction(self):
        """Test extracting summary from XML response."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": "<response><summary>Test coverage is adequate.</summary></response>",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "QUALITY ASSESSMENT" in report
        assert "Test coverage is adequate." in report

    def test_xml_coverage_improvement(self):
        """Test extracting coverage improvement from XML."""
        result = {
            "total_tests": 10,
            "files_covered": 5,
            "review_feedback": """<response>
                <summary>Good progress.</summary>
                <coverage-improvement>Coverage improved by 15%</coverage-improvement>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "📈 Coverage improved by 15%" in report

    def test_xml_findings_extraction(self):
        """Test extracting findings from XML."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="high">
                    <title>Missing error handling</title>
                    <location>module.py:42</location>
                    <fix>Add try-except block</fix>
                </finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "QUALITY FINDINGS" in report
        assert "🔴 [HIGH] Missing error handling" in report
        assert "Location: module.py:42" in report
        assert "Fix: Add try-except block" in report

    def test_multiple_findings_sorted_by_severity(self):
        """Test that findings are sorted by severity."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="low"><title>Low priority</title></finding>
                <finding severity="high"><title>High priority</title></finding>
                <finding severity="medium"><title>Medium priority</title></finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Check order: high, medium, low
        high_pos = report.find("HIGH")
        medium_pos = report.find("MEDIUM")
        low_pos = report.find("LOW")

        assert high_pos < medium_pos < low_pos

    def test_finding_severity_emojis(self):
        """Test that correct emojis are used for each severity."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="high"><title>High</title></finding>
                <finding severity="medium"><title>Medium</title></finding>
                <finding severity="low"><title>Low</title></finding>
                <finding severity="info"><title>Info</title></finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "🔴 [HIGH]" in report
        assert "🟠 [MEDIUM]" in report
        assert "🟡 [LOW]" in report
        assert "🔵 [INFO]" in report

    def test_xml_suggested_tests_extraction(self):
        """Test extracting suggested tests from XML."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <test target="login_function">
                    <type>unit</type>
                    <description>Test authentication flow</description>
                </test>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "SUGGESTED TESTS TO ADD" in report
        assert "login_function (unit)" in report
        assert "Test authentication flow" in report

    def test_suggested_tests_limited_to_five(self):
        """Test that suggested tests are limited to 5 displayed."""
        xml_tests = "".join(
            [
                f'<test target="func{i}"><type>unit</type><description>Test {i}</description></test>'
                for i in range(10)
            ],
        )
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": f"<response>{xml_tests}</response>",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "... and 5 more suggested tests" in report


@pytest.mark.unit
class TestReportFormatterPathTruncation:
    """Test path truncation for long file paths."""

    def test_long_source_path_truncated(self):
        """Test that long source file paths are truncated."""
        long_path = "a" * 60 + ".py"
        result = {"total_tests": 5, "files_covered": 1}
        input_data = {
            "generated_tests": [
                {"source_file": long_path, "test_count": 3, "test_file": "test_a.py"},
            ],
        }

        report = format_test_gen_report(result, input_data)

        # Should be truncated to "..." + last 47 chars = 50 total
        assert "..." in report
        assert long_path not in report

    def test_long_written_file_path_truncated(self):
        """Test that long written file paths are truncated."""
        long_path = "/very/long/path/" + ("subdir/" * 10) + "test_file.py"
        result = {"total_tests": 5, "files_covered": 1}
        input_data = {"written_files": [long_path]}

        report = format_test_gen_report(result, input_data)

        assert "..." in report

    def test_long_fix_recommendation_truncated(self):
        """Test that long fix recommendations are truncated."""
        long_fix = "This is a very long fix recommendation that should be truncated because it exceeds the maximum length"
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": f"""<response>
                <finding severity="high">
                    <title>Issue</title>
                    <fix>{long_fix}</fix>
                </finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should be truncated at 67 chars + "..."
        assert "Fix: " in report
        assert "..." in report

    def test_long_test_description_truncated(self):
        """Test that long test descriptions are truncated."""
        long_desc = "This is a very long test description that exceeds the maximum allowed length"
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": f"""<response>
                <test target="function">
                    <type>unit</type>
                    <description>{long_desc}</description>
                </test>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "..." in report


@pytest.mark.unit
class TestReportFormatterGeneratedTestsSection:
    """Test generated tests breakdown section."""

    def test_generated_tests_section(self):
        """Test display of generated tests breakdown."""
        result = {"total_tests": 6, "files_covered": 2}
        input_data = {
            "generated_tests": [
                {"source_file": "module1.py", "test_count": 3, "test_file": "test_module1.py"},
                {"source_file": "module2.py", "test_count": 3, "test_file": "test_module2.py"},
            ],
        }

        report = format_test_gen_report(result, input_data)

        assert "GENERATED TESTS BY FILE" in report
        assert "📁 module1.py" in report
        assert "└─ 3 test(s) → test_module1.py" in report

    def test_generated_tests_limited_to_ten(self):
        """Test that generated tests display is limited to 10."""
        generated_tests = [
            {"source_file": f"module{i}.py", "test_count": 2, "test_file": f"test_{i}.py"}
            for i in range(15)
        ]
        result = {"total_tests": 30, "files_covered": 15}
        input_data = {"generated_tests": generated_tests}

        report = format_test_gen_report(result, input_data)

        assert "... and 5 more files" in report

    def test_generated_tests_not_shown_with_xml_findings(self):
        """Test that generated tests section is hidden when XML findings exist."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": '<response><finding severity="high"><title>Test</title></finding></response>',
        }
        input_data = {
            "generated_tests": [
                {"source_file": "module.py", "test_count": 5, "test_file": "test_module.py"},
            ],
        }

        report = format_test_gen_report(result, input_data)

        assert "GENERATED TESTS BY FILE" not in report
        assert "QUALITY FINDINGS" in report


@pytest.mark.unit
class TestReportFormatterWrittenFilesSection:
    """Test written files section."""

    def test_written_files_section(self):
        """Test display of written test files."""
        result = {"total_tests": 5, "files_covered": 2}
        input_data = {"written_files": ["tests/test_module1.py", "tests/test_module2.py"]}

        report = format_test_gen_report(result, input_data)

        assert "TESTS WRITTEN TO DISK" in report
        assert "✅ tests/test_module1.py" in report
        assert "✅ tests/test_module2.py" in report
        assert "Run: pytest <file> to execute these tests" in report

    def test_written_files_limited_to_ten(self):
        """Test that written files display is limited to 10."""
        written_files = [f"tests/test_{i}.py" for i in range(15)]
        result = {"total_tests": 30, "files_covered": 15}
        input_data = {"written_files": written_files}

        report = format_test_gen_report(result, input_data)

        assert "... and 5 more files" in report

    def test_not_written_warning(self):
        """Test warning when tests generated but not written."""
        result = {"total_tests": 5, "files_covered": 2}
        input_data = {"tests_written": False}

        report = format_test_gen_report(result, input_data)

        assert "GENERATED TESTS (NOT WRITTEN)" in report
        assert "⚠️  Tests were generated but not written to disk." in report
        assert "To write tests, run with: write_tests=True" in report


@pytest.mark.unit
class TestReportFormatterRecommendations:
    """Test next steps recommendations section."""

    def test_high_priority_recommendation(self):
        """Test recommendation for high-priority findings."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="high"><title>Critical</title></finding>
                <finding severity="high"><title>Important</title></finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "NEXT STEPS" in report
        assert "🔴 Address 2 high-priority finding(s) first" in report

    def test_medium_priority_recommendation(self):
        """Test recommendation for medium-priority findings."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="medium"><title>Issue</title></finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "🟠 Review 1 medium-priority finding(s)" in report

    def test_suggested_tests_recommendation(self):
        """Test recommendation for suggested tests."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <test target="func1"><type>unit</type></test>
                <test target="func2"><type>unit</type></test>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "📝 Consider adding 2 suggested test(s)" in report

    def test_hotspot_recommendation(self):
        """Test recommendation for bug hotspots."""
        result = {"total_tests": 5, "files_covered": 2}
        input_data = {"hotspot_count": 3}

        report = format_test_gen_report(result, input_data)

        assert "🔥 3 bug hotspot file(s) need priority testing" in report

    def test_untested_files_recommendation(self):
        """Test recommendation for untested files."""
        result = {"total_tests": 5, "files_covered": 2}
        input_data = {"untested_count": 7}

        report = format_test_gen_report(result, input_data)

        assert "📁 7 file(s) have no existing tests" in report

    def test_good_shape_message_when_no_issues(self):
        """Test positive message when no issues found."""
        result = {"total_tests": 20, "files_covered": 10}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "✅ Test suite is in good shape!" in report


@pytest.mark.unit
class TestReportFormatterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_result_and_input(self):
        """Test handling completely empty data."""
        result = {}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should not crash, should show defaults
        assert "TEST GAP ANALYSIS REPORT" in report
        assert "Tests Generated:     0" in report

    def test_missing_review_feedback(self):
        """Test handling missing review feedback."""
        result = {"total_tests": 5, "files_covered": 2}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should not have XML sections
        assert "QUALITY ASSESSMENT" not in report
        assert "QUALITY FINDINGS" not in report

    def test_malformed_xml_review_feedback(self):
        """Test handling malformed XML."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": "<response>Malformed XML without proper tags",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should not crash, may not show XML sections
        assert "TEST GAP ANALYSIS REPORT" in report

    def test_xml_without_response_tag(self):
        """Test XML that doesn't have response wrapper."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": "<summary>No response wrapper</summary>",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should not parse XML sections
        assert "QUALITY ASSESSMENT" not in report

    def test_finding_without_optional_fields(self):
        """Test finding with missing optional fields."""
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": """<response>
                <finding severity="high">
                    <title>Issue</title>
                </finding>
            </response>""",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should show finding with defaults
        assert "🔴 [HIGH] Issue" in report

    def test_summary_word_wrapping(self):
        """Test that long summary text is word-wrapped."""
        long_summary = " ".join(["word"] * 30)  # Very long summary
        result = {
            "total_tests": 5,
            "files_covered": 2,
            "review_feedback": f"<response><summary>{long_summary}</summary></response>",
        }
        input_data = {}

        report = format_test_gen_report(result, input_data)

        # Should be word-wrapped (no single line > 58 chars)
        for line in report.split("\n"):
            if line and not line.startswith(("-", "=")):
                # Allow separator lines to be longer
                assert len(line) <= 70  # Some margin for emojis


@pytest.mark.unit
class TestReportFormatterIntegration:
    """Integration tests with realistic complete data."""

    def test_complete_report_with_all_sections(self):
        """Test complete report with all sections populated."""
        result = {
            "total_tests": 15,
            "files_covered": 8,
            "model_tier_used": "capable",
            "review_feedback": """<response>
                <summary>Test coverage has improved significantly with these additions.</summary>
                <coverage-improvement>Coverage increased from 45% to 68%</coverage-improvement>
                <finding severity="high">
                    <title>Missing authentication tests</title>
                    <location>auth.py:100-150</location>
                    <fix>Add tests for login, logout, and token validation</fix>
                </finding>
                <finding severity="medium">
                    <title>Incomplete error handling coverage</title>
                    <location>errors.py</location>
                    <fix>Test all exception branches</fix>
                </finding>
                <test target="validate_user">
                    <type>unit</type>
                    <description>Test user validation with various input types</description>
                </test>
            </response>""",
        }
        input_data = {
            "total_candidates": 50,
            "hotspot_count": 2,
            "untested_count": 10,
            "total_source_files": 100,
            "existing_test_files": 45,
            "large_project_warning": True,
            "analysis_coverage_percent": 60,
            "written_files": ["tests/test_auth.py", "tests/test_errors.py"],
        }

        report = format_test_gen_report(result, input_data)

        # Verify all major sections are present
        assert "TEST GAP ANALYSIS REPORT" in report
        assert "SUMMARY" in report
        assert "🟢 Generated 15 tests - good coverage" in report
        assert "SCOPE NOTICE" in report
        assert "⚠️  LARGE PROJECT" in report
        assert "QUALITY ASSESSMENT" in report
        assert "📈 Coverage increased from 45% to 68%" in report
        assert "QUALITY FINDINGS" in report
        assert "🔴 [HIGH] Missing authentication tests" in report
        assert "🟠 [MEDIUM] Incomplete error handling coverage" in report
        assert "SUGGESTED TESTS TO ADD" in report
        assert "validate_user (unit)" in report
        assert "TESTS WRITTEN TO DISK" in report
        assert "✅ tests/test_auth.py" in report
        assert "NEXT STEPS" in report
        assert "🔴 Address 1 high-priority finding(s) first" in report
        assert "🟠 Review 1 medium-priority finding(s)" in report
        assert "📝 Consider adding 1 suggested test(s)" in report
        assert "🔥 2 bug hotspot file(s) need priority testing" in report
        assert "Review completed using capable tier model" in report

    def test_minimal_success_report(self):
        """Test minimal successful report (few tests, no issues)."""
        result = {"total_tests": 3, "files_covered": 2, "model_tier_used": "cheap"}
        input_data = {}

        report = format_test_gen_report(result, input_data)

        assert "🟡 Generated 3 test(s) - consider adding more coverage" in report
        assert "✅ Test suite is in good shape!" in report
        assert "Review completed using cheap tier model" in report
