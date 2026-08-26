"""AST-based API signature extractor for accurate test generation.

This module parses Python source code to extract exact API signatures,
preventing LLM from guessing parameter names incorrectly.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FunctionSignature:
    """Extracted function signature."""

    name: str
    params: list[str]
    param_types: dict[str, str]
    return_type: str | None
    is_method: bool
    is_static: bool
    is_classmethod: bool
    docstring: str | None


@dataclass
class ClassSignature:
    """Extracted class signature."""

    name: str
    bases: list[str]
    is_dataclass: bool
    attributes: dict[str, str]  # name -> type annotation
    methods: list[FunctionSignature]
    init_params: list[str]
    properties: list[str]  # computed properties - DON'T pass to constructor
    docstring: str | None


class APIExtractor(ast.NodeVisitor):
    """Extract API signatures from Python AST."""

    def __init__(self):
        self.classes: list[ClassSignature] = []
        self.functions: list[FunctionSignature] = []
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class signature."""
        # Check if dataclass
        is_dataclass = any(
            isinstance(dec, ast.Name)
            and dec.id == "dataclass"
            or isinstance(dec, ast.Attribute)
            and dec.attr == "dataclass"
            for dec in node.decorator_list
        )

        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        # Extract attributes (for dataclasses)
        attributes = {}
        properties = []
        methods = []
        init_params = []

        for item in node.body:
            # Dataclass field annotations
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_name = item.target.id
                attr_type = ast.unparse(item.annotation) if item.annotation else "Any"
                attributes[attr_name] = attr_type
                if is_dataclass:
                    init_params.append(attr_name)

            # Methods
            elif isinstance(item, ast.FunctionDef):
                # Check if property
                is_property = any(
                    isinstance(dec, ast.Name) and dec.id == "property"
                    for dec in item.decorator_list
                )

                if is_property:
                    properties.append(item.name)
                else:
                    # Extract method signature
                    method_sig = self._extract_function(item, is_method=True)
                    methods.append(method_sig)

                    # Track __init__ params
                    if item.name == "__init__":
                        init_params = [arg.arg for arg in item.args.args if arg.arg != "self"]

        # Get docstring
        docstring = ast.get_docstring(node)

        class_sig = ClassSignature(
            name=node.name,
            bases=bases,
            is_dataclass=is_dataclass,
            attributes=attributes,
            methods=methods,
            init_params=init_params,
            properties=properties,
            docstring=docstring,
        )

        self.classes.append(class_sig)
        self._current_class = node.name

        # Continue visiting
        self.generic_visit(node)
        self._current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function signature (top-level functions only)."""
        if self._current_class is None:
            func_sig = self._extract_function(node, is_method=False)
            self.functions.append(func_sig)

        self.generic_visit(node)

    def _extract_function(self, node: ast.FunctionDef, is_method: bool) -> FunctionSignature:
        """Extract function/method signature details."""
        # Check decorators
        is_static = any(
            isinstance(dec, ast.Name) and dec.id == "staticmethod" for dec in node.decorator_list
        )
        is_classmethod = any(
            isinstance(dec, ast.Name) and dec.id == "classmethod" for dec in node.decorator_list
        )

        # Extract parameters
        params = []
        param_types = {}

        for arg in node.args.args:
            # Skip self/cls
            if arg.arg in ("self", "cls"):
                continue

            params.append(arg.arg)

            # Get type annotation
            if arg.annotation:
                param_types[arg.arg] = ast.unparse(arg.annotation)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Get docstring
        docstring = ast.get_docstring(node)

        return FunctionSignature(
            name=node.name,
            params=params,
            param_types=param_types,
            return_type=return_type,
            is_method=is_method,
            is_static=is_static,
            is_classmethod=is_classmethod,
            docstring=docstring,
        )


def extract_api_signatures(
    source_code: str,
) -> tuple[list[ClassSignature], list[FunctionSignature]]:
    """Extract API signatures from Python source code.

    Args:
        source_code: Python source code string

    Returns:
        Tuple of (classes, functions)
    """
    try:
        tree = ast.parse(source_code)
        extractor = APIExtractor()
        extractor.visit(tree)
        return extractor.classes, extractor.functions
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Invalid Python syntax: {e}") from e


def format_api_docs(classes: list[ClassSignature], functions: list[FunctionSignature]) -> str:
    """Format API signatures as documentation for LLM prompt.

    Args:
        classes: Extracted class signatures
        functions: Extracted function signatures

    Returns:
        Formatted API documentation string
    """
    docs = []

    docs.append("# EXTRACTED API SIGNATURES (USE THESE EXACT NAMES)")
    docs.append("=" * 70)

    # Document classes
    if classes:
        docs.append("\n## Classes\n")
        for cls in classes:
            docs.append(f"### {cls.name}")

            if cls.is_dataclass:
                docs.append("**Type:** @dataclass")

            if cls.docstring:
                docs.append(f"**Doc:** {cls.docstring.split(chr(10))[0][:80]}")

            # Constructor parameters
            docs.append(f"\n**Constructor Parameters:** {', '.join(cls.init_params)}")

            if cls.attributes:
                docs.append("\n**Attributes:**")
                for name, typ in cls.attributes.items():
                    is_property = (
                        " (COMPUTED - don't pass to __init__)" if name in cls.properties else ""
                    )
                    docs.append(f"  - {name}: {typ}{is_property}")

            # Example usage
            if cls.is_dataclass and cls.init_params:
                params_str = ", ".join(f"{p}=..." for p in cls.init_params[:3])
                if len(cls.init_params) > 3:
                    params_str += ", ..."
                docs.append(f"\n**Usage:** `{cls.name}({params_str})`")

            docs.append("")

    # Document functions
    if functions:
        docs.append("\n## Functions\n")
        for func in functions:
            params_str = ", ".join(f"{p}: {func.param_types.get(p, 'Any')}" for p in func.params)
            return_str = f" -> {func.return_type}" if func.return_type else ""
            docs.append(f"- `{func.name}({params_str}){return_str}`")

    docs.append("\n" + "=" * 70)

    return "\n".join(docs)


if __name__ == "__main__":
    # Test with cost_tracker.py
    test_file = Path("src/attune/cost_tracker.py")
    if test_file.exists():
        source = test_file.read_text()
        classes, functions = extract_api_signatures(source)

        print(format_api_docs(classes, functions))

        print("\n\n# VALIDATION")
        print("=" * 70)
        print(f"Classes found: {len(classes)}")
        print(f"Functions found: {len(functions)}")

        for cls in classes:
            print(f"\n{cls.name}:")
            print(f"  Init params: {cls.init_params}")
            print(f"  Properties (computed): {cls.properties}")
