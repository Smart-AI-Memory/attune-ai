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
import os
import sys
import urllib.request
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


def test_extract_heuristic_skips_git_log_noise(stash_mod):
    # Marker-matching lines that are actually git-log / commit noise must be
    # filtered (they dominate a transcript tail full of `git log` output).
    text = (
        "a1b2c3d docs(CLAUDE.md): release-tax fix + P2 build lessons (#599)\n"
        "fix(hooks): comment the sentinel-write except (code-quality nit)\n"
        "assistant: the real lesson was that a cold model times out and starves it\n"
    )
    found = stash_mod._extract_heuristic(text)
    contents = [f["content"] for f in found]
    assert not any(c.startswith("a1b2c3d") for c in contents), "commit-hash line leaked"
    assert not any(c.startswith("fix(hooks)") for c in contents), "conv-commit line leaked"
    assert any("cold model times out" in c for c in contents), "real insight dropped"


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


def test_extract_via_ollama_returns_none_on_empty_findings(stash_mod, monkeypatch):
    # A well-formed but empty response must return None (not []), so the
    # caller falls back to the heuristic instead of stashing nothing.
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"response": json.dumps({"findings": []})}).encode()

    monkeypatch.setattr(stash_mod.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert stash_mod._extract_via_ollama("some transcript") is None


# ==========================================================================
# session_stash — Ollama extraction, NON-MOCKED round-trip (real boundary)
# ==========================================================================


def _ollama_available() -> bool:
    """True when Ollama answers and the configured extraction model is pulled."""
    base = os.environ.get("ATTUNE_MEMORY_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("ATTUNE_MEMORY_OLLAMA_MODEL", "llama3.1:8b")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=2) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — any failure means "no Ollama" -> skip
        return False
    names = {m.get("name", "") for m in tags.get("models", [])}
    family = model.split(":")[0]
    return any(n == model or n.startswith(family) for n in names)


@pytest.mark.skipif(not _ollama_available(), reason="Ollama + extraction model not available")
def test_extract_via_ollama_real_round_trip(stash_mod):
    """NON-MOCKED: a real Ollama call returns parseable typed findings.

    The mocked test above proves parsing of a *canned* response; this proves
    the real ``/api/generate`` request shape + real model output parse
    end-to-end — the boundary a mock cannot exercise. Model output is
    non-deterministic, so assert STRUCTURE, not content.
    """
    transcript = (
        "user: We kept getting double charges on Stripe webhooks.\n"
        "assistant: Root cause was the idempotency key being omitted on retries; "
        "adding it fixed the double charge. We also decided to standardize on "
        "Redis AMS for cross-session memory.\n"
    )
    findings = stash_mod._extract_via_ollama(transcript)
    assert findings is not None, "real Ollama returned no parseable findings for a clear transcript"
    assert isinstance(findings, list) and findings
    for f in findings:
        assert isinstance(f, dict)
        assert isinstance(f.get("content"), str) and f["content"].strip()
    # Normalized output honors the contract: well-typed and clamped.
    norm = stash_mod._normalize(findings)
    assert 1 <= len(norm) <= stash_mod._MAX_FINDINGS
    assert all(n["type"] in stash_mod._VALID_TYPES for n in norm)


def test_extract_via_ollama_real_unreachable_returns_none(stash_mod, monkeypatch):
    """Real refused socket (dead port) -> None, so main() falls back to the
    heuristic. Complements the mocked-exception test with urllib's actual
    error path against a port where nothing listens.
    """
    monkeypatch.setenv("ATTUNE_MEMORY_OLLAMA_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("ATTUNE_MEMORY_STASH_TIMEOUT", "2")
    assert stash_mod._extract_via_ollama("a session where we fixed a real bug") is None


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
    # The skip must leave a forensic trail (2026-06-11 triage: silent
    # gate-skips made "why is the store empty" an hour of archaeology).
    log = (tmp_path / "stash.log").read_text(encoding="utf-8")
    assert "skip session=s2" in log and "util=0.010" in log


def test_stash_main_logs_write_path_failure(stash_mod, monkeypatch, tmp_path):
    # findings extracted but zero written (attune unimportable / backend
    # write failed) — the sentinel is still set to avoid per-turn Ollama
    # re-runs, so the log line is the ONLY visible signal of the loss.
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
    monkeypatch.setattr(stash_mod, "_stash_findings", lambda findings, **k: 0)
    _stdin(monkeypatch, {"session_id": "s9", "transcript_path": str(tpath), "cwd": "/proj"})
    assert stash_mod.main() == 0
    log = (tmp_path / "stash.log").read_text(encoding="utf-8")
    assert "findings=1 written=0" in log and "WRITE PATH FAILED" in log


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


def test_stash_main_falls_back_to_heuristic_when_ollama_empty(stash_mod, monkeypatch, tmp_path):
    # The dogfood bug: Ollama unavailable/empty must NOT starve extraction —
    # main() falls back to the heuristic so a real marker line still stashes.
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
    tpath = tmp_path / "t.jsonl"
    tpath.write_text(
        json.dumps(
            {"message": {"role": "assistant", "content": "the root cause was a stale lockfile"}}
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(stash_mod, "estimate_utilization", lambda _p: 0.9)
    monkeypatch.setattr(stash_mod, "_extract_via_ollama", lambda _t: None)  # unavailable/empty
    written = []
    monkeypatch.setattr(
        stash_mod,
        "_stash_findings",
        lambda findings, **k: written.extend(findings) or len(findings),
    )
    _stdin(monkeypatch, {"session_id": "s4", "transcript_path": str(tpath), "cwd": "/proj"})
    assert stash_mod.main() == 0
    assert written, "heuristic fallback should have produced a finding when Ollama returned None"
    assert any("root cause" in f["content"].lower() for f in written)


def test_stash_findings_round_trips_through_real_file_backend(stash_mod, monkeypatch, tmp_path):
    """Non-mocked receipt: extract -> real sanitize -> real file write -> recall."""
    import attune.memory.session_stash as ss
    from attune.memory.file_stash import FileStashBackend

    backend = FileStashBackend(base_dir=tmp_path / "stash")
    monkeypatch.setattr(ss, "resolve_backend", lambda *a, **k: backend)

    n = stash_mod._stash_findings(
        [{"type": "bug", "content": "a race in the runner stop hook"}],
        session_id="rt",
        cwd="/proj",
    )
    assert n == 1, "the finding should persist through the real backend"
    # query-less recall (SessionStart path)
    recent = ss.recent_entries(top_k=5, backend=backend)
    assert any("race in the runner" in (h.get("text") or "") for h in recent)
    # keyword recall (/recall path)
    found = ss.recall_entries("race runner", backend=backend)
    assert any("race in the runner" in (h.get("text") or "") for h in found)


# ==========================================================================
# session_stash — additionalContext emission (Claude Code >= 2.1.163)
# ==========================================================================


def test_emit_additional_context_envelope(stash_mod, capsys):
    stash_mod._emit_additional_context(
        [{"type": "bug", "content": "a race in the stop hook"}], written=1
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "Stop"
    ctx = hso["additionalContext"]
    assert "Stashed 1 session finding" in ctx
    assert "[bug] a race in the stop hook" in ctx


def test_emit_additional_context_noop_when_nothing_written(stash_mod, capsys):
    stash_mod._emit_additional_context([{"type": "note", "content": "x"}], written=0)
    assert capsys.readouterr().out == ""


def test_emit_additional_context_disabled_via_env(stash_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_MEMORY_STASH_CONTEXT", "0")
    stash_mod._emit_additional_context([{"type": "note", "content": "x"}], written=1)
    assert capsys.readouterr().out == ""


def test_stash_main_emits_additional_context(stash_mod, monkeypatch, tmp_path, capsys):
    """main() happy path injects the stashed findings into the next turn."""
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
    tpath = tmp_path / "t.jsonl"
    tpath.write_text(
        json.dumps({"message": {"role": "assistant", "content": "the bug was a race"}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(stash_mod, "estimate_utilization", lambda _p: 0.9)
    monkeypatch.setattr(
        stash_mod, "_extract_via_ollama", lambda _t: [{"type": "bug", "content": "a race"}]
    )
    monkeypatch.setattr(stash_mod, "_stash_findings", lambda findings, **k: len(findings))
    _stdin(monkeypatch, {"session_id": "ctx1", "transcript_path": str(tpath), "cwd": "/proj"})
    assert stash_mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "[bug] a race" in payload["hookSpecificOutput"]["additionalContext"]


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


_HEALTHY = {"backend": "FileStashBackend", "fallback": True, "unreachable_upgrade": None}
_DEGRADED = {"backend": "FileStashBackend", "fallback": True, "unreachable_upgrade": "redis"}


def test_recall_main_emits_block(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(
        ss, "recent_entries", lambda **k: [{"text": "a finding", "topics": ["type:note"]}]
    )
    monkeypatch.setattr(ss, "backend_status", lambda: dict(_HEALTHY))
    _stdin(monkeypatch, {"source": "startup", "cwd": "/proj"})
    assert recall_mod.main() == 0
    out = capsys.readouterr().out
    assert "## Recalled memories" in out and "- [note] a finding" in out
    assert "degraded" not in out


def test_recall_main_silent_when_empty(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(ss, "recent_entries", lambda **k: [])
    monkeypatch.setattr(ss, "backend_status", lambda: dict(_HEALTHY))
    _stdin(monkeypatch, {"source": "startup"})
    assert recall_mod.main() == 0
    assert capsys.readouterr().out == ""


def test_recall_main_warns_when_upgrade_unreachable_even_with_no_entries(
    recall_mod, monkeypatch, capsys
):
    # The 2026-06-11 incident: AMS down for a week, recall silently degraded
    # to an empty file tier. The health line must surface even when there is
    # nothing to recall — silence is exactly what hid the outage.
    import attune.memory.session_stash as ss

    monkeypatch.setattr(ss, "recent_entries", lambda **k: [])
    monkeypatch.setattr(ss, "backend_status", lambda: dict(_DEGRADED))
    _stdin(monkeypatch, {"source": "startup"})
    assert recall_mod.main() == 0
    out = capsys.readouterr().out
    assert "degraded" in out and "'redis'" in out


def test_recall_main_appends_warning_after_block_when_degraded(recall_mod, monkeypatch, capsys):
    import attune.memory.session_stash as ss

    monkeypatch.setattr(
        ss, "recent_entries", lambda **k: [{"text": "a finding", "topics": ["type:note"]}]
    )
    monkeypatch.setattr(ss, "backend_status", lambda: dict(_DEGRADED))
    _stdin(monkeypatch, {"source": "startup", "cwd": "/proj"})
    assert recall_mod.main() == 0
    out = capsys.readouterr().out
    assert "- [note] a finding" in out
    assert "degraded" in out and "'redis'" in out


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


# ==========================================================================
# Provenance filtering (#1263, docs/specs/stash-extractor-provenance/)
# ==========================================================================


def _jsonl_line(role: str, content) -> str:
    return json.dumps({"message": {"role": role, "content": content}})


@pytest.fixture
def poisoned_transcript(tmp_path):
    """The 2026-07-05 failure shape: a Read tool_result carrying
    memory-file prose (as a user-ROLE message), between genuine turns."""
    ambient_prose = (
        "Patrick has self-identified that pushing through exhaustion "
        "creates downstream debug cost. Lesson learned: compact reply "
        "vocab should be used consistently."
    )
    lines = [
        _jsonl_line("user", "please run the memory corpus lint"),
        _jsonl_line(
            "assistant",
            [
                {"type": "text", "text": "Reading the memory files now."},
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "x.md"}},
            ],
        ),
        _jsonl_line(
            "user",
            [
                {
                    "type": "tool_result",
                    "tool_use_id": "t1",
                    "content": [{"type": "text", "text": ambient_prose}],
                }
            ],
        ),
        _jsonl_line(
            "assistant",
            "Root cause found: the bulk regen wrote an empty-string "
            "source hash — that bug gutted all 36 template files.",
        ),
    ]
    p = tmp_path / "poisoned.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_tail_excludes_tool_result_content(stash_mod, poisoned_transcript):
    tail = stash_mod._read_transcript_tail(str(poisoned_transcript))
    assert "exhaustion" not in tail
    assert "compact reply vocab" not in tail
    assert stash_mod._OMITTED_MARKER in tail
    # Genuine turns survive, correctly attributed.
    assert "memory corpus lint" in tail
    assert "empty-string" in tail


def test_tail_excludes_tool_use_input(stash_mod, poisoned_transcript):
    tail = stash_mod._read_transcript_tail(str(poisoned_transcript))
    assert "x.md" not in tail  # tool_use input is ambient too


def test_heuristic_cannot_surface_ambient_prose(stash_mod, poisoned_transcript):
    """The poisoned line contains a marker word ('Lesson learned') — with
    the filter it never reaches the heuristic at all."""
    tail = stash_mod._read_transcript_tail(str(poisoned_transcript))
    found = stash_mod._extract_heuristic(tail)
    assert all("compact reply vocab" not in f["content"] for f in found)
    assert all("exhaustion" not in f["content"] for f in found)


def test_consecutive_omission_markers_collapse(stash_mod, tmp_path):
    result_block = [
        {
            "type": "tool_result",
            "tool_use_id": "t",
            "content": [{"type": "text", "text": "dump"}],
        }
    ]
    lines = [_jsonl_line("user", result_block) for _ in range(6)]
    lines.append(_jsonl_line("assistant", "Decision: ship it."))
    p = tmp_path / "toolheavy.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    tail = stash_mod._read_transcript_tail(str(p))
    assert tail.count(stash_mod._OMITTED_MARKER) < 6
    assert "Decision: ship it." in tail


def test_prompt_carries_provenance_rules(stash_mod, monkeypatch):
    """The Ollama prompt must instruct assertion-only extraction (R2)."""
    captured = {}

    class _Resp:
        def read(self):
            return json.dumps({"response": json.dumps({"findings": []})}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    stash_mod._extract_via_ollama("assistant: concluded X")
    prompt = captured["body"]["prompt"]
    assert "PROVENANCE" in prompt
    assert "merely read" in prompt
