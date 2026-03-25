"""Tests for framework detection module.

Tests cover Framework enum, from_string parsing, detect_installed_frameworks,
get_recommended_framework, and get_framework_info.
"""

import builtins
from unittest.mock import patch

import pytest

from attune.agent_factory.framework import (
    Framework,
    detect_installed_frameworks,
    get_framework_info,
    get_recommended_framework,
)

_real_import = builtins.__import__

OPTIONAL_FRAMEWORKS = frozenset(("langchain", "langgraph", "autogen", "haystack"))


def _make_import(allow: frozenset[str] = frozenset()):
    """Return an __import__ replacement that blocks optional frameworks.

    Args:
        allow: Set of framework module names to let through.
    """

    def _import(name, *args, **kwargs):
        if name in OPTIONAL_FRAMEWORKS:
            if name not in allow:
                raise ImportError(f"No module named '{name}'")
            return type(name, (), {})()
        return _real_import(name, *args, **kwargs)

    return _import


def _make_import_with_error(name_to_error: str, error: Exception):
    """Return an __import__ that raises a specific error for one framework."""

    def _import(name, *args, **kwargs):
        if name == name_to_error:
            raise error
        if name in OPTIONAL_FRAMEWORKS:
            raise ImportError(f"No module named '{name}'")
        return _real_import(name, *args, **kwargs)

    return _import


# ── Framework Enum ──────────────────────────────────────────────


@pytest.mark.unit
class TestFrameworkEnum:
    """Tests for Framework enum values."""

    def test_all_five_values_exist(self):
        """All 5 framework values are defined."""
        expected = {"NATIVE", "LANGCHAIN", "LANGGRAPH", "AUTOGEN", "HAYSTACK"}
        actual = {member.name for member in Framework}
        assert actual == expected

    def test_enum_values(self):
        """Each enum has the expected string value."""
        assert Framework.NATIVE.value == "native"
        assert Framework.LANGCHAIN.value == "langchain"
        assert Framework.LANGGRAPH.value == "langgraph"
        assert Framework.AUTOGEN.value == "autogen"
        assert Framework.HAYSTACK.value == "haystack"


# ── from_string ─────────────────────────────────────────────────


@pytest.mark.unit
class TestFromString:
    """Tests for Framework.from_string classmethod."""

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("native", Framework.NATIVE),
            ("empathy", Framework.NATIVE),
            ("langchain", Framework.LANGCHAIN),
            ("langgraph", Framework.LANGGRAPH),
            ("autogen", Framework.AUTOGEN),
            ("haystack", Framework.HAYSTACK),
        ],
    )
    def test_exact_match(self, name: str, expected: Framework):
        """Exact lowercase names resolve correctly."""
        assert Framework.from_string(name) == expected

    @pytest.mark.parametrize(
        "alias, expected",
        [
            ("lang_graph", Framework.LANGGRAPH),
            ("auto_gen", Framework.AUTOGEN),
        ],
    )
    def test_aliases(self, alias: str, expected: Framework):
        """Underscore and short aliases resolve correctly."""
        assert Framework.from_string(alias) == expected

    @pytest.mark.parametrize("name", ["NATIVE", "LangChain", "HayStack"])
    def test_case_insensitive(self, name: str):
        """from_string is case-insensitive."""
        result = Framework.from_string(name)
        assert isinstance(result, Framework)

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert Framework.from_string("  native  ") == Framework.NATIVE

    @pytest.mark.parametrize("name", ["unknown", "pytorch", "", "  ", "crewai"])
    def test_invalid_name_raises_value_error(self, name: str):
        """Invalid framework names raise ValueError."""
        with pytest.raises(ValueError, match="Unknown framework"):
            Framework.from_string(name)


# ── detect_installed_frameworks ─────────────────────────────────


@pytest.mark.unit
class TestDetectInstalledFrameworks:
    """Tests for detect_installed_frameworks."""

    def test_native_always_included(self):
        """NATIVE is always in the returned list."""
        with patch("builtins.__import__", side_effect=_make_import()):
            result = detect_installed_frameworks()
        assert Framework.NATIVE in result

    def test_no_optional_frameworks_installed(self):
        """When no optional frameworks are importable, only NATIVE is returned."""
        with patch("builtins.__import__", side_effect=_make_import()):
            result = detect_installed_frameworks()
        assert result == [Framework.NATIVE]

    def test_langchain_detected_when_installed(self):
        """LangChain is detected when importable."""
        with patch("builtins.__import__", side_effect=_make_import(allow={"langchain"})):
            result = detect_installed_frameworks()

        assert Framework.LANGCHAIN in result
        assert Framework.NATIVE in result

    def test_multiple_frameworks_detected(self):
        """Multiple frameworks detected when importable."""
        with patch(
            "builtins.__import__",
            side_effect=_make_import(allow={"langchain", "langgraph"}),
        ):
            result = detect_installed_frameworks()

        assert Framework.NATIVE in result
        assert Framework.LANGCHAIN in result
        assert Framework.LANGGRAPH in result
        assert len(result) == 3


# ── get_recommended_framework ───────────────────────────────────


@pytest.mark.unit
class TestGetRecommendedFramework:
    """Tests for get_recommended_framework."""

    def test_falls_back_to_native_when_nothing_installed(self):
        """Returns NATIVE when no optional frameworks are installed."""
        with patch("builtins.__import__", side_effect=_make_import()):
            result = get_recommended_framework("general")
        assert result == Framework.NATIVE

    def test_general_prefers_langgraph(self):
        """'general' use case prefers LANGGRAPH when installed."""
        with patch("builtins.__import__", side_effect=_make_import(allow={"langgraph"})):
            result = get_recommended_framework("general")
        assert result == Framework.LANGGRAPH

    def test_rag_prefers_haystack(self):
        """'rag' use case prefers HAYSTACK when installed."""
        with patch("builtins.__import__", side_effect=_make_import(allow={"haystack"})):
            result = get_recommended_framework("rag")
        assert result == Framework.HAYSTACK

    def test_multi_agent_prefers_autogen(self):
        """'multi_agent' use case prefers AUTOGEN when installed."""
        with patch("builtins.__import__", side_effect=_make_import(allow={"autogen"})):
            result = get_recommended_framework("multi_agent")
        assert result == Framework.AUTOGEN

    def test_conversational_prefers_autogen(self):
        """'conversational' use case prefers AUTOGEN when installed."""
        with patch("builtins.__import__", side_effect=_make_import(allow={"autogen"})):
            result = get_recommended_framework("conversational")
        assert result == Framework.AUTOGEN

    def test_unknown_use_case_uses_general_defaults(self):
        """Unknown use case falls back to 'general' recommendation order."""
        with patch("builtins.__import__", side_effect=_make_import()):
            result = get_recommended_framework("nonexistent_use_case")
        assert result == Framework.NATIVE

    @pytest.mark.parametrize(
        "use_case",
        ["general", "rag", "multi_agent", "code_analysis", "workflow", "conversational"],
    )
    def test_all_use_cases_return_native_when_nothing_installed(self, use_case: str):
        """Every known use case returns NATIVE as final fallback."""
        with patch("builtins.__import__", side_effect=_make_import()):
            result = get_recommended_framework(use_case)
        assert result == Framework.NATIVE


# ── get_framework_info ──────────────────────────────────────────


@pytest.mark.unit
class TestGetFrameworkInfo:
    """Tests for get_framework_info."""

    EXPECTED_KEYS = {"name", "description", "best_for", "install_command", "docs_url"}

    @pytest.mark.parametrize("framework", list(Framework))
    def test_returns_expected_keys(self, framework: Framework):
        """Every framework returns a dict with all expected keys."""
        info = get_framework_info(framework)
        assert set(info.keys()) == self.EXPECTED_KEYS

    @pytest.mark.parametrize("framework", list(Framework))
    def test_name_is_string(self, framework: Framework):
        """Name field is a non-empty string."""
        info = get_framework_info(framework)
        assert isinstance(info["name"], str)
        assert len(info["name"]) > 0

    @pytest.mark.parametrize("framework", list(Framework))
    def test_best_for_is_list(self, framework: Framework):
        """best_for field is a non-empty list."""
        info = get_framework_info(framework)
        assert isinstance(info["best_for"], list)
        assert len(info["best_for"]) > 0

    def test_native_has_no_install_command(self):
        """NATIVE framework has no install command (built-in)."""
        info = get_framework_info(Framework.NATIVE)
        assert info["install_command"] is None

    @pytest.mark.parametrize(
        "framework",
        [
            Framework.LANGCHAIN,
            Framework.LANGGRAPH,
            Framework.AUTOGEN,
            Framework.HAYSTACK,
        ],
    )
    def test_non_native_has_install_command(self, framework: Framework):
        """Non-native frameworks have a pip install command."""
        info = get_framework_info(framework)
        assert isinstance(info["install_command"], str)
        assert info["install_command"].startswith("pip install")

    @pytest.mark.parametrize("framework", list(Framework))
    def test_docs_url_is_string(self, framework: Framework):
        """docs_url is a non-empty string for every framework."""
        info = get_framework_info(framework)
        assert isinstance(info["docs_url"], str)
        assert info["docs_url"].startswith("https://")

    def test_unknown_framework_falls_back_to_native(self):
        """Unknown framework value returns NATIVE info (via dict.get fallback)."""
        native_info = get_framework_info(Framework.NATIVE)
        assert native_info["name"] == "Empathy Native"
