"""The Anthropic Memory-tool bridge is reachable from ``attune.memory``.

Phase 1 shipped ``attune.memory.memory_tool`` but never exported it from
the package, so the capability was importable only via the deep path and
had no consumers. These tests guard that:

1. ``from attune.memory import make_memory_tool, AttuneMemoryTool`` works.
2. The export stays **lazy** about the ``anthropic`` SDK — importing the
   name must not require the memory-tool helper; only *calling* the
   factory does. (Protects the "invisible runtime deps" invariant: a
   vanilla ``pip install attune-ai`` must import ``attune.memory`` even
   without the anthropic memory-tool SDK.)
"""

from __future__ import annotations

import sys

import pytest

from attune.memory.file_stash import FileStashBackend


def test_memory_tool_exported_from_package() -> None:
    """The factory + class are reachable from the package root."""
    import attune.memory as m
    from attune.memory import AttuneMemoryTool, make_memory_tool
    from attune.memory import memory_tool as mt

    assert "make_memory_tool" in m.__all__
    assert "AttuneMemoryTool" in m.__all__
    # The re-exported names resolve to the same objects as the submodule.
    assert make_memory_tool is mt.make_memory_tool
    assert AttuneMemoryTool is mt.AttuneMemoryTool


def test_export_is_lazy_about_anthropic(monkeypatch, tmp_path) -> None:
    """Importing the name is light; only calling the factory needs anthropic.

    Simulate an ``anthropic`` install without the memory-tool helper via
    the ``sys.modules[name] = None`` sentinel (cross-version): the name
    import still succeeds, and the factory raises a clear RuntimeError
    only when actually invoked.
    """
    from attune.memory import make_memory_tool

    monkeypatch.setitem(sys.modules, "anthropic.lib.tools", None)
    backend = FileStashBackend(base_dir=str(tmp_path))
    with pytest.raises(RuntimeError, match="memory-tool"):
        make_memory_tool(backend)
