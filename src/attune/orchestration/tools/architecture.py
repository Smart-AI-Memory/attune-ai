"""Architecture tools — dependency mapping and modularity analysis.

Analyzes Python package structure for circular imports, module
coupling, and package depth. All checks are static (AST-based)
with no LLM calls.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureReport:
    """Architecture analysis report."""

    score: float  # 0-10
    total_modules: int
    total_packages: int
    max_depth: int
    circular_imports: list[tuple[str, str]]
    high_coupling: list[dict[str, int]]  # modules with many imports
    passed: bool
    details: dict[str, int] = field(default_factory=dict)


class RealArchitectureAnalyzer:
    """Static architecture analysis for Python projects.

    Checks:
        - Circular import detection (A imports B, B imports A)
        - Module coupling (files importing too many siblings)
        - Package depth (deeply nested packages)
        - Overall modularity score
    """

    # Modules importing more than this are "high coupling"
    COUPLING_THRESHOLD = 15

    def __init__(self, project_root: str = ".") -> None:
        """Initialize architecture analyzer.

        Args:
            project_root: Project root directory.

        """
        self.project_root = Path(project_root).resolve()

    def analyze(self, target_path: str = "src") -> ArchitectureReport:
        """Run architecture analysis.

        Args:
            target_path: Path to analyze (default: src).

        Returns:
            ArchitectureReport with modularity metrics.

        """
        root = self.project_root / target_path
        if not root.exists():
            logger.warning("Target path does not exist: %s", root)
            return ArchitectureReport(
                score=5.0,
                total_modules=0,
                total_packages=0,
                max_depth=0,
                circular_imports=[],
                high_coupling=[],
                passed=True,
            )

        py_files = list(root.rglob("*.py"))
        if not py_files:
            return ArchitectureReport(
                score=10.0,
                total_modules=0,
                total_packages=0,
                max_depth=0,
                circular_imports=[],
                high_coupling=[],
                passed=True,
            )

        # Build import graph
        import_graph = self._build_import_graph(py_files, root)

        # Detect circular imports
        circular = self._find_circular_imports(import_graph)

        # Detect high coupling
        high_coupling = [
            {"module": mod, "import_count": len(imports)}
            for mod, imports in import_graph.items()
            if len(imports) > self.COUPLING_THRESHOLD
        ]

        # Calculate package depth
        packages = {f.parent for f in py_files if f.name == "__init__.py"}
        max_depth = 0
        for pkg in packages:
            try:
                depth = len(pkg.relative_to(root).parts)
            except ValueError:
                depth = 0
            max_depth = max(max_depth, depth)

        # Score: start at 10, deduct for issues
        score = 10.0
        score -= min(len(circular) * 1.5, 5.0)  # -1.5 per circular, max -5
        score -= min(len(high_coupling) * 0.5, 3.0)  # -0.5 per coupled, max -3
        if max_depth > 6:
            score -= 1.0  # Penalize very deep nesting
        score = max(score, 0.0)

        passed = len(circular) == 0 and score >= 7.0

        logger.info(
            "Architecture analysis: %d modules, %d packages, "
            "%d circular imports, %d high-coupling modules, score=%.1f",
            len(py_files),
            len(packages),
            len(circular),
            len(high_coupling),
            score,
        )

        return ArchitectureReport(
            score=score,
            total_modules=len(py_files),
            total_packages=len(packages),
            max_depth=max_depth,
            circular_imports=circular,
            high_coupling=high_coupling,
            passed=passed,
            details={
                "total_imports": sum(len(v) for v in import_graph.values()),
                "avg_imports": (
                    sum(len(v) for v in import_graph.values()) / len(import_graph)
                    if import_graph
                    else 0
                ),
            },
        )

    def _build_import_graph(self, py_files: list[Path], root: Path) -> dict[str, set[str]]:
        """Build a module-level import graph.

        Args:
            py_files: Python files to analyze.
            root: Root directory for module name resolution.

        Returns:
            Dict mapping module name to set of imported module names.

        """
        graph: dict[str, set[str]] = {}
        for py_file in py_files:
            mod_name = self._path_to_module(py_file, root)
            imports = self._extract_imports(py_file)
            graph[mod_name] = imports
        return graph

    def _path_to_module(self, py_file: Path, root: Path) -> str:
        """Convert a file path to a dotted module name.

        Args:
            py_file: Path to Python file.
            root: Root directory.

        Returns:
            Dotted module name string.

        """
        try:
            rel = py_file.relative_to(root)
        except ValueError:
            return py_file.stem

        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else py_file.stem

    def _extract_imports(self, py_file: Path) -> set[str]:
        """Extract import targets from a Python file.

        Args:
            py_file: Path to Python file.

        Returns:
            Set of top-level module names imported.

        """
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (
            SyntaxError,
            UnicodeDecodeError,
            OSError,
            ValueError,
        ) as exc:  # ast.parse: null bytes -> ValueError, not SyntaxError
            logger.debug("Skipping %s: %s", py_file, exc)
            return set()

        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Take top-level package
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])
        return imports

    def _find_circular_imports(self, graph: dict[str, set[str]]) -> list[tuple[str, str]]:
        """Find direct circular imports (A->B and B->A).

        Args:
            graph: Import graph from _build_import_graph.

        Returns:
            List of (module_a, module_b) circular pairs.

        """
        circular: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for mod_a, imports_a in graph.items():
            for mod_b in imports_a:
                if mod_b in graph and mod_a in graph[mod_b]:
                    pair = tuple(sorted((mod_a, mod_b)))
                    if pair not in seen:
                        seen.add(pair)
                        circular.append(pair)
        return circular
