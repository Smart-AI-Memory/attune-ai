"""AST Skeleton Generator for Attune AI.

Parses Python source code and generates compressed structural skeletons
by preserving class contracts, function signatures, docstrings, and type
hints while stripping method bodies.
"""

import ast
import logging

logger = logging.getLogger(__name__)


class ASTSkeletonGenerator:
    """Generates structural AST code skeletons to optimize LLM context usage."""

    def __init__(self, strip_docstrings: bool = False) -> None:
        """Initialize ASTSkeletonGenerator.

        Args:
            strip_docstrings: If True, also strips module, class, and
                function docstrings for maximum compression.
        """
        self.strip_docstrings = strip_docstrings

    def generate_skeleton(self, source_code: str) -> str:
        """Parses source code string and returns a compressed skeleton.

        Args:
            source_code: Raw Python code string.

        Returns:
            Compressed skeletal Python code string; the original source
            when it cannot be parsed or re-rendered.
        """
        if not source_code or not source_code.strip():
            return ""

        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            logger.debug("skeleton: source does not parse, passing through: %s", exc)
            return source_code

        transformer = _SkeletonTransformer(strip_docstrings=self.strip_docstrings)
        transformed_tree = transformer.visit(tree)
        ast.fix_missing_locations(transformed_tree)

        try:
            return ast.unparse(transformed_tree)
        except (ValueError, TypeError, RecursionError) as exc:
            logger.debug("skeleton: unparse failed, passing through: %s", exc)
            return source_code


class _SkeletonTransformer(ast.NodeTransformer):
    """Replaces function bodies with ``...`` and optionally drops docstrings."""

    def __init__(self, strip_docstrings: bool = False) -> None:
        super().__init__()
        self.strip_docstrings = strip_docstrings

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.generic_visit(node)
        if self.strip_docstrings:
            self._drop_docstring(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        if self.strip_docstrings:
            self._drop_docstring(node)
            if not node.body:
                node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        return self._transform_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self._transform_callable(node)

    def _transform_callable(self, node):
        self.generic_visit(node)
        docstring = ast.get_docstring(node)

        new_body = []
        if docstring and not self.strip_docstrings:
            new_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
        node.body = new_body
        return node

    @staticmethod
    def _drop_docstring(node: ast.Module | ast.ClassDef) -> None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:]
