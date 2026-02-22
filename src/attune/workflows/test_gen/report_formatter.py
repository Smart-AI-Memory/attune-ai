"""Test Generation Report Formatter.

Format test generation output as human-readable reports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re


def format_test_gen_report(result: dict, input_data: dict) -> str:
    """Format test generation output as a human-readable report.

    Args:
        result: The review stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("TEST GAP ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append("")

    total_tests = result.get("total_tests", 0)
    files_covered = result.get("files_covered", 0)

    _format_summary_section(lines, total_tests, files_covered, input_data)
    _format_scope_notice(lines, input_data, files_covered)

    # Parse XML review feedback
    xml_summary, xml_findings, xml_tests, coverage_improvement = _parse_xml_review(
        result.get("review_feedback", "")
    )

    _format_quality_section(lines, xml_summary, coverage_improvement)
    _format_findings_section(lines, xml_findings)
    _format_suggested_tests(lines, xml_tests)
    _format_generated_tests(lines, input_data, xml_findings)
    _format_written_files(lines, input_data, total_tests)
    _format_recommendations(lines, xml_findings, xml_tests, input_data)

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Review completed using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def _format_summary_section(
    lines: list[str], total_tests: int, files_covered: int, input_data: dict
) -> None:
    """Format the summary stats and status indicator."""
    total_candidates = input_data.get("total_candidates", 0)
    hotspot_count = input_data.get("hotspot_count", 0)
    untested_count = input_data.get("untested_count", 0)

    lines.append("-" * 60)
    lines.append("SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Tests Generated:     {total_tests}")
    lines.append(f"Files Covered:       {files_covered}")
    lines.append(f"Total Candidates:    {total_candidates}")
    lines.append(f"Bug Hotspots Found:  {hotspot_count}")
    lines.append(f"Untested Files:      {untested_count}")
    lines.append("")

    # Status indicator
    if total_tests == 0:
        lines.append("\u26a0\ufe0f  No tests were generated")
    elif total_tests < 5:
        lines.append(f"\U0001f7e1 Generated {total_tests} test(s) - consider adding more coverage")
    elif total_tests < 20:
        lines.append(f"\U0001f7e2 Generated {total_tests} tests - good coverage")
    else:
        lines.append(f"\u2705 Generated {total_tests} tests - excellent coverage")
    lines.append("")


def _format_scope_notice(lines: list[str], input_data: dict, files_covered: int) -> None:
    """Format the scope notice section for large projects."""
    total_source = input_data.get("total_source_files", 0)
    existing_tests = input_data.get("existing_test_files", 0)
    coverage_pct = input_data.get("analysis_coverage_percent", 100)
    large_project = input_data.get("large_project_warning", False)

    if total_source <= 0 and existing_tests <= 0:
        return

    lines.append("-" * 60)
    lines.append("SCOPE NOTICE")
    lines.append("-" * 60)

    if large_project:
        lines.append("\u26a0\ufe0f  LARGE PROJECT: Only high-priority files analyzed")
        lines.append(f"   Coverage: {coverage_pct:.0f}% of candidate files")
        lines.append("")

    lines.append(f"Source Files Found:   {total_source}")
    lines.append(f"Existing Test Files:  {existing_tests}")
    lines.append(f"Files Analyzed:       {files_covered}")

    if existing_tests > 0:
        lines.append("")
        lines.append("Note: This report identifies gaps in untested files.")
        lines.append("Run 'pytest --co -q' for full test suite statistics.")
    lines.append("")


def _parse_xml_review(
    review: str,
) -> tuple[str, list[dict], list[dict], str]:
    """Parse XML review feedback into structured data.

    Returns:
        Tuple of (summary, findings, suggested_tests, coverage_improvement)

    """
    xml_summary = ""
    xml_findings = []
    xml_tests = []
    coverage_improvement = ""

    if not review or "<response>" not in review:
        return xml_summary, xml_findings, xml_tests, coverage_improvement

    # Extract summary
    summary_match = re.search(r"<summary>(.*?)</summary>", review, re.DOTALL)
    if summary_match:
        xml_summary = summary_match.group(1).strip()

    # Extract coverage improvement
    coverage_match = re.search(
        r"<coverage-improvement>(.*?)</coverage-improvement>",
        review,
        re.DOTALL,
    )
    if coverage_match:
        coverage_improvement = coverage_match.group(1).strip()

    # Extract findings
    for finding_match in re.finditer(
        r'<finding severity="(\w+)">(.*?)</finding>',
        review,
        re.DOTALL,
    ):
        severity = finding_match.group(1)
        finding_content = finding_match.group(2)

        title_match = re.search(r"<title>(.*?)</title>", finding_content, re.DOTALL)
        location_match = re.search(r"<location>(.*?)</location>", finding_content, re.DOTALL)
        fix_match = re.search(r"<fix>(.*?)</fix>", finding_content, re.DOTALL)

        xml_findings.append(
            {
                "severity": severity,
                "title": title_match.group(1).strip() if title_match else "Unknown",
                "location": location_match.group(1).strip() if location_match else "",
                "fix": fix_match.group(1).strip() if fix_match else "",
            },
        )

    # Extract suggested tests
    for test_match in re.finditer(r'<test target="([^"]+)">(.*?)</test>', review, re.DOTALL):
        target = test_match.group(1)
        test_content = test_match.group(2)

        type_match = re.search(r"<type>(.*?)</type>", test_content, re.DOTALL)
        desc_match = re.search(r"<description>(.*?)</description>", test_content, re.DOTALL)

        xml_tests.append(
            {
                "target": target,
                "type": type_match.group(1).strip() if type_match else "unit",
                "description": desc_match.group(1).strip() if desc_match else "",
            },
        )

    return xml_summary, xml_findings, xml_tests, coverage_improvement


def _format_quality_section(lines: list[str], xml_summary: str, coverage_improvement: str) -> None:
    """Format the quality assessment section."""
    if not xml_summary:
        return

    lines.append("-" * 60)
    lines.append("QUALITY ASSESSMENT")
    lines.append("-" * 60)

    # Word wrap the summary
    words = xml_summary.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= 58:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    lines.append("")

    if coverage_improvement:
        lines.append(f"\U0001f4c8 {coverage_improvement}")
        lines.append("")


def _format_findings_section(lines: list[str], xml_findings: list[dict]) -> None:
    """Format quality findings sorted by severity."""
    if not xml_findings:
        return

    lines.append("-" * 60)
    lines.append("QUALITY FINDINGS")
    lines.append("-" * 60)

    severity_emoji = {
        "high": "\U0001f534",
        "medium": "\U0001f7e0",
        "low": "\U0001f7e1",
        "info": "\U0001f535",
    }
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}

    sorted_findings = sorted(xml_findings, key=lambda f: severity_order.get(f["severity"], 4))

    for finding in sorted_findings:
        emoji = severity_emoji.get(finding["severity"], "\u26aa")
        lines.append(f"{emoji} [{finding['severity'].upper()}] {finding['title']}")
        if finding["location"]:
            lines.append(f"   Location: {finding['location']}")
        if finding["fix"]:
            fix_text = finding["fix"]
            if len(fix_text) > 70:
                fix_text = fix_text[:67] + "..."
            lines.append(f"   Fix: {fix_text}")
        lines.append("")


def _format_suggested_tests(lines: list[str], xml_tests: list[dict]) -> None:
    """Format suggested tests from XML review."""
    if not xml_tests:
        return

    lines.append("-" * 60)
    lines.append("SUGGESTED TESTS TO ADD")
    lines.append("-" * 60)

    for i, test in enumerate(xml_tests[:5], 1):  # Limit to 5
        lines.append(f"{i}. {test['target']} ({test['type']})")
        if test["description"]:
            desc = test["description"]
            if len(desc) > 55:
                desc = desc[:52] + "..."
            lines.append(f"   {desc}")
        lines.append("")

    if len(xml_tests) > 5:
        lines.append(f"   ... and {len(xml_tests) - 5} more suggested tests")
        lines.append("")


def _format_generated_tests(lines: list[str], input_data: dict, xml_findings: list[dict]) -> None:
    """Format generated tests breakdown by file."""
    generated_tests = input_data.get("generated_tests", [])
    if not generated_tests or xml_findings:
        return

    lines.append("-" * 60)
    lines.append("GENERATED TESTS BY FILE")
    lines.append("-" * 60)
    for test_file in generated_tests[:10]:  # Limit display
        source = test_file.get("source_file", "unknown")
        test_count = test_file.get("test_count", 0)
        if len(source) > 50:
            source = "..." + source[-47:]
        lines.append(f"  \U0001f4c1 {source}")
        lines.append(
            f"     \u2514\u2500 {test_count} test(s) \u2192 {test_file.get('test_file', 'test_*.py')}",
        )
    if len(generated_tests) > 10:
        lines.append(f"  ... and {len(generated_tests) - 10} more files")
    lines.append("")


def _format_written_files(lines: list[str], input_data: dict, total_tests: int) -> None:
    """Format the written files section or not-written notice."""
    written_files = input_data.get("written_files", [])
    if written_files:
        lines.append("-" * 60)
        lines.append("TESTS WRITTEN TO DISK")
        lines.append("-" * 60)
        for file_path in written_files[:10]:
            if len(file_path) > 55:
                file_path = "..." + file_path[-52:]
            lines.append(f"  \u2705 {file_path}")
        if len(written_files) > 10:
            lines.append(f"  ... and {len(written_files) - 10} more files")
        lines.append("")
        lines.append("  Run: pytest <file> to execute these tests")
        lines.append("")
    elif input_data.get("tests_written") is False and total_tests > 0:
        lines.append("-" * 60)
        lines.append("GENERATED TESTS (NOT WRITTEN)")
        lines.append("-" * 60)
        lines.append("  \u26a0\ufe0f  Tests were generated but not written to disk.")
        lines.append("  To write tests, run with: write_tests=True")
        lines.append("")


def _format_recommendations(
    lines: list[str],
    xml_findings: list[dict],
    xml_tests: list[dict],
    input_data: dict,
) -> None:
    """Format the next steps / recommendations section."""
    lines.append("-" * 60)
    lines.append("NEXT STEPS")
    lines.append("-" * 60)

    hotspot_count = input_data.get("hotspot_count", 0)
    untested_count = input_data.get("untested_count", 0)
    high_findings = sum(1 for f in xml_findings if f["severity"] == "high")
    medium_findings = sum(1 for f in xml_findings if f["severity"] == "medium")

    if high_findings > 0:
        lines.append(f"  \U0001f534 Address {high_findings} high-priority finding(s) first")

    if medium_findings > 0:
        lines.append(f"  \U0001f7e0 Review {medium_findings} medium-priority finding(s)")

    if xml_tests:
        lines.append(f"  \U0001f4dd Consider adding {len(xml_tests)} suggested test(s)")

    if hotspot_count > 0:
        lines.append(f"  \U0001f525 {hotspot_count} bug hotspot file(s) need priority testing")

    if untested_count > 0:
        lines.append(f"  \U0001f4c1 {untested_count} file(s) have no existing tests")

    if not any([high_findings, medium_findings, xml_tests, hotspot_count, untested_count]):
        lines.append("  \u2705 Test suite is in good shape!")

    lines.append("")
