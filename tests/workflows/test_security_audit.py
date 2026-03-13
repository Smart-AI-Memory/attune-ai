"""Tests for src/attune/workflows/security_audit.py

Comprehensive tests covering:
- SKIP_DIRECTORIES set
- DETECTION_PATTERNS list
- FAKE_CREDENTIAL_PATTERNS list
- SECURITY_EXAMPLE_PATHS list
- TEST_FILE_PATTERNS list
- SECURITY_PATTERNS dict
- SECURITY_STEPS dict
- SecurityAuditWorkflow class

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re

import pytest

from attune.workflows.security_audit import (
    DETECTION_PATTERNS,
    FAKE_CREDENTIAL_PATTERNS,
    SECURITY_EXAMPLE_PATHS,
    SECURITY_PATTERNS,
    SECURITY_STEPS,
    SKIP_DIRECTORIES,
    TEST_FILE_PATTERNS,
    SecurityAuditWorkflow,
    format_security_report,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_findings():
    """Sample security findings for testing."""
    return [
        {
            "type": "sql_injection",
            "file": "/path/to/file.py",
            "line": 42,
            "match": 'cursor.execute(f"SELECT * FROM {table}")',
            "severity": "critical",
            "owasp": "A03:2021 Injection",
            "is_test": False,
        },
        {
            "type": "xss",
            "file": "/path/to/component.tsx",
            "line": 10,
            "match": "innerHTML = userInput",
            "severity": "high",
            "owasp": "A03:2021 Injection",
            "is_test": False,
        },
    ]


# =============================================================================
# TestSkipDirectories - Test all directories in SKIP_DIRECTORIES set
# =============================================================================


class TestSkipDirectories:
    """Test the SKIP_DIRECTORIES set."""

    def test_skip_directories_is_set(self):
        """SKIP_DIRECTORIES should be a set."""
        assert isinstance(SKIP_DIRECTORIES, set)

    def test_skip_directories_not_empty(self):
        """SKIP_DIRECTORIES should contain entries."""
        assert len(SKIP_DIRECTORIES) > 0

    def test_contains_git(self):
        """Should skip .git directory."""
        assert ".git" in SKIP_DIRECTORIES

    def test_contains_node_modules(self):
        """Should skip node_modules directory."""
        assert "node_modules" in SKIP_DIRECTORIES

    def test_contains_pycache(self):
        """Should skip __pycache__ directory."""
        assert "__pycache__" in SKIP_DIRECTORIES

    def test_contains_venv(self):
        """Should skip venv directory."""
        assert "venv" in SKIP_DIRECTORIES

    def test_contains_dot_venv(self):
        """Should skip .venv directory."""
        assert ".venv" in SKIP_DIRECTORIES

    def test_contains_env(self):
        """Should skip env directory."""
        assert "env" in SKIP_DIRECTORIES

    def test_contains_next(self):
        """Should skip .next (Next.js build output)."""
        assert ".next" in SKIP_DIRECTORIES

    def test_contains_dist(self):
        """Should skip dist directory."""
        assert "dist" in SKIP_DIRECTORIES

    def test_contains_build(self):
        """Should skip build directory."""
        assert "build" in SKIP_DIRECTORIES

    def test_contains_tox(self):
        """Should skip .tox directory."""
        assert ".tox" in SKIP_DIRECTORIES

    def test_contains_site(self):
        """Should skip site (MkDocs output)."""
        assert "site" in SKIP_DIRECTORIES

    def test_contains_ebook_site(self):
        """Should skip ebook-site directory."""
        assert "ebook-site" in SKIP_DIRECTORIES

    def test_contains_website(self):
        """Should skip website directory."""
        assert "website" in SKIP_DIRECTORIES

    def test_contains_anthropic_cookbook(self):
        """Should skip anthropic-cookbook (third-party)."""
        assert "anthropic-cookbook" in SKIP_DIRECTORIES

    def test_contains_eggs(self):
        """Should skip .eggs directory."""
        assert ".eggs" in SKIP_DIRECTORIES

    def test_contains_egg_info(self):
        """Should skip *.egg-info pattern."""
        assert "*.egg-info" in SKIP_DIRECTORIES

    def test_contains_htmlcov(self):
        """Should skip htmlcov (coverage output)."""
        assert "htmlcov" in SKIP_DIRECTORIES

    def test_contains_htmlcov_logging(self):
        """Should skip htmlcov_logging directory."""
        assert "htmlcov_logging" in SKIP_DIRECTORIES

    def test_contains_coverage(self):
        """Should skip .coverage file."""
        assert ".coverage" in SKIP_DIRECTORIES

    def test_contains_vscode_extension(self):
        """Should skip vscode-extension directory."""
        assert "vscode-extension" in SKIP_DIRECTORIES

    def test_contains_vscode_memory_panel(self):
        """Should skip vscode-memory-panel directory."""
        assert "vscode-memory-panel" in SKIP_DIRECTORIES

    def test_all_entries_are_strings(self):
        """All entries should be strings."""
        for entry in SKIP_DIRECTORIES:
            assert isinstance(entry, str)


# =============================================================================
# TestDetectionPatterns - Test regex pattern validity
# =============================================================================


class TestDetectionPatterns:
    """Test the DETECTION_PATTERNS list."""

    def test_detection_patterns_is_list(self):
        """DETECTION_PATTERNS should be a list."""
        assert isinstance(DETECTION_PATTERNS, list)

    def test_detection_patterns_not_empty(self):
        """DETECTION_PATTERNS should contain entries."""
        assert len(DETECTION_PATTERNS) > 0

    def test_all_patterns_are_valid_regex(self):
        """All patterns should be valid regex."""
        for pattern in DETECTION_PATTERNS:
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Invalid regex pattern '{pattern}': {e}")

    def test_eval_string_pattern(self):
        """Should detect 'eval(' as string literal."""
        pattern = DETECTION_PATTERNS[0]
        compiled = re.compile(pattern)
        assert compiled.search('"eval("')
        assert compiled.search("'eval('")

    def test_exec_string_pattern(self):
        """Should detect 'exec(' as string literal."""
        pattern = DETECTION_PATTERNS[1]
        compiled = re.compile(pattern)
        assert compiled.search('"exec("')
        assert compiled.search("'exec('")

    def test_in_content_pattern(self):
        """Should detect 'in content' pattern detection."""
        pattern = DETECTION_PATTERNS[2]
        compiled = re.compile(pattern)
        assert compiled.search('if "eval(" in content:')

    def test_re_compile_pattern(self):
        """Should detect re.compile for detection code."""
        pattern = DETECTION_PATTERNS[3]
        compiled = re.compile(pattern)
        assert compiled.search("re.compile(pattern)")

    def test_finditer_pattern(self):
        """Should detect .finditer( for detection code."""
        pattern = DETECTION_PATTERNS[4]
        compiled = re.compile(pattern)
        assert compiled.search("regex.finditer(text)")

    def test_search_pattern(self):
        """Should detect .search( for detection code."""
        pattern = DETECTION_PATTERNS[5]
        compiled = re.compile(pattern)
        assert compiled.search("pattern.search(content)")


# =============================================================================
# TestFakeCredentialPatterns - Test patterns for test credentials
# =============================================================================


class TestFakeCredentialPatterns:
    """Test the FAKE_CREDENTIAL_PATTERNS list."""

    def test_fake_credential_patterns_is_list(self):
        """FAKE_CREDENTIAL_PATTERNS should be a list."""
        assert isinstance(FAKE_CREDENTIAL_PATTERNS, list)

    def test_fake_credential_patterns_not_empty(self):
        """FAKE_CREDENTIAL_PATTERNS should contain entries."""
        assert len(FAKE_CREDENTIAL_PATTERNS) > 0

    def test_all_patterns_are_valid_regex(self):
        """All patterns should be valid regex."""
        for pattern in FAKE_CREDENTIAL_PATTERNS:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Invalid regex pattern '{pattern}': {e}")

    def test_example_pattern(self):
        """Should match EXAMPLE in credentials."""
        pattern = r"EXAMPLE"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("AKIAIOSFODNN7EXAMPLE")

    def test_fake_pattern(self):
        """Should match FAKE in credentials."""
        pattern = r"FAKE"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("FAKE_API_KEY")

    def test_test_pattern(self):
        """Should match TEST in credentials."""
        pattern = r"TEST"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("TEST_SECRET")

    def test_your_key_here_pattern(self):
        """Should match your-*-here placeholder."""
        pattern = r"your-.*-here"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("your-api-key-here")

    def test_mock_pattern(self):
        """Should match mock credentials."""
        pattern = r"mock"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("mock_secret_key")

    def test_hardcoded_secret_pattern(self):
        """Should match literal 'hardcoded_secret' example text."""
        pattern = r'"hardcoded_secret"'
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('type: "hardcoded_secret"')

    def test_secret_pattern(self):
        """Should match generic 'secret' as value."""
        pattern = r'"secret"$'
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('password = "secret"')

    def test_pattern_constant_pattern(self):
        """Should match _PATTERN constants."""
        pattern = r"_PATTERN"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("SECRET_PATTERN")

    def test_example_constant_pattern(self):
        """Should match _EXAMPLE constants."""
        pattern = r"_EXAMPLE"
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("AWS_KEY_EXAMPLE")


# =============================================================================
# TestSecurityExamplePaths - Test security example paths
# =============================================================================


class TestSecurityExamplePaths:
    """Test the SECURITY_EXAMPLE_PATHS list."""

    def test_security_example_paths_is_list(self):
        """SECURITY_EXAMPLE_PATHS should be a list."""
        assert isinstance(SECURITY_EXAMPLE_PATHS, list)

    def test_security_example_paths_not_empty(self):
        """SECURITY_EXAMPLE_PATHS should contain entries."""
        assert len(SECURITY_EXAMPLE_PATHS) > 0

    def test_all_entries_are_strings(self):
        """All entries should be strings."""
        for entry in SECURITY_EXAMPLE_PATHS:
            assert isinstance(entry, str)

    def test_contains_owasp_patterns(self):
        """Should contain owasp_patterns.py."""
        assert "owasp_patterns.py" in SECURITY_EXAMPLE_PATHS

    def test_contains_vulnerability_scanner(self):
        """Should contain vulnerability_scanner.py."""
        assert "vulnerability_scanner.py" in SECURITY_EXAMPLE_PATHS

    def test_contains_test_security(self):
        """Should contain test_security prefix."""
        assert "test_security" in SECURITY_EXAMPLE_PATHS

    def test_contains_test_secrets(self):
        """Should contain test_secrets prefix."""
        assert "test_secrets" in SECURITY_EXAMPLE_PATHS

    def test_contains_test_owasp(self):
        """Should contain test_owasp prefix."""
        assert "test_owasp" in SECURITY_EXAMPLE_PATHS

    def test_contains_secrets_detector(self):
        """Should contain secrets_detector.py."""
        assert "secrets_detector.py" in SECURITY_EXAMPLE_PATHS

    def test_contains_pii_scrubber(self):
        """Should contain pii_scrubber.py."""
        assert "pii_scrubber.py" in SECURITY_EXAMPLE_PATHS

    def test_contains_secure_memdocs(self):
        """Should contain secure_memdocs."""
        assert "secure_memdocs" in SECURITY_EXAMPLE_PATHS

    def test_contains_security_path(self):
        """Should contain /security/ path."""
        assert "/security/" in SECURITY_EXAMPLE_PATHS


# =============================================================================
# TestTestFilePatterns - Test test file detection patterns
# =============================================================================


class TestTestFilePatterns:
    """Test the TEST_FILE_PATTERNS list."""

    def test_test_file_patterns_is_list(self):
        """TEST_FILE_PATTERNS should be a list."""
        assert isinstance(TEST_FILE_PATTERNS, list)

    def test_test_file_patterns_not_empty(self):
        """TEST_FILE_PATTERNS should contain entries."""
        assert len(TEST_FILE_PATTERNS) > 0

    def test_all_patterns_are_valid_regex(self):
        """All patterns should be valid regex."""
        for pattern in TEST_FILE_PATTERNS:
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Invalid regex pattern '{pattern}': {e}")

    def test_tests_directory_pattern(self):
        """Should match /tests/ directory."""
        pattern = r"/tests/"
        compiled = re.compile(pattern)
        assert compiled.search("/path/to/tests/test_file.py")

    def test_test_prefix_pattern(self):
        """Should match /test_ prefix."""
        pattern = r"/test_"
        compiled = re.compile(pattern)
        assert compiled.search("/path/to/test_something.py")

    def test_test_suffix_pattern(self):
        """Should match _test.py suffix."""
        pattern = r"_test\.py$"
        compiled = re.compile(pattern)
        assert compiled.search("something_test.py")
        assert not compiled.search("test_something.py")

    def test_demo_suffix_pattern(self):
        """Should match _demo.py suffix."""
        pattern = r"_demo\.py$"
        compiled = re.compile(pattern)
        assert compiled.search("security_demo.py")

    def test_example_suffix_pattern(self):
        """Should match _example.py suffix."""
        pattern = r"_example\.py$"
        compiled = re.compile(pattern)
        assert compiled.search("code_example.py")

    def test_examples_directory_pattern(self):
        """Should match /examples/ directory."""
        pattern = r"/examples/"
        compiled = re.compile(pattern)
        assert compiled.search("/path/to/examples/demo.py")

    def test_demo_directory_pattern(self):
        """Should match /demo path."""
        pattern = r"/demo"
        compiled = re.compile(pattern)
        assert compiled.search("/path/to/demo/file.py")

    def test_vscode_extension_pattern(self):
        """Should match coach/vscode-extension path."""
        pattern = r"coach/vscode-extension"
        compiled = re.compile(pattern)
        assert compiled.search("/coach/vscode-extension/src/file.ts")


# =============================================================================
# TestSecurityPatterns - Test security vulnerability patterns
# =============================================================================


class TestSecurityPatterns:
    """Test the SECURITY_PATTERNS dict."""

    def test_security_patterns_is_dict(self):
        """SECURITY_PATTERNS should be a dict."""
        assert isinstance(SECURITY_PATTERNS, dict)

    def test_security_patterns_not_empty(self):
        """SECURITY_PATTERNS should contain entries."""
        assert len(SECURITY_PATTERNS) > 0

    def test_contains_sql_injection(self):
        """Should contain sql_injection pattern."""
        assert "sql_injection" in SECURITY_PATTERNS

    def test_contains_xss(self):
        """Should contain xss pattern."""
        assert "xss" in SECURITY_PATTERNS

    def test_contains_hardcoded_secret(self):
        """Should contain hardcoded_secret pattern."""
        assert "hardcoded_secret" in SECURITY_PATTERNS

    def test_contains_insecure_random(self):
        """Should contain insecure_random pattern."""
        assert "insecure_random" in SECURITY_PATTERNS

    def test_contains_path_traversal(self):
        """Should contain path_traversal pattern."""
        assert "path_traversal" in SECURITY_PATTERNS

    def test_contains_command_injection(self):
        """Should contain command_injection pattern."""
        assert "command_injection" in SECURITY_PATTERNS

    def test_sql_injection_severity_is_critical(self):
        """SQL injection should be critical severity."""
        assert SECURITY_PATTERNS["sql_injection"]["severity"] == "critical"

    def test_xss_severity_is_high(self):
        """XSS should be high severity."""
        assert SECURITY_PATTERNS["xss"]["severity"] == "high"

    def test_hardcoded_secret_severity_is_critical(self):
        """Hardcoded secret should be critical severity."""
        assert SECURITY_PATTERNS["hardcoded_secret"]["severity"] == "critical"

    def test_insecure_random_severity_is_medium(self):
        """Insecure random should be medium severity."""
        assert SECURITY_PATTERNS["insecure_random"]["severity"] == "medium"

    def test_sql_injection_patterns_valid(self):
        """SQL injection patterns should be valid regex."""
        for pattern in SECURITY_PATTERNS["sql_injection"]["patterns"]:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Invalid SQL injection pattern '{pattern}': {e}")

    def test_xss_patterns_valid(self):
        """XSS patterns should be valid regex."""
        for pattern in SECURITY_PATTERNS["xss"]["patterns"]:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Invalid XSS pattern '{pattern}': {e}")


# =============================================================================
# TestSecurityPatternsStructure - Test severity, owasp, patterns keys
# =============================================================================


class TestSecurityPatternsStructure:
    """Test the structure of SECURITY_PATTERNS entries."""

    def test_all_patterns_have_severity(self):
        """All patterns should have severity key."""
        for name, info in SECURITY_PATTERNS.items():
            assert "severity" in info, f"{name} missing severity"

    def test_all_patterns_have_owasp(self):
        """All patterns should have owasp key."""
        for name, info in SECURITY_PATTERNS.items():
            assert "owasp" in info, f"{name} missing owasp"

    def test_all_patterns_have_patterns_list(self):
        """All patterns should have patterns list."""
        for name, info in SECURITY_PATTERNS.items():
            assert "patterns" in info, f"{name} missing patterns"
            assert isinstance(info["patterns"], list)

    def test_severity_values_are_valid(self):
        """Severity values should be valid."""
        valid_severities = {"critical", "high", "medium", "low"}
        for name, info in SECURITY_PATTERNS.items():
            assert (
                info["severity"] in valid_severities
            ), f"{name} has invalid severity: {info['severity']}"

    def test_owasp_format_is_valid(self):
        """OWASP references should follow expected format."""
        for name, info in SECURITY_PATTERNS.items():
            owasp = info["owasp"]
            # Should start with A (letter) and number
            assert owasp.startswith("A"), f"{name} OWASP doesn't start with A: {owasp}"

    def test_patterns_list_not_empty(self):
        """Each patterns list should not be empty."""
        for name, info in SECURITY_PATTERNS.items():
            assert len(info["patterns"]) > 0, f"{name} has empty patterns list"

    def test_all_pattern_regexes_compile(self):
        """All regex patterns should compile."""
        for name, info in SECURITY_PATTERNS.items():
            for pattern in info["patterns"]:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    pytest.fail(f"Invalid regex in {name}: '{pattern}': {e}")


# =============================================================================
# TestSecurityStepsConfig - Test step configuration
# =============================================================================


class TestSecurityStepsConfig:
    """Test the SECURITY_STEPS configuration dict."""

    def test_security_steps_is_dict(self):
        """SECURITY_STEPS should be a dict."""
        assert isinstance(SECURITY_STEPS, dict)

    def test_contains_remediate_step(self):
        """Should contain remediate step."""
        assert "remediate" in SECURITY_STEPS

    def test_remediate_step_has_name(self):
        """Remediate step should have name."""
        assert SECURITY_STEPS["remediate"].name == "remediate"

    def test_remediate_step_has_task_type(self):
        """Remediate step should have task_type."""
        assert SECURITY_STEPS["remediate"].task_type == "final_review"

    def test_remediate_step_has_tier_hint(self):
        """Remediate step should have premium tier hint."""
        assert SECURITY_STEPS["remediate"].tier_hint == "premium"

    def test_remediate_step_has_description(self):
        """Remediate step should have description."""
        assert len(SECURITY_STEPS["remediate"].description) > 0

    def test_remediate_step_has_max_tokens(self):
        """Remediate step should have max_tokens."""
        assert SECURITY_STEPS["remediate"].max_tokens == 3000


# =============================================================================
# TestWorkflowClassAttributes - Test name, stages, tier_map
# =============================================================================


class TestWorkflowClassAttributes:
    """Test SecurityAuditWorkflow class attributes."""

    def test_workflow_name(self):
        """Workflow should have correct name."""
        assert SecurityAuditWorkflow.name == "security-audit"


# =============================================================================
# TestPatternMatching - Test regex matching
# =============================================================================


class TestPatternMatching:
    """Test pattern matching functionality."""

    def test_sql_injection_pattern_matches_format_string(self):
        """SQL injection pattern should match format strings."""
        pattern = SECURITY_PATTERNS["sql_injection"]["patterns"][1]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('cursor.execute(f"SELECT * FROM {table}")')

    def test_sql_injection_pattern_matches_percent_format(self):
        """SQL injection pattern should match percent format."""
        pattern = SECURITY_PATTERNS["sql_injection"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('execute("SELECT * FROM users WHERE id = %s"')

    def test_xss_pattern_matches_innerhtml(self):
        """XSS pattern should match innerHTML."""
        pattern = SECURITY_PATTERNS["xss"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("element.innerHTML = userInput")

    def test_xss_pattern_matches_dangerously_set(self):
        """XSS pattern should match dangerouslySetInnerHTML."""
        pattern = SECURITY_PATTERNS["xss"]["patterns"][1]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("dangerouslySetInnerHTML={{__html: content}}")

    def test_hardcoded_secret_matches_password(self):
        """Hardcoded secret pattern should match password."""
        pattern = SECURITY_PATTERNS["hardcoded_secret"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('password = "mysecretpassword"')

    def test_hardcoded_secret_matches_api_key(self):
        """Hardcoded secret pattern should match api_key."""
        pattern = SECURITY_PATTERNS["hardcoded_secret"]["patterns"][1]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search('api_key = "sk-1234567890"')

    def test_insecure_random_matches_random_module(self):
        """Insecure random pattern should match random module."""
        pattern = SECURITY_PATTERNS["insecure_random"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("random.randint(0, 100)")

    def test_insecure_random_matches_math_random(self):
        """Insecure random pattern should match Math.random."""
        pattern = SECURITY_PATTERNS["insecure_random"]["patterns"][1]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("const token = Math.random()")

    def test_command_injection_matches_shell_true(self):
        """Command injection pattern should match shell=True."""
        pattern = SECURITY_PATTERNS["command_injection"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("subprocess.run(cmd, shell=True)")

    def test_command_injection_matches_os_system(self):
        """Command injection pattern should match os.system."""
        pattern = SECURITY_PATTERNS["command_injection"]["patterns"][1]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("os.system(command)")

    def test_command_injection_matches_eval(self):
        """Command injection pattern should match eval."""
        pattern = SECURITY_PATTERNS["command_injection"]["patterns"][2]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("result = eval(user_input)")

    def test_path_traversal_matches_open_concatenation(self):
        """Path traversal pattern should match open with concatenation."""
        pattern = SECURITY_PATTERNS["path_traversal"]["patterns"][0]
        compiled = re.compile(pattern, re.IGNORECASE)
        assert compiled.search("open(base_path + user_input)")


# =============================================================================
# TestIntegration - Test workflow scenarios
# =============================================================================


class TestIntegration:
    """Integration tests for workflow scenarios."""

    def test_format_security_report_generates_output(self, sample_findings):
        """format_security_report should generate formatted output."""
        output = {
            "assessment": {
                "risk_level": "high",
                "risk_score": 75,
                "severity_breakdown": {"critical": 1, "high": 1, "medium": 0, "low": 0},
            },
            "files_scanned": 100,
            "needs_review": sample_findings,
            "accepted_risks": [],
        }

        report = format_security_report(output)

        assert "SECURITY AUDIT REPORT" in report
        assert "Risk Level: HIGH" in report
        assert "Risk Score: 75/100" in report
        assert "sql_injection" in report

    def test_format_security_report_handles_empty_findings(self):
        """format_security_report should handle empty findings."""
        output = {
            "assessment": {
                "risk_level": "low",
                "risk_score": 0,
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            },
            "files_scanned": 50,
            "needs_review": [],
            "accepted_risks": [],
        }

        report = format_security_report(output)

        assert "All clear" in report
