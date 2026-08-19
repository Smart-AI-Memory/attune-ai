"""Unit tests for AST-driven dynamic context budgeting."""

import ast

from attune.context import ASTSkeletonGenerator, TokenBudgetAllocator

SAMPLE_CODE = '''
class DataProcessor:
    """Processes analytical datasets."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.items = []
        for i in range(100):
            self.items.append(i * 2)

    def process(self, data: list) -> dict:
        """Executes data transformation."""
        result = {}
        for x in data:
            result[x] = x ** 2
        return result
'''


class TestASTSkeletonGenerator:
    """Tests for ASTSkeletonGenerator."""

    def test_skeleton_generation_strips_bodies(self) -> None:
        generator = ASTSkeletonGenerator()
        skeleton = generator.generate_skeleton(SAMPLE_CODE)

        assert "class DataProcessor" in skeleton
        assert "def __init__(self, config: dict) -> None:" in skeleton
        assert "def process(self, data: list) -> dict:" in skeleton
        assert "self.items.append" not in skeleton
        assert "result[x] = x ** 2" not in skeleton

    def test_default_mode_retains_docstrings(self) -> None:
        generator = ASTSkeletonGenerator()
        skeleton = generator.generate_skeleton(SAMPLE_CODE)
        assert "Processes analytical datasets." in skeleton
        assert "Executes data transformation." in skeleton

    def test_token_reduction_ratio_with_stripped_docstrings(self) -> None:
        # The 50%+ reduction goal holds in maximum-compression mode;
        # default mode keeps docstrings and lands lower (~47% here).
        generator = ASTSkeletonGenerator(strip_docstrings=True)
        skeleton = generator.generate_skeleton(SAMPLE_CODE)

        compression_ratio = 1.0 - (len(skeleton) / len(SAMPLE_CODE))
        assert compression_ratio >= 0.50

    def test_strip_docstrings_removes_class_docstring(self) -> None:
        generator = ASTSkeletonGenerator(strip_docstrings=True)
        skeleton = generator.generate_skeleton(SAMPLE_CODE)
        assert "Processes analytical datasets." not in skeleton

    def test_unparseable_source_passes_through(self) -> None:
        generator = ASTSkeletonGenerator()
        broken = "def broken(:\n    pass"
        assert generator.generate_skeleton(broken) == broken

    def test_empty_source_returns_empty(self) -> None:
        generator = ASTSkeletonGenerator()
        assert generator.generate_skeleton("") == ""
        assert generator.generate_skeleton("   \n") == ""

    def test_async_functions_skeletonized(self) -> None:
        src = (
            "async def fetch(url: str) -> str:\n"
            '    """Fetches a URL."""\n'
            "    data = await client.get(url)\n"
            "    return data.text\n"
        )
        generator = ASTSkeletonGenerator()
        skeleton = generator.generate_skeleton(src)
        assert "async def fetch(url: str) -> str:" in skeleton
        assert "await client.get" not in skeleton

    def test_strip_docstrings_keeps_docstring_only_class_valid(self) -> None:
        # A class whose entire body is its docstring must get an
        # explicit `...` body, or the skeleton fails to unparse/reparse.
        src = 'class Marker:\n    """Only a docstring."""\n'
        generator = ASTSkeletonGenerator(strip_docstrings=True)
        skeleton = generator.generate_skeleton(src)
        assert "Only a docstring." not in skeleton
        assert "class Marker" in skeleton
        ast.parse(skeleton)  # still valid Python

    def test_unparse_failure_passes_through(self, monkeypatch) -> None:
        def boom(tree):
            raise ValueError("cannot unparse")

        monkeypatch.setattr("attune.context.skeleton.ast.unparse", boom)
        generator = ASTSkeletonGenerator()
        assert generator.generate_skeleton(SAMPLE_CODE) == SAMPLE_CODE


class TestTokenBudgetAllocator:
    """Tests for TokenBudgetAllocator."""

    def test_allocator_prioritizes_primary_target(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=500)
        files = {
            "main.py": SAMPLE_CODE,
            "utils.py": SAMPLE_CODE,
        }

        allocated = allocator.allocate_context(files, primary_target="main.py")

        assert allocated["main.py"] == SAMPLE_CODE  # Retains full source
        assert "self.items.append" not in allocated["utils.py"]  # Skeletal

    def test_budget_exhaustion_emits_stub(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=1)
        files = {"main.py": SAMPLE_CODE, "utils.py": SAMPLE_CODE}

        allocated = allocator.allocate_context(files, primary_target="main.py")

        assert allocated["main.py"] == SAMPLE_CODE  # primary always full
        assert allocated["utils.py"].startswith("# AST skeleton omitted")

    def test_no_primary_target_all_skeletal(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=4000)
        allocated = allocator.allocate_context({"a.py": SAMPLE_CODE})
        assert "self.items.append" not in allocated["a.py"]


class TestFitSource:
    """fit_source ladder: full source → skeleton → truncated skeleton."""

    def test_under_budget_passes_through_unchanged(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=4000)
        assert allocator.fit_source(SAMPLE_CODE) == SAMPLE_CODE

    def test_over_budget_degrades_to_skeleton(self) -> None:
        # SAMPLE_CODE is ~120 estimated tokens; its skeleton is ~65.
        allocator = TokenBudgetAllocator(default_token_limit=90)
        fitted = allocator.fit_source(SAMPLE_CODE)
        # Every signature survives; bodies are gone.
        assert "def __init__(self, config: dict) -> None:" in fitted
        assert "def process(self, data: list) -> dict:" in fitted
        assert "self.items.append" not in fitted
        assert "result[x] = x ** 2" not in fitted

    def test_skeleton_over_budget_truncates_with_marker(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=10)
        fitted = allocator.fit_source(SAMPLE_CODE)
        assert "truncated at token limit 10" in fitted
        # Truncation cap is limit * 4 chars plus the marker line.
        marker_start = fitted.index("\n# ... truncated")
        assert marker_start <= 40

    def test_non_python_over_budget_degrades_to_truncation(self) -> None:
        prose = "word " * 200  # unparseable as Python, ~250 tokens
        allocator = TokenBudgetAllocator(default_token_limit=50)
        fitted = allocator.fit_source(prose)
        assert fitted.startswith("word ")
        assert "truncated at token limit 50" in fitted

    def test_explicit_token_limit_overrides_default(self) -> None:
        allocator = TokenBudgetAllocator(default_token_limit=10)
        assert allocator.fit_source(SAMPLE_CODE, token_limit=4000) == SAMPLE_CODE
