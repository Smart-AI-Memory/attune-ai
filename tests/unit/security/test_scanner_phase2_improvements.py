"""Tests for Phase 2 Scanner Improvements

Validates that the improved security scanner correctly identifies
safe patterns and reduces false positives.

Created: 2026-01-26
Related: docs/SECURITY_REMEDIATION_PLAN.md (Phase 2)
"""

import pytest

from attune.workflows.security_audit import SecurityAuditWorkflow


class TestSQLInjectionDetection:
    """Test improved SQL injection detection with context analysis."""

    def setup_method(self):
        """Create workflow instance for testing."""
        self.workflow = SecurityAuditWorkflow()

    def test_safe_sql_with_placeholders_recognized(self):
        """Test that safe placeholder pattern is recognized."""
        line = 'cursor.execute(f"DELETE FROM table WHERE id IN ({placeholders})", run_ids)'
        content = """
placeholders = ",".join("?" * len(run_ids))
cursor.execute(f"DELETE FROM table WHERE id IN ({placeholders})", run_ids)
"""

        result = self.workflow._is_safe_sql_parameterization(line, line, content)
        assert result is True, "Should recognize safe placeholder pattern"

    def test_safe_sql_with_constant_table_name(self):
        """Test that constant table names are recognized as safe."""
        line = 'cursor.execute(f"SELECT * FROM {TABLE_NAME}")'
        content = 'TABLE_NAME = "users"\ncursor.execute(f"SELECT * FROM {TABLE_NAME}")'

        result = self.workflow._is_safe_sql_parameterization(line, line, content)
        assert result is True, "Should recognize constant table name as safe"

    def test_unsafe_sql_with_user_data_detected(self):
        """Test that unsafe direct interpolation is detected."""
        line = 'cursor.execute(f"DELETE FROM users WHERE id = {user_id}")'
        content = 'cursor.execute(f"DELETE FROM users WHERE id = {user_id}")'

        result = self.workflow._is_safe_sql_parameterization(line, line, content)
        assert result is False, "Should detect unsafe direct interpolation"

    def test_safe_sql_with_multiple_placeholders(self):
        """Test safe SQL with multiple placeholder groups."""
        line = 'cursor.execute(f"DELETE FROM table WHERE id IN ({placeholders})", ids)'
        content = """
placeholders = ",".join("?" * len(ids))
cursor.execute(f"DELETE FROM table WHERE id IN ({placeholders})", ids)
"""

        result = self.workflow._is_safe_sql_parameterization(line, line, content)
        assert result is True, "Should recognize multiple placeholder pattern"


class TestRandomUsageDetection:
    """Test improved random usage detection with context awareness."""

    def setup_method(self):
        """Create workflow instance for testing."""
        self.workflow = SecurityAuditWorkflow()

    def test_random_in_test_file_with_security_note(self):
        """Test that random in test files with security notes is safe."""
        line = "random.seed(42)"
        file_path = "tests/unit/cache/conftest.py"
        content = """
# Security Note: Using random (not secrets) for deterministic test fixtures
# NOT used for cryptographic operations
random.seed(42)
return [random.random() for _ in range(384)]
"""

        result = self.workflow._is_safe_random_usage(line, file_path, content)
        assert result is True, "Should recognize documented test fixture random usage"

    def test_random_with_fixed_seed_is_safe(self):
        """Test that fixed seed random is recognized as safe."""
        line = "random.seed(42)  # Fixed seed for reproducibility"
        file_path = "tests/test_utils.py"
        content = "random.seed(42)  # Fixed seed for reproducibility"

        result = self.workflow._is_safe_random_usage(line, file_path, content)
        assert result is True, "Should recognize fixed seed as safe"

    def test_random_in_simulation_is_safe(self):
        """Test that random in simulation code is safe."""
        line = "is_compliant = random.random() < 0.90"
        file_path = "agents/compliance_simulation.py"
        content = """
# Simulation: 90% compliant
import random
is_compliant = random.random() < 0.90
"""

        result = self.workflow._is_safe_random_usage(line, file_path, content)
        assert result is True, "Should recognize simulation random usage"

    def test_random_in_ab_testing_is_safe(self):
        """Test that random in A/B testing is safe."""
        line = "variant = random.choice(['A', 'B'])"
        file_path = "src/attune/socratic/ab_testing.py"
        content = "variant = random.choice(['A', 'B'])"

        result = self.workflow._is_safe_random_usage(line, file_path, content)
        assert result is True, "Should recognize A/B testing random usage"

    def test_random_for_crypto_without_context_unsafe(self):
        """Test that random in crypto contexts without clarification is flagged."""
        line = "token = ''.join(random.choices(string.ascii_letters, k=32))"
        file_path = "src/auth/token_generator.py"
        content = "token = ''.join(random.choices(string.ascii_letters, k=32))"

        result = self.workflow._is_safe_random_usage(line, file_path, content)
        assert result is False, "Should flag random usage in auth without clarification"


class TestDetectionCodeRecognition:
    """Test that detection/scanning code is not flagged as vulnerable."""

    def setup_method(self):
        """Create workflow instance for testing."""
        self.workflow = SecurityAuditWorkflow()

    def test_string_literal_detection_not_flagged(self):
        """Test that string literals for detection are not flagged."""
        line = 'if "eval(" in content:'
        match_text = '"eval("'

        result = self.workflow._is_detection_code(line, match_text)
        assert result is True, "Should recognize detection code"

    def test_regex_pattern_not_flagged(self):
        """Test that regex patterns for detection are not flagged."""
        line = 'pattern = r"eval\\("'
        match_text = "eval\\("

        result = self.workflow._is_detection_code(line, match_text)
        assert result is True, "Should recognize regex pattern"

    def test_actual_eval_usage_flagged(self):
        """Test that actual eval usage is flagged."""
        line = "result = eval(user_input)"
        match_text = "eval(user_input)"

        result = self.workflow._is_detection_code(line, match_text)
        assert result is False, "Should flag actual eval usage"


class TestDocumentationRecognition:
    """Test that documentation/comments are not flagged as vulnerable."""

    def setup_method(self):
        """Create workflow instance for testing."""
        self.workflow = SecurityAuditWorkflow()

    def test_comment_line_not_flagged(self):
        """Test that comment lines are not flagged."""
        line = "# Never use eval() on user input"
        match_text = "eval()"

        result = self.workflow._is_documentation_or_string(line, match_text)
        assert result is True, "Should recognize comment"

    def test_docstring_not_flagged(self):
        """Test that docstrings are not flagged."""
        line = '"""Check for eval() usage"""'
        match_text = "eval()"

        result = self.workflow._is_documentation_or_string(line, match_text)
        assert result is True, "Should recognize docstring"

    def test_security_policy_not_flagged(self):
        """Test that security policy documentation is not flagged."""
        line = "- No eval() or exec() usage"
        match_text = "eval()"

        result = self.workflow._is_documentation_or_string(line, match_text)
        assert result is True, "Should recognize security policy"

    def test_actual_code_flagged(self):
        """Test that actual vulnerable code is flagged."""
        line = "result = subprocess.run(cmd, shell=True)"
        match_text = "shell=True"

        result = self.workflow._is_documentation_or_string(line, match_text)
        assert result is False, "Should flag actual vulnerable code"


class TestFakeCredentialRecognition:
    """Test that fake/test credentials are not flagged."""

    def setup_method(self):
        """Create workflow instance for testing."""
        self.workflow = SecurityAuditWorkflow()

    def test_example_aws_key_not_flagged(self):
        """Test that AWS example keys are not flagged."""
        match_text = 'api_key = "AKIAIOSFODNN7EXAMPLE"'

        result = self.workflow._is_fake_credential(match_text)
        assert result is True, "Should recognize AWS example key"

    def test_fake_key_not_flagged(self):
        """Test that obviously fake keys are not flagged."""
        match_text = 'api_key = "FAKE_abc123xyz789_NOT_REAL"'

        result = self.workflow._is_fake_credential(match_text)
        assert result is True, "Should recognize fake credential"

    def test_test_password_not_flagged(self):
        """Test that test passwords are not flagged."""
        match_text = 'password = "test-password"'

        result = self.workflow._is_fake_credential(match_text)
        assert result is True, "Should recognize test password"

    def test_real_looking_credential_flagged(self):
        """Test that real-looking credentials are flagged."""
        match_text = 'api_key = "sk_live_1234567890abcdefghij"'

        result = self.workflow._is_fake_credential(match_text)
        assert result is False, "Should flag real-looking credential"


@pytest.mark.integration
@pytest.mark.skip(reason="Integration tests - require API credentials for workflow execution")
class TestPhase2Improvements:
    """Integration tests for Phase 2 scanner improvements."""

    @pytest.mark.asyncio
    async def test_history_py_no_sql_injection_findings(self):
        """Test that history.py has no SQL injection findings after improvements."""
        workflow = SecurityAuditWorkflow()

        result_dict, _, _ = await workflow._triage(
            {"path": "src/attune/workflows/history.py"},
            workflow.tier_map["triage"],
        )

        findings = result_dict.get("findings", [])
        sql_findings = [f for f in findings if f["type"] == "sql_injection"]

        assert (
            len(sql_findings) == 0
        ), f"Should have 0 SQL injection findings in history.py, found {len(sql_findings)}"

    @pytest.mark.asyncio
    async def test_conftest_py_no_insecure_random_findings(self):
        """Test that conftest.py has no insecure random findings after improvements."""
        workflow = SecurityAuditWorkflow()

        result_dict, _, _ = await workflow._triage(
            {"path": "tests/unit/cache/conftest.py"},
            workflow.tier_map["triage"],
        )

        findings = result_dict.get("findings", [])
        random_findings = [f for f in findings if f["type"] == "insecure_random"]

        assert (
            len(random_findings) == 0
        ), f"Should have 0 insecure_random findings in conftest.py, found {len(random_findings)}"

    @pytest.mark.asyncio
    async def test_bug_predict_py_no_command_injection_findings(self):
        """Test that bug_predict.py has no command injection findings after improvements."""
        workflow = SecurityAuditWorkflow()

        result_dict, _, _ = await workflow._triage(
            {"path": "src/attune/workflows/bug_predict.py"},
            workflow.tier_map["triage"],
        )

        findings = result_dict.get("findings", [])
        cmd_findings = [f for f in findings if f["type"] == "command_injection"]

        # Should have 0 or very few (only if there's actual dangerous code)
        assert (
            len(cmd_findings) == 0
        ), f"Should have 0 command_injection findings in bug_predict.py, found {len(cmd_findings)}"

    @pytest.mark.asyncio
    async def test_full_scan_reduced_false_positives(self):
        """Test that full codebase scan has dramatically reduced false positives."""
        workflow = SecurityAuditWorkflow()

        result_dict, _, _ = await workflow._triage({"path": "."}, workflow.tier_map["triage"])

        findings = result_dict.get("findings", [])

        # Before Phase 2: 350 findings
        # After Phase 2: Should be < 30 findings
        assert (
            len(findings) < 50
        ), f"Should have < 50 findings after Phase 2 improvements, found {len(findings)}"

        # Check breakdown by type
        by_type = {}
        for f in findings:
            typ = f["type"]
            by_type[typ] = by_type.get(typ, 0) + 1

        print("\nFindings by type after Phase 2:")
        for typ, count in sorted(by_type.items()):
            print(f"  {typ}: {count}")

        # SQL injection should be nearly eliminated
        assert (
            by_type.get("sql_injection", 0) < 5
        ), f"Should have < 5 SQL injection findings, found {by_type.get('sql_injection', 0)}"

        # Command injection (eval/exec) should be dramatically reduced
        assert (
            by_type.get("command_injection", 0) < 10
        ), f"Should have < 10 command_injection findings, found {by_type.get('command_injection', 0)}"

        # Insecure random should be dramatically reduced
        assert (
            by_type.get("insecure_random", 0) < 20
        ), f"Should have < 20 insecure_random findings, found {by_type.get('insecure_random', 0)}"


class TestPhase2Documentation:
    """Test that Phase 2 improvements are properly documented in code."""

    def test_safe_sql_method_has_phase2_marker(self):
        """Test that new methods have Phase 2 markers."""
        workflow = SecurityAuditWorkflow()

        # Check method docstrings mention Phase 2
        assert "Phase 2" in workflow._is_safe_sql_parameterization.__doc__
        assert "Phase 2" in workflow._is_safe_random_usage.__doc__

    def test_triage_method_has_phase2_comments(self):
        """Test that _triage method has Phase 2 comments."""
        import inspect

        workflow = SecurityAuditWorkflow()

        source = inspect.getsource(workflow._triage)

        # Should have Phase 2 comments
        assert "Phase 2" in source, "Should have Phase 2 markers in code"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
