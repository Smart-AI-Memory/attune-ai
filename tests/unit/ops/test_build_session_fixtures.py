"""Tests for the fixture-build helper script (S3b).

Smoke-tests the dry-run + write paths against a synthetic
``~/.claude/projects/<encoded>/`` tree. The script is invoked
in-process (no subprocess) so the patched ``Path.home()`` takes
effect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/ is not on the import path by default
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[3] / "scripts"),
)
import build_session_fixtures  # noqa: E402

from attune.ops import data  # noqa: E402


def _patch_home(monkeypatch, home_path: Path) -> None:
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))


def _seed_session(home: Path, project_root: Path, session_id: str, events: list[dict]) -> None:
    sessions_dir = home / ".claude" / "projects" / data._encoded_project_path(project_root)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / f"{session_id}.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )


def test_dry_run_reports_no_writes(tmp_path, monkeypatch, capsys):
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    project_root.mkdir()
    _seed_session(
        tmp_path / "home",
        project_root,
        "abc-001",
        [{"timestamp": "2026-05-14T10:00:00Z", "content": "Hello"}],
    )

    out_dir = tmp_path / "fixtures"
    count = build_session_fixtures.build_fixtures(
        project_root=project_root.resolve(),
        out_dir=out_dir,
        write=False,
        limit=None,
    )
    assert count == 1
    # Output dir should NOT be created on dry-run
    assert not out_dir.exists()
    captured = capsys.readouterr().out
    assert "Dry-run" in captured
    assert "abc-001" in captured


def test_write_persists_redacted_jsonl(tmp_path, monkeypatch, capsys):
    """A session with a secret in its content writes a redacted JSONL."""
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    project_root.mkdir()
    secret = "sk-ant-" + "B" * 40
    _seed_session(
        tmp_path / "home",
        project_root,
        "abc-002",
        [
            {"timestamp": "2026-05-14T10:00:00Z", "content": f"My key is {secret}"},
            {"timestamp": "2026-05-14T10:01:00Z", "content": "Plain follow-up"},
        ],
    )

    out_dir = tmp_path / "fixtures"
    count = build_session_fixtures.build_fixtures(
        project_root=project_root.resolve(),
        out_dir=out_dir,
        write=True,
        limit=None,
    )
    assert count == 1
    written = out_dir / "abc-002.jsonl"
    assert written.is_file()

    lines = written.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first_event = json.loads(lines[0])
    second_event = json.loads(lines[1])
    # Secret is gone, placeholder is in
    assert secret not in first_event["content"]
    assert "<redacted>" in first_event["content"]
    # Plain content survived
    assert second_event["content"] == "Plain follow-up"
    # Timestamps preserved
    assert first_event["timestamp"] == "2026-05-14T10:00:00Z"

    captured = capsys.readouterr().out
    assert "api_key=1" in captured  # the per-file redaction count line


def test_limit_caps_processed_sessions(tmp_path, monkeypatch):
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    project_root.mkdir()
    for i in range(5):
        _seed_session(
            tmp_path / "home",
            project_root,
            f"session-{i:02d}",
            [{"timestamp": "2026-05-14T10:00:00Z", "content": f"prompt {i}"}],
        )

    out_dir = tmp_path / "fixtures"
    count = build_session_fixtures.build_fixtures(
        project_root=project_root.resolve(),
        out_dir=out_dir,
        write=True,
        limit=2,
    )
    assert count == 2
    written = sorted(out_dir.glob("*.jsonl"))
    assert len(written) == 2


def test_empty_source_dir_reports_zero(tmp_path, monkeypatch, capsys):
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    project_root.mkdir()

    out_dir = tmp_path / "fixtures"
    count = build_session_fixtures.build_fixtures(
        project_root=project_root.resolve(),
        out_dir=out_dir,
        write=True,
        limit=None,
    )
    assert count == 0
    captured = capsys.readouterr()
    assert "No JSONLs found" in captured.err
