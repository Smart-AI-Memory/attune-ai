"""Exit-status receipts for ``scripts/land_pr.sh``.

A background task reporting "completed (exit 0)" must mean the PR is
MERGED — the same defect class as ``reach_snapshot.py`` exiting 0 on
rate-limit (lesson, 2026-07-17), seen again on #2513 (2026-09-11) when a
CONFLICTING PR was watched to green and then refused at merge time.

Every path is driven through a fake ``gh`` on PATH that answers the
script's exact queries from a JSON scenario and logs each call, so the
tests can assert both the exit status and *which* gh calls happened
(e.g. no ``checks --watch`` before a CONFLICTING refusal). Nothing here
touches the network.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "land_pr.sh"
HEAD = "dff8e5e03aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="land_pr.sh is a bash script driven through a POSIX fake gh",
)

FAKE_GH = '''#!{python}
"""Fake gh: answers land_pr.sh's exact queries from a JSON scenario."""
import json
import os
import sys
from pathlib import Path

argv = sys.argv[1:]
log = Path(os.environ["FAKE_GH_LOG"])
scenario = json.loads(Path(os.environ["FAKE_GH_SCENARIO"]).read_text())
prior = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
with log.open("a") as fh:
    fh.write(json.dumps(argv) + "\\n")
merged_marker = log.with_suffix(".merged")


def opt(name):
    return argv[argv.index(name) + 1] if name in argv else ""


sub = argv[:2]
if sub == ["pr", "checks"] and "--watch" in argv:
    sys.exit(0)
if sub == ["pr", "checks"]:
    names = scenario.get("failed_checks", [])
    if "length" in opt("--jq"):
        print(len(names))
    else:
        print("\\n".join("  " + n for n in names))
    sys.exit(0)
if sub == ["pr", "merge"]:
    if not scenario.get("merge_ok", False):
        sys.stderr.write(
            "X Pull request #%s is not mergeable: "
            "the merge commit cannot be cleanly created.\\n" % argv[2]
        )
        sys.exit(1)
    if scenario.get("merge_lands", True):
        merged_marker.touch()
    sys.exit(0)
if sub == ["pr", "view"]:
    fields = opt("--json")
    state = "MERGED" if merged_marker.exists() else scenario.get("state", "OPEN")
    if fields == "mergeable,mergeStateStatus":
        seq = scenario["mergeability"]
        n = sum(1 for call in prior if "mergeable,mergeStateStatus" in call)
        print(seq[min(n, len(seq) - 1)])
        sys.exit(0)
    if fields == "headRefOid":
        print(scenario["head"])
        sys.exit(0)
    if fields == "state":
        print(state)
        sys.exit(0)
    if fields == "state,mergedAt,mergeCommit":
        print("[land_pr] #%s: %s · mergedAt: t · sha: %s" % (argv[2], state, scenario["head"][:9]))
        sys.exit(0)
sys.stderr.write("fake gh: unexpected argv %r\\n" % (argv,))
sys.exit(99)
'''

GREEN = {
    "mergeability": ["MERGEABLE BLOCKED"],
    "failed_checks": [],
    "head": HEAD,
    "merge_ok": True,
}


def _run(tmp_path: Path, scenario: dict, *args: str):
    """Run land_pr.sh with a fake gh on PATH; return (proc, gh calls)."""
    fakebin = tmp_path / "bin"
    fakebin.mkdir(exist_ok=True)
    gh = fakebin / "gh"
    gh.write_text(FAKE_GH.format(python=sys.executable))
    gh.chmod(0o755)
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario))
    log = tmp_path / "gh_calls.jsonl"
    env = {
        **os.environ,
        "PATH": f"{fakebin}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_SCENARIO": str(scenario_path),
        "FAKE_GH_LOG": str(log),
        "LAND_PR_PROBE_DELAY": "0",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return proc, calls


def _watched(calls) -> bool:
    return any(c[:2] == ["pr", "checks"] and "--watch" in c for c in calls)


def _merge_attempted(calls) -> bool:
    return any(c[:2] == ["pr", "merge"] for c in calls)


def test_script_parses():
    assert subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode == 0


def test_green_at_authorized_head_merges_and_exits_0(tmp_path):
    proc, calls = _run(tmp_path, GREEN, "2513", HEAD[:9])
    assert proc.returncode == 0, proc.stderr
    assert _watched(calls) and _merge_attempted(calls)
    assert "#2513: MERGED" in proc.stdout


def test_conflicting_refuses_before_watching(tmp_path):
    proc, calls = _run(tmp_path, {**GREEN, "mergeability": ["CONFLICTING DIRTY"]}, "2513", HEAD[:9])
    assert proc.returncode == 2
    assert not _watched(calls) and not _merge_attempted(calls)
    assert "CONFLICTING" in proc.stderr and "before watching" in proc.stderr
    assert "git rebase -S origin/main" in proc.stderr
    assert "git push --force-with-lease" in proc.stderr
    assert "re-authorize at the NEW head" in proc.stderr


def test_draft_refuses_before_watching(tmp_path):
    proc, calls = _run(tmp_path, {**GREEN, "mergeability": ["MERGEABLE DRAFT"]}, "2513", HEAD[:9])
    assert proc.returncode == 2
    assert not _watched(calls)
    assert "DRAFT" in proc.stderr and "gh pr ready 2513" in proc.stderr


def test_conflict_appearing_during_watch_refuses_before_merging(tmp_path):
    scenario = {**GREEN, "mergeability": ["MERGEABLE BLOCKED", "CONFLICTING DIRTY"]}
    proc, calls = _run(tmp_path, scenario, "2513", HEAD[:9])
    assert proc.returncode == 2
    assert _watched(calls) and not _merge_attempted(calls)
    assert "before merging" in proc.stderr and "git rebase -S origin/main" in proc.stderr


def test_unknown_mergeability_is_reprobed_then_proceeds(tmp_path):
    scenario = {**GREEN, "mergeability": ["UNKNOWN UNKNOWN", "MERGEABLE BLOCKED"]}
    proc, calls = _run(tmp_path, scenario, "2513", HEAD[:9])
    assert proc.returncode == 0, proc.stderr
    probes = [c for c in calls if "mergeable,mergeStateStatus" in c]
    assert len(probes) >= 3  # UNKNOWN, re-probe, and the pre-merge probe


def test_merge_refused_by_gh_exits_1_not_0(tmp_path):
    """The #2513 shape: everything green, gh pr merge refuses, state stays OPEN."""
    proc, calls = _run(tmp_path, {**GREEN, "merge_ok": False}, "2513", HEAD[:9])
    assert proc.returncode == 1
    assert _merge_attempted(calls)
    assert "merge commit cannot be cleanly created" in proc.stderr
    assert "did NOT land (state: OPEN)" in proc.stderr


def test_merge_command_exit_0_but_state_not_merged_exits_1(tmp_path):
    """gh exiting 0 is not the receipt — the remote state re-read is."""
    proc, _ = _run(tmp_path, {**GREEN, "merge_lands": False}, "2513", HEAD[:9])
    assert proc.returncode == 1
    assert "did NOT land (state: OPEN)" in proc.stderr


def test_red_check_refuses_without_merging(tmp_path):
    scenario = {**GREEN, "failed_checks": ["test (windows-latest, 3.13)"]}
    proc, calls = _run(tmp_path, scenario, "2513", HEAD[:9])
    assert proc.returncode == 1
    assert not _merge_attempted(calls)
    assert "1 check(s) failed" in proc.stderr and "windows-latest" in proc.stderr


def test_moved_head_refuses_without_merging(tmp_path):
    proc, calls = _run(tmp_path, GREEN, "2513", "0000000")
    assert proc.returncode == 1
    assert not _merge_attempted(calls)
    assert "head moved since authorization" in proc.stderr


def test_usage_exits_64(tmp_path):
    proc, calls = _run(tmp_path, GREEN, "2513")
    assert proc.returncode == 64
    assert calls == []
