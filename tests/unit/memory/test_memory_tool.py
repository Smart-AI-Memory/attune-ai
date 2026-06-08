"""Tests for the Anthropic Memory-tool bridge over attune's backend.

Exercises ``attune.memory.memory_tool`` against the real file backend
(zero infra) so the six Memory-tool commands round-trip through
``stash``/``retrieve``/``keys``/``delete``.
"""

from __future__ import annotations

import pytest

from attune.memory.file_stash import FileStashBackend
from attune.memory.memory_tool import AttuneMemoryTool, make_memory_tool

# Real Anthropic command types — skip the whole module if the installed
# anthropic SDK predates the memory tool.
beta = pytest.importorskip("anthropic.types.beta")

CreateCommand = beta.BetaMemoryTool20250818CreateCommand
ViewCommand = beta.BetaMemoryTool20250818ViewCommand
StrReplaceCommand = beta.BetaMemoryTool20250818StrReplaceCommand
InsertCommand = beta.BetaMemoryTool20250818InsertCommand
DeleteCommand = beta.BetaMemoryTool20250818DeleteCommand
RenameCommand = beta.BetaMemoryTool20250818RenameCommand


@pytest.fixture()
def tool(tmp_path):
    """An AttuneMemoryTool over a file backend in a temp dir."""
    backend = FileStashBackend(base_dir=str(tmp_path))
    return AttuneMemoryTool(backend, user_id="tester")


def _create(tool, path, text):
    return tool.create(CreateCommand(command="create", path=path, file_text=text))


def _view(tool, path, view_range=None):
    return tool.view(ViewCommand(command="view", path=path, view_range=view_range))


# =====================================================================
# create / view
# =====================================================================


class TestCreateView:
    def test_create_then_view_with_line_numbers(self, tool):
        _create(tool, "/memories/a.md", "alpha\nbeta")
        out = _view(tool, "/memories/a.md")
        assert out == "1\talpha\n2\tbeta"

    def test_create_returns_confirmation(self, tool):
        assert _create(tool, "/memories/a.md", "x") == "Created /memories/a.md"

    def test_view_range_slices_lines(self, tool):
        _create(tool, "/memories/a.md", "l1\nl2\nl3\nl4")
        assert _view(tool, "/memories/a.md", [2, 3]) == "2\tl2\n3\tl3"

    def test_view_range_negative_end_means_to_end(self, tool):
        _create(tool, "/memories/a.md", "l1\nl2\nl3")
        assert _view(tool, "/memories/a.md", [2, -1]) == "2\tl2\n3\tl3"

    def test_view_directory_lists_files(self, tool):
        _create(tool, "/memories/a.md", "x")
        _create(tool, "/memories/sub/b.md", "y")
        out = _view(tool, "/memories")
        assert out.startswith("Directory /memories:")
        assert "/memories/a.md" in out
        assert "/memories/sub/b.md" in out

    def test_view_missing_file_is_error(self, tool):
        assert "Error" in _view(tool, "/memories/nope.md")

    def test_relative_path_is_tolerated(self, tool):
        _create(tool, "notes.md", "x")
        assert _view(tool, "/memories/notes.md") == "1\tx"


# =====================================================================
# str_replace / insert
# =====================================================================


class TestEdit:
    def test_str_replace_first_occurrence(self, tool):
        _create(tool, "/memories/a.md", "foo bar foo")
        tool.str_replace(
            StrReplaceCommand(
                command="str_replace", path="/memories/a.md", old_str="foo", new_str="X"
            )
        )
        assert _view(tool, "/memories/a.md") == "1\tX bar foo"

    def test_str_replace_no_match_is_error(self, tool):
        _create(tool, "/memories/a.md", "hello")
        out = tool.str_replace(
            StrReplaceCommand(
                command="str_replace", path="/memories/a.md", old_str="zzz", new_str="X"
            )
        )
        assert "no match" in out.lower()

    def test_str_replace_missing_file_is_error(self, tool):
        out = tool.str_replace(
            StrReplaceCommand(
                command="str_replace", path="/memories/no.md", old_str="a", new_str="b"
            )
        )
        assert "not found" in out.lower()

    def test_insert_after_line(self, tool):
        _create(tool, "/memories/a.md", "l1\nl2")
        tool.insert(
            InsertCommand(command="insert", path="/memories/a.md", insert_line=1, insert_text="INS")
        )
        assert _view(tool, "/memories/a.md") == "1\tl1\n2\tINS\n3\tl2"

    def test_insert_at_zero_prepends(self, tool):
        _create(tool, "/memories/a.md", "l1")
        tool.insert(
            InsertCommand(command="insert", path="/memories/a.md", insert_line=0, insert_text="top")
        )
        assert _view(tool, "/memories/a.md") == "1\ttop\n2\tl1"

    def test_insert_out_of_range_is_error(self, tool):
        _create(tool, "/memories/a.md", "l1")
        out = tool.insert(
            InsertCommand(command="insert", path="/memories/a.md", insert_line=99, insert_text="x")
        )
        assert "out of range" in out.lower()


# =====================================================================
# delete / rename
# =====================================================================


class TestDeleteRename:
    def test_delete_removes_file(self, tool):
        _create(tool, "/memories/a.md", "x")
        assert (
            tool.delete(DeleteCommand(command="delete", path="/memories/a.md"))
            == "Deleted /memories/a.md"
        )
        assert "Error" in _view(tool, "/memories/a.md")

    def test_delete_missing_is_error(self, tool):
        out = tool.delete(DeleteCommand(command="delete", path="/memories/no.md"))
        assert "not found" in out.lower()

    def test_rename_moves_content(self, tool):
        _create(tool, "/memories/a.md", "payload")
        tool.rename(
            RenameCommand(command="rename", old_path="/memories/a.md", new_path="/memories/b.md")
        )
        assert _view(tool, "/memories/b.md") == "1\tpayload"
        assert "Error" in _view(tool, "/memories/a.md")

    def test_rename_missing_source_is_error(self, tool):
        out = tool.rename(
            RenameCommand(command="rename", old_path="/memories/x.md", new_path="/memories/y.md")
        )
        assert "not found" in out.lower()

    def test_rename_existing_dest_is_error(self, tool):
        _create(tool, "/memories/a.md", "1")
        _create(tool, "/memories/b.md", "2")
        out = tool.rename(
            RenameCommand(command="rename", old_path="/memories/a.md", new_path="/memories/b.md")
        )
        assert "exists" in out.lower()


# =====================================================================
# security + isolation
# =====================================================================


class TestSecurity:
    def test_path_traversal_blocked(self, tool):
        out = _view(tool, "/memories/../etc/passwd")
        assert "traversal" in out.lower()

    def test_null_byte_blocked(self, tool):
        out = _create(tool, "/memories/a\x00.md", "x")
        assert "Error" in out

    def test_user_id_namespaces_memory(self, tmp_path):
        backend = FileStashBackend(base_dir=str(tmp_path))
        alice = AttuneMemoryTool(backend, user_id="alice")
        bob = AttuneMemoryTool(backend, user_id="bob")
        _create(alice, "/memories/secret.md", "alice-only")
        # Bob cannot see Alice's file (different key scope).
        assert "Error" in _view(bob, "/memories/secret.md")
        assert _view(alice, "/memories/secret.md") == "1\talice-only"


# =====================================================================
# SDK composition
# =====================================================================


class TestSDKComposition:
    def test_make_memory_tool_is_real_sdk_tool(self, tmp_path):
        from anthropic.lib.tools import BetaAbstractMemoryTool

        backend = FileStashBackend(base_dir=str(tmp_path))
        tool = make_memory_tool(backend, user_id="u")
        assert isinstance(tool, BetaAbstractMemoryTool)
        assert not getattr(type(tool), "__abstractmethods__", set())
        assert tool.name == "memory"

    def test_execute_dispatches_to_backend(self, tmp_path):
        backend = FileStashBackend(base_dir=str(tmp_path))
        tool = make_memory_tool(backend, user_id="u")
        tool.execute(CreateCommand(command="create", path="/memories/a.md", file_text="hi"))
        assert (
            tool.execute(ViewCommand(command="view", path="/memories/a.md", view_range=None))
            == "1\thi"
        )

    def test_clear_all_memory(self, tool):
        _create(tool, "/memories/a.md", "x")
        _create(tool, "/memories/b.md", "y")
        tool.clear_all_memory()
        assert "Error" in _view(tool, "/memories/a.md")
        assert "Error" in _view(tool, "/memories/b.md")
