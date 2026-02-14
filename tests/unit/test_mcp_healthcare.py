"""Tests for attune.mcp.healthcare module.

Tests the self-contained methods of HealthcareMCPServer and top-level functions.
External healthcare dependencies are mocked.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _normalize_sensor_data tests
# ---------------------------------------------------------------------------
class TestNormalizeSensorData:
    """Tests for HealthcareMCPServer._normalize_sensor_data."""

    @pytest.fixture(autouse=True)
    def _import_class(self):
        """Import the static method under test."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            self.normalize = HealthcareMCPServer._normalize_sensor_data

    def test_already_wrapped_vitals(self):
        """Sensor data with 'vitals' key passes through unchanged."""
        data = json.dumps({"vitals": {"hr": 110}})
        assert self.normalize(data) == data

    def test_flat_vital_keys_wrapped(self):
        """Flat vital keys are wrapped in a 'vitals' key."""
        flat = {"hr": 110, "systolic_bp": 85, "respiratory_rate": 24}
        result = json.loads(self.normalize(json.dumps(flat)))
        assert "vitals" in result
        assert result["vitals"]["hr"] == 110
        assert result["vitals"]["systolic_bp"] == 85

    def test_flat_with_meta_separated(self):
        """Non-vital keys become meta, vital keys go under 'vitals'."""
        flat = {"hr": 110, "patient_note": "test"}
        result = json.loads(self.normalize(json.dumps(flat)))
        assert result["vitals"] == {"hr": 110}
        assert result["patient_note"] == "test"

    def test_no_vital_keys_passes_through(self):
        """Data with no recognized vital keys passes through unchanged."""
        data = json.dumps({"foo": "bar", "baz": 42})
        assert self.normalize(data) == data

    def test_invalid_json_passes_through(self):
        """Invalid JSON returns original string."""
        raw = "not-json"
        assert self.normalize(raw) == raw

    def test_all_vital_key_variants(self):
        """Test all recognized vital key names."""
        for key in [
            "heart_rate",
            "diastolic_bp",
            "bp",
            "rr",
            "temp_f",
            "temp_c",
            "temperature",
            "o2_sat",
            "spo2",
            "mental_status",
            "pain",
        ]:
            flat = {key: 99}
            result = json.loads(self.normalize(json.dumps(flat)))
            assert key in result["vitals"]


# ---------------------------------------------------------------------------
# _audit tests
# ---------------------------------------------------------------------------
class TestAudit:
    """Tests for HealthcareMCPServer._audit."""

    def test_audit_appends_entry(self):
        """Audit adds a timestamped entry with tool name and param keys."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                server._audit_log = []

                server._audit("healthcare_analyze", {"patient_id": "p1", "sensor_data": "{}"})

                assert len(server._audit_log) == 1
                entry = server._audit_log[0]
                assert entry["tool"] == "healthcare_analyze"
                assert "patient_id" in entry["param_keys"]
                assert "sensor_data" in entry["param_keys"]
                assert "timestamp" in entry

    def test_audit_logs_multiple_calls(self):
        """Multiple audit calls accumulate entries."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                server._audit_log = []

                server._audit("tool_a", {"x": 1})
                server._audit("tool_b", {"y": 2})

                assert len(server._audit_log) == 2
                assert server._audit_log[0]["tool"] == "tool_a"
                assert server._audit_log[1]["tool"] == "tool_b"


# ---------------------------------------------------------------------------
# _register_healthcare_tools tests
# ---------------------------------------------------------------------------
class TestRegisterHealthcareTools:
    """Tests for HealthcareMCPServer._register_healthcare_tools."""

    def test_registers_9_tools(self):
        """Tool registration returns exactly 9 healthcare tools."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                tools = server._register_healthcare_tools()

                assert len(tools) == 9

    def test_tool_names_prefixed(self):
        """All healthcare tool names start with 'healthcare_'."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                tools = server._register_healthcare_tools()

                for name in tools:
                    assert name.startswith("healthcare_")

    def test_tool_has_input_schema(self):
        """Each tool definition includes an input_schema."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                tools = server._register_healthcare_tools()

                for name, defn in tools.items():
                    assert "input_schema" in defn, f"{name} missing input_schema"
                    assert "description" in defn, f"{name} missing description"


# ---------------------------------------------------------------------------
# _check_redis tests
# ---------------------------------------------------------------------------
class TestCheckRedis:
    """Tests for HealthcareMCPServer._check_redis."""

    def test_redis_available(self):
        """No warning when Redis is reachable."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)

                mock_redis = MagicMock()
                mock_redis.return_value.ping.return_value = True
                with patch.dict("sys.modules", {"redis": mock_redis}):
                    with patch("attune.mcp.healthcare.logger") as mock_logger:
                        server._check_redis()
                        mock_logger.info.assert_called()

    def test_redis_not_installed(self):
        """Warns when redis package not installed."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)

                with patch("builtins.__import__", side_effect=ImportError("no redis")):
                    with patch("attune.mcp.healthcare.logger") as mock_logger:
                        server._check_redis()
                        mock_logger.warning.assert_called()

    def test_redis_connection_fails(self):
        """Warns when Redis is installed but not reachable."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)

                mock_redis_mod = MagicMock()
                mock_redis_mod.Redis.return_value.ping.side_effect = ConnectionError("refused")
                with patch.dict("sys.modules", {"redis": mock_redis_mod}):
                    with patch("attune.mcp.healthcare.logger") as mock_logger:
                        server._check_redis()
                        mock_logger.warning.assert_called()


# ---------------------------------------------------------------------------
# _get_monitor tests
# ---------------------------------------------------------------------------
class TestGetMonitor:
    """Tests for HealthcareMCPServer._get_monitor."""

    def test_lazy_init(self):
        """Monitor is lazily initialized on first call."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                server._monitor = None

                mock_monitor_cls = MagicMock()
                with patch.dict(
                    "sys.modules",
                    {
                        "attune_healthcare": MagicMock(),
                        "attune_healthcare.monitors": MagicMock(
                            ClinicalProtocolMonitor=mock_monitor_cls
                        ),
                    },
                ):
                    result = server._get_monitor()
                    assert result == mock_monitor_cls.return_value

    def test_cached_after_init(self):
        """Monitor is not re-created on subsequent calls."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                server = HealthcareMCPServer.__new__(HealthcareMCPServer)
                mock = MagicMock()
                server._monitor = mock

                result = server._get_monitor()
                assert result is mock


# ---------------------------------------------------------------------------
# call_tool tests
# ---------------------------------------------------------------------------
class TestCallTool:
    """Tests for HealthcareMCPServer.call_tool."""

    @pytest.fixture
    def server(self):
        """Create a server with mocked init."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import HealthcareMCPServer

            with patch.object(HealthcareMCPServer, "__init__", lambda self: None):
                s = HealthcareMCPServer.__new__(HealthcareMCPServer)
                s._audit_log = []
                s._monitor = None
                s.tools = {}
                return s

    @pytest.mark.asyncio
    async def test_call_tool_audits_healthcare_tools(self, server):
        """Healthcare tool calls are audit-logged."""
        server._handle_list_protocols = AsyncMock(return_value={"success": True})
        await server.call_tool("healthcare_list_protocols", {})
        assert len(server._audit_log) == 1

    @pytest.mark.asyncio
    async def test_call_tool_no_audit_for_base_tools(self, server):
        """Base (non-healthcare) tools are not audited."""
        with patch(
            "attune.mcp.healthcare.EmpathyMCPServer.call_tool", new_callable=AsyncMock
        ) as mock_parent:
            mock_parent.return_value = {"ok": True}
            await server.call_tool("base_tool", {})
            assert len(server._audit_log) == 0

    @pytest.mark.asyncio
    async def test_call_tool_import_error(self, server):
        """ImportError returns helpful install message."""
        server._handle_list_protocols = AsyncMock(side_effect=ImportError("no package"))
        result = await server.call_tool("healthcare_list_protocols", {})
        assert result["success"] is False
        assert "not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_call_tool_value_error(self, server):
        """ValueError returns error message."""
        server._handle_analyze = AsyncMock(side_effect=ValueError("bad input"))
        result = await server.call_tool("healthcare_analyze", {"x": 1})
        assert result["success"] is False
        assert "Invalid input" in result["error"]

    @pytest.mark.asyncio
    async def test_call_tool_key_error(self, server):
        """KeyError returns missing field message."""
        server._handle_load_protocol = AsyncMock(side_effect=KeyError("patient_id"))
        result = await server.call_tool("healthcare_load_protocol", {"x": 1})
        assert result["success"] is False
        assert "Missing required field" in result["error"]

    @pytest.mark.asyncio
    async def test_call_tool_dispatches_all_handlers(self, server):
        """Each healthcare tool name dispatches to its handler."""
        tools_handlers = [
            ("healthcare_list_protocols", "_handle_list_protocols"),
            ("healthcare_load_protocol", "_handle_load_protocol"),
            ("healthcare_analyze", "_handle_analyze"),
            ("healthcare_check_compliance", "_handle_check_compliance"),
            ("healthcare_predict_trajectory", "_handle_predict_trajectory"),
            ("healthcare_ecg_analyze", "_handle_ecg_analyze"),
            ("healthcare_cds_assess", "_handle_cds_assess"),
            ("healthcare_fhir_bundle", "_handle_fhir_bundle"),
            ("healthcare_waveform_analyze", "_handle_waveform_analyze"),
        ]
        for tool_name, handler_name in tools_handlers:
            mock_handler = AsyncMock(return_value={"success": True})
            setattr(server, handler_name, mock_handler)
            server._audit_log = []
            await server.call_tool(tool_name, {"arg": "val"})
            mock_handler.assert_called_once()


# ---------------------------------------------------------------------------
# main / healthcare_main_loop tests
# ---------------------------------------------------------------------------
class TestMainEntryPoints:
    """Tests for module-level entry points."""

    def test_main_calls_asyncio_run(self):
        """main() calls asyncio.run with healthcare_main_loop."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import main

            with patch("attune.mcp.healthcare.asyncio.run") as mock_run:
                main()
                mock_run.assert_called_once()

    def test_main_handles_keyboard_interrupt(self):
        """main() handles KeyboardInterrupt gracefully."""
        with patch("attune.mcp.healthcare.EmpathyMCPServer"):
            from attune.mcp.healthcare import main

            with patch("attune.mcp.healthcare.asyncio.run", side_effect=KeyboardInterrupt):
                # Should not raise
                main()
