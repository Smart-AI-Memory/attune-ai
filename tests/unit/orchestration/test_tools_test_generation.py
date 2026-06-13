"""Tests for RealTestGenerator (LLM-powered test generation tool).

Covers the full tool without real API calls: LLM client init (success,
no-key, ImportError, generic-error fallbacks), the AST api-docs helper
(success + fallback), the basic template, the LLM generation path
(markdown-fence stripping + all-models-fail template fallback), and
generate_tests_for_file (template path, llm path, project-root fallback,
unreadable source). The Anthropic client is always mocked.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# Import pydantic.root_model before the SUT: importing the orchestration
# tools package transitively pulls in claude_agent_sdk -> mcp.types, whose
# RootModel[...] generic needs pydantic.root_model already registered in
# sys.modules. Under pytest collection that ordering isn't guaranteed, so
# we force it here (a no-op import everywhere else).
import pydantic.root_model  # noqa: F401
import pytest

from attune.orchestration.tools.test_generation import RealTestGenerator


def _gen(tmp_path, use_llm: bool = False) -> RealTestGenerator:
    return RealTestGenerator(project_root=str(tmp_path), use_llm=use_llm)


class TestInit:
    def test_creates_output_dir_and_flags(self, tmp_path):
        gen = RealTestGenerator(project_root=str(tmp_path), output_dir="tests/gen", use_llm=False)

        assert gen.output_dir == (tmp_path / "tests/gen")
        assert gen.output_dir.is_dir()
        assert gen.use_llm is False
        assert gen._llm is None

    def test_use_llm_triggers_initialize(self, tmp_path):
        with patch.object(RealTestGenerator, "_initialize_llm") as mock_init:
            RealTestGenerator(project_root=str(tmp_path), use_llm=True)
        mock_init.assert_called_once()


class TestInitializeLLM:
    def test_success_sets_client(self, tmp_path):
        gen = _gen(tmp_path)
        gen.api_key = "dummy-key"
        gen.use_llm = True
        client = MagicMock()
        anthropic_mod = MagicMock()
        anthropic_mod.Anthropic.return_value = client

        with patch.dict("sys.modules", {"anthropic": anthropic_mod}), patch("dotenv.load_dotenv"):
            gen._initialize_llm()

        assert gen._llm is client
        assert gen.use_llm is True
        anthropic_mod.Anthropic.assert_called_once_with(api_key="dummy-key")

    def test_no_api_key_disables_llm(self, tmp_path, monkeypatch):
        gen = _gen(tmp_path)
        gen.api_key = None
        gen.use_llm = True
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # present-but-empty -> falsy

        with patch("dotenv.load_dotenv"):
            gen._initialize_llm()

        assert gen.use_llm is False
        assert gen._llm is None

    def test_import_error_disables_llm(self, tmp_path):
        gen = _gen(tmp_path)
        gen.use_llm = True

        # A None entry forces ImportError on `from anthropic import Anthropic`.
        with patch.dict("sys.modules", {"anthropic": None}):
            gen._initialize_llm()

        assert gen.use_llm is False

    def test_generic_error_disables_llm(self, tmp_path):
        gen = _gen(tmp_path)
        gen.api_key = "dummy-key"
        gen.use_llm = True
        anthropic_mod = MagicMock()
        anthropic_mod.Anthropic.side_effect = RuntimeError("client boom")

        with patch.dict("sys.modules", {"anthropic": anthropic_mod}), patch("dotenv.load_dotenv"):
            gen._initialize_llm()

        assert gen.use_llm is False


class TestExtractApiDocs:
    def test_success_returns_string(self, tmp_path):
        gen = _gen(tmp_path)
        docs = gen._extract_api_docs("class Foo:\n    def bar(self):\n        pass\n")
        assert isinstance(docs, str)

    def test_failure_returns_fallback(self, tmp_path):
        gen = _gen(tmp_path)
        with patch.dict("sys.modules", {"ast_api_extractor": None}):
            docs = gen._extract_api_docs("class X: pass")
        assert "API extraction failed" in docs


class TestBasicTemplate:
    def test_contains_module_path_and_placeholder(self, tmp_path):
        gen = _gen(tmp_path)
        out = gen._generate_basic_test_template("src/attune/foo/bar.py", "x = 1\n", [10, 20, 30])

        assert "src.attune.foo.bar" in out  # dotted module path
        assert "src/attune/foo/bar.py" in out
        assert "test_placeholder_for_lines_10" in out
        assert "ATTUNE_ALLOW_PLACEHOLDER_TESTS" in out

    def test_empty_missing_lines_uses_zero(self, tmp_path):
        gen = _gen(tmp_path)
        out = gen._generate_basic_test_template("foo.py", "x = 1\n", [])
        assert "test_placeholder_for_lines_0" in out


class TestGenerateLLMTests:
    @staticmethod
    def _with_response(tmp_path, text: str) -> RealTestGenerator:
        gen = _gen(tmp_path)
        gen.use_llm = True
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        gen._llm = MagicMock()
        gen._llm.messages.create.return_value = resp
        return gen

    def test_strips_python_fence(self, tmp_path):
        gen = self._with_response(tmp_path, "```python\ndef test_x():\n    pass\n```")
        out = gen._generate_llm_tests("foo.py", "x = 1\n", [1])
        assert out == "def test_x():\n    pass"

    def test_strips_bare_fence(self, tmp_path):
        gen = self._with_response(tmp_path, "```\ndef test_y():\n    pass\n```")
        out = gen._generate_llm_tests("foo.py", "x = 1\n", [1])
        assert out == "def test_y():\n    pass"

    def test_plain_text_returned_unchanged(self, tmp_path):
        gen = self._with_response(tmp_path, "def test_z():\n    pass")
        out = gen._generate_llm_tests("foo.py", "x = 1\n", [1])
        assert out == "def test_z():\n    pass"

    def test_all_models_fail_falls_back_to_template(self, tmp_path):
        gen = _gen(tmp_path)
        gen.use_llm = True
        gen._llm = MagicMock()
        gen._llm.messages.create.side_effect = RuntimeError("model unavailable")

        out = gen._generate_llm_tests("foo.py", "x = 1\n", [1])

        # The RuntimeError is caught and the basic template is returned.
        assert "Auto-generated tests" in out


class TestGenerateTestsForFile:
    def test_template_path_writes_file(self, tmp_path):
        gen = _gen(tmp_path, use_llm=False)
        src = tmp_path / "mod.py"
        src.write_text("def f():\n    return 1\n", encoding="utf-8")

        out_path = gen.generate_tests_for_file(str(src), [1, 2])

        assert out_path.exists()
        assert out_path.name == "test_mod_generated.py"
        assert "Auto-generated tests" in out_path.read_text(encoding="utf-8")

    def test_project_root_fallback_for_relative_path(self, tmp_path):
        gen = _gen(tmp_path, use_llm=False)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1\n", encoding="utf-8")

        # Relative path doesn't exist from cwd -> resolved under project_root.
        out_path = gen.generate_tests_for_file("sub/mod.py", [1])

        assert out_path.exists()

    def test_llm_path_used_when_available(self, tmp_path):
        gen = _gen(tmp_path)
        gen.use_llm = True
        gen._llm = MagicMock()
        src = tmp_path / "mod.py"
        src.write_text("x = 1\n", encoding="utf-8")

        with patch.object(gen, "_generate_llm_tests", return_value="def test_a():\n    pass") as m:
            out_path = gen.generate_tests_for_file(str(src), [1])

        m.assert_called_once()
        assert out_path.read_text(encoding="utf-8") == "def test_a():\n    pass"

    def test_unreadable_source_raises_runtime_error(self, tmp_path):
        gen = _gen(tmp_path, use_llm=False)
        with pytest.raises(RuntimeError, match="Cannot read source file"):
            gen.generate_tests_for_file("nonexistent_anywhere.py", [1])
