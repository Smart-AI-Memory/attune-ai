"""Regression guard: the graph API removed in 10.0.0 stays removed.

The memorygraph-value-gate spec (docs/specs/memorygraph-value-gate/)
deleted MemoryGraph and its node/edge types. Accessing the removed
names must raise a pointed AttributeError naming the successor —
not resolve, and not raise a bare "no attribute" message.
"""

import pytest

REMOVED_NAMES = [
    "MemoryGraph",
    "Node",
    "NodeType",
    "BugNode",
    "PatternNode",
    "PerformanceNode",
    "VulnerabilityNode",
    "Edge",
    "EdgeType",
    "REVERSE_EDGE_TYPES",
    "WORKFLOW_EDGE_PATTERNS",
]


@pytest.mark.parametrize("name", REMOVED_NAMES)
def test_removed_name_raises_pointed_error(name: str) -> None:
    import attune.memory

    with pytest.raises(AttributeError, match="removed in 10.0.0"):
        getattr(attune.memory, name)


@pytest.mark.parametrize("name", REMOVED_NAMES)
def test_removed_name_not_in_all(name: str) -> None:
    import attune.memory

    assert name not in attune.memory.__all__


def test_from_import_fails() -> None:
    """The from-import form fails too — with CPython's generic
    ImportError (the import machinery swallows the pointed
    AttributeError text; see lessons.md 2026-07-05)."""
    with pytest.raises(ImportError, match="MemoryGraph"):
        from attune.memory import MemoryGraph  # noqa: F401,PLC0415
