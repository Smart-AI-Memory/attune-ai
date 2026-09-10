"""Behavioral regressions for selection shared by both starter hooks."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from attune.hooks.scripts import starter_prompt_nudge as nudge
from attune.hooks.scripts import starter_reconciler as reconciler


@pytest.mark.parametrize("surface", ["branch", "newest", "project", "global", "empty-project"])
def test_hooks_use_the_same_artifacts(tmp_path, monkeypatch, capsys, surface):
    """Record paths at each output boundary; an unrelated verdict cannot pass."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    project = repo / ".attune" / "next_session_starter.md"
    project.parent.mkdir()
    if surface != "global":
        project.write_text("" if surface == "empty-project" else "project", encoding="utf-8")
    global_path = tmp_path / "global.md"
    global_path.write_text("legacy", encoding="utf-8")
    expected = [project]
    if surface in {"branch", "newest"}:
        handoff = (
            repo / "docs" / "handoffs" / ("codex-current.md" if surface == "branch" else "other.md")
        )
        handoff.parent.mkdir(parents=True)
        handoff.write_text("handoff", encoding="utf-8")
        expected.insert(0, handoff)
    elif surface in {"global", "empty-project"}:
        expected = [global_path]
    monkeypatch.chdir(repo)
    monkeypatch.setattr(nudge, "_current_branch", lambda root: "codex/current")
    for module in (nudge, reconciler):
        monkeypatch.setattr(module, "STARTER_PATH", global_path)

    assert nudge.main() == 0
    output = capsys.readouterr().out
    for path in expected:
        assert str(path) in output
    if global_path not in expected:
        assert str(global_path) not in output

    checked = []
    monkeypatch.setattr(
        reconciler, "_reconcile_and_emit", lambda path, *args: checked.append(path) or True
    )
    assert reconciler.main() == 0
    assert checked == expected


def test_banner_states_decision_content_is_unverified():
    results = {"prs": {42: "MERGED"}, "branches": {}, "pypi": None, "versions": []}
    banner = reconciler.format_banner(results, "project", Path("starter.md"))
    assert "decision content unverified" in banner


def test_standalone_hooks_read_the_same_branch_handoff(tmp_path):
    """Exercise real script imports, git discovery, file reads, and output."""
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=codex/current", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/Smart-AI-Memory/attune-ai.git"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    handoff = tmp_path / "docs" / "handoffs" / "codex-current.md"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("Follow Smart-AI-Memory/attune#9000\n", encoding="utf-8")
    scripts = Path(nudge.__file__).resolve().parent
    env = dict(os.environ, ATTUNE_SDK_GATE_OVERRIDE="1")
    for script, marker in (
        ("starter_prompt_nudge.py", "[starter-prompt:handoff:branch:draft]"),
        ("starter_reconciler.py", "[starter-reconcile:handoff:branch:draft]"),
    ):
        result = subprocess.run(
            [sys.executable, str(scripts / script)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=12,
            check=True,
        )
        assert result.stderr == ""
        assert marker in result.stdout
        assert str(handoff) in result.stdout
        if script == "starter_reconciler.py":
            assert "smart-ai-memory/attune#9000 unverified" in result.stdout
            assert "#9000 MERGED" not in result.stdout
