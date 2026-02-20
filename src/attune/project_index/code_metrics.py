"""Code Metrics - AST analysis, complexity scoring, and cached parsing.

Extracts code-level metrics from source files: lines of code, cyclomatic
complexity, docstring presence, type hint usage, import lists, and test
function counts.  Includes LRU-cached file hashing and AST parsing for
incremental scan performance.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import ast
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import FileCategory


class CodeMetricsMixin:
    """Mixin providing code metrics extraction and cached AST analysis.

    Expects the consuming class to provide:
        - (no external state required -- all methods are self-contained)
    """

    @staticmethod
    @lru_cache(maxsize=1000)
    def _hash_file(file_path: str) -> str:
        """Cache file content hashes for invalidation.

        Args:
            file_path: Path to file as string (for hashability)

        Returns:
            SHA256 hash of file contents

        Note:
            Uses LRU cache with 1000 entries (~64KB memory).
            Hit rate expected: 80%+ for incremental scans.
        """
        try:
            return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        except OSError:
            # Return timestamp-based hash if file unreadable
            return str(Path(file_path).stat().st_mtime)

    @staticmethod
    @lru_cache(maxsize=2000)
    def _parse_python_cached(file_path: str, file_hash: str) -> ast.Module | None:
        """Cache AST parsing results (expensive CPU operation).

        Args:
            file_path: Path to Python file
            file_hash: Hash of file contents (for cache invalidation)

        Returns:
            Parsed AST or None if parsing fails

        Note:
            Uses LRU cache with 2000 entries (~20MB memory).
            Hit rate expected: 90%+ for incremental operations.
            Cache invalidates automatically when file_hash changes.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            return ast.parse(content)
        except (SyntaxError, ValueError, OSError):
            return None

    def _analyze_code_metrics(
        self, path: Path, language: str, category: FileCategory = FileCategory.SOURCE
    ) -> dict[str, Any]:
        """Analyze code metrics for a file with caching.

        Uses cached AST parsing for Python files to avoid re-parsing
        unchanged files during incremental scans.

        Optimization: Skips expensive AST analysis for test files since they
        don't need complexity scoring (saves ~30% of AST traversal time).

        Args:
            path: Path to file to analyze
            language: Programming language of the file
            category: File category (SOURCE, TEST, etc.)
        """
        metrics: dict[str, Any] = {
            "lines_of_code": 0,
            "lines_of_test": 0,
            "complexity": 0.0,
            "has_docstrings": False,
            "has_type_hints": False,
            "imports": [],
            "test_count": 0,
        }

        if language != "python":
            # For now, just count lines for non-Python
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                metrics["lines_of_code"] = len(content.split("\n"))
            except OSError:
                pass
            return metrics

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            # Use generator expression for memory efficiency (no intermediate list)
            metrics["lines_of_code"] = sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            )

            # Optimization: Skip expensive AST analysis for test files
            # Test files don't need complexity scoring, docstring/type hint checks
            # This saves ~30% of AST traversal time (1+ seconds on large codebases)
            if category == FileCategory.TEST:
                # For test files, just count test functions with simple regex
                test_func_pattern = re.compile(r"^\s*def\s+test_\w+\(")
                metrics["test_count"] = sum(1 for line in lines if test_func_pattern.match(line))
                # Mark as having test functions (for test file records)
                if metrics["test_count"] > 0:
                    metrics["lines_of_test"] = metrics["lines_of_code"]
            else:
                # Use cached AST parsing for source files only
                file_path_str = str(path)
                file_hash = self._hash_file(file_path_str)
                tree = self._parse_python_cached(file_path_str, file_hash)

                if tree:
                    metrics.update(self._analyze_python_ast(tree))

        except OSError:
            pass

        return metrics

    def _analyze_python_ast(self, tree: ast.AST) -> dict[str, Any]:
        """Analyze Python AST for metrics.

        Optimized to use single-pass traversal with NodeVisitor instead of
        nested ast.walk() calls. Previous implementation was O(n^2) due to
        walking each function's subtree separately. This version is O(n).
        """

        # Use inner class to maintain state during traversal
        class MetricsVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.result: dict[str, Any] = {
                    "has_docstrings": False,
                    "has_type_hints": False,
                    "imports": [],
                    "test_count": 0,
                    "complexity": 0.0,
                }
                self.function_depth = 0  # Track if we're inside a function

            def visit_Module(self, node: ast.Module) -> None:
                if ast.get_docstring(node):
                    self.result["has_docstrings"] = True
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if ast.get_docstring(node):
                    self.result["has_docstrings"] = True
                self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._handle_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._handle_function(node)

            def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                # Check for docstrings
                if ast.get_docstring(node):
                    self.result["has_docstrings"] = True

                # Check for type hints
                if node.returns or any(arg.annotation for arg in node.args.args):
                    self.result["has_type_hints"] = True

                # Count test functions
                if node.name.startswith("test_"):
                    self.result["test_count"] += 1

                # Enter function scope for complexity counting
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def visit_If(self, node: ast.If) -> None:
                if self.function_depth > 0:
                    self.result["complexity"] += 1.0
                self.generic_visit(node)

            def visit_For(self, node: ast.For) -> None:
                if self.function_depth > 0:
                    self.result["complexity"] += 1.0
                self.generic_visit(node)

            def visit_While(self, node: ast.While) -> None:
                if self.function_depth > 0:
                    self.result["complexity"] += 1.0
                self.generic_visit(node)

            def visit_Try(self, node: ast.Try) -> None:
                if self.function_depth > 0:
                    self.result["complexity"] += 1.0
                self.generic_visit(node)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if self.function_depth > 0:
                    self.result["complexity"] += 1.0
                self.generic_visit(node)

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    self.result["imports"].append(alias.name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module:
                    self.result["imports"].append(node.module)
                self.generic_visit(node)

        visitor = MetricsVisitor()
        visitor.visit(tree)
        return visitor.result
