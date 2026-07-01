"""
Symbol extraction and hashing for semantic-freshness staleness detection.

Extracted verbatim from attune-author's ``freshness/symbols.py`` during
the attune-author consolidation (``docs/specs/attune-author-consolidation/``).
Pure ``ast`` + ``hashlib``: no LLM, no jinja, no network. The
``signature_hash`` here is load-bearing for staleness detection and MUST
stay byte-compatible with the hashes stored in existing ``.help/`` files.

Public API:
    SymbolRecord      — frozen dataclass; one per public symbol
    SymbolExtractor   — parses Python source, emits SymbolRecord lists
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SymbolKind = Literal["function", "class", "method"]


@dataclass(frozen=True)
class SymbolRecord:
    """A normalized record of a public symbol's contract surface.

    `signature_hash` is the load-bearing field for staleness detection:
    it is stable across docstring edits, body edits, formatter passes, and
    import reorders, but changes when the *contract* changes (parameters,
    return type, decorators, bases, public attributes).

    `body_hash` is recorded for downstream phases (Phase 2 quality scoring)
    but does NOT participate in Phase 1 staleness decisions.
    """

    file: str
    qualname: str
    kind: SymbolKind
    signature: str
    decorators: tuple[str, ...] = ()
    bases: tuple[str, ...] = ()
    public_attrs: tuple[str, ...] = ()
    body_ast_repr: str = ""

    @property
    def signature_hash(self) -> str:
        payload = "\n".join(
            [
                self.kind,
                self.qualname,
                self.signature,
                "|".join(self.decorators),
                "|".join(self.bases),
                "|".join(self.public_attrs),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def body_hash(self) -> str:
        return hashlib.sha256(self.body_ast_repr.encode("utf-8")).hexdigest()


# ---------- Internal helpers ----------


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Drop a leading string-literal expression statement (the docstring)."""
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _format_arg(arg: ast.arg) -> str:
    if arg.annotation is not None:
        return f"{arg.arg}: {ast.unparse(arg.annotation)}"
    return arg.arg


def _normalize_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a canonical signature string. Stable across formatter changes."""
    args = node.args
    parts: list[str] = []

    # positional-only
    for arg in args.posonlyargs:
        parts.append(_format_arg(arg))
    if args.posonlyargs:
        parts.append("/")

    # regular positional + defaults (defaults align to the *end* of args.args)
    n_pos = len(args.args)
    n_defaults = len(args.defaults)
    default_start = n_pos - n_defaults
    for i, arg in enumerate(args.args):
        formatted = _format_arg(arg)
        if i >= default_start:
            formatted += f"={ast.unparse(args.defaults[i - default_start])}"
        parts.append(formatted)

    # *args (or bare * marker if there are kwonly args without *args)
    if args.vararg is not None:
        parts.append(f"*{_format_arg(args.vararg)}")
    elif args.kwonlyargs:
        parts.append("*")

    # keyword-only
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
        formatted = _format_arg(arg)
        if default is not None:
            formatted += f"={ast.unparse(default)}"
        parts.append(formatted)

    # **kwargs
    if args.kwarg is not None:
        parts.append(f"**{_format_arg(args.kwarg)}")

    args_str = ", ".join(parts)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    return f"{prefix}{node.name}({args_str}){returns}"


def _normalize_body(body: list[ast.stmt]) -> str:
    """Stable representation of a function/method body. Strips docstring."""
    stripped = _strip_docstring(body)
    if not stripped:
        return ""
    return "\n".join(ast.unparse(s) for s in stripped)


def _is_public(name: str) -> bool:
    """Public if not underscore-prefixed; `__init__` is the documented exception."""
    return not name.startswith("_") or name == "__init__"


# ---------- Public extractor ----------


class SymbolExtractor:
    """Parses Python source and emits normalized `SymbolRecord` lists.

    Only top-level public symbols are extracted. Nested classes and inner
    functions are out of scope for Phase 1 — templates that reference them
    can declare deps explicitly via features.yaml.
    """

    def extract(self, file: Path) -> list[SymbolRecord]:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source)
        records: list[SymbolRecord] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if _is_public(node.name):
                    records.append(
                        self._function_record(file, node, qualname=node.name, kind="function")
                    )
            elif isinstance(node, ast.ClassDef):
                if _is_public(node.name):
                    records.append(self._class_record(file, node))
                    records.extend(self._class_method_records(file, node))
        return records

    def extract_one(self, file: Path, qualname: str) -> SymbolRecord | None:
        """Return the first record matching `qualname`, or None.

        Note: properties with a setter share a qualname. `extract_one` returns
        the first match; staleness checks that need both should use `extract()`
        and filter. Tracked as an open question in the Phase 1 spec.
        """
        for r in self.extract(file):
            if r.qualname == qualname:
                return r
        return None

    # ---------- private builders ----------

    def _function_record(
        self,
        file: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        qualname: str,
        kind: SymbolKind,
    ) -> SymbolRecord:
        return SymbolRecord(
            file=str(file),
            qualname=qualname,
            kind=kind,
            signature=_normalize_signature(node),
            decorators=tuple(ast.unparse(d) for d in node.decorator_list),
            body_ast_repr=_normalize_body(node.body),
        )

    def _class_record(self, file: Path, node: ast.ClassDef) -> SymbolRecord:
        public_attrs: list[str] = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and _is_public(target.id):
                        public_attrs.append(target.id)
            elif isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Name) and _is_public(stmt.target.id):
                    public_attrs.append(stmt.target.id)

        return SymbolRecord(
            file=str(file),
            qualname=node.name,
            kind="class",
            signature=f"class {node.name}",
            decorators=tuple(ast.unparse(d) for d in node.decorator_list),
            bases=tuple(ast.unparse(b) for b in node.bases),
            public_attrs=tuple(public_attrs),
        )

    def _class_method_records(self, file: Path, class_node: ast.ClassDef) -> list[SymbolRecord]:
        records: list[SymbolRecord] = []
        for stmt in class_node.body:
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef) and _is_public(stmt.name):
                records.append(
                    self._function_record(
                        file,
                        stmt,
                        qualname=f"{class_node.name}.{stmt.name}",
                        kind="method",
                    )
                )
        return records
