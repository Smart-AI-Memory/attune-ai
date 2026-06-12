"""Tests for the run-view structured report panel.

Workflow-result-formatting T6: the CLI emits the serialized
``WorkflowReport`` over the ``ATTUNE_RUN_META report_b64`` stdout
side-channel; the runner stashes it on ``Run.report`` (persisted with
the record and flagged via ``has_report`` in the SSE done payload);
``GET /runs/{run_id}/report`` serves the dict plus server-rendered
summary markdown; ``run_view.js`` converts that markdown subset to
HTML in a panel above the (collapsing) process log.

Spec: docs/specs/workflow-result-formatting/ T6.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")
pytest.importorskip("yaml")

from fastapi.testclient import TestClient  # noqa: E402

from attune.cli_commands.workflow_commands import _emit_run_meta_for_daemon  # noqa: E402
from attune.ops import run_meta_stdout  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import Run, RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402
from attune.workflows.output import (  # noqa: E402
    FindingsSection,
    NextAction,
    NextStepsSection,
    WorkflowReport,
)

_SRC = Path(__file__).resolve().parents[3] / "src" / "attune" / "ops"
_TEMPLATE = _SRC / "templates" / "run_view.html"
_JS = _SRC / "static" / "js" / "run_view.js"
_CSS = _SRC / "static" / "css" / "main.css"


def _report_dict() -> dict[str, Any]:
    report = WorkflowReport(
        title="Security audit",
        summary="2 findings across 14 files.",
        score=87,
        sections=[
            FindingsSection(title="Findings", tier="essential", findings=[]),
            NextStepsSection(
                title="Next steps",
                tier="essential",
                items=[
                    NextAction(
                        text="Re-run the audit on src/",
                        command="attune workflow run security-audit",
                    ),
                    NextAction(
                        text="Fix the flagged file",
                        file="src/attune/config.py:42",
                    ),
                ],
            ),
        ],
    )
    return report.to_dict()


# ---------------------------------------------------------------------------
# run_meta_stdout — report_b64 wire format
# ---------------------------------------------------------------------------


class TestReportWireFormat:
    def test_encode_decode_round_trip(self):
        encoded = run_meta_stdout.encode_report(_report_dict())
        assert encoded
        assert run_meta_stdout.decode_report(encoded) == _report_dict()

    def test_decode_malformed_b64_returns_none(self):
        assert run_meta_stdout.decode_report("!!notb64!!") is None

    def test_decode_non_dict_json_returns_none(self):
        import base64

        encoded = base64.b64encode(b'["not", "a", "dict"]').decode("ascii")
        assert run_meta_stdout.decode_report(encoded) is None

    def test_encode_unserializable_returns_empty(self):
        assert run_meta_stdout.encode_report({"bad": object()}) == ""

    def test_parse_line_accepts_report_b64_key(self):
        encoded = run_meta_stdout.encode_report(_report_dict())
        parsed = run_meta_stdout.parse_line(f"ATTUNE_RUN_META report_b64={encoded}")
        assert parsed == {"event": "field", "key": "report_b64", "value": encoded}


# ---------------------------------------------------------------------------
# CLI emitter — final_output report dict → report_b64 line
# ---------------------------------------------------------------------------


@dataclass
class _FakeResult:
    metadata: dict[str, Any] = field(default_factory=dict)
    final_output: Any = None


def _capture(callback) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        callback()
    return buf.getvalue()


class TestCliEmitter:
    def test_report_final_output_emits_report_b64(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(final_output=_report_dict())
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        lines = out.strip().split("\n")
        assert lines[0].startswith("ATTUNE_RUN_META_VERSION ")
        b64_lines = [ln for ln in lines if ln.startswith("ATTUNE_RUN_META report_b64=")]
        assert len(b64_lines) == 1
        encoded = b64_lines[0].split("=", 1)[1]
        assert run_meta_stdout.decode_report(encoded) == _report_dict()

    def test_non_report_final_output_emits_nothing(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(final_output={"formatted_report": "legacy text"})
        assert _capture(lambda: _emit_run_meta_for_daemon(result)) == ""

    def test_env_unset_emits_nothing_even_with_report(self, monkeypatch):
        monkeypatch.delenv("ATTUNE_RUN_META_EMIT", raising=False)
        result = _FakeResult(final_output=_report_dict())
        assert _capture(lambda: _emit_run_meta_for_daemon(result)) == ""

    def test_report_and_sdk_error_both_emit(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_META_EMIT", "1")
        result = _FakeResult(
            metadata={"sdk_error_kind": "auth"},
            final_output=_report_dict(),
        )
        out = _capture(lambda: _emit_run_meta_for_daemon(result))
        assert "ATTUNE_RUN_META sdk_error_kind=auth" in out
        assert "ATTUNE_RUN_META report_b64=" in out


# ---------------------------------------------------------------------------
# Runner — stash, done payload, persistence round-trip
# ---------------------------------------------------------------------------


def _make_runner() -> RunnerService:
    return RunnerService(command_builder=lambda _name: ("true",))


class TestRunnerStash:
    def test_report_b64_marker_stashes_on_run(self):
        runner = _make_runner()
        run = Run(id="testrunid01", workflow="security-audit")
        encoded = run_meta_stdout.encode_report(_report_dict())
        runner.handle_stdout_line(run, f"ATTUNE_RUN_META report_b64={encoded}")
        assert run.report == _report_dict()
        assert "ATTUNE_RUN_META" not in "\n".join(run.lines)

    def test_malformed_report_b64_does_not_clobber(self):
        runner = _make_runner()
        run = Run(id="testrunid01", workflow="security-audit")
        encoded = run_meta_stdout.encode_report(_report_dict())
        runner.handle_stdout_line(run, f"ATTUNE_RUN_META report_b64={encoded}")
        runner.handle_stdout_line(run, "ATTUNE_RUN_META report_b64=!!notb64!!")
        assert run.report == _report_dict()

    def test_done_payload_flags_has_report(self):
        run = Run(id="testrunid01", workflow="security-audit")
        run.report = _report_dict()
        captured: list[tuple[str, object]] = []
        run._broadcast = captured.append  # type: ignore[method-assign]
        run.mark_done(0)
        ((kind, payload),) = captured
        assert kind == "done"
        assert payload["has_report"] is True  # type: ignore[index]

    def test_done_payload_has_report_false_without_report(self):
        run = Run(id="testrunid01", workflow="security-audit")
        captured: list[tuple[str, object]] = []
        run._broadcast = captured.append  # type: ignore[method-assign]
        run.mark_done(0)
        ((_, payload),) = captured
        assert payload["has_report"] is False  # type: ignore[index]

    def test_record_round_trip_preserves_report(self):
        run = Run(id="abc12345", workflow="security-audit", status="completed")
        run.report = _report_dict()
        restored = Run.from_record(run.to_record())
        assert restored.report == _report_dict()

    def test_old_record_without_report_reads_back_none(self):
        restored = Run.from_record(
            {"id": "abc12345", "workflow": "security-audit", "status": "completed"}
        )
        assert restored.report is None


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/report
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=True,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=lambda _name: ("true",))
    app = create_app(config, runner=runner)
    return app, runner


class TestReportRoute:
    def test_unknown_run_404(self, tmp_path, monkeypatch):
        app, _ = _make_app(tmp_path, monkeypatch)
        with TestClient(app) as client:
            resp = client.get("/runs/deadbeef0001/report")
        assert resp.status_code == 404

    def test_run_without_report_404(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch)
        run = Run(id="deadbeef0001", workflow="security-audit", status="completed")
        runner._runs[run.id] = run
        with TestClient(app) as client:
            resp = client.get("/runs/deadbeef0001/report")
        assert resp.status_code == 404

    def test_run_with_report_returns_dict_and_markdown(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch)
        run = Run(id="deadbeef0001", workflow="security-audit", status="completed")
        run.report = _report_dict()
        runner._runs[run.id] = run
        with TestClient(app) as client:
            resp = client.get("/runs/deadbeef0001/report")
        assert resp.status_code == 200
        body = resp.json()
        assert body["report"] == _report_dict()
        # Rendered by the canonical renderer — title heading + summary
        # text + the next-steps command fence must all survive.
        assert "# Security audit" in body["markdown"]
        assert "2 findings across 14 files." in body["markdown"]
        assert "attune workflow run security-audit" in body["markdown"]


# ---------------------------------------------------------------------------
# Template / JS surface (source-grep level, like the copy-report tests)
# ---------------------------------------------------------------------------


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestTemplateAndJs:
    def test_template_has_report_panel_slot(self):
        text = _read(_TEMPLATE)
        assert "data-report-panel" in text

    def test_template_wraps_log_in_collapsible(self):
        text = _read(_TEMPLATE)
        assert "data-log-details" in text
        assert "Process log" in text
        # The wrapper must still contain the canonical [data-log] pre so
        # the copy-report button and SSE append path keep working.
        details_idx = text.find("data-log-details")
        log_idx = text.find("data-log>", details_idx)
        assert details_idx >= 0 and log_idx > details_idx

    def test_template_injects_run_id(self):
        assert '"run_id"' in _read(_TEMPLATE)

    def test_js_exports_report_panel_helpers(self):
        text = _read(_JS)
        for name in (
            "function mdToHtml(",
            "function renderReportPanel(",
            "function fetchAndRenderReport(",
            "function runnableNextActions(",
            "mdToHtml: mdToHtml",
            "renderReportPanel: renderReportPanel",
            "fetchAndRenderReport: fetchAndRenderReport",
        ):
            assert name in text, f"missing {name!r} in run_view.js"

    def test_js_fetches_report_on_done_and_disk_loaded(self):
        text = _read(_JS)
        assert "info.has_report" in text
        assert text.count("fetchAndRenderReport()") >= 2

    def test_js_escapes_before_inline_markup(self):
        """The converter must escape HTML before applying inline
        transforms — the escape call inside mdInline is the guard
        against report text injecting markup."""
        text = _read(_JS)
        inline_idx = text.find("function mdInline(")
        assert inline_idx >= 0
        body = text[inline_idx : text.find("}", inline_idx)]
        assert "escapeHtml(" in body

    def test_css_styles_report_panel(self):
        text = _read(_CSS)
        assert ".run-report-panel" in text
        assert ".run-log-details" in text
