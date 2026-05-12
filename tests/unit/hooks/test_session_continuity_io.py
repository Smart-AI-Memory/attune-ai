"""End-to-end IO tests for spec_orient.py and compact_warning.py.

Each test runs the actual hook script in a subprocess with a
synthetic JSON payload on stdin, mirroring how Claude Code
invokes them. Covers:

- SessionStart's four ``source`` values (startup / resume /
  clear / compact).
- Stop hook's threshold + sentinel logic.
- Crash-safety: forced helper failure must still exit 0.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"
_SPEC_ORIENT = _HOOKS_DIR / "spec_orient.py"
_COMPACT_WARNING = _HOOKS_DIR / "compact_warning.py"


def _run_hook(
    script: Path,
    payload: dict,
    *,
    env_overrides: dict | None = None,
    workspace_roots: Path | None = None,
) -> subprocess.CompletedProcess:
    """Invoke a hook with a JSON payload on stdin."""
    env = os.environ.copy()
    if workspace_roots is not None:
        env["ATTUNE_AI_WORKSPACE_ROOTS"] = str(workspace_roots)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=10,
    )


def _seed_workspace_with_spec(root: Path, *, slug: str = "feat-x") -> Path:
    """Lay out a minimal workspace with one in-flight spec."""
    spec_dir = root / "specs" / slug
    spec_dir.mkdir(parents=True)
    (spec_dir / "tasks.md").write_text(
        "# Tasks\n\n**Status**: approved\n\n"
        "| # | Task | Status | Notes |\n"
        "|---|------|--------|-------|\n"
        "| 1 | first task | completed | done |\n",
        encoding="utf-8",
    )
    return spec_dir


# ── spec_orient.py — SessionStart ─────────────────────────────


class TestSpecOrient:
    @pytest.mark.parametrize("source", ["startup", "resume", "clear"])
    def test_orientation_paragraph_for_non_compact(self, tmp_path: Path, source: str) -> None:
        _seed_workspace_with_spec(tmp_path, slug="feat-x")
        result = _run_hook(
            _SPEC_ORIENT,
            {"source": source, "cwd": str(tmp_path)},
            workspace_roots=tmp_path,
        )
        assert result.returncode == 0
        assert "in-flight specs" in result.stdout
        assert "specs/feat-x/" in result.stdout

    def test_compact_emits_spec_body(self, tmp_path: Path) -> None:
        _seed_workspace_with_spec(tmp_path, slug="post-compact-feat")
        result = _run_hook(
            _SPEC_ORIENT,
            {"source": "compact", "cwd": str(tmp_path)},
            workspace_roots=tmp_path,
        )
        assert result.returncode == 0
        assert "Active spec restored after compact" in result.stdout
        assert "post-compact-feat" in result.stdout
        # Should include the actual tasks-md body.
        assert "first task" in result.stdout

    def test_no_specs_silent(self, tmp_path: Path) -> None:
        # Empty workspace — nothing to orient on.
        result = _run_hook(
            _SPEC_ORIENT,
            {"source": "startup", "cwd": str(tmp_path)},
            workspace_roots=tmp_path,
        )
        assert result.returncode == 0
        assert result.stdout == ""

    def test_malformed_payload_no_crash(self, tmp_path: Path) -> None:
        # Stdin isn't JSON at all.
        proc = subprocess.run(
            [sys.executable, str(_SPEC_ORIENT)],
            input="not-json",
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env={
                **os.environ,
                "ATTUNE_AI_WORKSPACE_ROOTS": str(tmp_path),
            },
            timeout=10,
        )
        assert proc.returncode == 0


# ── compact_warning.py — Stop ─────────────────────────────────


class TestCompactWarning:
    def test_below_threshold_silent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({"role": "user", "content": "hi"}) + "\n")
        sentinel_dir = tmp_path / "sentinels"
        sentinel_dir.mkdir()
        result = _run_hook(
            _COMPACT_WARNING,
            {
                "session_id": "below-threshold",
                "transcript_path": str(transcript),
                "cwd": str(tmp_path),
            },
            env_overrides={"ATTUNE_AI_SENTINEL_DIR": str(sentinel_dir)},
        )
        assert result.returncode == 0
        assert result.stdout == ""
        assert not (sentinel_dir / ".compact-warned-below-threshold").exists()

    def test_above_threshold_fires_once(self, tmp_path: Path) -> None:
        # Pad the transcript well above the threshold by tightening
        # the context window via the env tuning hook.
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({"role": "user", "content": "x" * 4000}) + "\n")
        sentinel_dir = tmp_path / "sentinels"
        sentinel_dir.mkdir()
        env = {
            "ATTUNE_AI_SENTINEL_DIR": str(sentinel_dir),
            # 4000 chars / 4 chars-per-token / 1000 tokens = 1.0 utilization
            "ATTUNE_AI_CONTEXT_WINDOW_TOKENS": "1000",
            "ATTUNE_AI_COMPACT_WARNING_THRESHOLD": "0.50",
        }
        first = _run_hook(
            _COMPACT_WARNING,
            {
                "session_id": "fires-once",
                "transcript_path": str(transcript),
                "cwd": str(tmp_path),
            },
            env_overrides=env,
        )
        assert first.returncode == 0
        assert "context at 100%" in first.stdout
        assert "Resume prompt for a fresh session" in first.stdout
        sentinel = sentinel_dir / ".compact-warned-fires-once"
        assert sentinel.exists()

        second = _run_hook(
            _COMPACT_WARNING,
            {
                "session_id": "fires-once",
                "transcript_path": str(transcript),
                "cwd": str(tmp_path),
            },
            env_overrides=env,
        )
        # Sentinel respected — second invocation silent.
        assert second.returncode == 0
        assert second.stdout == ""

    def test_missing_transcript_path_silent(self, tmp_path: Path) -> None:
        result = _run_hook(
            _COMPACT_WARNING,
            {"session_id": "no-transcript", "cwd": str(tmp_path)},
        )
        assert result.returncode == 0
        assert result.stdout == ""

    def test_malformed_payload_silent(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_COMPACT_WARNING)],
            input="<not json>",
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=os.environ.copy(),
            timeout=10,
        )
        assert proc.returncode == 0
        assert proc.stdout == ""

    def test_invalid_threshold_falls_back(self, tmp_path: Path) -> None:
        """Hook still works when env threshold is garbage."""
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({"role": "user", "content": "hi"}) + "\n")
        result = _run_hook(
            _COMPACT_WARNING,
            {
                "session_id": "bad-threshold",
                "transcript_path": str(transcript),
                "cwd": str(tmp_path),
            },
            env_overrides={
                "ATTUNE_AI_SENTINEL_DIR": str(tmp_path),
                "ATTUNE_AI_COMPACT_WARNING_THRESHOLD": "garbage",
            },
        )
        assert result.returncode == 0
        # Default 0.70 is well above the tiny transcript's util → silent.
        assert result.stdout == ""
