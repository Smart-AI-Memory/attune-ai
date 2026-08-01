"""Coverage-lane tests for AST Function Analyzer.

Targets branches left uncovered by test_ast_analyzer_coverage_boost.py:
attribute-form base classes, attribute-form raised exceptions,
attribute-form (no-call) decorators, and BoolOp complexity counting.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

import attune.workflows.test_gen.ast_analyzer as ast_analyzer_module

ASTFunctionAnalyzer = ast_analyzer_module.ASTFunctionAnalyzer


@pytest.mark.unit
class TestASTFunctionAnalyzerAttributeBaseClasses:
    """Test base-class extraction when the base is a dotted attribute."""

    def test_attribute_base_class(self):
        """A base class expressed as `module.Name` is unparsed, not skipped."""
        analyzer = ASTFunctionAnalyzer()
        code = """
import abc

class Foo(abc.ABC):
    pass
"""
        _, classes = analyzer.analyze(code)

        assert classes[0].base_classes == ["abc.ABC"]

    def test_mixed_name_and_attribute_base_classes(self):
        """A class with both a plain-name base and an attribute base."""
        analyzer = ASTFunctionAnalyzer()
        code = """
import exceptions

class Local:
    pass

class Combined(Local, exceptions.BaseError):
    pass
"""
        _, classes = analyzer.analyze(code)

        combined = [c for c in classes if c.name == "Combined"][0]
        assert combined.base_classes == ["Local", "exceptions.BaseError"]


@pytest.mark.unit
class TestASTFunctionAnalyzerAttributeExceptions:
    """Test raised-exception detection when the exception is dotted."""

    def test_raise_attribute_call(self):
        """`raise module.CustomError(...)` records the attribute name."""
        analyzer = ASTFunctionAnalyzer()
        code = """
import exceptions

def risky():
    raise exceptions.CustomError("bad")
"""
        functions, _ = analyzer.analyze(code)

        assert "CustomError" in functions[0].raises

    def test_raise_nested_attribute_call(self):
        """A deeper dotted path still records the final attribute segment."""
        analyzer = ASTFunctionAnalyzer()
        code = """
def risky():
    raise pkg.errors.ValidationError("bad")
"""
        functions, _ = analyzer.analyze(code)

        assert "ValidationError" in functions[0].raises


@pytest.mark.unit
class TestASTFunctionAnalyzerAttributeDecorators:
    """Test decorator extraction when the decorator is a dotted attribute (no call)."""

    def test_attribute_decorator_no_call(self):
        """`@module.decorator` (no parentheses) is unparsed, not skipped."""
        analyzer = ASTFunctionAnalyzer()
        code = """
import abc

class Foo:
    @abc.abstractmethod
    def bar(self):
        pass
"""
        _, classes = analyzer.analyze(code)

        assert classes[0].methods[0].decorators == ["abc.abstractmethod"]

    def test_attribute_decorator_on_top_level_function(self):
        """Attribute decorators on top-level functions are also captured."""
        analyzer = ASTFunctionAnalyzer()
        code = """
import functools

@functools.wraps
def wrapped():
    pass
"""
        functions, _ = analyzer.analyze(code)

        assert "functools.wraps" in functions[0].decorators


@pytest.mark.unit
class TestASTFunctionAnalyzerBoolOpComplexity:
    """Test complexity contribution from boolean operators (and/or)."""

    def test_and_expression_increases_complexity(self):
        """A boolean `and` of N operands adds N-1 to complexity."""
        analyzer = ASTFunctionAnalyzer()
        code = """
def with_bool(a, b, c):
    if a and b and c:
        return True
    return False
"""
        functions, _ = analyzer.analyze(code)

        # 1 base + 1 if + 2 (three-operand `and` contributes len(values)-1)
        assert functions[0].complexity == 4

    def test_or_expression_increases_complexity(self):
        """A boolean `or` also contributes len(values)-1 to complexity."""
        analyzer = ASTFunctionAnalyzer()
        code = """
def with_or(a, b):
    return a or b
"""
        functions, _ = analyzer.analyze(code)

        # 1 base + 1 (two-operand `or` contributes len(values)-1 = 1)
        assert functions[0].complexity == 2
