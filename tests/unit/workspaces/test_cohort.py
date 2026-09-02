"""Cohort-level order and provisional-interface ratchets."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from attune.mcp.server import AttuneMCPServer
from attune.workspaces import COHORT_ADAPTER_ORDER


def test_ten_cohort_adapters_are_registered_in_chair_approved_order() -> None:
    with patch("attune.mcp.version_check.check_for_updates", return_value=None):
        server = AttuneMCPServer(workspace_root=str(Path.cwd()))

    registered = tuple(server._command_workspaces._adapters)  # noqa: SLF001
    assert len(COHORT_ADAPTER_ORDER) == 10
    assert registered[-10:] == COHORT_ADAPTER_ORDER
    assert registered[:3] == ("fix", "roundtable", "spec")


def test_every_cohort_adapter_implements_provisional_v1_surface() -> None:
    with patch("attune.mcp.version_check.check_for_updates", return_value=None):
        server = AttuneMCPServer(workspace_root=str(Path.cwd()))

    adapters = server._command_workspaces._adapters  # noqa: SLF001
    for adapter_id in COHORT_ADAPTER_ORDER:
        adapter = adapters[adapter_id]
        assert adapter.adapter_id == adapter_id
        assert adapter.schema_version == 1
        assert callable(adapter.create)
        assert callable(adapter.project)
        assert callable(adapter.apply)
        assert callable(adapter.publish)
