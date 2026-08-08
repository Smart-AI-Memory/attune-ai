"""Tests for the redis_health_check doctor diagnostic — redis-config-truth rct-3.

Pins R2: the ``effective_config`` section is DERIVED from the
canonical resolver's source-map and the R3 classifier — which env
var supplied each component, the redacted URL shape, recorded
overrides, and the classified health state — with no secret material
anywhere in the rendered output. The incident shape (password-less
REDIS_URL + REDIS_PASSWORD set, 2026-08-08) is the load-bearing case.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import redis as redis_lib

from attune_redis.mcp_tools import (
    TOOL_HANDLERS,
    _effective_config_report,
    handle_redis_health_check,
)


def _healthy_ping_patch():
    client = MagicMock()
    client.ping.return_value = True
    return patch.object(redis_lib.Redis, "from_url", return_value=client)


class TestEffectiveConfigReport:
    def test_incident_shape_names_sources_and_merges_password(self):
        """The 2026-08-08 incident, post-fix: password merged, sources named."""
        env = {
            "REDIS_URL": "redis://127.0.0.1:6379/0",
            "REDIS_PASSWORD": "sekret-pw",  # pragma: allowlist secret
        }
        with patch.dict("os.environ", env, clear=False), _healthy_ping_patch():
            report = _effective_config_report()
        assert report["available"] is True
        assert report["source_map"]["url"] == "REDIS_URL"
        assert report["source_map"]["password"] == "REDIS_PASSWORD"
        assert report["redacted_url"] == "redis://:***@127.0.0.1:6379/0"

    def test_rendered_output_contains_no_secret_material(self):
        """The XML block's grep check: dump the whole report, grep the password."""
        env = {
            "REDIS_URL": "redis://127.0.0.1:6379/0",
            "REDIS_PASSWORD": "sekret-pw",  # pragma: allowlist secret
        }
        with patch.dict("os.environ", env, clear=False), _healthy_ping_patch():
            rendered = json.dumps(_effective_config_report())
        assert "sekret-pw" not in rendered
        assert "***" in rendered

    def test_overrides_surface_in_report(self):
        env = {
            "REDIS_URL": "redis://main:6379/0",
            "REDIS_PRIVATE_URL": "redis://private:6379/0",
        }
        with patch.dict("os.environ", env, clear=False), _healthy_ping_patch():
            report = _effective_config_report()
        assert any("REDIS_PRIVATE_URL ignored" in o for o in report["overrides"])

    def test_health_state_included(self):
        exc = redis_lib.exceptions.AuthenticationError("invalid password")
        client = MagicMock()
        client.ping.side_effect = exc
        env = {
            "REDIS_URL": "redis://127.0.0.1:6379/0",
            "REDIS_PASSWORD": "wrongpw",  # pragma: allowlist secret
        }
        with (
            patch.dict("os.environ", env, clear=False),
            patch.object(redis_lib.Redis, "from_url", return_value=client),
        ):
            report = _effective_config_report()
        assert report["health"] == "degraded_auth"
        assert "wrongpw" not in json.dumps(report)

    def test_malformed_config_reports_without_source_map(self):
        """Resolver raise: health_detail carries the scrubbed error, no map."""
        with patch.dict("os.environ", {"REDIS_URL": "redis://h:notaport/0"}, clear=False):
            report = _effective_config_report()
        assert report["available"] is True
        assert report["health"] == "degraded_auth"
        assert "non-numeric port" in report["health_detail"]
        assert "source_map" not in report

    def test_attune_core_absent_degrades_gracefully(self):
        """The diagnostic never breaks the health tool (P15 posture)."""
        import builtins

        real_import = builtins.__import__

        def _no_attune(name, *args, **kwargs):
            if name.startswith("attune.memory"):
                raise ImportError("attune core not importable (test)")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=_no_attune):
            report = _effective_config_report()
        assert report == {"available": False, "reason": "attune core not importable"}


class TestHandlerIntegration:
    def test_handler_includes_effective_config_and_backend(self):
        server = MagicMock()
        backend = MagicMock()
        backend.is_connected.return_value = True
        backend.get_stats.return_value = {"total_keys": 1}
        with (
            patch("attune_redis.mcp_tools._get_backend", return_value=backend),
            patch(
                "attune_redis.mcp_tools._effective_config_report",
                return_value={"available": True, "health": "healthy"},
            ),
        ):
            result = asyncio.run(handle_redis_health_check(server, {}))
        assert result["success"] is True
        assert result["backend_selected"] == "MagicMock"
        assert result["effective_config"]["health"] == "healthy"

    def test_handler_registered(self):
        assert TOOL_HANDLERS["redis_health_check"] is handle_redis_health_check

    def test_handler_failure_path_still_degrades(self):
        server = MagicMock()
        with patch("attune_redis.mcp_tools._get_backend", side_effect=RuntimeError("boom")):
            result = asyncio.run(handle_redis_health_check(server, {}))
        assert result["success"] is False
        assert "boom" in result["error"]
