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


def test_repo_projection_carries_artifact_tiers_and_verification_receipts() -> None:
    contract = (REPO_ROOT / projector.MASTER_PATH).read_text(encoding="utf-8")
    handoff = (REPO_ROOT / projector.HANDOFF_TARGET).read_text(encoding="utf-8")

    for target in projector.CONTRACT_TARGETS:
        projected = (REPO_ROOT / target).read_text(encoding="utf-8")
        assert "### Artifact selection" in projected
        assert "**Inline edit**" in projected
        assert "**Structured one-shot**" in projected
        assert "**XML task**" in projected
        assert "**Spec**" in projected
        assert "### Verification receipts" in projected
        assert "require a non-mocked round trip" in projected
        assert "working receipts" in projected

    assert "### Artifact selection" in contract
    assert "### Verification receipts" in contract
    assert "| Claim | Failure-sensitive probe | Result |" in handoff


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


def test_invalid_claude_target_does_not_partially_update_agents(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    agents = tmp_path / "AGENTS.md"
    original_agents = agents.read_bytes()
    (tmp_path / ".claude" / "CLAUDE.md").write_text("# Missing markers\n", encoding="utf-8")

    with pytest.raises(projector.ProjectionError, match="marker pair"):
        projector.project(tmp_path)

    assert agents.read_bytes() == original_agents


def test_rejects_symlinked_target_outside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _seed_repo(root)
    external = tmp_path / "outside.md"
    external.write_text("outside\n", encoding="utf-8")
    handoff = root / projector.HANDOFF_TARGET
    handoff.parent.mkdir(parents=True)
    try:
        handoff.symlink_to(external)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    with pytest.raises(projector.ProjectionError, match="escapes repository"):
        projector.project(root)

    assert external.read_text(encoding="utf-8") == "outside\n"


def test_main_reports_unchanged_targets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    result = projector.ProjectionResult(unchanged=[Path("AGENTS.md")])
    monkeypatch.setattr(projector, "project", lambda root, check: result)

    assert projector.main(["--check"]) == 0
    assert capsys.readouterr().out == "unchanged AGENTS.md\n"


def test_main_reports_projection_drift(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    result = projector.ProjectionResult(stale=[Path(".claude/CLAUDE.md")])
    monkeypatch.setattr(projector, "project", lambda root, check: result)

    assert projector.main(["--check"]) == 1
    assert capsys.readouterr().out == ("collaboration projection drift:\n  .claude/CLAUDE.md\n")


def test_main_reports_projection_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def fail_projection(root: Path, *, check: bool) -> None:
        raise projector.ProjectionError("bad target")

    monkeypatch.setattr(projector, "project", fail_projection)

    assert projector.main([]) == 1
    assert capsys.readouterr().out == "error: bad target\n"
