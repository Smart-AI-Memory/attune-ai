"""
Tests for SymbolExtractor / SymbolRecord.

Each test maps to a numbered acceptance criterion in
docs/specs/phase-1-semantic-freshness-spec.md.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from attune.authoring.symbols import SymbolExtractor


@pytest.fixture
def extractor() -> SymbolExtractor:
    return SymbolExtractor()


def write(tmp_path: Path, name: str, source: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


# ---------- Criterion 1: docstring invariance ----------


def test_docstring_only_edit_does_not_change_signature_hash(tmp_path, extractor):
    a = write(
        tmp_path,
        "a.py",
        '''
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}"
        ''',
    )
    b = write(
        tmp_path,
        "b.py",
        '''
        def greet(name: str) -> str:
            """Say a warm and friendly hello to the user."""
            return f"Hello, {name}"
        ''',
    )
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa is not None and sb is not None
    assert sa.signature_hash == sb.signature_hash


def test_class_docstring_edit_does_not_change_signature_hash(tmp_path, extractor):
    a = write(
        tmp_path,
        "a.py",
        '''
        class Greeter:
            """A polite greeter."""
            def greet(self, name: str) -> str:
                return f"Hello, {name}"
        ''',
    )
    b = write(
        tmp_path,
        "b.py",
        '''
        class Greeter:
            """A warm, friendly greeter that welcomes users."""
            def greet(self, name: str) -> str:
                return f"Hello, {name}"
        ''',
    )
    sa = extractor.extract_one(a, "Greeter")
    sb = extractor.extract_one(b, "Greeter")
    assert sa is not None and sb is not None
    assert sa.signature_hash == sb.signature_hash


# ---------- Criterion 2: signature sensitivity ----------


def test_added_parameter_changes_signature_hash(tmp_path, extractor):
    a = write(tmp_path, "a.py", "def greet(name: str) -> str:\n    return name\n")
    b = write(
        tmp_path,
        "b.py",
        "def greet(name: str, formal: bool = False) -> str:\n    return name\n",
    )
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash != sb.signature_hash


def test_changed_return_type_changes_signature_hash(tmp_path, extractor):
    a = write(tmp_path, "a.py", "def count() -> int:\n    return 1\n")
    b = write(tmp_path, "b.py", "def count() -> str:\n    return '1'\n")
    sa = extractor.extract_one(a, "count")
    sb = extractor.extract_one(b, "count")
    assert sa.signature_hash != sb.signature_hash


def test_changed_default_value_changes_signature_hash(tmp_path, extractor):
    a = write(tmp_path, "a.py", "def greet(name: str = 'world') -> str:\n    return name\n")
    b = write(tmp_path, "b.py", "def greet(name: str = 'friend') -> str:\n    return name\n")
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash != sb.signature_hash


def test_signature_change_does_not_affect_unrelated_template(tmp_path, extractor):
    """Criterion 2: signature change flags exactly the dependent — no others."""
    file = write(
        tmp_path,
        "x.py",
        """
        def greet(name: str) -> str:
            return name
        def farewell(name: str) -> str:
            return name
        """,
    )
    greet_v1 = extractor.extract_one(file, "greet")
    farewell_v1 = extractor.extract_one(file, "farewell")

    # Now change `greet` only
    file.write_text(
        textwrap.dedent(
            """
            def greet(name: str, formal: bool = False) -> str:
                return name
            def farewell(name: str) -> str:
                return name
            """
        ),
        encoding="utf-8",
    )
    greet_v2 = extractor.extract_one(file, "greet")
    farewell_v2 = extractor.extract_one(file, "farewell")

    assert greet_v1.signature_hash != greet_v2.signature_hash
    assert farewell_v1.signature_hash == farewell_v2.signature_hash


# ---------- Criterion 3: rename detection ----------


def test_renamed_function_disappears_under_old_qualname(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        "def greet_warmly(name: str) -> str:\n    return name\n",
    )
    assert extractor.extract_one(file, "greet") is None
    assert extractor.extract_one(file, "greet_warmly") is not None


def test_renamed_method_disappears_under_old_qualname(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        """
        class Greeter:
            def hello(self, name: str) -> str:
                return name
        """,
    )
    assert extractor.extract_one(file, "Greeter.greet") is None
    assert extractor.extract_one(file, "Greeter.hello") is not None


# ---------- Criterion 4: removal ----------


def test_removed_function_returns_none(tmp_path, extractor):
    file = write(tmp_path, "x.py", "def survivor() -> None:\n    pass\n")
    assert extractor.extract_one(file, "removed") is None


# ---------- Criterion 5: formatter invariance ----------


def test_whitespace_and_blank_lines_dont_change_signature_hash(tmp_path, extractor):
    a = write(
        tmp_path,
        "a.py",
        """
        def greet(name: str) -> str:
            return f"Hello, {name}"
        """,
    )
    b_source = (
        "\n\n"
        "def   greet(   name :  str  )  ->  str  :\n"
        "\n\n"
        '    return  f"Hello, {name}"\n'
        "\n\n"
    )
    b = tmp_path / "b.py"
    b.write_text(b_source, encoding="utf-8")
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash == sb.signature_hash


def test_import_reorder_does_not_affect_function_hashes(tmp_path, extractor):
    a = write(
        tmp_path,
        "a.py",
        """
        import os
        import sys

        def greet(name: str) -> str:
            return name
        """,
    )
    b = write(
        tmp_path,
        "b.py",
        """
        import sys
        import os

        def greet(name: str) -> str:
            return name
        """,
    )
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash == sb.signature_hash
    assert sa.body_hash == sb.body_hash


# ---------- Sanity coverage ----------


def test_method_qualname_is_class_dot_method(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        """
        class Greeter:
            def greet(self, name: str) -> str:
                return name
        """,
    )
    methods = [r for r in extractor.extract(file) if r.kind == "method"]
    assert len(methods) == 1
    assert methods[0].qualname == "Greeter.greet"


def test_class_record_captures_bases_decorators_and_attrs(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Config(BaseConfig, Mixin):
            name: str
            value: int = 0
            _private: int = 0
        """,
    )
    cls = extractor.extract_one(file, "Config")
    assert cls is not None
    assert cls.kind == "class"
    assert "BaseConfig" in cls.bases
    assert "Mixin" in cls.bases
    assert "dataclass" in cls.decorators
    assert "name" in cls.public_attrs
    assert "value" in cls.public_attrs
    assert "_private" not in cls.public_attrs


def test_async_function_signature_includes_async(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        "async def fetch(url: str) -> bytes:\n    return b''\n",
    )
    rec = extractor.extract_one(file, "fetch")
    assert rec is not None
    assert "async def" in rec.signature


def test_private_top_level_functions_are_skipped(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        """
        def public_one() -> None: pass
        def _private_one() -> None: pass
        """,
    )
    qualnames = [r.qualname for r in extractor.extract(file)]
    assert "public_one" in qualnames
    assert "_private_one" not in qualnames


def test_init_method_is_extracted(tmp_path, extractor):
    file = write(
        tmp_path,
        "x.py",
        """
        class Foo:
            def __init__(self, x: int) -> None:
                self.x = x
            def _helper(self) -> None: pass
        """,
    )
    qualnames = [r.qualname for r in extractor.extract(file)]
    assert "Foo.__init__" in qualnames
    assert "Foo._helper" not in qualnames


def test_body_changes_alter_body_hash_but_not_signature_hash(tmp_path, extractor):
    """body_hash is informational in Phase 1; spec says it must not affect staleness."""
    a = write(
        tmp_path,
        "a.py",
        """
        def greet(name: str) -> str:
            return f"Hello, {name}"
        """,
    )
    b = write(
        tmp_path,
        "b.py",
        """
        def greet(name: str) -> str:
            return f"Hi, {name}!"
        """,
    )
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash == sb.signature_hash
    assert sa.body_hash != sb.body_hash


def test_property_getter_and_setter_both_extracted(tmp_path, extractor):
    """Spec open question: properties share qualname; both records appear."""
    file = write(
        tmp_path,
        "x.py",
        """
        class Box:
            @property
            def size(self) -> int:
                return self._size

            @size.setter
            def size(self, v: int) -> None:
                self._size = v
        """,
    )
    methods = [r for r in extractor.extract(file) if r.qualname == "Box.size"]
    assert len(methods) == 2
    decorator_sets = {r.decorators for r in methods}
    assert ("property",) in decorator_sets
    assert ("size.setter",) in decorator_sets
    # The two records must have distinct signature hashes
    assert methods[0].signature_hash != methods[1].signature_hash


def test_added_decorator_changes_signature_hash(tmp_path, extractor):
    a = write(tmp_path, "a.py", "def greet() -> str:\n    return 'hi'\n")
    b = write(
        tmp_path,
        "b.py",
        """
        from functools import lru_cache

        @lru_cache
        def greet() -> str:
            return 'hi'
        """,
    )
    sa = extractor.extract_one(a, "greet")
    sb = extractor.extract_one(b, "greet")
    assert sa.signature_hash != sb.signature_hash
