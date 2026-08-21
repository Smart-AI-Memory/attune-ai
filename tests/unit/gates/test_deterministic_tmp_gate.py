"""Gate: a temp file that is renamed onto a target must have a unique name.

The durable shape for "replace this file atomically" is
:func:`tempfile.mkstemp` in the target's own directory followed by
``Path.replace``. The unsafe shape — and the one this gate scans for —
derives the temp path *deterministically* from the target
(``path.with_suffix(".tmp")``, ``dir / f"{name}.tmp"``,
``path.parent / (path.name + ".tmp")``) and then renames it into place.

Two processes writing the same target then pick the *same* temp path.
One truncates the other's partial write and the rename publishes
whichever half won. Confirmed in the library review under class G1:
two OS processes x 20 ``remember()`` calls landed **22 of 40** records
(45% silently lost), with the loser's run emitting a
``findings.jsonl.tmp -> findings.jsonl`` ENOENT as the tell.

The memory layer was fixed in the tier-1 PR. This gate is the mechanical
guard so the class cannot reappear anywhere in the tree — it scans the
shipped source rather than pinning a list of known sites, because a list
cannot stop the class showing up in a module nobody has written yet.

Reference implementation: :func:`attune.memory.atomic_io.atomic_write_text`.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "attune"
REPO_ROOT = SRC_ROOT.parent.parent

#: Producing the temp name through one of these makes it unique per call,
#: which is the whole point — such a function is never a G1 site.
_UNIQUE_MAKERS = {"mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryDirectory"}

#: Publishing calls. A deterministic ``.tmp`` that is never renamed onto
#: a target is scratch, not a publish step, and is out of scope.
_PUBLISH = {"replace", "rename", "move"}


def _ends_with_tmp(node: ast.AST) -> bool:
    """True if the expression's literal tail is a ``.tmp`` suffix.

    Covers a plain constant (``".tmp"``, ``".json.tmp"``), an f-string
    whose final piece is a ``.tmp`` literal, and ``a + ".tmp"``.
    """
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and node.value.endswith(".tmp")
    if isinstance(node, ast.JoinedStr):
        tail = node.values[-1] if node.values else None
        return isinstance(tail, ast.Constant) and str(tail.value).endswith(".tmp")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _ends_with_tmp(node.right)
    return False


def _builds_deterministic_tmp(node: ast.AST) -> bool:
    """True if this expression builds a ``.tmp`` path from literal text."""
    for sub in ast.walk(node):
        # dir / f"{name}.tmp"   |   path.parent / (path.name + ".tmp")
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div):
            if _ends_with_tmp(sub.right):
                return True
        # path.with_suffix(".tmp") | .with_suffix(path.suffix + ".tmp")
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr == "with_suffix" and sub.args:
                if _ends_with_tmp(sub.args[0]):
                    return True
    return False


def _uses_unique_maker(fn: ast.AST) -> bool:
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in _UNIQUE_MAKERS:
                return True
    return False


def _publishes(fn: ast.AST) -> bool:
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in _PUBLISH:
                return True
    return False


def _offending_sites(path: Path) -> list[str]:
    """Return ``file:line`` for each deterministic-tmp publish in ``path``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if _uses_unique_maker(node) or not _publishes(node):
            continue
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.Assign | ast.AnnAssign) or stmt.value is None:
                continue
            if _builds_deterministic_tmp(stmt.value):
                hits.append(f"{_label(path)}:{stmt.lineno}")
    return hits


def _label(path: Path) -> str:
    """Repo-relative path when possible; the fixtures live outside it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shipped_modules() -> list[Path]:
    return sorted(p for p in SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def test_no_deterministic_tmp_publish() -> None:
    """No shipped module may rename a deterministically-named temp file."""
    offenders: list[str] = []
    for module in _shipped_modules():
        offenders.extend(_offending_sites(module))

    assert not offenders, (
        "Deterministic temp-file publish (class G1) found at:\n  "
        + "\n  ".join(offenders)
        + "\n\nTwo processes writing the same target pick the SAME temp path; "
        "one truncates the other's partial write and the rename publishes "
        "whichever half won.\nUse tempfile.mkstemp in the target's directory "
        "then Path.replace — see attune.memory.atomic_io.atomic_write_text."
    )


def test_rule_flags_the_unsafe_shape(tmp_path: Path) -> None:
    """The rule must fire on the shape the class is defined by."""
    module = tmp_path / "offender.py"
    module.write_text(
        "from pathlib import Path\n"
        "def save(path: Path, text: str) -> None:\n"
        "    tmp = path.with_suffix('.tmp')\n"
        "    tmp.write_text(text)\n"
        "    tmp.replace(path)\n",
        encoding="utf-8",
    )
    assert _offending_sites(module), "rule failed to flag a with_suffix('.tmp') publish"

    joined = tmp_path / "offender_fstring.py"
    joined.write_text(
        "from pathlib import Path\n"
        "def save(d: Path, name: str, text: str) -> None:\n"
        "    tmp = d / f'{name}.json.tmp'\n"
        "    tmp.write_text(text)\n"
        "    tmp.replace(d / name)\n",
        encoding="utf-8",
    )
    assert _offending_sites(joined), "rule failed to flag an f-string .tmp publish"


def test_rule_clears_the_safe_shape(tmp_path: Path) -> None:
    """The reference implementation must not be flagged."""
    module = tmp_path / "safe.py"
    module.write_text(
        "import os, tempfile\n"
        "from pathlib import Path\n"
        "def save(path: Path, text: str) -> None:\n"
        "    fd, name = tempfile.mkstemp(suffix='.tmp', dir=str(path.parent))\n"
        "    tmp = Path(name)\n"
        "    with os.fdopen(fd, 'w') as fh:\n"
        "        fh.write(text)\n"
        "    tmp.replace(path)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module), "rule false-positived on mkstemp"


def test_reference_implementation_is_clean() -> None:
    """The real atomic writer this gate points offenders at must pass."""
    assert not _offending_sites(SRC_ROOT / "memory" / "atomic_io.py")


@pytest.mark.parametrize("scratch", [".tmp scratch never renamed"])
def test_scratch_tmp_is_out_of_scope(tmp_path: Path, scratch: str) -> None:
    """A deterministic .tmp that is never published is not this class."""
    module = tmp_path / "scratch.py"
    module.write_text(
        "from pathlib import Path\n"
        "def cache(path: Path, text: str) -> None:\n"
        "    tmp = path.with_suffix('.tmp')\n"
        "    tmp.write_text(text)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module), scratch
