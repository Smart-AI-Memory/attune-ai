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


def test_signature_features_posonly_vararg_kwonly_kwarg(tmp_path: Path) -> None:
    # Exercises the positional-only marker, *args, the keyword-only loop
    # (with and without a default), and **kwargs formatting in one pass.
    src = _write(
        tmp_path,
        "module.py",
        """
        def f_kitchen_sink(a, b, /, c, *args, d, e=2, **kwargs) -> None:
            pass
        """,
    )

    result = extract_public_api([src])

    assert "def f_kitchen_sink(a, b, /, c, *args, d, e = 2, **kwargs) -> None" in result


def test_ast_unparse_failure_falls_back_to_ellipsis(tmp_path: Path, monkeypatch) -> None:
    # Defensive fallback: if ast.unparse ever raises on a well-formed node
    # (annotation, default, or return type), each call site substitutes
    # "..." rather than propagating. Also exercises the bare "*" marker
    # for keyword-only args with no vararg.
    src = _write(
        tmp_path,
        "module.py",
        """
        def f(x: int = 1, *, y: str = "a") -> bool:
            return True
        """,
    )

    monkeypatch.setattr(
        "attune.authoring.ground_truth.public_api.ast.unparse",
        lambda node: (_ for _ in ()).throw(ValueError("boom")),
    )

    result = extract_public_api([src])

    assert "def f(x: ... = ..., *, y: ... = ...) -> ..." in result


def test_non_dunder_all_assignment_is_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        SOME_CONST = 5

        def public_thing():
            pass
        """,
    )

    result = extract_public_api([src])

    assert "def public_thing()" in result
    assert "__all__" not in result
    assert "SOME_CONST" not in result


def test_private_class_is_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        class _Hidden:
            def method(self):
                pass

        def marker():
            pass
        """,
    )

    result = extract_public_api([src])

    assert "marker" in result
    assert "_Hidden" not in result


def test_unreadable_file_is_skipped(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"  # never written -> read_text() raises OSError
    good = _write(
        tmp_path,
        "good.py",
        """
        def working() -> None:
            pass
        """,
    )

    result = extract_public_api([missing, good])

    assert "working" in result


def test_module_label_drops_src_parent_segment(tmp_path: Path) -> None:
    sub = tmp_path / "src"
    sub.mkdir()
    src = sub / "core.py"
    src.write_text("def thing(): pass\n", encoding="utf-8")

    result = extract_public_api([src])

    assert "# core" in result
    assert "# src.core" not in result


def test_class_with_no_public_methods_has_no_body(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        class Empty:
            pass
        """,
    )

    result = extract_public_api([src])

    assert "class Empty" in result
    assert "class Empty:\n" not in result


def test_file_with_no_public_symbols_is_skipped(tmp_path: Path) -> None:
    empty = _write(tmp_path, "constants.py", "TIMEOUT = 30\n")
    good = _write(
        tmp_path,
        "module.py",
        """
        def public_thing():
            pass
        """,
    )

    result = extract_public_api([empty, good])

    assert "public_thing" in result
    assert "constants" not in result
    assert "TIMEOUT" not in result
