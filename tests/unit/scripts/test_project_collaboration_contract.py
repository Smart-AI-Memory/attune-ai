"""Tests for the cross-provider collaboration contract projector."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "project_collaboration_contract.py"
spec = importlib.util.spec_from_file_location("project_collaboration_contract", SCRIPT)
assert spec is not None and spec.loader is not None
projector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = projector
spec.loader.exec_module(projector)


def _seed_repo(tmp_path: Path) -> None:
    master = tmp_path / "content" / "collaboration" / "contract.md"
    master.parent.mkdir(parents=True)
    master.write_text(
        "# Contract\n\n"
        "## Shared contract\n\n"
        "Shared rule.\n\n"
        "## Portable handoff template\n\n"
        "# Handoff\n\n"
        "## Goal\n\n"
        "Describe it.\n",
        encoding="utf-8",
    )
    for relative_path in projector.CONTRACT_TARGETS:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Provider rules\n\n"
            f"{projector.START_MARKER}\nold content\n{projector.END_MARKER}\n\n"
            "Provider-specific tail.\n",
            encoding="utf-8",
        )


def test_repo_projection_is_in_sync() -> None:
    result = projector.project(REPO_ROOT, check=True)
    assert result.stale == []


def test_projects_contract_and_handoff_without_clobbering_provider_tail(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    result = projector.project(tmp_path)

    assert set(result.written) == set(projector.CONTRACT_TARGETS) | {projector.HANDOFF_TARGET}
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Shared rule." in agents
    assert "Provider-specific tail." in agents
    handoff = (tmp_path / projector.HANDOFF_TARGET).read_text(encoding="utf-8")
    assert handoff.startswith("# Handoff")
    assert "## Goal" in handoff


def test_check_fires_when_master_changes_after_projection(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    projector.project(tmp_path)
    master = tmp_path / projector.MASTER_PATH
    master.write_text(
        master.read_text(encoding="utf-8").replace("Shared rule.", "Changed rule."),
        encoding="utf-8",
    )

    result = projector.project(tmp_path, check=True)

    assert set(result.stale) == set(projector.CONTRACT_TARGETS)
    assert projector.HANDOFF_TARGET not in result.stale


def test_second_projection_is_idempotent(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    projector.project(tmp_path)

    result = projector.project(tmp_path)

    assert result.written == []
    assert set(result.unchanged) == set(projector.CONTRACT_TARGETS) | {projector.HANDOFF_TARGET}


def test_handoff_projection_preserves_nested_h2_sections(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    projector.project(tmp_path)

    handoff = (tmp_path / projector.HANDOFF_TARGET).read_text(encoding="utf-8")
    assert "## Goal" in handoff


def test_rejects_target_without_exactly_one_marker_pair(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Missing markers\n", encoding="utf-8")

    with pytest.raises(projector.ProjectionError, match="marker pair"):
        projector.project(tmp_path)
