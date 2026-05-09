"""Tests for plugin/hooks/_transcript_size.py — utilization estimator.

Synthetic transcript JSONL files of known sizes drive the
estimator. The proxy is monotonic and bounded to ``[0.0, 1.0]``;
tests verify those properties plus env-var tuning hooks.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ts_mod():
    return _load_module("_transcript_size")


def _write_transcript(path: Path, messages: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(m) for m in messages) + "\n",
        encoding="utf-8",
    )


# ── _sum_message_chars ──────────────────────────────────────


class TestSumMessageChars:
    def test_missing_file_returns_zero(self, tmp_path: Path, ts_mod) -> None:
        assert ts_mod._sum_message_chars(tmp_path / "absent.jsonl") == 0

    def test_string_content(self, tmp_path: Path, ts_mod) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(
            path,
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world!"},
            ],
        )
        assert ts_mod._sum_message_chars(path) == len("hello") + len("world!")

    def test_list_of_text_parts(self, tmp_path: Path, ts_mod) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(
            path,
            [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "hello"},
                        {"type": "text", "text": "world"},
                    ],
                }
            ],
        )
        assert ts_mod._sum_message_chars(path) == 10

    def test_legacy_envelope_with_message_field(self, tmp_path: Path, ts_mod) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(
            path,
            [
                {
                    "type": "user_turn",
                    "message": {"role": "user", "content": "abc"},
                }
            ],
        )
        assert ts_mod._sum_message_chars(path) == 3

    def test_malformed_lines_skipped(self, tmp_path: Path, ts_mod) -> None:
        path = tmp_path / "transcript.jsonl"
        path.write_text(
            'not-json\n{"role": "user", "content": "ok"}\n',
            encoding="utf-8",
        )
        assert ts_mod._sum_message_chars(path) == 2

    def test_blank_lines_skipped(self, tmp_path: Path, ts_mod) -> None:
        path = tmp_path / "transcript.jsonl"
        path.write_text(
            '\n\n{"role": "assistant", "content": "x"}\n\n',
            encoding="utf-8",
        )
        assert ts_mod._sum_message_chars(path) == 1


# ── estimate_utilization ────────────────────────────────────


class TestEstimateUtilization:
    def test_empty_path_zero(self, ts_mod) -> None:
        assert ts_mod.estimate_utilization("") == 0.0

    def test_missing_file_zero(self, ts_mod, tmp_path: Path) -> None:
        assert ts_mod.estimate_utilization(tmp_path / "absent.jsonl") == 0.0

    def test_small_session_low_util(self, ts_mod, tmp_path: Path) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(path, [{"role": "user", "content": "hi"} for _ in range(5)])
        util = ts_mod.estimate_utilization(path)
        assert 0.0 < util < 0.01

    def test_large_session_higher_util_clamped_to_one(self, ts_mod, tmp_path: Path) -> None:
        path = tmp_path / "transcript.jsonl"
        # 1 million chars / 4 chars-per-token / 200k tokens = 1.25 → clamped
        big = "x" * 1_000_000
        _write_transcript(path, [{"role": "user", "content": big}])
        util = ts_mod.estimate_utilization(path)
        assert util == 1.0

    def test_monotonic_growth(self, ts_mod, tmp_path: Path) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(path, [{"role": "user", "content": "x" * 1000}])
        small = ts_mod.estimate_utilization(path)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"role": "assistant", "content": "y" * 1000}) + "\n")
        bigger = ts_mod.estimate_utilization(path)
        assert bigger > small

    def test_env_var_threshold_tuning(
        self, ts_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(path, [{"role": "user", "content": "x" * 4000}])
        # Default: 4000 / 4 / 200k = 0.005
        baseline = ts_mod.estimate_utilization(path)
        monkeypatch.setenv("ATTUNE_AI_CONTEXT_WINDOW_TOKENS", "1000")
        # Now: 4000 / 4 / 1000 = 1.0 (clamped)
        boosted = ts_mod.estimate_utilization(path)
        assert boosted > baseline
        assert boosted == 1.0

    def test_invalid_env_falls_back_to_default(
        self, ts_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "transcript.jsonl"
        _write_transcript(path, [{"role": "user", "content": "x" * 4000}])
        monkeypatch.setenv("ATTUNE_AI_CHARS_PER_TOKEN", "garbage")
        monkeypatch.setenv("ATTUNE_AI_CONTEXT_WINDOW_TOKENS", "also-garbage")
        # Both invalid env values → defaults; estimate should still
        # return a sensible number, not crash.
        util = ts_mod.estimate_utilization(path)
        assert 0.0 <= util <= 1.0
