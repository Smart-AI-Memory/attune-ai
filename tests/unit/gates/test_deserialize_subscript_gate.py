"""Gate: a parse result handed straight to a reconstructor must be
guarded (library-review class I-4).

I-4 is *deserialize here, subscript there*:

    return StagedPattern.from_dict(json.loads(raw))

The parse result is never bound to a name, so there is no local value to
isinstance-check — which is precisely why **the C3 dict-guard gate
cannot see this shape**. If the stored bytes hold a LIST, ``json.loads``
succeeds and ``from_dict`` raises ``TypeError`` from *inside* the
consumer, past a caller whose except tuple lists only
``JSONDecodeError``. Since that read backs promotion, one legacy or
hand-edited key blocked **every** promotion — a Principle-15 violation
(the memory layer degrades, it never blocks).

Confirmed by executed repro against the deprecated twin (2026-08-21),
one good staged record beside one legacy list-shaped key::

    pre-fix : TypeError: list indices must be integers or slices, not str
    post-fix: RETURNED 1 record(s): ['p-good']

Reference implementation: :func:`attune.memory.types.parse_stored_record`,
which collapses all three failure modes — unparseable JSON, a parsed
value that is not a mapping, and fields ``from_dict`` rejects — to None.

**Scope, deliberately narrow.** The rule fires only on the RECONSTRUCTOR
shape, where the consumer subscripts immediately. The looser
``out.append(json.loads(line))`` shape defers the subscript to a caller;
that is C3's territory (its row records 15 stored-data sites carried
into batch 3), and re-flagging it here would re-litigate dispositions
another gate already owns. Two classes, two gates, no overlap.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0

Register-Class: I-4
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOTS = (REPO_ROOT / "src" / "attune", REPO_ROOT / "attune_redis")

#: Deserialisers returning an object of unknown shape.
_PARSERS = {"loads", "safe_load", "load"}

#: Consumers that immediately subscript what they are handed.
_RECONSTRUCTORS = {"from_dict", "from_json", "parse_obj", "model_validate", "from_record"}

#: Catching any of these covers the TypeError a list-shaped record raises.
_COVERS = {"TypeError", "Exception", "BaseException"}


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    node = handler.type
    if node is None:
        return {"BaseException"}
    parts = node.elts if isinstance(node, ast.Tuple) else [node]
    return {
        p.id if isinstance(p, ast.Name) else p.attr
        for p in parts
        if isinstance(p, ast.Name | ast.Attribute)
    }


def _is_parse_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    return name in _PARSERS


def _guarded_for_typeerror(node: ast.AST, tree: ast.AST) -> bool:
    """True if node sits in a try body whose handlers cover TypeError."""
    for t in ast.walk(tree):
        if not isinstance(t, ast.Try):
            continue
        if not any(node is sub for stmt in t.body for sub in ast.walk(stmt)):
            continue
        caught: set[str] = set()
        for h in t.handlers:
            caught |= _handler_names(h)
        if caught & _COVERS:
            return True
    return False


def _offending_sites(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        cname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        reconstructor = cname in _RECONSTRUCTORS and any(_is_parse_call(a) for a in node.args)
        # Model(**json.loads(raw)) is the same hazard with a splat.
        splat = any(k.arg is None and _is_parse_call(k.value) for k in node.keywords)
        if not reconstructor and not splat:
            continue
        if _guarded_for_typeerror(node, tree):
            continue
        hits.append(f"{_label(path)}:{node.lineno}  {cname}(<parse>(...)) unguarded")
    return hits


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shipped_modules() -> list[Path]:
    out: list[Path] = []
    for root in SRC_ROOTS:
        if root.exists():
            out.extend(
                p
                for p in root.rglob("*.py")
                if "__pycache__" not in p.parts and "tests" not in p.parts
            )
    return sorted(out)


def test_no_unguarded_deserialize_into_reconstructor() -> None:
    """No shipped module may hand a bare parse result to a reconstructor."""
    offenders: list[str] = []
    for module in _shipped_modules():
        offenders.extend(_offending_sites(module))

    assert not offenders, (
        "Unguarded deserialize-into-reconstructor (class I-4):\n  "
        + "\n  ".join(offenders)
        + "\n\nThe parse result is never bound, so nothing can be "
        "isinstance-checked and the C3 dict-guard cannot see it. A stored "
        "LIST parses fine and makes the reconstructor raise TypeError from "
        "inside the call — past an except tuple listing only "
        "JSONDecodeError.\n"
        "Use attune.memory.types.parse_stored_record, which returns None "
        "for unparseable JSON, a non-mapping, or rejected fields."
    )


def test_rule_flags_the_class(tmp_path: Path) -> None:
    module = tmp_path / "offender.py"
    module.write_text(
        "import json\n" "def load(raw):\n" "    return Model.from_dict(json.loads(raw))\n",
        encoding="utf-8",
    )
    assert _offending_sites(module), "rule missed the canonical I-4 shape"


def test_rule_flags_the_splat_form(tmp_path: Path) -> None:
    """Model(**json.loads(raw)) is the same hazard."""
    module = tmp_path / "splat.py"
    module.write_text(
        "import json\ndef load(raw):\n    return Model(**json.loads(raw))\n",
        encoding="utf-8",
    )
    assert _offending_sites(module), "rule missed the **splat form"


def test_rule_clears_a_typeerror_guarded_site(tmp_path: Path) -> None:
    """The same shape inside a TypeError-covering try is DEFENDED.

    This is not hypothetical: gates/lifecycle/ledger.py writes exactly
    this, and its except tuple includes TypeError. Flagging it would have
    made the gate demand a change to already-correct code.
    """
    module = tmp_path / "guarded.py"
    module.write_text(
        "import json\n"
        "def load(lines):\n"
        "    out = []\n"
        "    for line in lines:\n"
        "        try:\n"
        "            out.append(Model.from_dict(json.loads(line)))\n"
        "        except (json.JSONDecodeError, KeyError, TypeError, ValueError):\n"
        "            pass\n"
        "    return out\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_rule_clears_the_total_helper(tmp_path: Path) -> None:
    """Routing through parse_stored_record is the fix, and must pass."""
    module = tmp_path / "fixed.py"
    module.write_text(
        "def load(raw, key):\n    return parse_stored_record(Model, raw, key=key)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_rule_ignores_deferred_subscript(tmp_path: Path) -> None:
    """append(json.loads(x)) is C3's class, not this one.

    The subscript happens in a caller, not inside the consumer. C3 owns
    those sites; double-gating them would re-litigate its dispositions.
    """
    module = tmp_path / "deferred.py"
    module.write_text(
        "import json\n"
        "def load(lines):\n"
        "    out = []\n"
        "    for line in lines:\n"
        "        out.append(json.loads(line))\n"
        "    return out\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_reference_implementation_is_clean() -> None:
    """parse_stored_record itself must not be an offender."""
    types_mod = REPO_ROOT / "src/attune/memory/types.py"
    if types_mod.exists():
        assert not _offending_sites(types_mod)
