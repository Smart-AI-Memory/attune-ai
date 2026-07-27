"""Unit tests for AST-driven dynamic context budgeting."""

import ast

from attune.context import (
    ASTSkeletonGenerator,
    ContextInflater,
    TokenBudgetAllocator,
)

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


class TestContextInflater:
    """Tests for ContextInflater."""

    def test_inflation_on_mutating_action(self) -> None:
        inflater = ContextInflater(full_source_repository={"main.py": SAMPLE_CODE})
        skeleton = "... skeletal code ..."

        # Read action keeps skeleton
        res_read = inflater.inflate_if_requested("main.py", skeleton, "Read")
        assert res_read == skeleton

        # Mutating action inflates to full source (case-insensitive)
        res_edit = inflater.inflate_if_requested("main.py", skeleton, "Edit")
        assert res_edit == SAMPLE_CODE
        res_write = inflater.inflate_if_requested("main.py", skeleton, "write")
        assert res_write == SAMPLE_CODE

    def test_adapter_supplied_mutating_actions(self) -> None:
        # Provider adapters may use their own tool vocabulary.
        inflater = ContextInflater(
            full_source_repository={"main.py": SAMPLE_CODE},
            mutating_actions={"replace_file_content"},
        )
        skeleton = "..."
        assert (
            inflater.inflate_if_requested("main.py", skeleton, "replace_file_content")
            == SAMPLE_CODE
        )
        # Canonical names are NOT mutating once overridden
        assert inflater.inflate_if_requested("main.py", skeleton, "Edit") == skeleton

    def test_unregistered_file_keeps_context(self) -> None:
        inflater = ContextInflater()
        assert inflater.inflate_if_requested("ghost.py", "ctx", "Edit") == "ctx"

    def test_register_file_makes_source_inflatable(self) -> None:
        inflater = ContextInflater()
        inflater.register_file("late.py", SAMPLE_CODE)
        assert inflater.inflate_if_requested("late.py", "skel", "Edit") == SAMPLE_CODE
