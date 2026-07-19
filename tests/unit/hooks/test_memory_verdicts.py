"""Verdict-scorer receipts — memory-feedback-signal STEP 2 (MI-1..MI-7).

Receipt 1 (MI-6a, CI-mandatory, non-mocked): real surfacing write →
real scorer run with Ollama ABSENT → real reader aggregation, all on
disk under an isolated ``ATTUNE_HOME`` — proves persistence plus the
``unscored`` degradation contract end-to-end.

Receipt 2 (MI-6b, hermetic): a loopback fake-Ollama HTTP server (a
real local HTTP round-trip, not a mocked client) exercises the
``acted_on`` / ``ignored`` / ``wrong`` parse paths, the 2026-07-08
stale-recall ``wrong`` case, and the MI-7 injection coercions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.delenv("ATTUNE_MEMORY_TELEMETRY", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    return tmp_path


@pytest.fixture
def verdicts_mod(isolated_home):
    return _load_module("_memory_verdicts")


@pytest.fixture
def telemetry_mod(isolated_home):
    return _load_module("_memory_telemetry")


def _events_file(home: Path) -> Path:
    return home / "telemetry" / "memory_events.jsonl"


def _read_events(home: Path) -> list[dict]:
    path = _events_file(home)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_surfacing(telemetry_mod, session="s1", surfacing="abc123def456", items=("L1", "L2")):
    telemetry_mod.log_memory_event(
        "lesson_recall", session_id=session, surfacing_id=surfacing, lessons=list(items)
    )


class TestReceipt1KeylessRoundTrip:
    """MI-6a: real write → real scorer (Ollama absent) → real reader."""

    def test_unscored_end_to_end(self, isolated_home, verdicts_mod, telemetry_mod, monkeypatch):
        # Dead loopback port: connection refused == Ollama unavailable.
        monkeypatch.setenv("ATTUNE_MEMORY_OLLAMA_URL", "http://127.0.0.1:9")
        _write_surfacing(telemetry_mod)
        written = verdicts_mod.score_session("s1", "some transcript tail text")
        assert written == 2

        records = [e for e in _read_events(isolated_home) if e["event"] == "memory_signal"]
        assert {r["verdict"] for r in records} == {"unscored"}
        assert {r["item_id"] for r in records} == {"L1", "L2"}
        assert all(r["source_event"] == "lesson_recall" for r in records)

        from attune.ops.data import estimate_intervention_signal, read_memory_signal

        signal = read_memory_signal(_events_file(isolated_home))
        assert signal["unscored"] == 2 and signal["scored"] == 0
        assert signal["wrong_rate"] is None  # never fabricated from zero

        # All-unscored must NOT flip the caption (MI-5).
        est = estimate_intervention_signal(_events_file(isolated_home))
        from attune.ops.data import INTERVENTION_SIGNAL_CAPTION

        assert est["caption"] == INTERVENTION_SIGNAL_CAPTION
        assert "noise_denominator" not in est

    def test_empty_tail_means_unscored(self, isolated_home, verdicts_mod, telemetry_mod):
        _write_surfacing(telemetry_mod, items=("L1",))
        assert verdicts_mod.score_session("s1", "   ") == 1
        records = [e for e in _read_events(isolated_home) if e["event"] == "memory_signal"]
        assert records[0]["verdict"] == "unscored"


class _FakeOllama(BaseHTTPRequestHandler):
    """Loopback fake-Ollama; the class attr ``verdicts`` is the script."""

    verdicts: list[dict] = []

    def do_POST(self):  # noqa: N802 — BaseHTTPRequestHandler API
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"response": json.dumps({"verdicts": self.verdicts})})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):  # noqa: D102 — silence test output
        return


@pytest.fixture
def fake_ollama(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("ATTUNE_MEMORY_OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    yield _FakeOllama
    server.shutdown()


class TestReceipt2HermeticScoredLabels:
    """MI-6b: real loopback HTTP round-trip through the scored labels."""

    def test_all_three_labels_parse(self, isolated_home, verdicts_mod, telemetry_mod, fake_ollama):
        _write_surfacing(telemetry_mod, surfacing="aaa111bbb222", items=("L1", "L2", "L3"))
        fake_ollama.verdicts = [
            {"surfacing_id": "aaa111bbb222", "item_id": "L1", "label": "acted_on"},
            # L2 models the 2026-07-08 stale-/recall datum: transcript
            # identified the surfaced finding as already-fixed → wrong.
            {"surfacing_id": "aaa111bbb222", "item_id": "L2", "label": "wrong"},
            {"surfacing_id": "aaa111bbb222", "item_id": "L3", "label": "ignored"},
        ]
        assert verdicts_mod.score_session("s1", "tail discussing L1 use and stale L2") == 3
        by_item = {
            e["item_id"]: e["verdict"]
            for e in _read_events(isolated_home)
            if e["event"] == "memory_signal"
        }
        assert by_item == {"L1": "acted_on", "L2": "wrong", "L3": "ignored"}

        from attune.ops.data import (
            INTERVENTION_DENOMINATOR_NOTE,
            estimate_intervention_signal,
            read_memory_signal,
        )

        signal = read_memory_signal(_events_file(isolated_home))
        assert signal["scored"] == 3 and signal["unscored"] == 0
        assert signal["wrong_rate"] == 0.5  # wrong / (acted_on + wrong)
        assert signal["ignored_rate"] == pytest.approx(1 / 3)
        assert signal["candidate_noise_rate"] == pytest.approx(2 / 3)
        assert signal["headline"] == "wrong_rate"

        # Scored verdicts in scope DO flip the caption (MI-5).
        est = estimate_intervention_signal(_events_file(isolated_home))
        assert est["caption"].endswith(INTERVENTION_DENOMINATOR_NOTE)
        assert est["noise_denominator"]["wrong_rate"] == 0.5

    def test_injection_and_bogus_labels_coerce_to_unscored(
        self, isolated_home, verdicts_mod, telemetry_mod, fake_ollama
    ):
        """MI-7: non-schema labels and unknown items never survive."""
        _write_surfacing(telemetry_mod, items=("L1", "L2"))
        fake_ollama.verdicts = [
            {"surfacing_id": "abc123def456", "item_id": "L1", "label": "definitely_helpful"},
            {"surfacing_id": "attacker", "item_id": "evil", "label": "acted_on"},
        ]
        assert verdicts_mod.score_session("s1", "tail with injection attempt") == 2
        records = [e for e in _read_events(isolated_home) if e["event"] == "memory_signal"]
        assert {r["verdict"] for r in records} == {"unscored"}
        assert {r["item_id"] for r in records} == {"L1", "L2"}  # no 'evil' record

    def test_idempotent_rerun_writes_nothing_new(
        self, isolated_home, verdicts_mod, telemetry_mod, fake_ollama
    ):
        _write_surfacing(telemetry_mod, items=("L1",))
        fake_ollama.verdicts = [
            {"surfacing_id": "abc123def456", "item_id": "L1", "label": "acted_on"}
        ]
        assert verdicts_mod.score_session("s1", "tail") == 1
        assert verdicts_mod.score_session("s1", "tail") == 0  # MI-1 idempotency
        records = [e for e in _read_events(isolated_home) if e["event"] == "memory_signal"]
        assert len(records) == 1


class TestGuards:
    def test_non_loopback_endpoint_never_contacted(
        self, isolated_home, verdicts_mod, telemetry_mod, monkeypatch
    ):
        """MI-3: a non-loopback endpoint is rejected, not contacted."""
        monkeypatch.setenv("ATTUNE_MEMORY_OLLAMA_URL", "http://ollama.example.com:11434")

        def _boom(*a, **k):
            raise AssertionError("remote endpoint must not be contacted")

        monkeypatch.setattr(verdicts_mod.urllib.request, "urlopen", _boom)
        _write_surfacing(telemetry_mod, items=("L1",))
        assert verdicts_mod.score_session("s1", "tail") == 1
        records = [e for e in _read_events(isolated_home) if e["event"] == "memory_signal"]
        assert records[0]["verdict"] == "unscored"

    def test_corrupt_events_lines_are_skipped(self, isolated_home, verdicts_mod, telemetry_mod):
        _write_surfacing(telemetry_mod, items=("L1",))
        with _events_file(isolated_home).open("a", encoding="utf-8") as fh:
            fh.write("{not json}\n\x00garbage\n")
        items, scored = verdicts_mod.snapshot_surfacings("s1")
        assert [i["item_id"] for i in items] == ["L1"] and scored == set()

    def test_scorer_crash_is_isolated(self, isolated_home, verdicts_mod, monkeypatch):
        """MI-4: an unexpected error yields 0, never an exception."""
        monkeypatch.setattr(
            verdicts_mod, "snapshot_surfacings", lambda s: (_ for _ in ()).throw(RuntimeError())
        )
        assert verdicts_mod.score_session("s1", "tail") == 0

    def test_rotated_siblings_join_the_snapshot(self, isolated_home, verdicts_mod, telemetry_mod):
        """MI-1: rotation cannot split surfacing→verdict correlation."""
        rotated = _events_file(isolated_home).with_name("memory_events.2026-07-01.jsonl")
        rotated.parent.mkdir(parents=True, exist_ok=True)
        rotated.write_text(
            json.dumps(
                {
                    "v": "1.0",
                    "event": "jit_recall",
                    "session_id": "s1",
                    "surfacing_id": "rot111rot222",
                    "rules": ["R9"],
                }
            )
            + "\n"
        )
        items, _ = verdicts_mod.snapshot_surfacings("s1")
        assert {i["item_id"] for i in items} == {"R9"}


class TestReader:
    def test_dedup_keeps_latest_and_drops_unknown_labels(self, tmp_path):
        from attune.ops.data import read_memory_signal

        live = tmp_path / "memory_events.jsonl"
        rotated = tmp_path / "memory_events.2026-07-01.jsonl"
        rotated.write_text(
            json.dumps(
                {
                    "event": "memory_signal",
                    "session_id": "s1",
                    "surfacing_id": "a",
                    "item_id": "L1",
                    "verdict": "ignored",
                }
            )
            + "\n"
        )
        lines = [
            # supersedes the rotated 'ignored' for the same identity
            {
                "event": "memory_signal",
                "session_id": "s1",
                "surfacing_id": "a",
                "item_id": "L1",
                "verdict": "acted_on",
            },
            {
                "event": "memory_signal",
                "session_id": "s1",
                "surfacing_id": "a",
                "item_id": "L2",
                "verdict": "wrong",
            },
            {
                "event": "memory_signal",
                "session_id": "s2",
                "surfacing_id": "b",
                "item_id": "R1",
                "verdict": "not_a_label",
            },
            {
                "event": "memory_signal",
                "session_id": "s2",
                "surfacing_id": "b",
                "item_id": "R2",
                "verdict": "unscored",
            },
            {"event": "jit_recall", "session_id": "s2", "surfacing_id": "c", "rules": ["R3"]},
        ]
        live.write_text("\n".join(json.dumps(rec) for rec in lines) + "\n")

        signal = read_memory_signal(live)
        assert signal["counts"] == {"acted_on": 1, "ignored": 0, "wrong": 1, "unscored": 1}
        assert signal["scored"] == 2
        assert signal["wrong_rate"] == 0.5
        assert signal["ignored_rate"] == 0.0
        assert signal["candidate_noise_rate"] == 0.5

    def test_missing_file_yields_zeroes(self, tmp_path):
        from attune.ops.data import read_memory_signal

        signal = read_memory_signal(tmp_path / "memory_events.jsonl")
        assert signal["scored"] == 0 and signal["unscored"] == 0
        assert signal["wrong_rate"] is None
