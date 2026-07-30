"""Tests for attune.authoring.generator's AST extractors and scaffold metadata.

Covers the pure source-introspection helpers (exception/raise
extraction, Literal and constant surfacing, signature formatting)
and the scaffold-hash skip machinery (hash computation, injection,
read-back, in-place metadata refresh). All tests are keyless and
LLM-free: the helpers under test are deterministic functions over
ASTs and files.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

from attune.authoring.generator import (
    GenerationResult,
    _exception_name,
    _extract_class_properties,
    _extract_dataclass_fields,
    _extract_literal_values,
    _extract_module_constant,
    _extract_param_literals,
    _extract_raises,
    _extract_return_data,
    _extract_source_info,
    _faithfulness_telemetry,
    _format_class_methods,
    _format_function_signature,
    _has_property_decorator,
    _inject_scaffold_hash,
    _is_dataclass,
    _project_doc_output_path,
    _raise_message,
    _read_scaffold_hash,
    _refresh_metadata_in_place,
    _split_signature,
    _string_collection_values,
    _unparse_annotation,
    compute_scaffold_hash,
    generate_feature_templates,
    reset_faithfulness_telemetry,
)
from attune.authoring.manifest import Feature


def _parse_func(src: str) -> ast.FunctionDef:
    node = ast.parse(textwrap.dedent(src)).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def _parse_class(src: str) -> ast.ClassDef:
    node = ast.parse(textwrap.dedent(src)).body[0]
    assert isinstance(node, ast.ClassDef)
    return node


def _first_expr(src: str) -> ast.expr:
    node = ast.parse(textwrap.dedent(src)).body[0]
    assert isinstance(node, ast.Expr)
    return node.value


class TestExceptionName:
    def test_plain_name(self) -> None:
        assert _exception_name(_first_expr("ValueError")) == "ValueError"

    def test_call_unwraps_to_name(self) -> None:
        assert _exception_name(_first_expr('ValueError("boom")')) == "ValueError"

    def test_dotted_attribute(self) -> None:
        assert _exception_name(_first_expr("errors.config.BadName")) == "errors.config.BadName"

    def test_call_on_attribute(self) -> None:
        assert _exception_name(_first_expr('pkg.Err("x")')) == "pkg.Err"

    def test_attribute_chain_not_rooted_in_name(self) -> None:
        # ``a().b`` — the chain bottoms out in a Call, not a Name.
        assert _exception_name(_first_expr("a().b")) is None

    def test_unsupported_expression(self) -> None:
        assert _exception_name(_first_expr("(lambda: 1)()")) is None


class TestRaiseMessage:
    def test_string_literal(self) -> None:
        assert _raise_message(_first_expr('ValueError("bad input")')) == "bad input"

    def test_fstring_preserves_literal_stem(self) -> None:
        msg = _raise_message(_first_expr('ValueError(f"Invalid name: {name!r}")'))
        assert msg == "Invalid name: {...}"

    def test_no_args(self) -> None:
        assert _raise_message(_first_expr("ValueError()")) == ""

    def test_not_a_call(self) -> None:
        assert _raise_message(_first_expr("ValueError")) == ""

    def test_computed_first_arg(self) -> None:
        assert _raise_message(_first_expr("ValueError(msg)")) == ""


class TestExtractRaises:
    def test_distinct_messages_in_source_order(self) -> None:
        node = _parse_func(
            """
            def f(x):
                if not x:
                    raise ValueError("empty")
                raise errors.CustomError(f"bad: {x!r}")
            """
        )
        assert _extract_raises(node) == [
            {"class_name": "ValueError", "message": "empty"},
            {"class_name": "errors.CustomError", "message": "bad: {...}"},
        ]

    def test_exact_duplicate_pairs_collapse(self) -> None:
        node = _parse_func(
            """
            def f(x):
                if x:
                    raise ValueError("same")
                raise ValueError("same")
            """
        )
        assert _extract_raises(node) == [{"class_name": "ValueError", "message": "same"}]

    def test_bare_reraise_ignored(self) -> None:
        node = _parse_func(
            """
            def f():
                try:
                    g()
                except KeyError:
                    raise
            """
        )
        assert _extract_raises(node) == []


class TestExtractLiteralValues:
    def test_bare_literal(self) -> None:
        node = _parse_func('def f(m: Literal["a", "b"]): ...')
        assert _extract_literal_values(node.args.args[0].annotation) == ["a", "b"]

    def test_qualified_literal_single_value(self) -> None:
        node = _parse_func('def f(m: typing.Literal["only"]): ...')
        assert _extract_literal_values(node.args.args[0].annotation) == ["only"]

    def test_non_literal_subscript(self) -> None:
        node = _parse_func("def f(m: list[str]): ...")
        assert _extract_literal_values(node.args.args[0].annotation) is None

    def test_non_string_member(self) -> None:
        node = _parse_func('def f(m: Literal["a", 1]): ...')
        assert _extract_literal_values(node.args.args[0].annotation) is None

    def test_none_annotation(self) -> None:
        assert _extract_literal_values(None) is None

    def test_plain_name_annotation(self) -> None:
        node = _parse_func("def f(m: str): ...")
        assert _extract_literal_values(node.args.args[0].annotation) is None


class TestExtractParamLiterals:
    def test_collects_across_arg_kinds(self) -> None:
        node = _parse_func(
            """
            def f(pos: Literal["p"], /, mode: Literal["a", "b"], *,
                  level: typing.Literal["x"], plain: str = "y"): ...
            """
        )
        assert _extract_param_literals(node) == {
            "pos": ["p"],
            "mode": ["a", "b"],
            "level": ["x"],
        }

    def test_empty_when_no_literals(self) -> None:
        node = _parse_func("def f(a: int, b): ...")
        assert _extract_param_literals(node) == {}


class TestIsDataclass:
    def test_bare_decorator(self) -> None:
        assert _is_dataclass(_parse_class("@dataclass\nclass C: ..."))

    def test_call_decorator(self) -> None:
        assert _is_dataclass(_parse_class("@dataclass(frozen=True)\nclass C: ..."))

    def test_attribute_decorator(self) -> None:
        assert _is_dataclass(_parse_class("@dataclasses.dataclass\nclass C: ..."))

    def test_attribute_call_decorator(self) -> None:
        assert _is_dataclass(_parse_class("@dataclasses.dataclass(order=True)\nclass C: ..."))

    def test_other_decorator(self) -> None:
        assert not _is_dataclass(_parse_class("@register\nclass C: ..."))

    def test_no_decorator(self) -> None:
        assert not _is_dataclass(_parse_class("class C: ..."))


class TestStringCollectionValues:
    def test_list_tuple_set(self) -> None:
        assert _string_collection_values(_first_expr('["a", "b"]')) == ["a", "b"]
        assert _string_collection_values(_first_expr('("a",)')) == ["a"]
        assert _string_collection_values(_first_expr('{"a", "b"}')) == ["a", "b"]

    def test_mixed_types_rejected(self) -> None:
        assert _string_collection_values(_first_expr('["a", 1]')) is None

    def test_non_collection_rejected(self) -> None:
        assert _string_collection_values(_first_expr('"a"')) is None


class TestExtractModuleConstant:
    def _stmt(self, src: str) -> ast.Assign | ast.AnnAssign:
        node = ast.parse(textwrap.dedent(src)).body[0]
        assert isinstance(node, ast.Assign | ast.AnnAssign)
        return node

    def test_string_constant(self) -> None:
        assert _extract_module_constant(self._stmt('NAME = "value"')) == {
            "name": "NAME",
            "kind": "str",
            "values": ["value"],
        }

    def test_tuple_list_set(self) -> None:
        assert _extract_module_constant(self._stmt('T = ("a", "b")')) == {
            "name": "T",
            "kind": "tuple",
            "values": ["a", "b"],
        }
        assert _extract_module_constant(self._stmt('L = ["a"]')) == {
            "name": "L",
            "kind": "list",
            "values": ["a"],
        }
        assert _extract_module_constant(self._stmt('S = {"a"}')) == {
            "name": "S",
            "kind": "set",
            "values": ["a"],
        }

    def test_frozenset_and_set_calls(self) -> None:
        assert _extract_module_constant(self._stmt('F = frozenset({"a", "b"})')) == {
            "name": "F",
            "kind": "frozenset",
            "values": ["a", "b"],
        }
        assert _extract_module_constant(self._stmt('S = set(["a"])')) == {
            "name": "S",
            "kind": "set",
            "values": ["a"],
        }

    def test_annassign_with_value(self) -> None:
        assert _extract_module_constant(self._stmt('N: str = "v"')) == {
            "name": "N",
            "kind": "str",
            "values": ["v"],
        }

    def test_annassign_without_value(self) -> None:
        assert _extract_module_constant(self._stmt("N: str")) is None

    def test_multi_target_rejected(self) -> None:
        assert _extract_module_constant(self._stmt('A = B = "v"')) is None

    def test_non_name_target_rejected(self) -> None:
        assert _extract_module_constant(self._stmt('obj.attr = "v"')) is None

    def test_non_string_value_rejected(self) -> None:
        assert _extract_module_constant(self._stmt("N = 42")) is None

    def test_frozenset_of_non_strings_rejected(self) -> None:
        assert _extract_module_constant(self._stmt("F = frozenset({1, 2})")) is None

    def test_other_call_rejected(self) -> None:
        assert _extract_module_constant(self._stmt('D = dict(a="b")')) is None


class TestExtractReturnData:
    def test_literal_dict(self) -> None:
        node = _parse_func(
            """
            def get_defaults():
                return {"a": 1, "b": ["x"]}
            """
        )
        assert _extract_return_data(node) == {"a": 1, "b": ["x"]}

    def test_literal_constant(self) -> None:
        node = _parse_func("def f():\n    return 3")
        assert _extract_return_data(node) == 3

    def test_computed_return_is_none(self) -> None:
        node = _parse_func(
            """
            def f():
                return build()
                return {"never": "reached"}
            """
        )
        assert _extract_return_data(node) is None

    def test_partially_dynamic_collection_is_none(self) -> None:
        node = _parse_func("def f():\n    return [foo]")
        assert _extract_return_data(node) is None

    def test_no_return(self) -> None:
        node = _parse_func("def f():\n    pass")
        assert _extract_return_data(node) is None

    def test_bare_return_skipped(self) -> None:
        node = _parse_func("def f():\n    return")
        assert _extract_return_data(node) is None


class TestClassProperties:
    def test_public_properties_with_variants(self) -> None:
        node = _parse_class(
            '''
            class C:
                @property
                def name(self) -> str:
                    """The name."""
                    return "x"

                @abc.abstractproperty
                def other(self):
                    return 1

                @property
                def _private(self) -> int:
                    return 2

                def method(self):
                    return 3
            '''
        )
        assert _extract_class_properties(node) == [
            {"name": "name", "return_type": "str", "doc": "The name."},
            {"name": "other", "return_type": "", "doc": ""},
        ]

    def test_has_property_decorator_negative(self) -> None:
        node = _parse_class("class C:\n    @staticmethod\n    def f():\n        return 1")
        child = node.body[0]
        assert isinstance(child, ast.FunctionDef)
        assert not _has_property_decorator(child)


class TestExtractDataclassFields:
    def test_annotated_public_fields(self) -> None:
        node = _parse_class(
            """
            class D:
                x: int
                y: list[str] = field(default_factory=list)
                _z: int = 0
                plain = 5
            """
        )
        assert _extract_dataclass_fields(node) == [
            {"name": "x", "type": "int", "default": ""},
            {"name": "y", "type": "list[str]", "default": "field(default_factory=list)"},
        ]


class TestFormatFunctionSignature:
    def test_posonly_varargs_kwonly_kwargs(self) -> None:
        node = _parse_func(
            """
            def f(a, b=1, /, c=2, *args: int, d: str = "x", **kw: object) -> None: ...
            """
        )
        assert _format_function_signature(node) == (
            "f(a, b = 1, /, c = 2, *args: int, d: str = 'x', **kw: object) -> None"
        )

    def test_kwonly_star_marker_without_vararg(self) -> None:
        node = _parse_func("def g(a, *, b: int = 3): ...")
        assert _format_function_signature(node) == "g(a, *, b: int = 3)"

    def test_plain_signature(self) -> None:
        node = _parse_func("def h(x: str) -> bool: ...")
        assert _format_function_signature(node) == "h(x: str) -> bool"


class TestSplitSignatureEdge:
    def test_missing_close_paren(self) -> None:
        assert _split_signature("f(", "f") == ("", "")


class TestFormatClassMethods:
    def test_skips_private_and_properties_keeps_init(self) -> None:
        node = _parse_class(
            """
            class C:
                def __init__(self, x: int): ...
                def run(self) -> None: ...
                def _hidden(self): ...
                @property
                def size(self) -> int:
                    return 1
            """
        )
        methods = _format_class_methods(node)
        assert methods == "__init__(self, x: int)\nrun(self) -> None"

    def test_empty_class(self) -> None:
        assert _format_class_methods(_parse_class("class C: ...")) == ""


class TestUnparseAnnotation:
    def test_fallback_on_malformed_node(self) -> None:
        # A Name node without an ``id`` makes ast.unparse raise —
        # the helper must degrade to the placeholder, never raise.
        assert _unparse_annotation(ast.Name()) == "<expr>"


class TestExtractSourceInfo:
    def test_full_extraction(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text(
            textwrap.dedent(
                '''
                """Module summary line.

                Longer text.
                """

                PUBLIC = "v"
                _TOKENS = ("a", "b")
                NUM = 42


                def visible(x: int) -> str:
                    """Do the thing."""
                    return str(x)


                def _hidden(): ...


                class Widget:
                    """A widget."""

                    def render(self) -> str:
                        return "w"


                class _Internal: ...
                '''
            ).lstrip(),
            encoding="utf-8",
        )
        (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        (tmp_path / "data.txt").write_text("not python\n", encoding="utf-8")

        info = _extract_source_info(["mod.py", "bad.py", "data.txt", "missing.py"], tmp_path)

        assert info.file_count == 4
        assert info.module_docstrings == ["Module summary line."]
        assert [f["name"] for f in info.public_functions] == ["visible"]
        assert [c["name"] for c in info.public_classes] == ["Widget"]
        # Both public and underscore-prefixed string constants
        # surface; the int constant is skipped.
        assert [c["name"] for c in info.module_constants] == ["PUBLIC", "_TOKENS"]
        assert info.module_constants[1]["values"] == ["a", "b"]
        # Enriched signature view is populated alongside the legacy one.
        sig = info.function_signatures[0]
        assert sig["signature"] == "visible(x: int) -> str"
        assert sig["params"] == "x: int"
        assert sig["returns"] == "str"
        cls = info.class_signatures[0]
        assert cls["is_dataclass"] is False
        assert "render(self) -> str" in cls["methods"]

    def test_dataclass_fields_populated_for_dataclass(self, tmp_path: Path) -> None:
        (tmp_path / "dc.py").write_text(
            textwrap.dedent(
                """
                from dataclasses import dataclass


                @dataclass
                class Config:
                    name: str
                    retries: int = 3
                """
            ).lstrip(),
            encoding="utf-8",
        )
        info = _extract_source_info(["dc.py"], tmp_path)
        cls = info.class_signatures[0]
        assert cls["is_dataclass"] is True
        assert cls["dataclass_fields"] == [
            {"name": "name", "type": "str", "default": ""},
            {"name": "retries", "type": "int", "default": "3"},
        ]


_HELP_TEMPLATE = (
    "---\n"
    "type: concept\n"
    "name: auth-concept\n"
    "feature: auth\n"
    "depth: concept\n"
    "generated_at: 2026-01-01T00:00:00+00:00\n"
    "source_hash: aaaa\n"
    "status: generated\n"
    "---\n"
    "\n"
    "# Auth\n"
    "\n"
    "Body text.\n"
)

_DOC_FOOTER = (
    "<!-- attune-generated: source_hash=aaaa feature=auth"
    " kind=how-to generated_at=2026-01-01 -->\n"
)

_PROJECT_DOC = "# Auth How-To\n\nSteps.\n" + _DOC_FOOTER


class TestScaffoldHash:
    def test_metadata_lines_excluded(self) -> None:
        changed_meta = _HELP_TEMPLATE.replace("2026-01-01T00:00:00+00:00", "2027-09-09").replace(
            "source_hash: aaaa", "source_hash: bbbb"
        )
        assert compute_scaffold_hash(_HELP_TEMPLATE) == compute_scaffold_hash(changed_meta)

    def test_body_change_changes_hash(self) -> None:
        assert compute_scaffold_hash(_HELP_TEMPLATE) != compute_scaffold_hash(
            _HELP_TEMPLATE.replace("Body text.", "Different body.")
        )

    def test_inject_and_read_back_frontmatter(self, tmp_path: Path) -> None:
        digest = compute_scaffold_hash(_HELP_TEMPLATE)
        injected = _inject_scaffold_hash(_HELP_TEMPLATE, digest, is_project_doc=False)
        assert f"\nscaffold_hash: {digest}\n" in injected
        out = tmp_path / "concept.md"
        out.write_text(injected, encoding="utf-8")
        assert _read_scaffold_hash(out) == digest

    def test_inject_and_read_back_project_doc(self, tmp_path: Path) -> None:
        digest = compute_scaffold_hash(_PROJECT_DOC)
        injected = _inject_scaffold_hash(_PROJECT_DOC, digest, is_project_doc=True)
        assert f" scaffold_hash={digest} generated_at=" in injected
        out = tmp_path / "how-to.md"
        out.write_text(injected, encoding="utf-8")
        assert _read_scaffold_hash(out) == digest

    def test_inject_without_frontmatter_is_noop(self) -> None:
        assert _inject_scaffold_hash("no frontmatter\n", "h", is_project_doc=False) == (
            "no frontmatter\n"
        )

    def test_inject_project_doc_without_footer_is_noop(self) -> None:
        assert _inject_scaffold_hash("no footer\n", "h", is_project_doc=True) == "no footer\n"

    def test_read_missing_file(self, tmp_path: Path) -> None:
        assert _read_scaffold_hash(tmp_path / "absent.md") is None

    def test_read_frontmatter_without_hash(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        out.write_text(_HELP_TEMPLATE, encoding="utf-8")
        assert _read_scaffold_hash(out) is None

    def test_read_empty_hash_value(self, tmp_path: Path) -> None:
        out = tmp_path / "concept.md"
        out.write_text(_HELP_TEMPLATE.replace("---\n\n", "scaffold_hash:\n---\n\n", 1), "utf-8")
        # An empty ``scaffold_hash:`` value reads as None, not "".
        content = "---\nscaffold_hash:\n---\nbody\n"
        out.write_text(content, encoding="utf-8")
        assert _read_scaffold_hash(out) is None


class TestRefreshMetadataInPlace:
    def test_help_template_frontmatter_refreshed_body_kept(self, tmp_path: Path) -> None:
        existing = _HELP_TEMPLATE.replace("---\n\n", "polish: skipped\n---\n\n", 1)
        canonical = _HELP_TEMPLATE.replace("2026-01-01T00:00:00+00:00", "2026-07-30").replace(
            "source_hash: aaaa", "source_hash: cccc"
        )
        out = tmp_path / "concept.md"
        out.write_text(existing, encoding="utf-8")

        _refresh_metadata_in_place(out, canonical, is_project_doc=False)

        refreshed = out.read_text(encoding="utf-8")
        # Deterministic fields adopt canonical values...
        assert "generated_at: 2026-07-30" in refreshed
        assert "source_hash: cccc" in refreshed
        # ...while polish-layer fields and the body are preserved.
        assert "polish: skipped" in refreshed
        assert "Body text." in refreshed

    def test_project_doc_footer_refreshed(self, tmp_path: Path) -> None:
        canonical = _PROJECT_DOC.replace("source_hash=aaaa", "source_hash=dddd")
        out = tmp_path / "how-to.md"
        out.write_text(_PROJECT_DOC, encoding="utf-8")

        _refresh_metadata_in_place(out, canonical, is_project_doc=True)

        refreshed = out.read_text(encoding="utf-8")
        assert "source_hash=dddd" in refreshed
        assert "Steps." in refreshed

    def test_canonical_without_footer_is_noop(self, tmp_path: Path) -> None:
        out = tmp_path / "how-to.md"
        out.write_text(_PROJECT_DOC, encoding="utf-8")
        _refresh_metadata_in_place(out, "no footer here\n", is_project_doc=True)
        assert out.read_text(encoding="utf-8") == _PROJECT_DOC

    def test_existing_without_footer_is_noop(self, tmp_path: Path) -> None:
        out = tmp_path / "how-to.md"
        out.write_text("no footer\n", encoding="utf-8")
        _refresh_metadata_in_place(out, _PROJECT_DOC, is_project_doc=True)
        assert out.read_text(encoding="utf-8") == "no footer\n"

    def test_missing_file_is_noop(self, tmp_path: Path) -> None:
        _refresh_metadata_in_place(tmp_path / "absent.md", _HELP_TEMPLATE, is_project_doc=False)


class TestFaithfulnessTelemetry:
    def test_state_initializes_and_resets(self) -> None:
        reset_faithfulness_telemetry()
        state = _faithfulness_telemetry()
        assert state == {"calls": 0.0, "skipped": 0.0, "cost_usd": 0.0}
        state["calls"] += 2
        state["cost_usd"] += 0.5
        # Same per-process state object is returned on re-read.
        assert _faithfulness_telemetry()["calls"] == 2
        reset_faithfulness_telemetry()
        assert _faithfulness_telemetry() == {"calls": 0.0, "skipped": 0.0, "cost_usd": 0.0}


class TestManualStatusFeature:
    def test_manual_feature_generates_nothing(self, help_dir: Path, project_root: Path) -> None:
        feature = Feature(
            name="auth",
            description="Authentication",
            files=["src/auth/**"],
            status="manual",
        )
        result = generate_feature_templates(
            feature=feature,
            help_dir=help_dir,
            project_root=project_root,
            use_rag=False,
        )
        assert isinstance(result, GenerationResult)
        assert result.feature == "auth"
        assert result.templates == []
        # Nothing was written for the manual feature.
        assert not (help_dir / "templates" / "auth").exists()


class TestProjectDocOutputPath:
    def test_architecture_uses_arch_path(self, tmp_path: Path) -> None:
        feature = Feature(
            name="auth",
            description="d",
            arch_path="docs/arch/auth-arch.md",
        )
        assert _project_doc_output_path("architecture", feature, tmp_path) == (
            tmp_path / "docs" / "arch" / "auth-arch.md"
        )

    def test_non_architecture_uses_doc_path(self, tmp_path: Path) -> None:
        feature = Feature(name="auth", description="d", doc_path="docs/howto/auth.md")
        assert _project_doc_output_path("how-to", feature, tmp_path) == (
            tmp_path / "docs" / "howto" / "auth.md"
        )

    def test_fallback_lands_under_docs_subdir(self, tmp_path: Path) -> None:
        feature = Feature(name="auth", description="d")
        out = _project_doc_output_path("tutorial", feature, tmp_path)
        assert out.name == "auth.md"
        assert out.parent.parent == tmp_path / "docs"
