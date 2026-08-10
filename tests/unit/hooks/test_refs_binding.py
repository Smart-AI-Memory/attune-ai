"""Tests for the refs-v2 extraction + binder path (memory-claim-verification T1+T2).

Design contract (docs/specs/memory-claim-verification/design.md, post-D9):
propose-at-extraction, validate-at-binding; the ENTIRE v2 path is gated
behind ATTUNE_MEMORY_REFS_V2 (default off — the T4 gate flips it); the
parser is syntax-only so an unknown kind reaches the binder and is stored
``rejected:bad_kind``; binding is exact membership against the
tool_use-derived universe — no LLM, no fuzzy matching.
"""

from __future__ import annotations

import importlib.util
import inspect
import io
import json
import sys
import types
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stash_mod():
    return _load_module("session_stash")


def _transcript(tmp_path: Path, blocks: list[dict]) -> str:
    """Write a minimal transcript JSONL carrying the given tool_use inputs."""
    lines = []
    for inputs in blocks:
        lines.append(
            json.dumps(
                {"message": {"content": [{"type": "tool_use", "name": "X", "input": inputs}]}}
            )
        )
    p = tmp_path / "transcript.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------- flag


def test_refs_v2_disabled_by_default(stash_mod, monkeypatch):
    monkeypatch.delenv("ATTUNE_MEMORY_REFS_V2", raising=False)
    assert stash_mod._refs_v2_enabled() is False


def _captured_prompt(stash_mod, monkeypatch) -> str:
    """Run _extract_via_ollama against a fake urlopen; return the prompt sent."""
    seen: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"response": json.dumps({"findings": []})}).encode()

    def fake_urlopen(req, timeout=0):
        seen["prompt"] = json.loads(req.data.decode())["prompt"]
        return _Resp()

    monkeypatch.setattr(stash_mod.urllib.request, "urlopen", fake_urlopen)
    stash_mod._extract_via_ollama("tail text")
    return seen["prompt"]


def test_flag_off_prompt_is_v1_shape(stash_mod, monkeypatch):
    monkeypatch.delenv("ATTUNE_MEMORY_REFS_V2", raising=False)
    prompt = _captured_prompt(stash_mod, monkeypatch)
    assert "source_ref" in prompt
    assert '"refs"' not in prompt
    assert "convenience reference" not in prompt


def test_flag_on_prompt_requests_refs_not_source_ref(stash_mod, monkeypatch):
    monkeypatch.setenv("ATTUNE_MEMORY_REFS_V2", "1")
    prompt = _captured_prompt(stash_mod, monkeypatch)
    assert '"refs"' in prompt
    assert "a convenience reference is a defect" in prompt
    assert "source_ref" not in prompt


# ---------------------------------------------------------------- parser


def _typed(refs) -> list[dict]:
    return [{"type": "bug", "content": "the parser eats refs", "confidence": 0.9, "refs": refs}]


def test_parse_keeps_valid_refs_deduped_and_capped(stash_mod):
    out = stash_mod._parse_typed_findings(
        _typed(["file:src/a.py", "file:src/a.py", "pr:12", "spec:x", "file:src/b.py"])
    )
    assert out[0]["refs"] == ["file:src/a.py", "pr:12", "spec:x"]


def test_parse_drops_bad_items_finding_survives(stash_mod):
    out = stash_mod._parse_typed_findings(
        _typed([42, "x" * 300, "no-colon-here", "file:ok.py", "---\nfile:evil"])
    )
    assert out and out[0]["refs"] == ["file:ok.py"]


def test_parse_all_items_dropped_yields_explicit_empty(stash_mod):
    out = stash_mod._parse_typed_findings(_typed([42, "nope"]))
    assert out and out[0]["refs"] == []


def test_parse_unknown_kind_survives_to_reach_binder(stash_mod):
    # Kind validation is the BINDER's — a parser allowlist would eat the
    # rejected:bad_kind evaluation surface (design D-2, codex lane).
    out = stash_mod._parse_typed_findings(_typed(["commit:abc123def"]))
    assert out and out[0]["refs"] == ["commit:abc123def"]


def test_parse_non_list_refs_treated_as_absent(stash_mod):
    out = stash_mod._parse_typed_findings(_typed("file:a.py"))
    assert out and "refs" not in out[0]


def test_normalize_carries_refs_through(stash_mod):
    clean = stash_mod._normalize(
        [{"type": "bug", "content": "carried through normalize", "refs": ["pr:7", 3]}]
    )
    assert clean[0]["refs"] == ["pr:7"]


# ---------------------------------------------------------------- universe


def test_derive_universe_from_tool_use(stash_mod, tmp_path):
    path = _transcript(
        tmp_path,
        [
            {"file_path": "/abs/src/attune/x.py"},
            {"command": "gh pr view 1234 && pytest tests/unit/test_y.py"},
            {"command": "cat docs/specs/memory-claim-verification/design.md"},
        ],
    )
    u = stash_mod._derive_session_refs(path)
    assert "/abs/src/attune/x.py" in u["file"]
    assert "1234" not in u["pr"]  # bare number: not a pr ref pattern
    assert "tests/unit/test_y.py" in u["file"]
    assert "memory-claim-verification" in u["spec"]


def test_derive_universe_pr_forms(stash_mod, tmp_path):
    path = _transcript(tmp_path, [{"command": "gh pr merge #77 and pull/88 today"}])
    u = stash_mod._derive_session_refs(path)
    assert u["pr"] == {"77", "88"}


def test_derive_universe_missing_transcript_is_none(stash_mod, tmp_path):
    assert stash_mod._derive_session_refs(str(tmp_path / "nope.jsonl")) is None
    assert stash_mod._derive_session_refs(None) is None


# ---------------------------------------------------------------- binder


def _bind_one(stash_mod, refs, transcript_path, cwd="/repo"):
    finding = {"type": "bug", "content": "c", "refs": refs}
    stash_mod._bind_findings([finding], transcript_path, cwd)
    return finding


def test_binder_binds_exact_file_pr_and_spec(stash_mod, tmp_path):
    path = _transcript(
        tmp_path,
        [
            {"file_path": "/repo/src/a.py"},
            {"command": "gh pr view #55; cat docs/specs/some-spec/x.md"},
        ],
    )
    f = _bind_one(stash_mod, ["file:src/a.py", "pr:#55", "spec:Some-Spec"], path, cwd="/repo")
    assert f["ref_status"] == "bound"
    tags = f["_ref_tags"]
    assert "ref_bound:file:/repo/src/a.py" in tags
    assert "ref_bound:pr:55" in tags
    assert "ref_bound:spec:some-spec" in tags
    assert "schema_version:2" in tags


def test_binder_rejects_bad_kind_reason_coded(stash_mod, tmp_path):
    path = _transcript(tmp_path, [{"file_path": "/repo/src/a.py"}])
    f = _bind_one(stash_mod, ["commit:abc123def", "file:src/a.py"], path)
    assert f["ref_status"] == "bound"
    assert "ref_rejected:bad_kind:commit:abc123def" in f["_ref_tags"]


def test_binder_rejects_not_in_session(stash_mod, tmp_path):
    path = _transcript(tmp_path, [{"file_path": "/repo/src/a.py"}])
    f = _bind_one(stash_mod, ["file:src/other.py"], path)
    assert f["ref_status"] == "unbound_all_rejected"
    assert "ref_rejected:not_in_session:file:src/other.py" in f["_ref_tags"]


def test_binder_no_prefix_containment(stash_mod, tmp_path):
    # /repo/src/a.py in universe must NOT bind /repo/src/a.py.bak or
    # a sibling sharing the prefix — exact membership only.
    path = _transcript(tmp_path, [{"file_path": "/repo/src/a.py"}])
    f = _bind_one(stash_mod, ["file:src/a.py.bak"], path)
    assert f["ref_status"] == "unbound_all_rejected"


def test_binder_empty_refs_is_explicit_unbound(stash_mod, tmp_path):
    path = _transcript(tmp_path, [{"file_path": "/repo/src/a.py"}])
    f = _bind_one(stash_mod, [], path)
    assert f["ref_status"] == "unbound_explicit"
    assert "ref_status:unbound_explicit" in f["_ref_tags"]


def test_binder_unreadable_transcript_degrades_honestly(stash_mod, tmp_path):
    f = _bind_one(stash_mod, ["file:src/a.py"], str(tmp_path / "gone.jsonl"))
    assert f["ref_status"] == "no_ref_universe"
    assert "ref_proposed:file:src/a.py" in f["_ref_tags"]
    assert not any(t.startswith("ref_rejected:not_in_session") for t in f["_ref_tags"])


def test_binder_zero_universe_session_degrades_honestly(stash_mod, tmp_path):
    path = _transcript(tmp_path, [{"description": "no strings of interest"}])
    f = _bind_one(stash_mod, ["file:src/a.py"], path)
    assert f["ref_status"] == "no_ref_universe"


# ---------------------------------------------------------------- stash tags


def test_stash_persists_ref_tags(stash_mod, monkeypatch):
    captured: list = []

    class _Entry:
        id = "abc12345"

        @classmethod
        def create(cls, **kwargs):
            captured.append(kwargs)
            return cls()

    fake = types.ModuleType("attune.memory.session_stash")
    fake.SessionStashEntry = _Entry
    fake.resolve_backend = lambda *a, **k: None
    fake.stash_entry = lambda entry: True
    monkeypatch.setitem(sys.modules, "attune.memory.session_stash", fake)

    findings = [
        {
            "type": "bug",
            "content": "c",
            "confidence": 0.8,
            "_ref_tags": ["schema_version:2", "ref_status:bound", "ref_bound:pr:55"],
        }
    ]
    written = stash_mod._stash_findings(findings, session_id="s", cwd="/repo")
    assert written == 1
    tags = captured[0]["tags"]
    assert "confidence:0.8" in tags
    assert "schema_version:2" in tags
    assert "ref_status:bound" in tags
    assert "ref_bound:pr:55" in tags


# ---------------------------------------------------------------- drift guard


def test_binder_contains_no_fuzzy_matching_constructs(stash_mod):
    """D8 retired fuzzy prose matching; the binder must never regrow it."""
    source = inspect.getsource(stash_mod._bind_findings) + inspect.getsource(
        stash_mod._normalize_ref_value
    )
    for forbidden in (".stem", "basename", "in content", "in lower", "findall"):
        assert forbidden not in source, f"fuzzy construct {forbidden!r} in binder"


def test_main_flag_off_never_calls_binder(stash_mod, monkeypatch, tmp_path):
    monkeypatch.delenv("ATTUNE_MEMORY_REFS_V2", raising=False)

    def _boom(*a, **k):  # pragma: no cover - failure branch
        raise AssertionError("binder must not run with the flag off")

    monkeypatch.setattr(stash_mod, "_bind_findings", _boom)
    monkeypatch.setattr(stash_mod, "_enabled", lambda: True)
    monkeypatch.setattr(stash_mod, "_stash_sentinel", lambda s: None)
    monkeypatch.setattr(stash_mod, "estimate_utilization", None)
    monkeypatch.setattr(stash_mod, "_read_transcript_tail", lambda p: "tail " * 20)
    monkeypatch.setattr(
        stash_mod,
        "_extract_via_ollama",
        lambda t: [{"type": "bug", "content": "finding text", "confidence": 0.9}],
    )
    monkeypatch.setattr(stash_mod, "_stash_findings", lambda f, session_id, cwd: 0)
    monkeypatch.setattr(stash_mod.sys, "stdin", io.StringIO(json.dumps({"session_id": "s"})))
    assert stash_mod.main() == 0
