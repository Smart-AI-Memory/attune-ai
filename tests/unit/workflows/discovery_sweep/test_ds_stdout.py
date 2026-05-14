"""Unit tests for the discovery-sweep ATTUNE_DS stdout side-channel.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 1b — ATTUNE_DS stdout emission)

Covers two surfaces:

1. The pure formatter / parser in :mod:`ds_stdout`. Round-trips
   verify the emitted lines parse back to event dicts so the daemon's
   future parser (Phase 2) has a stable contract today.

2. The engine wiring in :mod:`workflow`. When ``ATTUNE_DS_EMIT=1``,
   the engine writes a version line, a started/finished/failed line
   per source, and a final line carrying the SweepResult JSON.
   Without the env var, stdout is unchanged (preserves the
   pipe-to-file UX).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import pytest

from attune.workflows.discovery_sweep import (
    DiscoverySweepWorkflow,
    Finding,
    ds_stdout,
)


@dataclass
class FakeSource:
    """Test double — same shape as the engine tests."""

    name: str
    is_llm: bool = True
    budget_multiplier: float | None = None
    findings: list[Finding] | None = None
    raises: BaseException | None = None

    def __post_init__(self) -> None:
        if self.budget_multiplier is None:
            self.budget_multiplier = 1.0 if self.is_llm else 0.0

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        if self.raises is not None:
            raise self.raises
        return list(self.findings or [])


def _finding() -> Finding:
    return Finding(
        source="fake",
        severity="high",
        title="t",
        description="d",
        file="src/a.py",
        line=10,
        evidence=None,
        confidence=0.9,
        tags=(),
    )


# ---------------------------------------------------------------------------
# Formatter / parser round-trips
# ---------------------------------------------------------------------------


class TestFormatterParserRoundTrip:
    def test_version_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        ds_stdout.emit_version_line()
        out = capsys.readouterr().out.strip()
        assert out == f"ATTUNE_DS_VERSION {ds_stdout.VERSION}"
        parsed = ds_stdout.parse_line(out)
        assert parsed == {"event": "version", "version": ds_stdout.VERSION}

    def test_source_started_round_trip(self, capsys: pytest.CaptureFixture[str]) -> None:
        ds_stdout.emit_event_line(
            {
                "event": "source_started",
                "source": "bug-predict",
                "ts": "2026-05-13T12:00:00+00:00",
                "sweep_id": "r-1",
            }
        )
        line = capsys.readouterr().out.strip()
        parsed = ds_stdout.parse_line(line)
        assert parsed == {
            "event": "source_started",
            "source": "bug-predict",
            "ts": "2026-05-13T12:00:00+00:00",
        }

    def test_source_finished_round_trip(self, capsys: pytest.CaptureFixture[str]) -> None:
        ds_stdout.emit_event_line(
            {
                "event": "source_finished",
                "source": "pattern-scan",
                "ts": "2026-05-13T12:00:05+00:00",
                "sweep_id": None,
                "findings_count": 7,
            }
        )
        line = capsys.readouterr().out.strip()
        parsed = ds_stdout.parse_line(line)
        assert parsed == {
            "event": "source_finished",
            "source": "pattern-scan",
            "ts": "2026-05-13T12:00:05+00:00",
            "findings_count": 7,
        }

    def test_source_failed_round_trip(self, capsys: pytest.CaptureFixture[str]) -> None:
        ds_stdout.emit_event_line(
            {
                "event": "source_failed",
                "source": "security-audit",
                "ts": "2026-05-13T12:00:10+00:00",
                "sweep_id": None,
                "error": "BudgetExceededError",
            }
        )
        line = capsys.readouterr().out.strip()
        parsed = ds_stdout.parse_line(line)
        assert parsed == {
            "event": "source_failed",
            "source": "security-audit",
            "ts": "2026-05-13T12:00:10+00:00",
            "error": "BudgetExceededError",
        }

    def test_final_line_round_trip(self, capsys: pytest.CaptureFixture[str]) -> None:
        payload = {"queue": [], "questions": [], "rejected": [], "metadata": {}}
        ds_stdout.emit_final_line(json.dumps(payload))
        line = capsys.readouterr().out.strip()
        parsed = ds_stdout.parse_line(line)
        assert parsed is not None
        assert parsed["event"] == "final"
        assert json.loads(parsed["json"]) == payload

    def test_final_line_strips_embedded_newlines(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Pretty-printed JSON would break the one-line-per-record
        # grammar; emit_final_line must defend against that.
        pretty = '{\n  "queue": [],\n  "metadata": {}\n}'
        ds_stdout.emit_final_line(pretty)
        out = capsys.readouterr().out
        # Exactly one trailing newline written by emit_final_line.
        assert out.count("\n") == 1
        line = out.strip()
        parsed = ds_stdout.parse_line(line)
        assert parsed is not None
        assert parsed["event"] == "final"
        # JSON still parses after newline stripping.
        assert json.loads(parsed["json"]) == {"queue": [], "metadata": {}}


class TestParseLineNoMatch:
    def test_non_attune_ds_line_returns_none(self) -> None:
        assert ds_stdout.parse_line("hello world") is None
        assert ds_stdout.parse_line("") is None
        assert ds_stdout.parse_line("## Queue (0 findings)") is None

    def test_malformed_event_returns_none(self) -> None:
        # Right prefix, wrong shape.
        assert ds_stdout.parse_line("ATTUNE_DS source_started no-ts-here") is None
        assert ds_stdout.parse_line("ATTUNE_DS unknown_kind foo") is None

    def test_unknown_event_kind_is_dropped_by_emitter(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # An unknown kind produces no line at all; the parser would
        # refuse it on the daemon side anyway.
        ds_stdout.emit_event_line({"event": "weird_kind", "source": "s"})
        assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Emission gate
# ---------------------------------------------------------------------------


class TestEmissionGate:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ds_stdout.EMIT_ENV, raising=False)
        assert ds_stdout.is_emission_enabled() is False

    def test_empty_value_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ds_stdout.EMIT_ENV, "")
        assert ds_stdout.is_emission_enabled() is False

    def test_any_truthy_value_enables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for value in ("1", "true", "yes", "anything"):
            monkeypatch.setenv(ds_stdout.EMIT_ENV, value)
            assert ds_stdout.is_emission_enabled() is True


# ---------------------------------------------------------------------------
# Engine wiring
# ---------------------------------------------------------------------------


class TestEngineEmissionDisabled:
    def test_no_atune_ds_lines_when_env_unset(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv(ds_stdout.EMIT_ENV, raising=False)
        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", sources=[src]))
        out = capsys.readouterr().out
        # Strict assertion: zero ATTUNE_DS lines anywhere.
        assert "ATTUNE_DS" not in out


class TestEngineEmissionEnabled:
    @pytest.fixture(autouse=True)
    def _enable_emission(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ds_stdout.EMIT_ENV, "1")

    def test_version_line_is_first(self, capsys: pytest.CaptureFixture[str]) -> None:
        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", sources=[src]))
        out_lines = [ln for ln in capsys.readouterr().out.splitlines() if "ATTUNE_DS" in ln]
        assert out_lines, "expected at least one ATTUNE_DS line"
        assert out_lines[0] == f"ATTUNE_DS_VERSION {ds_stdout.VERSION}"

    def test_per_source_events_emitted(self, capsys: pytest.CaptureFixture[str]) -> None:
        src = FakeSource(name="alpha", findings=[_finding(), _finding()])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", sources=[src]))
        events = [
            ds_stdout.parse_line(ln)
            for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("ATTUNE_DS")
        ]
        kinds = [e["event"] for e in events if e is not None]
        # Expected order: version, source_started, source_finished, final.
        assert kinds == [
            "version",
            "source_started",
            "source_finished",
            "final",
        ]
        # finished line carries the right count.
        finished = next(e for e in events if e and e["event"] == "source_finished")
        assert finished["source"] == "alpha"
        assert finished["findings_count"] == 2

    def test_failed_source_emits_source_failed(self, capsys: pytest.CaptureFixture[str]) -> None:
        src = FakeSource(name="bad", raises=RuntimeError("boom"))
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", sources=[src]))
        events = [
            ds_stdout.parse_line(ln)
            for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("ATTUNE_DS")
        ]
        kinds = [e["event"] for e in events if e is not None]
        assert kinds == ["version", "source_started", "source_failed", "final"]
        failed = next(e for e in events if e and e["event"] == "source_failed")
        assert failed["source"] == "bad"
        assert failed["error"] == "RuntimeError"

    def test_final_line_carries_sweep_result_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", sources=[src]))
        events = [
            ds_stdout.parse_line(ln)
            for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("ATTUNE_DS")
        ]
        final = next(e for e in events if e and e["event"] == "final")
        payload = json.loads(final["json"])
        assert set(payload.keys()) >= {"queue", "questions", "rejected", "metadata"}
        assert len(payload["queue"]) == 1
        assert payload["queue"][0]["source"] == "fake"

    def test_user_event_sink_still_fires(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Both surfaces co-exist: an in-process user sink and the
        # stdout side-channel fire independently. A user passing an
        # event_sink sees their events; the daemon parses stdout.
        seen: list[dict] = []

        async def sink(event: dict) -> None:
            seen.append(event)

        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()

        async def runner() -> None:
            await wf.execute(path="src/", sources=[src], event_sink=sink)
            # Let fire-and-forget emit tasks drain.
            for _ in range(5):
                await asyncio.sleep(0)

        asyncio.run(runner())

        # User sink saw started + finished.
        kinds = [e["event"] for e in seen]
        assert kinds == ["source_started", "source_finished"]

        # Stdout side-channel also saw the events.
        out_kinds = [
            ds_stdout.parse_line(ln)["event"]
            for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("ATTUNE_DS") and ds_stdout.parse_line(ln) is not None
        ]
        assert "source_started" in out_kinds
        assert "source_finished" in out_kinds
        assert "final" in out_kinds
