"""Tests for SecurityFilterMixin in security_audit_filters.py.

Covers the untested branches in _is_safe_sql_parameterization() and
_is_safe_random_usage() to push coverage from 79.6% to 85%+.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.security_audit_filters import SecurityFilterMixin


class ConcreteFilter(SecurityFilterMixin):
    """Concrete class to instantiate the mixin for testing."""


@pytest.fixture
def f() -> ConcreteFilter:
    """Return a ConcreteFilter instance."""
    return ConcreteFilter()


# ---------------------------------------------------------------------------
# _is_safe_sql_parameterization
# ---------------------------------------------------------------------------


class TestIsSafeSqlParameterization:
    """Tests for _is_safe_sql_parameterization()."""

    def test_match_not_in_file_returns_false(self, f: ConcreteFilter) -> None:
        """When match_text and cursor.execute are absent, return False."""
        result = f._is_safe_sql_parameterization(
            line_content="SELECT * FROM users",
            match_text="totally_absent_text_xyz",
            file_content="def foo(): pass",
        )
        assert result is False

    def test_pattern1_regex_match_returns_true(self, f: ConcreteFilter) -> None:
        """f-string with {placeholders} and separate params → safe."""
        file_content = (
            'placeholders = ",".join("?" * len(ids))\n'
            'cursor.execute(f"SELECT * FROM t WHERE id IN ({placeholders})", ids)\n'
        )
        result = f._is_safe_sql_parameterization(
            line_content='cursor.execute(f"SELECT * WHERE id IN ({placeholders})", ids)',
            match_text="cursor.execute",
            file_content=file_content,
        )
        assert result is True

    def test_pattern1_placeholder_join_in_recent_lines(self, f: ConcreteFilter) -> None:
        """Placeholder built via join in recent lines + execute has params → safe."""
        file_content = (
            'placeholders = ",".join("?" * len(run_ids))\n'
            "result = cursor.execute(\n"
            '    f"DELETE FROM runs WHERE id IN ({placeholders})",\n'
            "    run_ids\n"
            ")\n"
        )
        result = f._is_safe_sql_parameterization(
            line_content='f"DELETE FROM runs WHERE id IN ({placeholders})"',
            match_text='f"DELETE FROM runs WHERE id IN ({placeholders})"',
            file_content=file_content,
        )
        assert result is True

    def test_pattern2_uppercase_constants_returns_true(self, f: ConcreteFilter) -> None:
        """f-string with only UPPERCASE vars (constants) → safe."""
        file_content = 'TABLE_NAME = "users"\ncursor.execute(f"SELECT * FROM {TABLE_NAME}")\n'
        result = f._is_safe_sql_parameterization(
            line_content='cursor.execute(f"SELECT * FROM {TABLE_NAME}")',
            match_text='cursor.execute(f"SELECT * FROM {TABLE_NAME}")',
            file_content=file_content,
        )
        assert result is True

    def test_pattern2_mixed_case_returns_false(self, f: ConcreteFilter) -> None:
        """f-string with lowercase user-controlled var → not safe."""
        file_content = 'cursor.execute(f"SELECT * FROM {user_input}")\n'
        result = f._is_safe_sql_parameterization(
            line_content='cursor.execute(f"SELECT * FROM {user_input}")',
            match_text='cursor.execute(f"SELECT * FROM {user_input}")',
            file_content=file_content,
        )
        assert result is False

    def test_pattern3_security_note_returns_true(self, f: ConcreteFilter) -> None:
        """Security note comment with 'safe' in recent lines → safe."""
        file_content = (
            "# security note: safe - column name is from a whitelist\n"
            'cursor.execute(f"SELECT {col} FROM t")\n'
        )
        result = f._is_safe_sql_parameterization(
            line_content='cursor.execute(f"SELECT {col} FROM t")',
            match_text='cursor.execute(f"SELECT {col} FROM t")',
            file_content=file_content,
        )
        assert result is True

    def test_cursor_execute_fallback_found(self, f: ConcreteFilter) -> None:
        """match_text absent but cursor.execute present → proceeds to context check."""
        file_content = "TABLE = 'users'\n" 'cursor.execute(f"SELECT * FROM {TABLE}")\n'
        result = f._is_safe_sql_parameterization(
            line_content='cursor.execute(f"SELECT * FROM {TABLE}")',
            match_text="nonexistent_match",
            file_content=file_content,
        )
        # TABLE is uppercase → pattern 2 triggers → True
        assert result is True


# ---------------------------------------------------------------------------
# _is_safe_random_usage
# ---------------------------------------------------------------------------


class TestIsSafeRandomUsage:
    """Tests for _is_safe_random_usage()."""

    def test_line_not_found_in_content_returns_false(self, f: ConcreteFilter) -> None:
        """When line_content isn't in file_content, line_index stays None → falls through."""
        result = f._is_safe_random_usage(
            line_content="x = random.randint(1, 10)",
            file_path="/src/util.py",
            file_content="completely different content\n",
        )
        assert result is False

    def test_safe_indicator_in_context_returns_true(self, f: ConcreteFilter) -> None:
        """'not cryptographic' comment near the line → True."""
        file_content = "# not cryptographic - just for simulation\nx = random.randint(1, 10)\n"
        result = f._is_safe_random_usage(
            line_content="x = random.randint(1, 10)",
            file_path="/src/util.py",
            file_content=file_content,
        )
        assert result is True

    def test_test_data_indicator_returns_true(self, f: ConcreteFilter) -> None:
        """'test data' comment nearby → True."""
        file_content = (
            "# test data - fixed values for reproducibility\nval = random.choice([1, 2, 3])\n"
        )
        result = f._is_safe_random_usage(
            line_content="val = random.choice([1, 2, 3])",
            file_path="/src/helpers.py",
            file_content=file_content,
        )
        assert result is True

    def test_random_seed_returns_true(self, f: ConcreteFilter) -> None:
        """random.seed() call → deterministic/reproducible, always safe."""
        result = f._is_safe_random_usage(
            line_content="random.seed(42)",
            file_path="/src/setup.py",
            file_content="random.seed(42)\n",
        )
        assert result is True

    def test_safe_context_in_file_path_returns_true(self, f: ConcreteFilter) -> None:
        """File path contains 'mock' → safe context."""
        result = f._is_safe_random_usage(
            line_content="x = random.randint(0, 100)",
            file_path="/src/mock_data.py",
            file_content="x = random.randint(0, 100)\n",
        )
        assert result is True

    def test_simulation_in_file_path_returns_true(self, f: ConcreteFilter) -> None:
        """File path contains 'simulation' → safe context."""
        result = f._is_safe_random_usage(
            line_content="delay = random.uniform(0.1, 0.5)",
            file_path="/benchmarks/simulation.py",
            file_content="delay = random.uniform(0.1, 0.5)\n",
        )
        assert result is True

    def test_test_file_without_crypto_returns_true(self, f: ConcreteFilter) -> None:
        """Test file with no crypto indicator in path → safe."""
        result = f._is_safe_random_usage(
            line_content="n = random.randint(1, 5)",
            file_path="/tests/test_utils.py",
            file_content="n = random.randint(1, 5)\n",
        )
        assert result is True

    def test_test_file_with_crypto_indicator_returns_false(self, f: ConcreteFilter) -> None:
        """Test file but path contains 'token' → not auto-safe."""
        result = f._is_safe_random_usage(
            line_content="t = random.randint(1, 100)",
            file_path="/tests/test_token_generator.py",
            file_content="t = random.randint(1, 100)\n",
        )
        assert result is False

    def test_non_test_non_safe_path_returns_false(self, f: ConcreteFilter) -> None:
        """Regular production file with no safe indicators → False."""
        result = f._is_safe_random_usage(
            line_content="key = random.randint(0, 2**32)",
            file_path="/src/auth/token_gen.py",
            file_content="key = random.randint(0, 2**32)\n",
        )
        assert result is False

    def test_fixed_seed_indicator_in_context(self, f: ConcreteFilter) -> None:
        """'fixed seed' comment nearby → True."""
        file_content = (
            "# fixed seed for reproducible benchmark results\n"
            "samples = [random.random() for _ in range(10)]\n"
        )
        result = f._is_safe_random_usage(
            line_content="samples = [random.random() for _ in range(10)]",
            file_path="/benchmarks/bench.py",
            file_content=file_content,
        )
        assert result is True
