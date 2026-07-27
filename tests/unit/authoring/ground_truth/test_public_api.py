"""Tests for the public-API ground-truth extractor."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from attune.authoring.ground_truth.public_api import extract_public_api


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(dedent(source), encoding="utf-8")
    return path


def test_extract_public_functions_with_signatures(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        def public_function(name: str, count: int = 1) -> bool:
            return True

        def _private():
            pass
        """,
    )

    result = extract_public_api([src])

    assert "def public_function(name: str, count: int = 1) -> bool" in result
    assert "_private" not in result


def test_extract_class_with_method_signatures(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "thing.py",
        """
        class Widget:
            def __init__(self, label: str) -> None:
                self.label = label

            def render(self) -> str:
                return self.label

            def _internal(self) -> None:
                pass
        """,
    )

    result = extract_public_api([src])

    assert "class Widget:" in result
    assert "def __init__(self, label: str) -> None" in result
    assert "def render(self) -> str" in result
    assert "_internal" not in result


def test_extract_respects_dunder_all(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        __all__ = ["public_thing", "another"]

        def public_thing():
            pass
        """,
    )

    result = extract_public_api([src])

    assert "__all__ = ['public_thing', 'another']" in result


def test_dynamic_dunder_all_is_ignored(tmp_path: Path) -> None:
    # A dynamically-computed __all__ (not a literal list/tuple) can't be
    # resolved statically, so it is skipped — no `__all__ = [...]` line is
    # emitted, but public symbols are still extracted.
    src = _write(
        tmp_path,
        "module.py",
        """
        __all__ = _compute_exports()

        def public_thing():
            pass
        """,
    )

    result = extract_public_api([src])

    assert "def public_thing()" in result
    assert "__all__ = [" not in result


def test_empty_source_list_returns_empty_string() -> None:
    assert extract_public_api([]) == ""


def test_syntax_error_skips_file(tmp_path: Path) -> None:
    bad = _write(tmp_path, "broken.py", "def oops(:\n")
    good = _write(
        tmp_path,
        "good.py",
        """
        def working() -> None:
            pass
        """,
    )

    result = extract_public_api([bad, good])

    assert "working" in result
    assert "broken" not in result


def test_non_python_files_skipped(tmp_path: Path) -> None:
    txt = tmp_path / "notes.txt"
    txt.write_text("def looks_like_python(): pass", encoding="utf-8")
    src = _write(
        tmp_path,
        "real.py",
        """
        def real_function() -> None:
            pass
        """,
    )

    result = extract_public_api([txt, src])

    assert "real_function" in result
    assert "looks_like_python" not in result


def test_module_label_includes_parent_dir(tmp_path: Path) -> None:
    sub = tmp_path / "feature_pkg"
    sub.mkdir()
    src = sub / "core.py"
    src.write_text("def thing(): pass\n", encoding="utf-8")

    result = extract_public_api([src])

    assert "# feature_pkg.core" in result
