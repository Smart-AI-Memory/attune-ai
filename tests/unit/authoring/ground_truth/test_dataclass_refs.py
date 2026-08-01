"""Tests for the dataclass-fields ground-truth extractor."""

from __future__ import annotations

import ast
from pathlib import Path
from textwrap import dedent

from attune.authoring.ground_truth.dataclass_refs import (
    _annotation_str,
    _default_str,
    _module_label,
    extract_dataclasses,
)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(dedent(source), encoding="utf-8")
    return path


def test_simple_dataclass_fields(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Config:
            host: str
            port: int = 8080
            debug: bool = False
        """,
    )

    result = extract_dataclasses([src])

    assert "class Config:" in result
    assert "host: str" in result
    assert "port: int = 8080" in result
    assert "debug: bool = False" in result


def test_dataclass_decorator_with_args(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Settings:
            name: str
        """,
    )

    result = extract_dataclasses([src])

    assert "class Settings:" in result
    assert "name: str" in result


def test_non_dataclass_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        class PlainOldClass:
            field: str = "not a dataclass"
        """,
    )

    result = extract_dataclasses([src])

    assert result == ""


def test_private_dataclass_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class _Internal:
            field: str
        """,
    )

    result = extract_dataclasses([src])

    assert result == ""


def test_private_fields_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Public:
            visible: str
            _hidden: str = ""
        """,
    )

    result = extract_dataclasses([src])

    assert "visible: str" in result
    assert "_hidden" not in result


def test_multiple_dataclasses_in_one_file(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class First:
            a: int

        @dataclass
        class Second:
            b: str
        """,
    )

    result = extract_dataclasses([src])

    assert "class First:" in result
    assert "class Second:" in result
    assert result.count("@dataclass") == 2


def test_dataclass_without_fields_skipped(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Empty:
            pass
        """,
    )

    result = extract_dataclasses([src])

    assert result == ""


def test_empty_source_list_returns_empty_string() -> None:
    assert extract_dataclasses([]) == ""


def test_decorator_unrecognized_expression_form_skipped(tmp_path: Path) -> None:
    """A decorator that is neither a Name, Call, nor Attribute is not a dataclass."""
    src = _write(
        tmp_path,
        "models.py",
        """
        @(lambda cls: cls)
        class NotADataclass:
            x: int
        """,
    )

    result = extract_dataclasses([src])

    assert result == ""


def test_decorator_attribute_call_form(tmp_path: Path) -> None:
    """``@module.dataclass(...)`` — Call whose func is an Attribute."""
    src = _write(
        tmp_path,
        "models.py",
        """
        import dataclasses

        @dataclasses.dataclass(frozen=True)
        class Frozen:
            value: int
        """,
    )

    result = extract_dataclasses([src])

    assert "class Frozen:" in result
    assert "value: int" in result


def test_decorator_bare_attribute_form(tmp_path: Path) -> None:
    """``@module.dataclass`` — a bare Attribute, not called."""
    src = _write(
        tmp_path,
        "models.py",
        """
        import dataclasses

        @dataclasses.dataclass
        class Bare:
            value: str
        """,
    )

    result = extract_dataclasses([src])

    assert "class Bare:" in result
    assert "value: str" in result


def test_non_name_annassign_target_skipped(tmp_path: Path) -> None:
    """An ``AnnAssign`` whose target is an Attribute (not a Name) is skipped."""
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Widget:
            obj.attr: int
            real: str
        """,
    )

    result = extract_dataclasses([src])

    assert "real: str" in result
    assert "obj.attr" not in result


def test_non_python_file_skipped(tmp_path: Path) -> None:
    txt = tmp_path / "notes.txt"
    txt.write_text("@dataclass\nclass Fake:\n    x: int\n", encoding="utf-8")
    src = _write(
        tmp_path,
        "real.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Real:
            x: int
        """,
    )

    result = extract_dataclasses([txt, src])

    assert "class Real:" in result
    assert "Fake" not in result


def test_unreadable_source_skipped(tmp_path: Path) -> None:
    """A path with a ``.py`` suffix that can't be read as text is skipped.

    A directory named ``weird.py`` passes the suffix check but raises
    ``IsADirectoryError`` (an ``OSError`` subclass) on ``read_text``.
    """
    bad = tmp_path / "weird.py"
    bad.mkdir()
    good = _write(
        tmp_path,
        "good.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Good:
            x: int
        """,
    )

    result = extract_dataclasses([bad, good])

    assert "class Good:" in result


def test_syntax_error_skips_file(tmp_path: Path) -> None:
    bad = _write(tmp_path, "broken.py", "class Oops(:\n")
    good = _write(
        tmp_path,
        "good.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Good:
            x: int
        """,
    )

    result = extract_dataclasses([bad, good])

    assert "class Good:" in result
    assert "Oops" not in result


def test_module_label_src_parent_omitted(tmp_path: Path) -> None:
    """A module directly under a ``src`` parent gets a bare label."""
    sub = tmp_path / "src"
    sub.mkdir()
    src = _write(
        sub,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Rooted:
            x: int
        """,
    )

    result = extract_dataclasses([src])

    assert "# models" in result
    assert "# src.models" not in result


def test_module_label_no_parent_dir() -> None:
    """A bare relative path (no directory component) gets a bare label.

    ``_module_label`` is a pure helper over ``Path`` metadata, so this
    is exercised directly rather than through a real filesystem layout.
    """
    assert _module_label(Path("bare.py")) == "bare"


def test_annotation_str_none_returns_placeholder() -> None:
    """Defensive branch: ``_annotation_str`` guards a missing annotation.

    Real ``AnnAssign`` nodes parsed from source always carry an
    annotation, so this path is unreachable via ``extract_dataclasses``
    and is exercised directly against the pure helper.
    """
    assert _annotation_str(None) == "..."


def test_annotation_str_unparse_failure_returns_placeholder() -> None:
    """Defensive branch: a malformed AST node that ``ast.unparse`` can't render.

    Real parsed source never produces a node like this; it models
    robustness against unparse failures rather than a reachable
    real-world input.
    """
    malformed = ast.BinOp(left=ast.Name(id="x", ctx=ast.Load()), op=ast.Add(), right=None)

    assert _annotation_str(malformed) == "..."


def test_default_str_unparse_failure_returns_placeholder() -> None:
    """Defensive branch: same as above, for ``_default_str``."""
    malformed = ast.BinOp(left=ast.Name(id="x", ctx=ast.Load()), op=ast.Add(), right=None)

    assert _default_str(malformed) == "..."
