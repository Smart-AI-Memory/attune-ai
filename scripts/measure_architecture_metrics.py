"""Measure the numbers in ``docs/ARCHITECTURE.md`` from the tree.

The architecture doc's metric tables drift silently: the previous pair
was stamped v11.0.0 and still claimed 23,597 tests when the suite
collected 25,510, and gave the ``mcp`` row a tool count in a column
that means dependents. Numbers nobody can re-derive cannot be checked,
so this script IS the method the doc cites.

Run before a major and paste the output into the two tables::

    python scripts/measure_architecture_metrics.py

Read-only: it parses source and writes nothing.
"""

from __future__ import annotations

import ast
import collections
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "attune"

#: Rows of the coupling table, in display order after sorting by count.
TRACKED_MODULES = (
    "attune.security.path_validation",
    "attune.models",
    "attune.memory",
    "attune.workflows",
    "attune.config",
    "attune.telemetry",
    "attune.meta_workflows",
    "attune.mcp",
)


def _dotted_name(path: pathlib.Path) -> str:
    """Return the ``attune.x.y`` module name for a source file."""
    parts = list(path.relative_to(SRC.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imported_targets(node: ast.AST, package: str) -> list[str]:
    """Return the module names one import statement refers to.

    Relative imports are resolved against ``package`` so that a
    subpackage's ``from .config import X`` is not miscounted as a
    dependency on the top-level ``attune.config``.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if not node.level:
        return [node.module] if node.module else []
    base = package.split(".")
    if node.level > 1:
        base = base[: len(base) - (node.level - 1)]
    return [".".join(base + ([node.module] if node.module else []))]


def measure() -> dict[str, object]:
    """Walk the tree once and return every number the doc reports."""
    files = sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))
    functions = classes = lines = 0
    dependents: dict[str, set[str]] = collections.defaultdict(set)

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines += text.count("\n") + (0 if text.endswith("\n") else 1)
        tree = ast.parse(text)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1

        module = _dotted_name(path)
        package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            for target in _imported_targets(node, package):
                if not target.startswith("attune"):
                    continue
                # Credit the target and every ancestor package: importing
                # attune.memory.store is a dependency on attune.memory too.
                parts = target.split(".")
                for i in range(2, len(parts) + 1):
                    dependents[".".join(parts[:i])].add(str(path))

    return {
        "files": len(files),
        "lines": lines,
        "functions": functions,
        "classes": classes,
        "subpackages": len({p.parent for p in files if (p.parent / "__init__.py").exists()}),
        "dependents": dependents,
    }


def _count_external(dependents: dict[str, set[str]], module: str) -> int:
    """Dependents of ``module`` excluding files inside the module itself."""
    prefix = str(SRC.parent / module.replace(".", "/"))
    return sum(1 for f in dependents.get(module, ()) if not f.startswith(prefix))


def main() -> None:
    """Print both ARCHITECTURE.md tables' values."""
    m = measure()
    print("Codebase Metrics")
    print(f"  Python files              {m['files']:,}")
    print(f"  Lines of code             {m['lines']:,}")
    print(f"  Functions (incl. methods) {m['functions']:,}")
    print(f"  Classes                   {m['classes']:,}")
    print(f"  Subpackages               {m['subpackages']:,}")
    print("  Tests                     run: pytest tests --collect-only -q")
    print()
    print("Key Coupling Metrics")
    deps = m["dependents"]
    assert isinstance(deps, dict)
    rows = [(mod, _count_external(deps, mod)) for mod in TRACKED_MODULES]
    for mod, count in sorted(rows, key=lambda r: -r[1]):
        print(f"  {mod.removeprefix('attune.'):28s} {count:4d}")


if __name__ == "__main__":
    main()
