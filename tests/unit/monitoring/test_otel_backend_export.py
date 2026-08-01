"""Export/detection-branch tests for OTELBackend.

Complements test_otel_backend.py (availability negatives) by covering
the span-emitting paths (log_call, log_workflow), _init_otel success +
failure, flush, the __init__ -> _init_otel hop, and the endpoint
detection / availability parsing branches. opentelemetry is mocked, so
no collector or real tracer provider is touched.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import gc
import importlib.util
import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.monitoring.otel_backend import OTELBackend

MOD = "attune.monitoring.otel_backend"


def _bare() -> OTELBackend:
    """An OTELBackend instance with __init__ bypassed."""
    return OTELBackend.__new__(OTELBackend)


def _ready() -> OTELBackend:
    """A backend that reports available with a mock tracer."""
    b = _bare()
    b.endpoint = "http://localhost:4317"
    b._available = True
    b._otel_available = True
    b.tracer = MagicMock()
    return b


def _call_record() -> MagicMock:
    r = MagicMock()
    r.provider = "anthropic"
    r.model_id = "claude-sonnet-5"
    r.tier = "CAPABLE"
    r.task_type = "generation"
    r.input_tokens = 100
    r.output_tokens = 50
    r.estimated_cost = 0.10
    r.actual_cost = 0.12
    r.latency_ms = 250
    r.workflow_name = "review"
    r.step_name = "scan"
    r.session_id = "sess-1"
    r.fallback_used = True
    r.original_provider = "openai"
    r.original_model = "gpt-4"
    r.success = False
    r.error_type = "Timeout"
    r.error_message = "took too long"
    return r


def _stage() -> MagicMock:
    s = MagicMock()
    s.stage_name = "plan"
    s.tier = "CHEAP"
    s.model_id = "haiku"
    s.input_tokens = 10
    s.output_tokens = 5
    s.cost = 0.01
    s.latency_ms = 40
    s.success = True
    s.skipped = True
    s.skip_reason = "cached"
    s.error = "minor warning"
    return s


def _workflow_record() -> MagicMock:
    r = MagicMock()
    r.workflow_name = "review"
    r.run_id = "run-1"
    r.session_id = "sess-1"
    r.total_input_tokens = 200
    r.total_output_tokens = 80
    r.total_cost = 1.0
    r.baseline_cost = 2.0
    r.savings = 1.0
    r.savings_percent = 50.0
    r.total_duration_ms = 500
    r.providers_used = ["anthropic"]
    r.tiers_used = ["CHEAP", "CAPABLE"]
    r.success = False
    r.error = "stage failed"
    r.stages = [_stage()]
    return r


class TestLogCall:
    def test_unavailable_is_noop(self):
        b = _ready()
        b._available = False
        b.log_call(_call_record())
        b.tracer.start_as_current_span.assert_not_called()

    def test_sets_llm_span_attributes(self):
        b = _ready()
        b.log_call(_call_record())

        span = b.tracer.start_as_current_span.return_value.__enter__.return_value
        span.set_attribute.assert_any_call("llm.provider", "anthropic")
        span.set_attribute.assert_any_call("llm.cost.actual", 0.12)
        span.set_attribute.assert_any_call("llm.fallback.used", True)
        span.set_attribute.assert_any_call("llm.error", True)
        span.set_attribute.assert_any_call("llm.error.type", "Timeout")

    def test_export_error_swallowed(self, capsys):
        b = _ready()
        b.tracer.start_as_current_span.side_effect = RuntimeError("export down")
        b.log_call(_call_record())
        assert "Failed to export LLM call" in capsys.readouterr().out


class TestLogWorkflow:
    def test_unavailable_is_noop(self):
        b = _ready()
        b._otel_available = False
        b.log_workflow(_workflow_record())
        b.tracer.start_as_current_span.assert_not_called()

    def test_sets_workflow_and_stage_attributes(self):
        b = _ready()
        b.log_workflow(_workflow_record())

        span = b.tracer.start_as_current_span.return_value.__enter__.return_value
        span.set_attribute.assert_any_call("workflow.run_id", "run-1")
        span.set_attribute.assert_any_call("workflow.success", False)
        span.set_attribute.assert_any_call("workflow.error", "stage failed")
        # Stage child-span attributes (skip reason + error branches).
        span.set_attribute.assert_any_call("stage.skipped", True)
        span.set_attribute.assert_any_call("stage.skip_reason", "cached")
        span.set_attribute.assert_any_call("stage.error", "minor warning")

    def test_export_error_swallowed(self, capsys):
        b = _ready()
        b.tracer.start_as_current_span.side_effect = RuntimeError("trace down")
        b.log_workflow(_workflow_record())
        assert "Failed to export workflow" in capsys.readouterr().out


def _otel_modules(trace_mock: MagicMock) -> dict:
    return {
        "opentelemetry": MagicMock(trace=trace_mock),
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(),
        "opentelemetry.sdk.resources": MagicMock(),
        "opentelemetry.sdk.trace": MagicMock(),
        "opentelemetry.sdk.trace.export": MagicMock(),
    }


class TestInitOtel:
    def test_success_sets_tracer(self):
        b = _bare()
        b.endpoint = "http://localhost:4317"
        b._available = True
        trace_mock = MagicMock()
        with patch.dict(sys.modules, _otel_modules(trace_mock)):
            b._init_otel()
        assert b.tracer is trace_mock.get_tracer.return_value
        assert b._available is True

    def test_failure_disables_available(self, capsys):
        b = _bare()
        b.endpoint = "http://localhost:4317"
        b._available = True
        trace_mock = MagicMock()
        trace_mock.set_tracer_provider.side_effect = RuntimeError("no provider")
        with patch.dict(sys.modules, _otel_modules(trace_mock)):
            b._init_otel()
        assert b._available is False
        assert "Failed to initialize OTEL" in capsys.readouterr().out


class TestInitHop:
    def test_init_calls_init_otel_when_available(self):
        with (
            patch.object(OTELBackend, "_detect_endpoint", return_value="http://x:4317"),
            patch.object(OTELBackend, "_check_availability", return_value=True),
            patch.object(OTELBackend, "_check_otel_installed", return_value=True),
            patch.object(OTELBackend, "_init_otel") as mock_init,
        ):
            OTELBackend(endpoint="http://x:4317")
        mock_init.assert_called_once()


class TestFlush:
    @pytest.fixture(autouse=True)
    def _freeze_finalizers(self):
        """Stop stray ``OTELBackend.__del__`` -> ``flush()`` polluting counts.

        These tests patch the process-global ``sys.modules['opentelemetry']``.
        Other tests leave "available" backends alive in reference cycles; if the
        cyclic collector fires *inside* the patched window it finalizes one, and
        its ``__del__`` -> ``flush()`` reaches the SAME mock tracer provider,
        making ``force_flush`` look "called 2 times" (the xdist-ordering-only
        flake). Drain pending finalizers, then freeze the cyclic collector for
        the test body so exactly one flush (ours) runs against the mock.
        """
        gc.collect()
        gc.disable()
        try:
            yield
        finally:
            gc.enable()

    def test_unavailable_is_noop(self):
        b = _ready()
        b._available = False
        b.flush()  # no import attempted, no crash

    def test_force_flush_invoked(self):
        b = _ready()
        provider = MagicMock()
        trace_mock = MagicMock()
        trace_mock.get_tracer_provider.return_value = provider
        with patch.dict(sys.modules, {"opentelemetry": MagicMock(trace=trace_mock)}):
            b.flush()
        provider.force_flush.assert_called_once()

    def test_flush_error_swallowed(self, capsys):
        b = _ready()
        trace_mock = MagicMock()
        trace_mock.get_tracer_provider.side_effect = RuntimeError("flush boom")
        with patch.dict(sys.modules, {"opentelemetry": MagicMock(trace=trace_mock)}):
            b.flush()
        assert "Failed to flush OTEL data" in capsys.readouterr().out


class TestDetectEndpoint:
    def test_env_var_wins(self):
        b = _bare()
        with (
            patch(f"{MOD}.OTELBackend._is_port_open", return_value=False),
            patch("attune.config.env_compat.get_attune_env", return_value="http://env:4317"),
        ):
            assert b._detect_endpoint() == "http://env:4317"

    def test_localhost_when_port_open(self):
        b = _bare()
        with (
            patch("attune.config.env_compat.get_attune_env", return_value=None),
            patch.object(OTELBackend, "_is_port_open", return_value=True),
        ):
            assert b._detect_endpoint() == "http://localhost:4317"

    def test_default_when_nothing(self):
        b = _bare()
        with (
            patch("attune.config.env_compat.get_attune_env", return_value=None),
            patch.object(OTELBackend, "_is_port_open", return_value=False),
        ):
            assert b._detect_endpoint() == "http://localhost:4317"


class TestIsPortOpen:
    def test_open(self, monkeypatch):
        monkeypatch.setattr(f"{MOD}.socket.socket", lambda *a, **k: MagicMock())
        assert _bare()._is_port_open("host", 4317) is True

    def test_closed(self, monkeypatch):
        sock = MagicMock()
        sock.connect.side_effect = OSError("refused")
        monkeypatch.setattr(f"{MOD}.socket.socket", lambda *a, **k: sock)
        assert _bare()._is_port_open("host", 4317) is False


class TestCheckOtelInstalled:
    # NOTE: find_spec is mocked here. In a real otel-absent env, find_spec
    # actually *raises* ModuleNotFoundError (missing parent package) rather
    # than returning None, which crashes OTELBackend.__init__ — logged as a
    # bug in docs/COVERAGE_BUG_LOG.md. These tests cover the intended logic.
    #
    # The mock is SELECTIVE (otel names only, real find_spec otherwise):
    # a blanket patch hands a MagicMock to ANY find_spec call in the
    # process during the with-window — under xdist, a GC-triggered
    # unraisable landing in that window makes pytest's unraisable handler
    # itself crash ("RuntimeError: Failed to process unraisable
    # exception"), sniping unrelated CI lanes.
    def test_all_present_returns_true(self):
        real_find_spec = importlib.util.find_spec

        def fake(name, *args, **kwargs):
            if name.startswith("opentelemetry"):
                return MagicMock()
            return real_find_spec(name, *args, **kwargs)

        with patch("importlib.util.find_spec", side_effect=fake):
            assert _bare()._check_otel_installed() is True

    def test_any_missing_returns_false(self):
        real_find_spec = importlib.util.find_spec

        def fake(name, *args, **kwargs):
            if name.startswith("opentelemetry"):
                return None
            return real_find_spec(name, *args, **kwargs)

        with patch("importlib.util.find_spec", side_effect=fake):
            assert _bare()._check_otel_installed() is False


class TestCheckAvailability:
    def test_no_endpoint(self):
        b = _bare()
        b.endpoint = ""
        assert b._check_availability() is False

    def test_endpoint_with_port(self):
        b = _bare()
        b.endpoint = "http://collector:9999"
        with patch.object(OTELBackend, "_is_port_open", return_value=True) as mock_open:
            assert b._check_availability() is True
        mock_open.assert_called_once_with("collector", 9999)

    def test_endpoint_without_port_uses_default(self):
        b = _bare()
        b.endpoint = "http://collector"
        with patch.object(OTELBackend, "_is_port_open", return_value=True) as mock_open:
            assert b._check_availability() is True
        mock_open.assert_called_once_with("collector", 4317)

    def test_malformed_port_returns_false(self):
        b = _bare()
        b.endpoint = "http://collector:not-a-port"
        assert b._check_availability() is False
