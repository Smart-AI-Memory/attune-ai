"""Deterministic source introspection and scaffold hashing.

Extracted verbatim from attune-author's ``generator.py`` — the no-LLM,
AST-only core the projector depends on — during the attune-author
consolidation (``docs/specs/attune-author-consolidation/``). Pure
``ast`` + ``hashlib``: no LLM, no jinja, no network. The projector and
the numeric-refs fact-check are its only callers.
"""

from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_SCAFFOLD_HASH_EXCLUDE = ("generated_at", "scaffold_hash", "source_hash")


def compute_scaffold_hash(content: str) -> str:
    """SHA-256 of a rendered scaffold with metadata lines normalized.

    The scaffold is the deterministic pre-polish render. Two renders
    with equal scaffold hash would feed the polish LLM equivalent
    content — so if the on-disk file was produced from an
    equal-hash scaffold, re-polishing it is pure spend with no
    content change (polish-cost-reduction lever 2; see attune-ai
    docs/specs/polish-cost-reduction/ D3).
    """
    lines = [
        ln
        for ln in content.splitlines()
        if not any(marker in ln for marker in _SCAFFOLD_HASH_EXCLUDE)
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


@dataclass
class _SourceInfo:
    """Extracted information from source files.

    Attributes:
        public_functions: Legacy list of ``{name, doc, file}``
            dicts. Kept for template rendering compatibility.
        public_classes: Legacy list of ``{name, doc, file}``
            dicts for classes.
        module_docstrings: First lines of module docstrings.
        config_keys: Top-level config constants discovered
            in source files.
        file_count: Number of source files matched.
        function_signatures: Enriched view of functions that
            includes formatted signatures (``name(arg: T) ->
            R``). Populated alongside ``public_functions`` so
            the polish pass can feed the LLM typed context
            without changing existing callers.
        class_signatures: Enriched view of classes with
            public method signatures joined by newlines.
    """

    public_functions: list[dict[str, str]] = field(default_factory=list)
    public_classes: list[dict[str, str]] = field(default_factory=list)
    module_docstrings: list[str] = field(default_factory=list)
    config_keys: list[str] = field(default_factory=list)
    file_count: int = 0
    function_signatures: list[dict[str, str]] = field(default_factory=list)
    class_signatures: list[dict[str, str]] = field(default_factory=list)
    module_constants: list[dict[str, object]] = field(default_factory=list)


def _docstring_first_line(node: ast.AST) -> str:
    """Return the first non-empty line of an AST node's docstring."""
    doc = ast.get_docstring(node) or ""
    return doc.split("\n", 1)[0].strip()


def _exception_name(exc: ast.expr) -> str | None:
    """Return the dotted name of an exception expression, or None."""
    if isinstance(exc, ast.Call):
        return _exception_name(exc.func)
    if isinstance(exc, ast.Name):
        return exc.id
    if isinstance(exc, ast.Attribute):
        parts: list[str] = []
        cur: ast.expr = exc
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _raise_message(exc: ast.expr) -> str:
    """Return the literal message text of a ``raise X(...)``, or "".

    Handles three shapes:

    - ``raise X("literal")`` → ``"literal"``
    - ``raise X(f"Invalid name: {name!r}")`` → ``"Invalid name: {...}"``
      (literal prefix preserved, computed parts replaced with ``{...}``
      so the diagnostic stem callers grep for is still verifiable)
    - Anything else (computed expression, variable, no args) → ``""``

    The diagnostic stem is what reference pages want to surface:
    ``"Invalid feature name:"`` is the part users recognize when
    debugging, and it's verifiable from source.
    """
    if not isinstance(exc, ast.Call) or not exc.args:
        return ""
    first = exc.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    if isinstance(first, ast.JoinedStr):
        parts: list[str] = []
        for v in first.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("{...}")
        return "".join(parts)
    return ""


def _extract_raises(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, str]]:
    """Exceptions raised in a function body, in source order.

    Returns a list of ``{"class_name", "message"}`` dicts — one
    per unique (class_name, message) pair in source order. A single
    function can raise the same exception class with several
    different literal messages (e.g. ``validate_file_path`` raises
    ``ValueError`` with a different diagnostic in each guard
    clause); each distinct message becomes its own entry so the
    rendered reference can list every diagnostic the caller might
    see. Exact duplicate pairs within the same function are
    collapsed.

    Bare ``raise`` (re-raise) statements are ignored because they
    rethrow whatever the current exception handler caught — which
    is not a signature-level fact.
    """
    # Pre-order DFS via iter_child_nodes preserves source order;
    # ast.walk is BFS and would surface siblings before their
    # earlier-in-source nested statements.
    seen: list[dict[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def visit(n: ast.AST) -> None:
        if isinstance(n, ast.Raise) and n.exc is not None:
            name = _exception_name(n.exc)
            if name:
                msg = _raise_message(n.exc)
                pair = (name, msg)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    seen.append({"class_name": name, "message": msg})
        for child in ast.iter_child_nodes(n):
            visit(child)

    visit(node)
    return seen


def _extract_literal_values(annotation: ast.expr | None) -> list[str] | None:
    """Return the string values of a ``Literal[...]`` annotation, or None.

    Handles both ``Literal["a", "b"]`` and ``typing.Literal["a", "b"]``
    forms. Returns None if the annotation is not a Literal, or if any
    argument is a non-string constant — we only surface enum-like
    string literals since those are what users ask about.
    """
    if annotation is None or not isinstance(annotation, ast.Subscript):
        return None
    value = annotation.value
    name = (
        value.id
        if isinstance(value, ast.Name)
        else (value.attr if isinstance(value, ast.Attribute) else None)
    )
    if name != "Literal":
        return None
    slice_node = annotation.slice
    items = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
    out: list[str] = []
    for item in items:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            out.append(item.value)
        else:
            return None
    return out


def _extract_param_literals(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, list[str]]:
    """Map parameter name -> list of Literal[...] string values."""
    out: dict[str, list[str]] = {}
    all_args = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
    for arg in all_args:
        values = _extract_literal_values(arg.annotation)
        if values:
            out[arg.arg] = values
    return out


def _is_dataclass(node: ast.ClassDef) -> bool:
    """Return True if the class has a ``@dataclass`` decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "dataclass":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id == "dataclass":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "dataclass":
                return True
        if isinstance(dec, ast.Attribute) and dec.attr == "dataclass":
            return True
    return False


def _string_collection_values(node: ast.expr) -> list[str] | None:
    """Return the string values inside a list/tuple/set literal, or None.

    Accepts ``["a", "b"]``, ``("a", "b")``, ``{"a", "b"}``. Returns
    None if any element is not a string constant or the node is not
    a supported collection literal — we deliberately don't surface
    mixed-type collections since users ask about string enums.
    """
    if not isinstance(node, ast.List | ast.Tuple | ast.Set):
        return None
    out: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            out.append(elt.value)
        else:
            return None
    return out


def _extract_module_constant(node: ast.Assign | ast.AnnAssign) -> dict[str, object] | None:
    """Return a structured record for a module-level string constant.

    Recognizes four shapes that users routinely ask about:

    - ``NAME = "value"``
    - ``NAME = ("a", "b")`` / ``["a", "b"]`` / ``{"a", "b"}``
    - ``NAME = frozenset({"a", "b"})`` / ``frozenset(["a", "b"])``
    - ``NAME = set({"a", "b"})``

    Returns ``{"name", "kind", "values"}`` where ``kind`` is one of
    ``str`` / ``tuple`` / ``list`` / ``set`` / ``frozenset``, or
    None if the shape is unrecognized. Non-string-valued constants
    are intentionally skipped — those are runtime config, not the
    string-enum-like constants this extractor surfaces.
    """
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return None
        name = node.targets[0].id
        value = node.value
    else:  # AnnAssign
        if not isinstance(node.target, ast.Name) or node.value is None:
            return None
        name = node.target.id
        value = node.value

    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return {"name": name, "kind": "str", "values": [value.value]}

    if isinstance(value, ast.Tuple):
        vals = _string_collection_values(value)
        if vals is not None:
            return {"name": name, "kind": "tuple", "values": vals}

    if isinstance(value, ast.List):
        vals = _string_collection_values(value)
        if vals is not None:
            return {"name": name, "kind": "list", "values": vals}

    if isinstance(value, ast.Set):
        vals = _string_collection_values(value)
        if vals is not None:
            return {"name": name, "kind": "set", "values": vals}

    if isinstance(value, ast.Call):
        func = value.func
        call_name = None
        if isinstance(func, ast.Name):
            call_name = func.id
        elif isinstance(func, ast.Attribute):
            call_name = func.attr
        if call_name in ("frozenset", "set") and len(value.args) == 1:
            vals = _string_collection_values(value.args[0])
            if vals is not None:
                return {"name": name, "kind": call_name, "values": vals}
    return None


def _extract_return_data(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> object | None:
    """Return the Python value of a function's literal return, or None.

    Walks the function body in source order for the first ``return``
    statement whose value is a fully-literal dict / list / tuple / set
    / constant (handled via ``ast.literal_eval``). Surfaces
    declarative-config factories — ``get_tools()``,
    ``get_defaults()``, MCP-style tool-schema builders — so the
    polish LLM can render the structure it returns rather than
    hallucinating it from the signature alone. Returns ``None`` if
    the first return is a computed expression (name reference,
    function call, etc.) — we intentionally do not surface partial
    or dynamic returns.
    """
    for child in node.body:
        if not isinstance(child, ast.Return) or child.value is None:
            continue
        value = child.value
        if not isinstance(value, ast.Dict | ast.List | ast.Tuple | ast.Set | ast.Constant):
            return None
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
    return None


def _extract_class_properties(node: ast.ClassDef) -> list[dict[str, str]]:
    """Return ``[{name, return_type, doc}]`` for ``@property`` methods.

    Only captures public properties. Parameterless by definition,
    so no args surfaced. Recognizes the bare ``@property`` form and
    the qualified ``@builtins.property`` / ``@abc.abstractproperty``
    variants that show up in practice.
    """
    props: list[dict[str, str]] = []
    for child in node.body:
        if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if child.name.startswith("_"):
            continue
        if not _has_property_decorator(child):
            continue
        ret = _unparse_annotation(child.returns) if child.returns else ""
        props.append({"name": child.name, "return_type": ret, "doc": _docstring_first_line(child)})
    return props


def _has_property_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check whether a method has a @property (or variant) decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "property":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr in ("property", "abstractproperty"):
            return True
    return False


def _extract_dataclass_fields(node: ast.ClassDef) -> list[dict[str, str]]:
    """Return ``[{name, type, default}]`` for each public annotated field.

    Captures every top-level ``AnnAssign`` whose target is a non-underscore
    name. The ``default`` is the unparsed right-hand side (e.g.
    ``"field(default_factory=list)"``) or the empty string when the field
    has no default.
    """
    fields_out: list[dict[str, str]] = []
    for child in node.body:
        if not isinstance(child, ast.AnnAssign) or not isinstance(child.target, ast.Name):
            continue
        name = child.target.id
        if name.startswith("_"):
            continue
        field_type = _unparse_annotation(child.annotation) if child.annotation else ""
        default = _unparse_annotation(child.value) if child.value is not None else ""
        fields_out.append({"name": name, "type": field_type, "default": default})
    return fields_out


def _collect_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    rel_path: str,
    info: _SourceInfo,
) -> None:
    first_line = _docstring_first_line(node)
    signature = _format_function_signature(node)
    params, returns = _split_signature(signature, node.name)
    info.public_functions.append({"name": node.name, "doc": first_line, "file": rel_path})
    info.function_signatures.append(
        {
            "name": node.name,
            "signature": signature,
            "params": params,
            "returns": returns,
            "doc": first_line,
            "file": rel_path,
            "raises": _extract_raises(node),
            "param_literals": _extract_param_literals(node),
            "return_data": _extract_return_data(node),
        }
    )


def _collect_class(
    node: ast.ClassDef,
    rel_path: str,
    info: _SourceInfo,
) -> None:
    first_line = _docstring_first_line(node)
    info.public_classes.append({"name": node.name, "doc": first_line, "file": rel_path})
    is_dc = _is_dataclass(node)
    info.class_signatures.append(
        {
            "name": node.name,
            "methods": _format_class_methods(node),
            "doc": first_line,
            "file": rel_path,
            "is_dataclass": is_dc,
            "dataclass_fields": _extract_dataclass_fields(node) if is_dc else [],
            "properties": _extract_class_properties(node),
        }
    )


def _extract_source_info(
    matched_files: list[str],
    project_root: Path,
) -> _SourceInfo:
    """Extract public API info from Python source files.

    Reads AST to find public functions, classes, and
    module docstrings. Non-Python files are counted
    but not parsed.

    Args:
        matched_files: Relative paths to source files.
        project_root: Project root directory.

    Returns:
        Extracted source information.
    """
    info = _SourceInfo(file_count=len(matched_files))

    for rel_path in matched_files:
        if not rel_path.endswith(".py"):
            continue

        full_path = project_root / rel_path
        try:
            source = full_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel_path)
        except (OSError, SyntaxError, ValueError) as e:
            # A null-byte source is rejected as ValueError on CPython
            # <= 3.11 and SyntaxError on 3.12+, so both are named:
            # otherwise one corrupt file aborts the whole batch on part
            # of the supported range (library-review F5 / C4a).
            logger.debug("Cannot parse %s: %s", rel_path, e)
            continue

        module_doc = _docstring_first_line(tree)
        if module_doc:
            info.module_docstrings.append(module_doc)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if not node.name.startswith("_"):
                    _collect_function(node, rel_path, info)
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    _collect_class(node, rel_path, info)
            elif isinstance(node, ast.Assign | ast.AnnAssign):
                # Module-level string constants — both public and
                # underscore-prefixed, because the leading underscore
                # is the Python convention for "module-private" but
                # the VALUES they hold (allowed tokens, env var
                # names, enum members) are still the kind of detail
                # reference docs answer questions about.
                const = _extract_module_constant(node)
                if const is not None:
                    const["file"] = rel_path
                    info.module_constants.append(const)

    return info


def _format_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    """Format a function AST node as a readable signature.

    Produces ``name(arg1: T1, arg2: T2 = default) -> R`` —
    good enough for the LLM to understand argument types
    and defaults without running a full unparse. Missing
    annotations are omitted rather than replaced with
    ``Any``.

    Args:
        node: AST function node.

    Returns:
        Human-readable signature string.
    """
    args: list[str] = []

    posonly = list(node.args.posonlyargs)
    regular = list(node.args.args)
    kwonly = list(node.args.kwonlyargs)
    defaults = list(node.args.defaults)
    kw_defaults = list(node.args.kw_defaults)

    # Map positional/regular args to their defaults
    positional = posonly + regular
    num_no_default = len(positional) - len(defaults)
    last_posonly_idx = len(posonly) - 1
    for idx, arg in enumerate(positional):
        arg_str = arg.arg
        if arg.annotation is not None:
            arg_str += f": {_unparse_annotation(arg.annotation)}"
        if idx >= num_no_default:
            default = defaults[idx - num_no_default]
            arg_str += f" = {_unparse_annotation(default)}"
        args.append(arg_str)
        if idx == last_posonly_idx:
            args.append("/")

    if node.args.vararg is not None:
        vararg = node.args.vararg
        vararg_str = f"*{vararg.arg}"
        if vararg.annotation is not None:
            vararg_str += f": {_unparse_annotation(vararg.annotation)}"
        args.append(vararg_str)
    elif kwonly:
        args.append("*")

    for kw_arg, kw_default in zip(kwonly, kw_defaults, strict=False):
        kw_str = kw_arg.arg
        if kw_arg.annotation is not None:
            kw_str += f": {_unparse_annotation(kw_arg.annotation)}"
        if kw_default is not None:
            kw_str += f" = {_unparse_annotation(kw_default)}"
        args.append(kw_str)

    if node.args.kwarg is not None:
        kwarg = node.args.kwarg
        kwarg_str = f"**{kwarg.arg}"
        if kwarg.annotation is not None:
            kwarg_str += f": {_unparse_annotation(kwarg.annotation)}"
        args.append(kwarg_str)

    sig = f"{node.name}({', '.join(args)})"
    if node.returns is not None:
        sig += f" -> {_unparse_annotation(node.returns)}"
    return sig


def _split_signature(signature: str, name: str) -> tuple[str, str]:
    # Splits ``name(params) -> R`` into ``(params, R)``. Returns
    # ``("", "")`` if the signature doesn't match the expected
    # shape — keeps rendering callers defensive.
    prefix = f"{name}("
    if not signature.startswith(prefix):
        return ("", "")
    rest = signature[len(prefix) :]
    end = rest.rfind(")")
    if end == -1:
        return ("", "")
    params = rest[:end]
    tail = rest[end + 1 :].lstrip()
    returns = tail[3:].strip() if tail.startswith("->") else ""
    return (params, returns)


def _format_class_methods(node: ast.ClassDef) -> str:
    """Format a class's public method signatures.

    Returns a newline-separated string of signatures for
    methods whose names do not start with an underscore.
    Includes ``__init__`` because callers need to know the
    constructor shape.

    Args:
        node: AST class node.

    Returns:
        Newline-separated method signatures, or the empty
        string if the class has no public methods.
    """
    methods: list[str] = []
    for child in node.body:
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            name = child.name
            if name.startswith("_") and name != "__init__":
                continue
            # @property methods are surfaced separately via
            # _extract_class_properties — skip here so the
            # polish LLM doesn't render them as callable methods.
            if _has_property_decorator(child):
                continue
            methods.append(_format_function_signature(child))
    return "\n".join(methods)


def _unparse_annotation(node: ast.expr) -> str:
    """Convert an AST expression to a readable string.

    Falls back to ``<expr>`` if ``ast.unparse`` fails so
    signature extraction never raises on exotic annotations.

    Args:
        node: AST expression node.

    Returns:
        Readable string representation.
    """
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: signature extraction is best-effort
        # context for the LLM — never block generation on
        # an exotic annotation we can't render.
        return "<expr>"
