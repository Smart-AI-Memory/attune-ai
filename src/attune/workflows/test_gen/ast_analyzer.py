"""AST-based Function and Class Analyzer.

Extracts function signatures, exception types, side effects, and complexity
from Python source code using AST parsing.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import ast

from .data_models import ClassSignature, FunctionSignature


class ASTFunctionAnalyzer(ast.NodeVisitor):
    """AST-based function analyzer for accurate test generation.

    Extracts:
    - Function signatures with types
    - Exception types raised
    - Side effects detection
    - Complexity estimation

    Parse errors are tracked in the `last_error` attribute for debugging.
    """

    def __init__(self):
        """Initialize the analyzer with empty function and class lists."""
        self.functions: list[FunctionSignature] = []
        self.classes: list[ClassSignature] = []
        self._current_class: str | None = None
        self.last_error: str | None = None  # Track parse errors for debugging

    def analyze(
        self,
        code: str,
        file_path: str = "",
    ) -> tuple[list[FunctionSignature], list[ClassSignature]]:
        """Analyze code and extract function/class signatures.

        Args:
            code: Python source code to analyze
            file_path: Optional file path for error reporting

        Returns:
            Tuple of (functions, classes) lists. If parsing fails,
            returns empty lists and sets self.last_error with details.

        """
        self.last_error = None
        try:
            tree = ast.parse(code)
            self.functions = []
            self.classes = []
            self.visit(tree)
            return self.functions, self.classes
        except SyntaxError as e:
            # Track the error for debugging instead of silent failure
            location = f" at line {e.lineno}" if e.lineno else ""
            file_info = f" in {file_path}" if file_path else ""
            self.last_error = f"SyntaxError{file_info}{location}: {e.msg}"
            return [], []
        except ValueError as e:
            # ast.parse rejects a null byte with ValueError, which
            # carries no .msg/.lineno — record it the same way rather
            # than letting it escape to the caller.
            file_info = f" in {file_path}" if file_path else ""
            self.last_error = f"ValueError{file_info}: {e}"
            return [], []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function signature."""
        if self._current_class is None:  # Only top-level functions
            sig = self._extract_function_signature(node)
            self.functions.append(sig)
            # Don't visit nested functions - we only want top-level
        else:
            # Inside a class - this is a method, visit it
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function signature."""
        if self._current_class is None:
            sig = self._extract_function_signature(node, is_async=True)
            self.functions.append(sig)
            # Don't visit nested functions - we only want top-level
        else:
            # Inside a class - this is a method, visit it
            self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class signature with methods."""
        self._current_class = node.name
        methods = []
        init_params: list[tuple[str, str, str | None]] = []

        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(ast.unparse(base))

        # Detect if this is an Enum
        enum_bases = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "auto"}
        is_enum = any(b in enum_bases for b in base_classes)

        # Detect if this is a dataclass
        is_dataclass = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                is_dataclass = True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
                    is_dataclass = True

        # Process methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                method_sig = self._extract_function_signature(
                    item,
                    is_async=isinstance(item, ast.AsyncFunctionDef),
                )
                methods.append(method_sig)

                # Extract __init__ params
                if item.name == "__init__":
                    init_params = method_sig.params[1:]  # Skip 'self'

        # Count required init params (those without defaults)
        required_init_params = sum(1 for p in init_params if p[2] is None)

        self.classes.append(
            ClassSignature(
                name=node.name,
                methods=methods,
                init_params=init_params,
                base_classes=base_classes,
                docstring=ast.get_docstring(node),
                is_enum=is_enum,
                is_dataclass=is_dataclass,
                required_init_params=required_init_params,
            ),
        )

        self._current_class = None
        # Don't call generic_visit to avoid processing methods again

    def _extract_function_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool = False,
    ) -> FunctionSignature:
        """Extract detailed signature from function node."""
        # Extract parameters with types and defaults
        params = []
        defaults = list(node.args.defaults)
        num_defaults = len(defaults)
        num_args = len(node.args.args)

        for i, arg in enumerate(node.args.args):
            param_name = arg.arg
            param_type = ast.unparse(arg.annotation) if arg.annotation else "Any"

            # Calculate default index
            default_idx = i - (num_args - num_defaults)
            default_val = None
            if default_idx >= 0:
                try:
                    default_val = ast.unparse(defaults[default_idx])
                except Exception:  # noqa: BLE001
                    default_val = "..."

            params.append((param_name, param_type, default_val))

        # Extract return type
        return_type = ast.unparse(node.returns) if node.returns else None

        # Find raised exceptions
        raises: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                if isinstance(child.exc, ast.Call):
                    if isinstance(child.exc.func, ast.Name):
                        raises.add(child.exc.func.id)
                    elif isinstance(child.exc.func, ast.Attribute):
                        raises.add(child.exc.func.attr)
                elif isinstance(child.exc, ast.Name):
                    raises.add(child.exc.id)

        # Detect side effects (simple heuristic)
        has_side_effects = self._detect_side_effects(node)

        # Estimate complexity
        complexity = self._estimate_complexity(node)

        # Extract decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(ast.unparse(dec))
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)

        return FunctionSignature(
            name=node.name,
            params=params,
            return_type=return_type,
            is_async=is_async or isinstance(node, ast.AsyncFunctionDef),
            raises=raises,
            has_side_effects=has_side_effects,
            docstring=ast.get_docstring(node),
            complexity=complexity,
            decorators=decorators,
        )

    def _detect_side_effects(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Detect if function has side effects (writes to files, global state, etc.)."""
        side_effect_names = {
            "print",
            "write",
            "open",
            "save",
            "delete",
            "remove",
            "update",
            "insert",
            "execute",
            "send",
            "post",
            "put",
            "patch",
        }

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id.lower() in side_effect_names:
                        return True
                elif isinstance(child.func, ast.Attribute):
                    if child.func.attr.lower() in side_effect_names:
                        return True
        return False

    def _estimate_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Estimate cyclomatic complexity (simplified)."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
