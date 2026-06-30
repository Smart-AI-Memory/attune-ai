"""Unit tests for the new AST extractors in generator.py.

Covers:
- _extract_raises: exception classes raised by a function
- _extract_literal_values: Literal[...] allowed string values
- _extract_param_literals: per-param literal enumerations
- _is_dataclass: @dataclass decorator detection
- _extract_dataclass_fields: field name/type/default for dataclasses

These feed the polish LLM so the reference template can render
defaults, raises, enum members, and dataclass field tables — the
four gaps the v0.3.6 hallucination benchmark surfaced.
"""

from __future__ import annotations

import ast

from attune.authoring.source_introspection import (
    _extract_class_properties,
    _extract_dataclass_fields,
    _extract_literal_values,
    _extract_module_constant,
    _extract_param_literals,
    _extract_raises,
    _extract_return_data,
    _is_dataclass,
)

# -- return-data extraction -----------------------------------------


def _extract_return_data_from_src(src: str) -> object | None:
    tree = ast.parse(src)
    node = tree.body[0]
    assert isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    return _extract_return_data(node)


class TestExtractReturnData:
    def test_dict_literal(self) -> None:
        src = "def f():\n    return {'a': 1, 'b': 2}"
        assert _extract_return_data_from_src(src) == {"a": 1, "b": 2}

    def test_nested_dict_literal(self) -> None:
        src = (
            "def get_tools():\n"
            "    return {\n"
            "        'author_lookup': {\n"
            "            'description': 'Look up help',\n"
            "            'input_schema': {'query': 'str'},\n"
            "        },\n"
            "    }"
        )
        result = _extract_return_data_from_src(src)
        assert isinstance(result, dict)
        assert result["author_lookup"]["description"] == "Look up help"
        assert result["author_lookup"]["input_schema"] == {"query": "str"}

    def test_list_literal(self) -> None:
        src = "def f():\n    return [1, 2, 3]"
        assert _extract_return_data_from_src(src) == [1, 2, 3]

    def test_tuple_literal(self) -> None:
        src = "def f():\n    return ('a', 'b')"
        assert _extract_return_data_from_src(src) == ("a", "b")

    def test_constant_literal(self) -> None:
        src = "def f():\n    return 42"
        assert _extract_return_data_from_src(src) == 42

    def test_computed_return_none(self) -> None:
        """Function calls, name references, and operators are not
        literal — we deliberately don't surface dynamic returns."""
        src = "def f():\n    return some_func()"
        assert _extract_return_data_from_src(src) is None

    def test_name_reference_returns_none(self) -> None:
        src = "def f():\n    x = 1\n    return x"
        assert _extract_return_data_from_src(src) is None

    def test_dict_with_name_values_returns_none(self) -> None:
        """Dict with computed values fails literal_eval — safe."""
        src = "def f():\n    return {'a': some_var}"
        assert _extract_return_data_from_src(src) is None

    def test_no_return_statement(self) -> None:
        src = "def f():\n    pass"
        assert _extract_return_data_from_src(src) is None

    def test_nested_return_transparent_guard_clause_ignored(self) -> None:
        """Returns inside nested blocks (if/try/etc) are transparent.

        A factory like ``if legacy: return legacy_tools(); return {...}``
        should still surface the literal schema — the guard clause
        isn't what the reference is documenting.
        """
        src = "def f(x):\n    if x:\n        return None\n    return {'a': 1}"
        assert _extract_return_data_from_src(src) == {"a": 1}

    def test_top_level_non_literal_return_aborts(self) -> None:
        """A top-level non-literal return DOES abort extraction.

        If the first thing the function does is return a computed
        value, we don't want to surface a later literal — the
        function isn't a literal-data factory.
        """
        src = "def f():\n    return compute()"
        assert _extract_return_data_from_src(src) is None

    def test_bool_and_none_preserved(self) -> None:
        src = "def f():\n" "    return {'ok': True, 'err': False, 'val': None}"
        assert _extract_return_data_from_src(src) == {
            "ok": True,
            "err": False,
            "val": None,
        }


# -- class property extraction --------------------------------------


class TestExtractClassProperties:
    def test_single_property(self) -> None:
        src = (
            "class C:\n"
            "    @property\n"
            "    def count(self) -> int:\n"
            "        '''Count of items.'''\n"
            "        return 0"
        )
        assert _extract_class_properties(_cls(src)) == [
            {"name": "count", "return_type": "int", "doc": "Count of items."}
        ]

    def test_regular_method_not_property(self) -> None:
        src = "class C:\n" "    def do_it(self) -> int:\n" "        return 0"
        assert _extract_class_properties(_cls(src)) == []

    def test_underscore_property_skipped(self) -> None:
        src = "class C:\n" "    @property\n" "    def _private(self) -> int:\n" "        return 0"
        assert _extract_class_properties(_cls(src)) == []

    def test_multiple_properties(self) -> None:
        src = (
            "class C:\n"
            "    @property\n"
            "    def a(self) -> int:\n"
            "        return 0\n"
            "    @property\n"
            "    def b(self) -> str:\n"
            "        return ''\n"
            "    def regular(self) -> None:\n"
            "        return None"
        )
        props = _extract_class_properties(_cls(src))
        assert [p["name"] for p in props] == ["a", "b"]
        assert [p["return_type"] for p in props] == ["int", "str"]

    def test_property_without_return_type(self) -> None:
        src = "class C:\n" "    @property\n" "    def count(self):\n" "        return 0"
        props = _extract_class_properties(_cls(src))
        assert props == [{"name": "count", "return_type": "", "doc": ""}]


def _fn(src: str) -> ast.FunctionDef:
    tree = ast.parse(src)
    node = tree.body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def _cls(src: str) -> ast.ClassDef:
    tree = ast.parse(src)
    node = tree.body[0]
    assert isinstance(node, ast.ClassDef)
    return node


# -- raises ----------------------------------------------------------


class TestExtractRaises:
    def test_single_raise(self) -> None:
        assert _extract_raises(_fn("def f():\n    raise ValueError('x')")) == [
            {"class_name": "ValueError", "message": "x"}
        ]

    def test_bare_raise_is_ignored(self) -> None:
        src = "def f():\n    try:\n        pass\n    except Exception:\n        raise"
        assert _extract_raises(_fn(src)) == []

    def test_same_class_different_messages_preserved(self) -> None:
        """Functions that raise the same class with multiple distinct
        diagnostics (e.g. ``validate_file_path``) need every message
        surfaced — the rendered reference should list each diagnostic
        a caller might see. Exact duplicate pairs still collapse."""
        src = (
            "def f(x):\n"
            "    if x < 0:\n"
            "        raise ValueError('neg')\n"
            "    if x > 100:\n"
            "        raise ValueError('big')\n"
            "    if x == 0:\n"
            "        raise ValueError('neg')\n"  # dupe, should collapse
            "    raise TypeError('no')\n"
        )
        assert _extract_raises(_fn(src)) == [
            {"class_name": "ValueError", "message": "neg"},
            {"class_name": "ValueError", "message": "big"},
            {"class_name": "TypeError", "message": "no"},
        ]

    def test_dotted_exception_name(self) -> None:
        src = "def f():\n    raise subprocess.TimeoutExpired('cmd', 1)"
        assert _extract_raises(_fn(src)) == [
            {"class_name": "subprocess.TimeoutExpired", "message": "cmd"}
        ]

    def test_exception_without_call(self) -> None:
        src = "def f():\n    raise StopIteration"
        assert _extract_raises(_fn(src)) == [{"class_name": "StopIteration", "message": ""}]

    def test_call_without_args(self) -> None:
        src = "def f():\n    raise RuntimeError()"
        assert _extract_raises(_fn(src)) == [{"class_name": "RuntimeError", "message": ""}]

    def test_nested_function_raises_counted(self) -> None:
        src = "def f():\n" "    def inner():\n" "        raise RuntimeError('x')\n" "    inner()\n"
        assert _extract_raises(_fn(src)) == [{"class_name": "RuntimeError", "message": "x"}]

    def test_fstring_message_literal_prefix_preserved(self) -> None:
        """f-string messages keep the literal prefix and replace
        interpolated parts with ``{...}`` — so the diagnostic stem
        users grep for remains verifiable."""
        src = "def f(name):\n" "    raise ValueError(f'Invalid feature name: {name!r}')"
        assert _extract_raises(_fn(src)) == [
            {"class_name": "ValueError", "message": "Invalid feature name: {...}"}
        ]

    def test_fstring_only_interpolation_gives_placeholder(self) -> None:
        src = "def f(x):\n    raise ValueError(f'{x}')"
        assert _extract_raises(_fn(src)) == [{"class_name": "ValueError", "message": "{...}"}]

    def test_computed_message_returns_empty(self) -> None:
        """Non-literal first arg (name, call, concatenation) is
        unverifiable and surfaces as empty message."""
        src = "def f():\n    msg = 'x'\n    raise ValueError(msg)"
        assert _extract_raises(_fn(src)) == [{"class_name": "ValueError", "message": ""}]


# -- Literal values --------------------------------------------------


class TestExtractLiteralValues:
    def test_literal_tuple(self) -> None:
        ann = ast.parse("x: Literal['a', 'b', 'c']", mode="exec").body[0].annotation
        assert _extract_literal_values(ann) == ["a", "b", "c"]

    def test_literal_single_value(self) -> None:
        ann = ast.parse("x: Literal['only']", mode="exec").body[0].annotation
        assert _extract_literal_values(ann) == ["only"]

    def test_typing_qualified(self) -> None:
        ann = ast.parse("x: typing.Literal['a', 'b']", mode="exec").body[0].annotation
        assert _extract_literal_values(ann) == ["a", "b"]

    def test_non_literal_returns_none(self) -> None:
        ann = ast.parse("x: str", mode="exec").body[0].annotation
        assert _extract_literal_values(ann) is None

    def test_none_annotation_returns_none(self) -> None:
        assert _extract_literal_values(None) is None

    def test_int_literal_rejected(self) -> None:
        """Non-string literal members are intentionally skipped.

        Users ask about string enums (depths, doc_type, etc) —
        numeric literals are rare and muddy the rendered table.
        """
        ann = ast.parse("x: Literal[1, 2, 3]", mode="exec").body[0].annotation
        assert _extract_literal_values(ann) is None


class TestExtractParamLiterals:
    def test_mixed_params(self) -> None:
        node = _fn(
            "def f(depth: Literal['concept', 'task', 'reference'], name: str) -> None:\n    pass"
        )
        assert _extract_param_literals(node) == {
            "depth": ["concept", "task", "reference"],
        }

    def test_kwonly_literal(self) -> None:
        node = _fn("def f(*, mode: Literal['r', 'w']) -> None:\n    pass")
        assert _extract_param_literals(node) == {"mode": ["r", "w"]}

    def test_no_literal_params(self) -> None:
        node = _fn("def f(x: int, y: str) -> None:\n    pass")
        assert _extract_param_literals(node) == {}


# -- dataclass detection --------------------------------------------


class TestIsDataclass:
    def test_plain_decorator(self) -> None:
        assert _is_dataclass(_cls("@dataclass\nclass C:\n    x: int = 0")) is True

    def test_call_decorator(self) -> None:
        src = "@dataclass(frozen=True)\nclass C:\n    x: int = 0"
        assert _is_dataclass(_cls(src)) is True

    def test_qualified_decorator(self) -> None:
        src = "@dataclasses.dataclass\nclass C:\n    x: int = 0"
        assert _is_dataclass(_cls(src)) is True

    def test_qualified_call_decorator(self) -> None:
        src = "@dataclasses.dataclass(frozen=True)\nclass C:\n    x: int = 0"
        assert _is_dataclass(_cls(src)) is True

    def test_no_decorator(self) -> None:
        assert _is_dataclass(_cls("class C:\n    pass")) is False

    def test_unrelated_decorator(self) -> None:
        assert _is_dataclass(_cls("@property\nclass C:\n    pass")) is False


# -- dataclass fields ------------------------------------------------


class TestExtractDataclassFields:
    def test_fields_with_types_and_defaults(self) -> None:
        src = (
            "@dataclass\n"
            "class C:\n"
            "    name: str\n"
            "    count: int = 0\n"
            "    tags: list[str] = field(default_factory=list)\n"
        )
        assert _extract_dataclass_fields(_cls(src)) == [
            {"name": "name", "type": "str", "default": ""},
            {"name": "count", "type": "int", "default": "0"},
            {"name": "tags", "type": "list[str]", "default": "field(default_factory=list)"},
        ]

    def test_underscore_fields_skipped(self) -> None:
        src = "@dataclass\nclass C:\n    public: int = 0\n    _private: int = 0"
        assert _extract_dataclass_fields(_cls(src)) == [
            {"name": "public", "type": "int", "default": "0"},
        ]

    def test_empty_dataclass(self) -> None:
        src = "@dataclass\nclass C:\n    pass"
        assert _extract_dataclass_fields(_cls(src)) == []

    def test_plain_assignments_skipped(self) -> None:
        """Non-annotated class-level assignments are not fields."""
        src = "@dataclass\nclass C:\n    FOO = 1\n    bar: int = 0"
        assert _extract_dataclass_fields(_cls(src)) == [
            {"name": "bar", "type": "int", "default": "0"},
        ]


# -- module-level string constants ----------------------------------


def _module_const(src: str) -> dict | None:
    """Parse ``src`` as a single statement and extract its constant record."""
    tree = ast.parse(src)
    node = tree.body[0]
    assert isinstance(node, ast.Assign | ast.AnnAssign)
    return _extract_module_constant(node)


class TestExtractModuleConstant:
    def test_scalar_string(self) -> None:
        assert _module_const('STRICT_ENV_VAR = "ATTUNE_AUTHOR_STRICT_POLISH"') == {
            "name": "STRICT_ENV_VAR",
            "kind": "str",
            "values": ["ATTUNE_AUTHOR_STRICT_POLISH"],
        }

    def test_tuple_of_strings(self) -> None:
        assert _module_const('_UNSAFE = ("/", "\\\\", "..", "\\x00")') == {
            "name": "_UNSAFE",
            "kind": "tuple",
            "values": ["/", "\\", "..", "\x00"],
        }

    def test_list_of_strings(self) -> None:
        assert _module_const('NAMES = ["a", "b"]') == {
            "name": "NAMES",
            "kind": "list",
            "values": ["a", "b"],
        }

    def test_set_of_strings(self) -> None:
        assert _module_const('NAMES = {"a", "b"}') == {
            "name": "NAMES",
            "kind": "set",
            "values": ["a", "b"],
        }

    def test_frozenset_call_with_set_literal(self) -> None:
        assert _module_const('_FALSY = frozenset({"0", "false", "no", "off"})') == {
            "name": "_FALSY",
            "kind": "frozenset",
            "values": ["0", "false", "no", "off"],
        }

    def test_frozenset_call_with_list_literal(self) -> None:
        assert _module_const('F = frozenset(["a", "b"])') == {
            "name": "F",
            "kind": "frozenset",
            "values": ["a", "b"],
        }

    def test_set_call_with_tuple_literal(self) -> None:
        assert _module_const('S = set(("a", "b"))') == {
            "name": "S",
            "kind": "set",
            "values": ["a", "b"],
        }

    def test_annotated_assign(self) -> None:
        assert _module_const('NAMES: tuple[str, ...] = ("a", "b")') == {
            "name": "NAMES",
            "kind": "tuple",
            "values": ["a", "b"],
        }

    def test_int_constant_returns_none(self) -> None:
        """Non-string scalar constants are intentionally skipped."""
        assert _module_const("COUNT = 42") is None

    def test_mixed_type_collection_returns_none(self) -> None:
        """Mixed-type collections are skipped — we only surface string enums."""
        assert _module_const('MIX = ("a", 1, "b")') is None

    def test_tuple_unpacking_returns_none(self) -> None:
        """Multi-target assignment doesn't produce a constant record."""
        assert _module_const('A, B = "x", "y"') is None

    def test_name_reference_returns_none(self) -> None:
        """Assignments to non-literal expressions are skipped."""
        assert _module_const("FOO = bar") is None

    def test_annotated_assign_without_value_returns_none(self) -> None:
        """Bare type declarations (no RHS) aren't constants."""
        assert _module_const("FOO: str") is None

    def test_non_string_frozenset_returns_none(self) -> None:
        assert _module_const("NUMS = frozenset({1, 2, 3})") is None
