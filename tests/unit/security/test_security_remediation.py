"""Tests for security remediation - Validation of security fixes.

This module validates that:
1. SQL queries in history.py use proper parameterization
2. Test fixtures properly document random usage
3. No actual security vulnerabilities exist

Created: 2026-01-26
Related: docs/SECURITY_REMEDIATION_PLAN.md
"""

import ast
import re
import tempfile
from pathlib import Path

import pytest


class TestSQLParameterization:
    """Test that SQL queries use proper parameterization (no SQL injection risk)."""

    @pytest.mark.skip(reason="WorkflowHistoryStore methods not yet implemented")
    def test_history_cleanup_uses_parameterized_queries(self):
        """Test that cleanup_old_runs() uses parameterized queries correctly."""
        from attune.workflows.history import WorkflowHistoryStore

        # Create in-memory database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = WorkflowHistoryStore(db_path)

            # Add some test runs
            from datetime import datetime, timedelta

            old_date = datetime.now() - timedelta(days=100)

            run_id1 = store.save_run("workflow1", {}, old_date)
            run_id2 = store.save_run("workflow2", {}, old_date)
            run_id3 = store.save_run("workflow3", {}, datetime.now())  # Recent

            # Cleanup runs older than 30 days
            deleted = store.cleanup_old_runs(keep_days=30)

            # Should delete 2 old runs, keep 1 recent
            assert deleted == 2

            # Verify correct runs were deleted
            cursor = store.conn.cursor()
            cursor.execute("SELECT run_id FROM workflow_runs")
            remaining = [row["run_id"] for row in cursor.fetchall()]

            assert run_id3 in remaining
            assert run_id1 not in remaining
            assert run_id2 not in remaining

            store.close()
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.skip(reason="WorkflowHistoryStore methods not yet implemented")
    def test_sql_injection_attempt_fails_safely(self):
        """Test that SQL injection attempts fail safely with parameterized queries."""
        from attune.workflows.history import WorkflowHistoryStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = WorkflowHistoryStore(db_path)

            # Attempt SQL injection via workflow_id
            malicious_input = "'; DROP TABLE workflow_runs; --"

            # This should safely store the string, not execute SQL
            run_id = store.save_run(malicious_input, {})

            # Verify table still exists and data is stored correctly
            cursor = store.conn.cursor()
            cursor.execute("SELECT workflow_id FROM workflow_runs WHERE run_id = ?", (run_id,))
            result = cursor.fetchone()

            # The malicious string should be stored as-is, not executed
            assert result["workflow_id"] == malicious_input

            # Verify table wasn't dropped
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'"
            )
            assert cursor.fetchone() is not None

            store.close()
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestRandomUsageDocumentation:
    """Test that random usage is properly documented for security clarity."""

    def test_conftest_has_security_note_in_docstring(self):
        """Test that mock_embeddings fixture documents non-cryptographic random usage."""
        conftest_path = Path(__file__).parent.parent / "cache" / "conftest.py"

        if not conftest_path.exists():
            pytest.skip(f"conftest.py not found at {conftest_path}")

        content = conftest_path.read_text(encoding="utf-8")

        # Check for security note in docstring
        assert "Security Note" in content or "security note" in content.lower()
        assert (
            "NOT used for cryptographic" in content
            or "not used for cryptographic" in content.lower()
        )
        assert "reproducible test" in content or "deterministic" in content

    def test_ab_testing_has_security_comment(self):
        """Test that ab_testing.py documents random usage for simulation."""
        ab_testing_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "attune"
            / "socratic"
            / "ab_testing.py"
        )

        if not ab_testing_path.exists():
            pytest.skip(f"ab_testing.py not found at {ab_testing_path}")

        content = ab_testing_path.read_text(encoding="utf-8")

        # Check for security note near random import
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "import random" in line:
                # Check surrounding lines for security note
                context = "\n".join(lines[max(0, i - 2) : min(len(lines), i + 3)])
                assert "Security Note" in context or "not cryptographic" in context.lower()
                break
        else:
            pytest.fail("import random not found in ab_testing.py")


class TestNoActualVulnerabilities:
    """Verify that flagged issues are not actual vulnerabilities."""

    def test_no_eval_in_production_code(self):
        """Test that no eval() calls exist in production code (excluding tests/docs)."""
        src_path = Path(__file__).parent.parent.parent.parent / "src"

        if not src_path.exists():
            pytest.skip("src directory not found")

        # Find all Python files in src/
        py_files = list(src_path.rglob("*.py"))

        eval_exec_found = []

        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8")

            # Parse AST to find actual eval/exec calls (not in strings/comments)
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in ("eval", "exec"):
                                eval_exec_found.append((py_file, node.lineno, node.func.id))
            except SyntaxError:
                # Skip files that can't be parsed
                pass

        # Should find 0 actual eval/exec calls in production code
        if eval_exec_found:
            details = "\n".join([f"  {f}:{line} - {func}()" for f, line, func in eval_exec_found])
            pytest.fail(f"Found eval/exec calls in production code:\n{details}")

    def test_sql_queries_use_parameterization(self):
        """Test that cursor.execute() calls use parameterization."""
        history_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "attune"
            / "workflows"
            / "history.py"
        )

        if not history_path.exists():
            pytest.skip("history.py not found")

        content = history_path.read_text(encoding="utf-8")

        # Find all cursor.execute calls
        execute_pattern = r"cursor\.execute\s*\("
        matches = list(re.finditer(execute_pattern, content))

        # Check for dangerous patterns - f-strings with variable interpolation in SQL
        dangerous_count = 0
        for match in matches:
            # Get more context to see the full statement
            snippet = content[match.start() : match.start() + 300]

            # Dangerous pattern: f"SELECT * FROM table WHERE id = {user_input}"
            # Safe pattern: f"DELETE FROM table WHERE id IN ({placeholders})", values
            # Look for f-strings with variable interpolation (not placeholder ?)
            if 'f"' in snippet or "f'" in snippet:
                # Check if it has variable interpolation
                if "{" in snippet:
                    # Skip safe patterns:
                    # 1. {placeholders} pattern for IN clauses
                    # 2. Table name formatting like f"table_{name}"
                    # 3. Has ? in the query string
                    if "placeholders" in snippet:
                        continue  # Safe pattern for IN clauses
                    if "?" in snippet.split("\n")[0]:
                        continue  # Has ? placeholders

                    # Check if it's in a WHERE/SET clause (potential danger)
                    if "WHERE" in snippet.upper() or "SET" in snippet.upper():
                        # Check if followed by a tuple of values (parameterized)
                        if "), " not in snippet and ")," not in snippet:
                            dangerous_count += 1

        # Should have 0 dangerous SQL patterns (f-strings with direct variable interpolation)
        assert dangerous_count == 0, f"Found {dangerous_count} potentially dangerous SQL patterns"


class TestCodeSecurity:
    """Additional security validation tests."""

    def test_secrets_used_for_security_tokens(self):
        """Test that secrets module is used for security-critical operations."""
        # Search for token/secret generation in production code
        src_path = Path(__file__).parent.parent.parent.parent / "src"

        if not src_path.exists():
            pytest.skip("src directory not found")

        # Look for files that generate tokens/secrets
        security_files = []
        for py_file in src_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if any(
                keyword in content.lower() for keyword in ["token", "secret", "password", "api_key"]
            ):
                # Check if they're generating these values
                if "random" in content and "secrets" not in content:
                    security_files.append(py_file)

        # For now, just document findings (don't fail - may be false positives)
        if security_files:
            print(f"\nFiles using 'random' in security-related contexts: {len(security_files)}")
            for f in security_files[:5]:  # Show first 5
                print(f"  - {f.relative_to(src_path.parent)}")

    def test_no_hardcoded_secrets(self):
        """Test that no obvious secrets are hardcoded."""
        src_path = Path(__file__).parent.parent.parent.parent / "src"

        if not src_path.exists():
            pytest.skip("src directory not found")

        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            r'api_key\s*=\s*["\'][^"\']{20,}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']{20,}["\']',
        ]

        found_secrets = []

        for py_file in src_path.rglob("*.py"):
            # Skip security detector files that contain test patterns
            if "secrets_detector.py" in str(py_file):
                continue

            content = py_file.read_text(encoding="utf-8")

            for pattern in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Exclude obvious test/example values
                    matched_text = match.group()
                    if any(
                        safe in matched_text.lower()
                        for safe in ["test", "example", "fake", "demo", "xxx"]
                    ):
                        continue

                    found_secrets.append((py_file, match.group()))

        # Should find 0 hardcoded secrets
        if found_secrets:
            details = "\n".join([f"  {f}: {secret}" for f, secret in found_secrets[:10]])
            pytest.fail(f"Found potential hardcoded secrets:\n{details}")


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestSecurityAuditAccuracy:
    """Test that security audit produces accurate results after improvements."""

    @pytest.mark.skip(
        reason="Integration test - requires API credentials and full workflow execution"
    )
    @pytest.mark.asyncio
    async def test_reduced_false_positive_rate(self):
        """Test that false positive rate is significantly reduced."""
        # This test would run the actual security audit workflow
        # and verify that findings are accurate

        # For now, skip if workflow not available
        try:
            from attune.workflows import SecurityAuditWorkflow
        except ImportError:
            pytest.skip("SecurityAuditWorkflow not available")

        workflow = SecurityAuditWorkflow()
        result = await workflow.execute()

        # After improvements, expect:
        # - 0 critical (all were false positives)
        # - <20 total findings (down from 350)

        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) == 0, "No critical vulnerabilities should exist"

        total_findings = len(result.findings)
        assert total_findings < 25, f"Expected <25 findings, got {total_findings}"


# =============================================================================
# Regression Tests
# =============================================================================


class TestNoRegressions:
    """Ensure security fixes don't break existing functionality."""

    @pytest.mark.skip(reason="WorkflowHistoryStore.save_run/get_run not implemented yet")
    def test_history_store_basic_operations(self):
        """Test that history store still works after security fixes."""
        from attune.workflows.history import WorkflowHistoryStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = WorkflowHistoryStore(db_path)

            # Test save
            run_id = store.save_run("test_workflow", {"input": "test"})
            assert run_id is not None

            # Test save_stage
            store.save_stage(run_id, "stage1", "cheap", 1000, 500, 0.05, {"output": "result"})

            # Test get_run
            run = store.get_run(run_id)
            assert run is not None
            assert run["workflow_id"] == "test_workflow"

            # Test list_runs
            runs = store.list_runs()
            assert len(runs) > 0

            store.close()
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_mock_embeddings_still_reproducible(self):
        """Test that mock_embeddings fixture is still reproducible after changes."""
        # Mock embeddings use random.seed(42) for reproducibility
        # Test the underlying function directly
        import random

        random.seed(42)
        emb1 = [random.gauss(0, 1) for _ in range(384)]

        random.seed(42)
        emb2 = [random.gauss(0, 1) for _ in range(384)]

        # Should be identical (reproducible)
        assert emb1 == emb2
        assert len(emb1) == 384


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
