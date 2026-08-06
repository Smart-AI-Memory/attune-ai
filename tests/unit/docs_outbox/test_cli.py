# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""CLI surface: write, list, status, sweep, apply."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from attune.docs_outbox.__main__ import main

NOW = datetime(2026, 8, 6, 14, 32)


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    """Point Path.home() at tmp so the CLI never touches ~/.attune."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return tmp_path


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "lessons.md").write_text("# Lessons\n", encoding="utf-8")
    return root


def test_write_then_status_and_list(tmp_path, capsys):
    body = tmp_path / "body.md"
    body.write_text("A lesson.\n", encoding="utf-8")
    assert main(["write", "--kind", "lesson", "--slug", "cli-one", "--file", str(body)]) == 0
    assert main(["status", "--json"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    status = json.loads(out[-1])
    assert status["count"] == 1
    assert status["stale"] is False
    assert main(["list"]) == 0
    assert "lesson-cli-one" in capsys.readouterr().out


def test_write_rejects_merge_now_kind(tmp_path, capsys):
    body = tmp_path / "body.md"
    body.write_text("Ruling.\n", encoding="utf-8")
    assert main(["write", "--kind", "decision", "--slug", "d", "--file", str(body)]) == 1
    assert "merge-now" in capsys.readouterr().err


def test_status_empty(capsys):
    assert main(["status"]) == 0
    assert "empty" in capsys.readouterr().out


def test_sweep_and_apply_round_trip(tmp_path, repo, capsys):
    body = tmp_path / "body.md"
    body.write_text("- CLI lesson.\n", encoding="utf-8")
    main(["write", "--kind", "lesson", "--slug", "cli-sweep", "--file", str(body)])
    assert main(["sweep", "--repo-root", str(repo)]) == 0
    assert "cli-sweep" in capsys.readouterr().out
    assert main(["apply", "--repo-root", str(repo)]) == 0
    assert "CLI lesson." in (repo / ".claude" / "lessons.md").read_text(encoding="utf-8")


def test_apply_empty_outbox(repo, capsys):
    assert main(["apply", "--repo-root", str(repo)]) == 0
    assert "nothing applied" in capsys.readouterr().out
