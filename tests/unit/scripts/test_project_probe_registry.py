"""Free guards for the probe-registry projector.

Pin the spec-ruled mechanics (workflow-behavioral-validation D3/D7/D9):
commit order — not ``ran_at`` — is the ordering key; untracked records
rank newest; projection is idempotent; a workflow with neither record
nor disposition renders as needing attention, never as clean.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "project_probe_registry.py"


def _load():
    spec = importlib.util.spec_from_file_location("project_probe_registry", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


projector = _load()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _record(records: Path, fname: str, workflow: str, verdict: str, ran_at: str) -> None:
    records.mkdir(parents=True, exist_ok=True)
    (records / fname).write_text(
        json.dumps(
            {
                "workflow": workflow,
                "fixture": "f",
                "receipt_type": "named-defect",
                "verdict": verdict,
                "cost_usd": 1.0,
                "duration_s": 2.0,
                "ran_at": ran_at,
                "runner_version": "test",
                "git_sha": "abc",
                "evidence": {},
            }
        ),
        encoding="utf-8",
    )


def _repo_with_records(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    records = repo / "records"
    records.mkdir(parents=True)
    _git(repo, "init", "-q")
    return records


def test_commit_order_beats_ran_at(tmp_path: Path) -> None:
    # D9 round-3 finding 1: a future-skewed ran_at must NOT win. The
    # record committed LATER wins even though its ran_at is EARLIER.
    records = _repo_with_records(tmp_path)
    repo = records.parent
    _record(records, "a.json", "wf", "fail", ran_at="2099-01-01T00:00:00Z")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "first")
    _record(records, "b.json", "wf", "pass", ran_at="2026-01-01T00:00:00Z")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second")

    loaded = projector.load_records(records)
    order = projector.commit_order(records)
    latest = projector.latest_per_workflow(loaded, order)
    assert latest["wf"]["_file"] == "b.json"
    assert latest["wf"]["verdict"] == "pass"


def test_untracked_record_ranks_newest(tmp_path: Path) -> None:
    records = _repo_with_records(tmp_path)
    repo = records.parent
    _record(records, "a.json", "wf", "pass", ran_at="2099-01-01T00:00:00Z")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "first")
    # New record, not yet committed — it is about to be, so it wins.
    _record(records, "b.json", "wf", "fail", ran_at="2020-01-01T00:00:00Z")

    loaded = projector.load_records(records)
    order = projector.commit_order(records)
    latest = projector.latest_per_workflow(loaded, order)
    assert latest["wf"]["_file"] == "b.json"


def test_malformed_record_skipped(tmp_path: Path, capsys) -> None:
    records = tmp_path / "records"
    records.mkdir()
    (records / "bad.json").write_text("{not json", encoding="utf-8")
    _record(records, "good.json", "wf", "pass", ran_at="2026-01-01T00:00:00Z")
    loaded = projector.load_records(records)
    assert [r["_file"] for r in loaded] == ["good.json"]
    assert "skipping" in capsys.readouterr().err


def test_render_is_deterministic_and_flags_missing_dispositions(tmp_path: Path) -> None:
    records = tmp_path / "records"
    _record(records, "a.json", "wf-a", "pass", ran_at="2026-01-01T00:00:00Z")
    loaded = projector.load_records(records)
    latest = projector.latest_per_workflow(loaded, {})
    fleet = ["wf-a", "wf-b", "wf-c"]
    dispositions = {"wf-b": "intentionally unprobed"}
    one = projector.render(latest, fleet, dispositions)
    two = projector.render(latest, fleet, dispositions)
    assert one == two  # idempotent
    assert "| wf-a | PASS |" in one
    assert "intentionally unprobed" in one
    # No record + no disposition must read as attention-needed, not clean.
    assert "wf-c" in one
    assert "NO DISPOSITION RECORDED" in one


def test_parse_dispositions_joins_wrapped_lines(tmp_path: Path) -> None:
    path = tmp_path / "dispositions.md"
    path.write_text(
        "# Ledger\n\nintro text\n\n"
        "- **wf-a** — first half of the\n"
        "  reason continues here.\n"
        "- **wf-b** — single line.\n",
        encoding="utf-8",
    )
    parsed = projector.parse_dispositions(path)
    assert parsed["wf-a"] == "first half of the reason continues here."
    assert parsed["wf-b"] == "single line."


def test_live_registry_matches_projection() -> None:
    # The committed registry.md must equal a fresh projection — the same
    # invariant `--check` enforces in CI. Run against the real spec dir.
    content = projector.project()
    committed = projector.REGISTRY_PATH.read_text(encoding="utf-8")
    assert committed == content, "registry.md is stale — run scripts/project_probe_registry.py"


def test_every_fleet_workflow_is_recorded_or_dispositioned() -> None:
    # Absence must be explained: each fleet workflow has a run-record or
    # a dispositions entry. A new workflow added to the fleet without
    # either fails here instead of silently looking clean.
    fleet = set(projector.default_fleet())
    recorded = {r["workflow"] for r in projector.load_records(projector.RECORDS_DIR)}
    dispositioned = set(projector.parse_dispositions(projector.DISPOSITIONS_PATH))
    unexplained = fleet - recorded - dispositioned
    assert not unexplained, f"no record and no disposition for: {sorted(unexplained)}"
