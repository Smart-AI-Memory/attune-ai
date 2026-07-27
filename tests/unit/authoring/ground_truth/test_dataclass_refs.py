"""Tests for the dataclass-fields ground-truth extractor."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from attune.authoring.ground_truth.dataclass_refs import extract_dataclasses


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
