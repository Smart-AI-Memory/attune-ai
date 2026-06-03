"""Tests for the P2 memory hooks — session_stash (Stop) + session_recall.

The hooks are standalone scripts; they're loaded via importlib so their
pure helpers (transcript parsing, Ollama extraction, normalization,
recall formatting) and their gate/sentinel control flow can be exercised
without a live Claude Code session, Ollama, or a real backend.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]  # fresh load so module-level env reads are clean
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stash_mod():
    return _load_module("session_stash")


@pytest.fixture
def recall_mod():
    return _load_module("session_recall")


def _stdin(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


# ==========================================================================
# session_stash — pure helpers
# ==========================================================================


def test_text_of_handles_str_list_dict(stash_mod):
    assert stash_mod._text_of("plain") == "plain"
    assert stash_mod._text_of([{"text": "a"}, {"text": "b"}]) == "a b"
    assert stash_mod._text_of({"text": "x", "content": [{"text": "y"}]}) == "x y"
    assert stash_mod._text_of(None) == ""


def test_read_transcript_tail(tmp_path, stash_mod):
    p = tmp_path / "t.jsonl"
    p.write_text(
        "\n".join(
            json.dumps(m)
            for m in [
                {"message": {"role": "user", "content": "hello there"}},
                {
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "hi back"}],
                    }
                },
                "not json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tail = stash_mod._read_transcript_tail(str(p))
    assert "hello there" in tail and "hi back" in tail


def test_read_transcript_tail_missing_file(stash_mod):
    assert stash_mod._read_transcript_tail(None) == ""
    assert stash_mod._read_transcript_tail("/no/such/file.jsonl") == ""


def test_extract_heuristic_finds_markers(stash_mod):
    text = (
        "user: just chatting about the weather today and stuff\n"
        "assistant: The root cause was a stale lockfile in the build step\n"
        "assistant: I decided to drop the security check from required gates\n"
        "assistant: ok\n"
    )
    found = stash_mod._extract_heuristic(text)
    assert 1 <= len(found) <= stash_mod._MAX_FINDINGS
    assert all(f["type"] == "note" for f in found)
    assert any("root cause" in f["content"].lower() for f in found)


def test_normalize_clamps_type_and_count(stash_mod):
    raw = [{"type": "bogus", "content": "keep me"}] + [
        {"type": "bug", "content": f"f{i}"} for i in range(10)
    ]
    out = stash_mod._normalize(raw)
    assert len(out) == stash_mod._MAX_FINDINGS
    assert out[0] == {"type": "note", "content": "keep me"}  # bogus type -> note


def test_normalize_drops_empty_content(stash_mod):
    assert stash_mod._normalize([{"type": "bug", "content": "  "}, {"type": "bug"}]) == []


def test_extract_via_ollama_parses_response(stash_mod, monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(
                {"response": json.dumps({"findings": [{"type": "bug", "content": "x"}]})}
            ).encode()

    monkeypatch.setattr(stash_mod.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = stash_mod._extract_via_ollama("some transcript")
    assert out == [{"type": "bug", "content": "x"}]


def test_extract_via_ollama_returns_none_when_unreachable(stash_mod, monkeypatch):
    def _boom(*a, **k):
        raise stash_mod.urllib.error.URLError("connection refused")

    monkeypatch.setattr(stash_mod.urllib.request, "urlopen", _boom)
    assert stash_mod._extract_via_ollama("x") is None


# ==========================================================================
# session_stash — main() gate / sentinel control flow
# ==========================================================================


def test_stash_main_disabled_via_env(stash_mod, monkeypatch):
    monkeypatch.setenv("ATTUNE_MEMORY_STASH", "0")
    _stdin(monkeypatch, {"session_id": "s1"})
    assert stash_mod.main() == 0


def test_stash_main_skips_when_sentinel_exists(stash_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
    sent = stash_mod._stash_sentinel("s1")
    sent.parent.mkdir(parents=True, exist_ok=True)
    sent.write_text("done\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(stash_mod, "_stash_findings", lambda *a, **k: calls.append(a))
    _stdin(monkeypatch, {"session_id": "s1", "transcript_path": str(tmp_path / "t")})
    assert stash_mod.main() == 0
    assert calls == [], "must not stash again when the sentinel is present"


def test_stash_main_skips_below_util_gate(stash_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
    monkeypatch.setattr(stash_mod, "estimate_utilization", lambda _p: 0.01)
    calls = []
    monkeypatch.setattr(stash_mod, "_stash_findings", lambda *a, **k: calls.append(a))
    _stdin(monkeypatch, {"session_id": "s2", "transcript_path": str(tmp_path / "t.jsonl")})
    assert stash_mod.main() == 0
    assert calls == []


def test_stash_main_happy_path_writes_sentinel(stash_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
    tpath = tmp_path / "t.jsonl"
    tpath.write_text(
        json.dumps({"message": {"role": "assistant", "content": "the bug was a race"}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(stash_mod, "estimate_utilization", lambda _p: 0.9)
    monkeypatch.setattr(
        stash_mod, "_extract_via_ollama", lambda _t: [{"type": "bug", "content": "z"}]
    )
    written = []
    monkeypatch.setattr(
        stash_mod,
        "_stash_findings",
        lambda findings, **k: written.extend(findings) or len(findings),
    )
    _stdin(monkeypatch, {"session_id": "s3", "transcript_path": str(tpath), "cwd": "/proj"})
    assert stash_mod.main() == 0
    assert written == [{"type": "bug", "content": "z"}]
    assert stash_mod._stash_sentinel("s3").exists(), "sentinel written after a successful stash"


# ==========================================================================
# session_recall
# ==========================================================================


def test_type_of(recall_mod):
    assert recall_mod._type_of(["cwd:/p", "type:decision"]) == "decision"
    assert recall_mod._type_of(["cwd:/p"]) == "note"
    assert recall_mod._type_of(None) == "note"


def test_format_renders_typed_lines(recall_mod):
    block = recall_mod._format(
        [
            {"text": "dropped reviews to 0", "topics": ["type:decision"]},
            {"text": "race in the runner", "topics": ["type:bug"]},
        ]
    )
    assert "## Recalled memories" in block
    assert "- [decision] dropped reviews to 0" in block
    assert "- [bug] race in the runner" in block


def test_format_respects_budget(recall_mod, monkeypatch):
    monkeypatch.setattr(recall_mod, "_CONTENT_BUDGET", 10)
    block = recall_mod._format(
        [{"text": "x" * 50, "topics": []}, {"text": "should not appear", "topics": []}]
    )
    assert "should not appear" not in block


def test_recall_main_emits_block(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(
        ss, "recent_entries", lambda **k: [{"text": "a finding", "topics": ["type:note"]}]
    )
    _stdin(monkeypatch, {"source": "startup", "cwd": "/proj"})
    assert recall_mod.main() == 0
    out = capsys.readouterr().out
    assert "## Recalled memories" in out and "- [note] a finding" in out


def test_recall_main_silent_when_empty(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(ss, "recent_entries", lambda **k: [])
    _stdin(monkeypatch, {"source": "startup"})
    assert recall_mod.main() == 0
    assert capsys.readouterr().out == ""


def test_recall_main_skips_on_compact(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(ss, "recent_entries", lambda **k: [{"text": "x", "topics": []}])
    _stdin(monkeypatch, {"source": "compact"})
    assert recall_mod.main() == 0
    assert capsys.readouterr().out == ""


def test_recall_main_disabled_via_env(recall_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_MEMORY_RECALL", "0")
    _stdin(monkeypatch, {"source": "startup"})
    assert recall_mod.main() == 0
    assert capsys.readouterr().out == ""
