"""Stage orchestration (release-audit-stage R3, steps 0-5).

The orderings are the contract: reconcile red must abort BEFORE any
sitting, and the stage must never choose a disposition on the chair's
behalf. Both are pinned here, with every external call injected.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from attune.classes.stage import StageAborted, run_stage

_REPO = "Smart-AI-Memory/attune-ai"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30, check=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
    for key, value in (
        ("user.email", "t@t"),
        ("user.name", "t"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        _git(tmp_path, "config", key, value)
    src = tmp_path / "src" / "attune"
    src.mkdir(parents=True)
    (src / "mod.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "tag", "v1.0.0")
    (src / "mod.py").write_text("x = 2\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "change")
    return tmp_path


def _green_ci(repo, sha):
    return [
        {
            "databaseId": 1,
            "name": "Tests",
            "conclusion": "success",
            "status": "completed",
            "headSha": sha,
        }
    ]


def _no_ci(repo, sha):
    return []


def _seat(text="NO AMENDMENTS\nGATE-RANK: C3\n"):
    return lambda recipe, brief: (0, text)


class TestOrderingIsTheContract:
    def test_reconcile_red_aborts_BEFORE_any_sitting(self, tmp_path):
        """R3 — seats never deliberate on a broken baseline."""
        repo = _repo(tmp_path)
        seat_calls = []

        def spy(recipe, brief):
            seat_calls.append(recipe)
            return 0, "NO AMENDMENTS"

        with pytest.raises(StageAborted) as exc:
            run_stage(repo, _REPO, runs_provider=_no_ci, invoke_seat=spy)

        assert exc.value.step == "1-reconcile"
        assert seat_calls == [], "no seat may be invoked after a red reconcile"

    def test_baseline_failure_aborts_at_step_0(self, tmp_path):
        bare = tmp_path / "untagged"
        subprocess.run(["git", "init", "-q", str(bare)], check=True, timeout=30)

        with pytest.raises(StageAborted) as exc:
            run_stage(bare, _REPO, runs_provider=_green_ci)

        assert exc.value.step == "0-baseline"

    def test_packet_is_hashed_before_the_sitting_sees_it(self, tmp_path):
        repo = _repo(tmp_path)

        result = run_stage(repo, _REPO, runs_provider=_green_ci, invoke_seat=_seat())

        assert result.sitting is not None
        assert result.sitting.packet_hash == result.packet.packet_hash


class TestTheStageDoesNotRule:
    def test_no_dispositions_are_chosen(self, tmp_path):
        """A tool that picked dispositions would make the manifest a
        record of itself rather than of the chair."""
        repo = _repo(tmp_path)

        result = run_stage(repo, _REPO, runs_provider=_green_ci, invoke_seat=_seat())

        assert not hasattr(result, "rulings")
        # every item still carries only its PRE-FILLED default
        for item in result.packet.items:
            assert item.default_disposition in ("SHIP", "HOLD", "GATE-FIRST", "DEFER")

    def test_result_exposes_what_would_block(self, tmp_path):
        repo = _repo(tmp_path)

        result = run_stage(repo, _REPO, runs_provider=_green_ci, invoke_seat=_seat())

        assert "blocking_by_default" in result.as_dict()


class TestEscapesAreVisible:
    def test_skip_reconcile_records_a_null_receipt_not_a_green_one(self, tmp_path):
        """The gap must be visible, never implied-green."""
        repo = _repo(tmp_path)

        result = run_stage(repo, _REPO, skip_reconcile=True, invoke_seat=_seat())

        assert result.reconcile_receipt is None
        assert result.packet.sections["1_reconcile"] is None

    def test_no_sitting_flag_builds_the_packet_only(self, tmp_path):
        repo = _repo(tmp_path)

        result = run_stage(repo, _REPO, runs_provider=_green_ci, hold=False)

        assert result.sitting is None
        assert result.packet is not None

    def test_sweep_is_package_scoped(self, tmp_path):
        """D10 — and the packet says what it did not look at."""
        repo = _repo(tmp_path)
        (repo / "tests").mkdir()
        (repo / "tests" / "t.py").write_text("y = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "add test")

        result = run_stage(repo, _REPO, runs_provider=_green_ci, hold=False)

        header = result.packet.sections["0_header"]
        assert header["files_not_swept"] >= 1
        assert header["sweep_scope"] == ["src/"]


class TestExitCodes:
    def test_stage_result_serialises(self, tmp_path):
        repo = _repo(tmp_path)

        data = run_stage(repo, _REPO, runs_provider=_green_ci, invoke_seat=_seat()).as_dict()

        assert set(data) >= {"baseline", "reconcile", "packet", "packet_hash", "sitting"}
        assert data["reconcile"]["conclusion"] == "success"
