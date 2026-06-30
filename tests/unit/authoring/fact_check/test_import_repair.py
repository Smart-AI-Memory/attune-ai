"""Tests for deterministic import-path repair.

Covers the bug class where the polish pass emits ``from pipeline
import …`` (directory basename) instead of the real package path
``from attune.pipeline import …``. The repair restores the canonical
dotted module deterministically, before the fact-check pass runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from attune.authoring.fact_check.import_repair import (
    _file_to_module,
    build_symbol_module_map,
    repair_imports,
)


@dataclass
class _FakeSourceInfo:
    """Minimal stand-in for the generator's ``_SourceInfo``."""

    public_functions: list[dict] = field(default_factory=list)
    public_classes: list[dict] = field(default_factory=list)
    module_constants: list[dict] = field(default_factory=list)


# --- _file_to_module -------------------------------------------------


def test_file_to_module_strips_src_and_extension() -> None:
    """``src/attune/spec/runner.py`` -> ``attune.spec.runner``."""
    assert _file_to_module("src/attune/spec/runner.py") == "attune.spec.runner"


def test_file_to_module_collapses_init() -> None:
    """A package ``__init__.py`` maps to the package itself."""
    assert _file_to_module("src/attune/pipeline/__init__.py") == "attune.pipeline"


def test_file_to_module_handles_windows_separators() -> None:
    """Backslash paths resolve the same as posix ones."""
    assert _file_to_module("src\\attune\\pipeline\\models.py") == "attune.pipeline.models"


# --- build_symbol_module_map ----------------------------------------


def test_build_map_prefers_reexporting_parent_package() -> None:
    """A symbol re-exported by its package uses the shallow path."""

    def importer(name: str) -> object:
        # attune.pipeline re-exports PipelineOrchestrator.
        return {"attune.pipeline": type("M", (), {"PipelineOrchestrator": 1})()}[name]

    info = _FakeSourceInfo(
        public_classes=[
            {"name": "PipelineOrchestrator", "file": "src/attune/pipeline/orchestrator.py"}
        ]
    )
    result = build_symbol_module_map(info, importer=importer)
    assert result == {"PipelineOrchestrator": "attune.pipeline"}


def test_build_map_falls_back_to_defining_module_when_not_reexported() -> None:
    """A symbol the package does NOT re-export keeps the submodule."""

    def importer(name: str) -> object:
        # attune.spec does NOT expose execute_with_approval.
        return type("M", (), {})()

    info = _FakeSourceInfo(
        public_functions=[{"name": "execute_with_approval", "file": "src/attune/spec/runner.py"}]
    )
    result = build_symbol_module_map(info, importer=importer)
    assert result == {"execute_with_approval": "attune.spec.runner"}


def test_build_map_degrades_to_defining_module_on_import_error() -> None:
    """Import failures degrade to the defining module, not a crash."""

    def importer(name: str) -> object:
        raise ImportError(name)

    info = _FakeSourceInfo(
        public_functions=[{"name": "read_spec", "file": "src/attune/pipeline/spec_reader.py"}]
    )
    result = build_symbol_module_map(info, importer=importer)
    assert result == {"read_spec": "attune.pipeline.spec_reader"}


def test_build_map_includes_constants_and_skips_incomplete_entries() -> None:
    """Module constants are mapped; entries missing name/file skip."""

    def importer(name: str) -> object:
        raise ImportError(name)

    info = _FakeSourceInfo(
        module_constants=[
            {"name": "ALLOWED_TOKENS", "file": "src/attune/spec/state.py"},
            {"file": "src/attune/spec/state.py"},  # no name -> skipped
        ]
    )
    result = build_symbol_module_map(info, importer=importer)
    assert result == {"ALLOWED_TOKENS": "attune.spec.state"}


# --- repair_imports --------------------------------------------------

_MAP = {
    "PipelineOrchestrator": "attune.pipeline",
    "read_spec": "attune.pipeline",
    "execute_with_approval": "attune.spec.runner",
    "find_resumable_plans": "attune.spec",
    "load_state": "attune.spec",
}


def test_repair_rewrites_bare_module_to_package() -> None:
    """A single bare-module import is rewritten to the real package."""
    content = "```python\nfrom pipeline import PipelineOrchestrator\n```\n"
    out = repair_imports(content, _MAP)
    assert "from attune.pipeline import PipelineOrchestrator" in out
    assert "from pipeline import" not in out


def test_repair_splits_group_across_resolved_modules() -> None:
    """Symbols resolving to different modules split into separate lines."""
    content = "```python\nfrom spec import execute_with_approval, find_resumable_plans\n```\n"
    out = repair_imports(content, _MAP)
    assert "from attune.spec.runner import execute_with_approval" in out
    assert "from attune.spec import find_resumable_plans" in out
    assert "from spec import" not in out


def test_repair_preserves_aliases_and_indentation() -> None:
    """``as`` aliases and leading indentation survive the rewrite."""
    content = "```python\n    from spec import load_state as ls\n```\n"
    out = repair_imports(content, _MAP)
    assert "    from attune.spec import load_state as ls" in out


def test_repair_leaves_unmapped_symbols_untouched() -> None:
    """Stdlib / unknown symbols are not rewritten (still fact-checkable)."""
    content = "```python\nfrom os import path\nimport json\n```\n"
    out = repair_imports(content, _MAP)
    assert out == content


def test_repair_is_idempotent_on_correct_imports() -> None:
    """An already-correct import is a no-op (no double-prefixing)."""
    content = "```python\nfrom attune.pipeline import PipelineOrchestrator\n```\n"
    out = repair_imports(content, _MAP)
    assert out == content


def test_repair_ignores_prose_and_non_python_fences() -> None:
    """Matching text outside python fences is left alone."""
    content = (
        "Use `from pipeline import PipelineOrchestrator` in prose.\n\n"
        "```text\nfrom pipeline import PipelineOrchestrator\n```\n"
    )
    out = repair_imports(content, _MAP)
    assert out == content


def test_repair_empty_map_is_noop() -> None:
    """An empty symbol map returns content unchanged."""
    content = "```python\nfrom pipeline import PipelineOrchestrator\n```\n"
    assert repair_imports(content, {}) == content


def test_repair_preserves_missing_trailing_newline() -> None:
    """Content without a trailing newline stays that way."""
    content = "```python\nfrom pipeline import PipelineOrchestrator\n```"
    out = repair_imports(content, _MAP)
    assert not out.endswith("\n")
    assert "from attune.pipeline import PipelineOrchestrator" in out


def test_repair_mixed_group_keeps_unmapped_under_original() -> None:
    """A group with one mapped + one unknown splits, unknown stays put."""
    content = "```python\nfrom spec import load_state, mystery_symbol\n```\n"
    out = repair_imports(content, _MAP)
    assert "from attune.spec import load_state" in out
    assert "from spec import mystery_symbol" in out
