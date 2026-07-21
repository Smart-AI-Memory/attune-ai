"""Tests for attune.authoring.polish."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.authoring.polish import (
    _format_return_data,
    build_source_summary,
    polish_template,
)


class TestBuildSourceSummary:
    """Tests for build_source_summary()."""

    def test_builds_full_summary(self) -> None:
        """Test summary with classes, functions, and docstrings."""
        result = build_source_summary(
            public_classes=[
                {"name": "Foo", "doc": "Foo class", "file": "foo.py"},
            ],
            public_functions=[
                {"name": "bar", "doc": "bar function", "file": "bar.py"},
            ],
            module_docstrings=["First module.", "Second module."],
            file_count=5,
        )

        assert "Module purposes:" in result
        assert "First module." in result
        assert "Classes:" in result
        assert "Foo: Foo class" in result
        assert "Functions:" in result
        # v0.2.0: summary now uses em-dash separator and
        # omits parentheses when no signature is available
        assert "bar() — bar function" in result
        assert "Total source files: 5" in result

    def test_empty_inputs(self) -> None:
        """Test summary with no source info."""
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=0,
        )
        assert "Total source files: 0" in result

    def test_handles_missing_doc_field(self) -> None:
        """Test that missing 'doc' fields are handled."""
        result = build_source_summary(
            public_classes=[{"name": "Foo", "file": "f.py"}],
            public_functions=[{"name": "bar", "file": "b.py"}],
            module_docstrings=[],
            file_count=2,
        )
        assert "Foo" in result
        assert "bar" in result

    def test_truncates_long_lists(self) -> None:
        """Test that long lists are truncated."""
        many_classes = [{"name": f"Class{i}", "doc": "", "file": "f.py"} for i in range(20)]
        result = build_source_summary(
            public_classes=many_classes,
            public_functions=[],
            module_docstrings=[],
            file_count=20,
        )
        # Should only include first 10
        assert "Class0" in result
        assert "Class9" in result
        assert "Class15" not in result


class TestPolishTemplate:
    """Tests for polish_template()."""

    def test_returns_original_on_no_api_key_when_lenient(self) -> None:
        """Test fallback to original when API key missing.

        Polish is strict by default as of v0.3; this test
        opts into lenient mode explicitly via ``strict=False``
        so the missing-key path returns the raw content.
        """
        with patch.dict("os.environ", {}, clear=True):
            content = "# Test\nOriginal content."
            result = polish_template(content, "test", "summary", strict=False)
            assert result == content

    def test_returns_original_on_llm_error_when_lenient(self) -> None:
        """Test fallback to original when LLM call fails in lenient mode."""
        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "fake",  # pragma: allowlist secret
                "ATTUNE_MODEL_PREMIUM": "claude-sonnet-4-6",
            },
        ):
            with patch("attune.authoring.polish._call_llm") as mock_call:
                mock_call.side_effect = RuntimeError("API down")
                content = "# Test\nOriginal."
                result = polish_template(content, "test", "summary", strict=False)
                assert result == content

    def test_lenient_bypass_marks_yaml_frontmatter(self) -> None:
        # A polish bypass injects ``polish: skipped`` into the YAML
        # frontmatter so the regression is visible in PR diffs —
        # otherwise raw Jinja output is indistinguishable from a
        # normal generation. See attune-author#30.
        with patch.dict("os.environ", {}, clear=True):
            content = (
                "---\n"
                "type: reference\n"
                "feature: auth\n"
                "status: generated\n"
                "---\n"
                "\n# Auth reference\n"
            )
            result = polish_template(content, "auth", "summary", strict=False)
            assert "polish: skipped" in result
            # Original body is preserved verbatim — only the
            # frontmatter is annotated.
            assert "# Auth reference" in result

    def test_lenient_bypass_is_idempotent_when_already_marked(self) -> None:
        # Re-running polish on an already-marked file should not
        # double-write the marker.
        with patch.dict("os.environ", {}, clear=True):
            content = (
                "---\n"
                "type: reference\n"
                "status: generated\n"
                "polish: skipped\n"
                "---\n"
                "\n# Body\n"
            )
            result = polish_template(content, "auth", "summary", strict=False)
            assert result.count("polish: skipped") == 1

    def test_lenient_bypass_passes_through_non_frontmatter_content(self) -> None:
        # Content without YAML frontmatter (e.g., project-doc
        # templates with an HTML comment footer) is returned
        # unchanged — surfacing bypass there would need a
        # different mechanism.
        with patch.dict("os.environ", {}, clear=True):
            content = "# Test\nNo frontmatter here.\n"
            result = polish_template(content, "test", "summary", strict=False)
            assert result == content

    def test_returns_polished_on_success(self) -> None:
        """Test successful polish returns LLM output.

        polish_template now feeds the LLM response through
        _sanitize_output, which guarantees a single trailing
        newline. Sanitization is covered in detail in
        TestSanitizeOutput in test_polish_improvements.py.
        """
        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "fake",  # pragma: allowlist secret
                "ATTUNE_MODEL_PREMIUM": "claude-sonnet-4-6",
            },
        ):
            with patch("attune.authoring.polish._call_llm") as mock_call:
                mock_call.return_value = "# Test\nPolished content."
                result = polish_template("orig", "test", "summary")
                assert result == "# Test\nPolished content.\n"

    def test_call_llm_uses_anthropic_client(self) -> None:
        """Test that _call_llm builds and uses an Anthropic client."""
        from attune.authoring.polish import _call_llm

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="polished output")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "fake",  # pragma: allowlist secret
                "ATTUNE_MODEL_PREMIUM": "claude-sonnet-4-6",
            },
        ):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = _call_llm("content", "feature", "summary", "concept")

        assert result == "polished output"
        mock_client.messages.create.assert_called_once()

    def test_call_llm_raises_without_key(self) -> None:
        """Test that _call_llm raises without API key."""
        import pytest

        from attune.authoring.polish import _call_llm

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                _call_llm("content", "feature", "summary", "concept")


class TestStrictMode:
    """Tests for strict-mode behavior of polish_template().

    Strict mode is the production default. The conftest fixture
    ``_lenient_polish_by_default`` flips strict off for every test
    so that test runs without an API key don't accidentally hit
    the network — these tests opt back into strict explicitly to
    cover the strict-mode failure paths.
    """

    def test_strict_mode_raises_on_missing_api_key(self) -> None:
        import pytest

        from attune.authoring.polish import PolishError, polish_template

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(PolishError, match="auth"):
                polish_template("# Test", "auth", "summary", strict=True)

    def test_strict_mode_raises_on_llm_error(self) -> None:
        import pytest

        from attune.authoring.polish import PolishError, polish_template

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "fake"},  # pragma: allowlist secret
        ):
            with patch("attune.authoring.polish._call_llm") as mock_call:
                mock_call.side_effect = RuntimeError("API down")
                with pytest.raises(PolishError, match="API down"):
                    polish_template("# Test", "auth", "summary", strict=True)

    def test_env_var_strict_default_when_unset(self, monkeypatch) -> None:
        """When STRICT env var is unset, polish defaults to strict.

        Verifies that the conftest fixture's lenient default is the
        only thing keeping the test suite from raising — production
        code paths get strict by default.
        """
        import pytest

        from attune.authoring.polish import PolishError, polish_template

        monkeypatch.delenv("ATTUNE_AUTHOR_STRICT_POLISH", raising=False)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(PolishError):
                polish_template("# Test", "auth", "summary")


class TestFormatReturnData:
    """Tests for _format_return_data() — renders literal return
    values into the polish prompt.
    """

    def test_scalar_uses_repr(self) -> None:
        assert _format_return_data(42) == "42"
        assert _format_return_data("hi") == "'hi'"

    def test_empty_dict_and_list(self) -> None:
        assert _format_return_data({}) == "{}"
        assert _format_return_data([]) == "[]"

    def test_flat_dict_rendered_with_repr_values(self) -> None:
        out = _format_return_data({"a": 1, "b": "x"})
        assert "'a': 1" in out
        assert "'b': 'x'" in out

    def test_nested_dict_indents_children(self) -> None:
        out = _format_return_data({"outer": {"inner": 1}})
        lines = out.splitlines()
        assert lines[0] == "'outer':"
        # Nested dict is rendered one indent level deeper.
        assert "  'inner': 1" in lines[1]

    def test_list_of_scalars_uses_dash_prefix(self) -> None:
        out = _format_return_data([1, "x"])
        assert "- 1" in out
        assert "- 'x'" in out

    def test_list_of_dicts_renders_each_as_block(self) -> None:
        out = _format_return_data([{"k": 1}, {"k": 2}])
        # Each nested dict is introduced by a bare dash, then its
        # contents appear indented.
        assert out.count("\n-") >= 1
        assert "'k': 1" in out
        assert "'k': 2" in out

    def test_truncates_when_over_cap(self) -> None:
        """Large literals are truncated with a sentinel suffix so
        they can't dominate the polish prompt.
        """
        big = {f"k{i}": "x" * 100 for i in range(200)}
        out = _format_return_data(big)
        # Cap is 8000 chars; truncated output is at most cap +
        # suffix length.
        assert "... (truncated)" in out
        assert len(out) <= 8000 + len("\n... (truncated)")


class TestBuildSourceSummaryNewBranches:
    """Coverage for the v0.3.8/v0.3.9 additions to
    build_source_summary(): dataclass fields, properties, raises
    with messages, param literals, return_data, and module
    constants.
    """

    def test_renders_dataclass_fields(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            class_signatures=[
                {
                    "name": "Point",
                    "doc": "2D point.",
                    "methods": "",
                    "is_dataclass": True,
                    "dataclass_fields": [
                        {"name": "x", "type": "int", "default": "0"},
                        {"name": "y", "type": "int", "default": ""},
                    ],
                }
            ],
        )
        assert "Point [dataclass]" in result
        assert "field: x: int = 0" in result
        assert "field: y: int" in result

    def test_renders_properties(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            class_signatures=[
                {
                    "name": "Config",
                    "doc": "",
                    "methods": "",
                    "properties": [
                        {
                            "name": "debug",
                            "return_type": "bool",
                            "doc": "Debug flag.",
                        },
                        {"name": "name", "return_type": "", "doc": ""},
                    ],
                }
            ],
        )
        assert "property: debug -> bool  # Debug flag." in result
        assert "property: name" in result

    def test_renders_raises_with_and_without_message(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            function_signatures=[
                {
                    "name": "load",
                    "signature": "def load(path: str) -> None",
                    "doc": "Load a file.",
                    "raises": [
                        {"class_name": "FileNotFoundError", "message": "missing"},
                        {"class_name": "ValueError", "message": ""},
                        "RuntimeError",
                    ],
                }
            ],
        )
        assert "raises: FileNotFoundError — 'missing'" in result
        assert "raises: ValueError" in result
        assert "raises: RuntimeError" in result

    def test_renders_param_literals(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            function_signatures=[
                {
                    "name": "render",
                    "signature": "def render(mode: str) -> str",
                    "doc": "",
                    "param_literals": {"mode": ["html", "md"]},
                }
            ],
        )
        assert "mode allowed values: html, md" in result

    def test_renders_return_data(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            function_signatures=[
                {
                    "name": "schema",
                    "signature": "def schema() -> dict",
                    "doc": "",
                    "return_data": {"version": 1, "name": "attune"},
                }
            ],
        )
        assert "returns (literal data" in result
        assert "'version': 1" in result
        assert "'name': 'attune'" in result

    def test_renders_str_module_constant(self) -> None:
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            module_constants=[
                {"name": "DEFAULT_MODEL", "kind": "str", "values": ["sonnet"]},
            ],
        )
        assert "DEFAULT_MODEL (str) = 'sonnet'" in result

    def test_renders_non_str_module_constant(self) -> None:
        """Non-string constants (enum-like value sets) render as
        a brace-wrapped list of repr values.
        """
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
            module_constants=[
                {"name": "LEVELS", "kind": "int", "values": [1, 2, 3]},
            ],
        )
        assert "LEVELS (int) = {1, 2, 3}" in result
