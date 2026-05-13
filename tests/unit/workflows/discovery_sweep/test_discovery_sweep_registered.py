"""Drift-guard: discovery-sweep is wired into the workflow registry.

Asserts:

- ``list_workflows()`` includes the ``discovery-sweep`` entry
- ``get_workflow("discovery-sweep")`` resolves to ``DiscoverySweepWorkflow``
- ``PATH_ARG_REGISTRY`` carries a ``path`` kwarg entry for it

Failing here means the new workflow is invisible to the CLI
or the ops dashboard scope picker.
"""

from __future__ import annotations

from attune.ops.data import PATH_ARG_REGISTRY
from attune.workflows import get_workflow, list_workflows
from attune.workflows.discovery_sweep import DiscoverySweepWorkflow


def test_discovery_sweep_appears_in_list_workflows() -> None:
    names = {entry["name"] for entry in list_workflows()}
    assert "discovery-sweep" in names


def test_discovery_sweep_resolves_to_workflow_class() -> None:
    cls = get_workflow("discovery-sweep")
    assert cls is DiscoverySweepWorkflow


def test_discovery_sweep_in_path_arg_registry() -> None:
    assert "discovery-sweep" in PATH_ARG_REGISTRY
    spec = PATH_ARG_REGISTRY["discovery-sweep"]
    assert spec.kwarg == "path"
    assert spec.required is False
