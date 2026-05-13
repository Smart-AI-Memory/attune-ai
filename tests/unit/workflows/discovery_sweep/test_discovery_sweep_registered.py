"""Drift-guard: discovery-sweep must be visible everywhere it's wired.

Three integration points:

1. ``attune.workflows.list_workflows()`` includes ``discovery-sweep``.
2. ``attune.ops.data.PATH_ARG_REGISTRY`` has a Category A entry for
   it (``kwarg="path"``, ``required=False``).
3. ``DiscoverySweepWorkflow`` is importable via the lazy attribute
   handler on the ``attune.workflows`` package.
"""

from __future__ import annotations

import attune.workflows as workflows_pkg
from attune.ops.data import PATH_ARG_REGISTRY, PathArgSpec


def test_workflow_listed() -> None:
    names = {w["name"] for w in workflows_pkg.list_workflows()}
    assert "discovery-sweep" in names


def test_path_arg_registry_entry() -> None:
    entry = PATH_ARG_REGISTRY.get("discovery-sweep")
    assert entry == PathArgSpec(kwarg="path", required=False)


def test_lazy_class_attribute() -> None:
    cls = workflows_pkg.DiscoverySweepWorkflow
    assert cls.__name__ == "DiscoverySweepWorkflow"
    assert cls.name == "discovery-sweep"


def test_list_workflows_entry_shape() -> None:
    entries = [
        w for w in workflows_pkg.list_workflows() if w["name"] == "discovery-sweep"
    ]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["class"] == "DiscoverySweepWorkflow"
    assert "sweep" in entry["stages"]
