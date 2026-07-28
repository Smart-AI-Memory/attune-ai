"""Shared authoritative import resolver for doc fact-checking.

The single import-verdict implementation behind BOTH doc gates
(consolidation spec Step 2 / #1191 T1, tracked by #1586):

- ``scripts/audit_doc_imports.py`` (the CI doc-import gate) delegates
  its statement resolution here after preparing ``sys.path``.
- ``fact_check/python_refs.py`` (the master fact-check) resolves its
  code-fence imports and prose dotted paths through the same
  primitives.

The authority mechanism is ``ensure_src_on_path``: resolving against
the repo's own ``src/`` tree first, immune to the editable-install
MAPPING trap where the active venv points ``attune`` at a different
checkout (the "line-115" false-positive class — a symbol present in
the repo being checked reported as unresolvable because the venv
resolved a stale sibling checkout). Note the inherent limit: a
``sys.path`` insert cannot rebind modules ALREADY imported into the
running process — fresh processes (the audit script, authoring CLI
runs) get the full guarantee; long-lived processes keep their loaded
modules.

Resolution is import-only: modules are imported and attributes checked
with ``hasattr``/``getattr``; fence bodies are never executed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    """Walk up from ``start`` to the enclosing repo root, if any.

    A repo root is a directory holding both ``pyproject.toml`` and a
    ``src/`` directory — the layout whose in-repo source should win
    import resolution. Returns ``None`` when no such ancestor exists.
    """
    node = start.resolve()
    if node.is_file():
        node = node.parent
    for candidate in (node, *node.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "src").is_dir():
            return candidate
    return None


def ensure_src_on_path(repo_root: Path | None) -> None:
    """Put ``<repo_root>/src`` first on ``sys.path`` (idempotent).

    Call BEFORE resolving imports so not-yet-loaded modules resolve
    against the repo's own source rather than whatever the active
    venv's editable mapping points at. A no-op when ``repo_root`` is
    ``None`` or has no ``src/`` directory.
    """
    if repo_root is None:
        return
    src = repo_root / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def resolve_import_statement(statement: str) -> str | None:
    """Return an error message if ``statement`` does not resolve, else None.

    Handles ``import MOD [as A]`` and ``from MOD import A, B as C``.
    Import-only and in-process: imports the module and checks each name
    with ``hasattr``.
    """
    try:
        if statement.startswith("import "):
            mod = statement[len("import ") :].split(" as ")[0].strip()
            importlib.import_module(mod)
            return None
        # from MOD import A, B as C, ...
        head, _, tail = statement.partition(" import ")
        mod = head[len("from ") :].strip()
        module = importlib.import_module(mod)
        missing = []
        for piece in tail.split(","):
            name = piece.strip().split(" as ")[0].strip()
            if name and name != "*" and not hasattr(module, name):
                missing.append(name)
        if missing:
            return f"{mod} has no attribute(s): {', '.join(missing)}"
        return None
    except ModuleNotFoundError as e:
        return f"ModuleNotFoundError: {e}"
    except ImportError as e:
        return f"ImportError: {e}"
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: a doc import that blows up any other way (e.g. a
        # module-level error) is still a broken fence the reader would hit.
        return f"{type(e).__name__}: {e}"


def try_import(module: str) -> bool:
    """Best-effort import test. Returns True if importable."""
    try:
        importlib.import_module(module)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any failure (ImportError, syntax error in a
        # broken dep, ValueError on a bad dotted path) means the
        # reference is unresolvable — exactly what the doc author
        # needs surfaced.
        return False
    return True


def resolve_attr(module_path: str, attr: str) -> bool:
    """Import ``module_path`` and verify ``attr`` exists on it."""
    try:
        module = importlib.import_module(module_path)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: unimportable module == unresolvable attribute.
        return False
    return hasattr(module, attr)


def resolve_dotted(path: str) -> bool:
    """Resolve a full dotted path like ``attune.ops._readers.Foo``.

    Walks from longest module prefix down: tries to import each
    prefix; if a prefix imports, checks that the suffix attribute
    chain exists on the resulting object.
    """
    parts = path.split(".")
    # Try progressively shorter module prefixes.
    for split in range(len(parts), 0, -1):
        module_path = ".".join(parts[:split])
        try:
            obj = importlib.import_module(module_path)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: a shorter prefix may still import; keep walking.
            continue
        # Walk remaining attributes.
        ok = True
        for attr in parts[split:]:
            if not hasattr(obj, attr):
                ok = False
                break
            obj = getattr(obj, attr)
        if ok:
            return True
    return False
