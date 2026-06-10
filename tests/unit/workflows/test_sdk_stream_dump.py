"""Tests for the ATTUNE_SDK_STREAM_DUMP instrumentation
(opus-4-8-platform-fit Phase 0, design D-instrumentation).

The dump is the measurement substrate for every Phase-0 axis, so the
guards here are: OFF by default (zero behavior change), content-free
records (chars/flags, never text), full ResultMessage metadata, and
fail-soft on unwritable destinations.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import claude_agent_sdk
import pytest
from claude_agent_sdk import types as sdk_types

from attune.workflows.agent_sdk_adapter import collect_agent_output


def _assistant(*blocks: object) -> claude_agent_sdk.AssistantMessage:
    return claude_agent_sdk.AssistantMessage(content=list(blocks), model="claude-opus-4-8")


def _result(**overrides: object) -> claude_agent_sdk.ResultMessage:
    kwargs: dict[str, object] = {
        "subtype": "success",
        "duration_ms": 1200,
        "duration_api_ms": 900,
        "is_error": False,
        "num_turns": 3,
        "session_id": "sess-1",
        "total_cost_usd": 1.23,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    kwargs.update(overrides)
    return claude_agent_sdk.ResultMessage(**kwargs)


def _dump_lines(dump_dir: Path) -> list[dict]:
    files = list(dump_dir.glob("stream-*.jsonl"))
    if not files:
        return []
    return [json.loads(line) for line in files[0].read_text().splitlines()]


@pytest.mark.unit
class TestStreamDumpOffByDefault:
    def test_no_env_no_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ATTUNE_SDK_STREAM_DUMP", raising=False)
        monkeypatch.chdir(tmp_path)
        collect_agent_output(_assistant(sdk_types.TextBlock(text="hello")), [], [])
        assert list(tmp_path.rglob("stream-*.jsonl")) == []

    def test_collect_behavior_unchanged_when_dumping(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_SDK_STREAM_DUMP", str(tmp_path))
        parts: list[str] = []
        collect_agent_output(_assistant(sdk_types.TextBlock(text="analysis")), parts, [])
        assert parts == ["analysis"]
        run = collect_agent_output(_result(), [], [])
        assert run is not None and run.total_cost_usd == 1.23


@pytest.mark.unit
class TestStreamDumpRecords:
    def test_assistant_blocks_content_free(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_SDK_STREAM_DUMP", str(tmp_path))
        msg = _assistant(
            sdk_types.TextBlock(text="Should I proceed with the scan?"),
            sdk_types.ToolUseBlock(id="t1", name="Task", input={"prompt": "secret payload"}),
        )
        collect_agent_output(msg, [], [])
        (rec,) = _dump_lines(tmp_path)
        assert rec["type"] == "AssistantMessage"
        text_block, tool_block = rec["blocks"]
        assert text_block["kind"] == "TextBlock"
        assert text_block["chars"] == len("Should I proceed with the scan?")
        assert text_block["interrogative"] is True
        assert "Should I proceed" not in json.dumps(rec), "dump must be content-free"
        assert "secret payload" not in json.dumps(rec), "tool input must not be dumped"
        assert tool_block == {"kind": "ToolUseBlock", "tool_name": "Task"}

    def test_result_message_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_SDK_STREAM_DUMP", str(tmp_path))
        collect_agent_output(_result(), [], [])
        (rec,) = _dump_lines(tmp_path)
        assert rec["type"] == "ResultMessage"
        assert rec["result"]["total_cost_usd"] == 1.23
        assert rec["result"]["usage"] == {"input_tokens": 10, "output_tokens": 5}
        assert rec["result"]["num_turns"] == 3

    def test_appends_across_messages(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_SDK_STREAM_DUMP", str(tmp_path))
        collect_agent_output(_assistant(sdk_types.TextBlock(text="a")), [], [])
        collect_agent_output(_result(), [], [])
        assert len(_dump_lines(tmp_path)) == 2


@pytest.mark.unit
class TestStreamDumpFailSoft:
    def test_unwritable_dir_never_breaks_collection(self, tmp_path, monkeypatch):
        blocker = tmp_path / "blocked"
        blocker.write_text("a file, not a dir", encoding="utf-8")
        monkeypatch.setenv("ATTUNE_SDK_STREAM_DUMP", str(blocker / "sub"))
        parts: list[str] = []
        collect_agent_output(_assistant(sdk_types.TextBlock(text="x")), parts, [])
        assert parts == ["x"], "collection must survive a dump failure"
