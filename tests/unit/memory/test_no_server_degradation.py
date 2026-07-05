"""No-server degradation gate for the Redis memory surface.

Redis + agent-memory-client became CORE dependencies on 2026-07-04
(redis-facade-direction D6): the standard ``pip install attune-ai``
carries the client libraries, and the memory features are expected to
degrade with clean guidance — never a traceback — when no Redis Stack
server is reachable.

This is the gate D6 shipped with (the 9.3.0 lesson: boot-only smoke
checks pass broken features). It locks three contracts:

1. The client deps are importable in a standard environment.
2. Availability checks report "server not running" guidance instead
   of raising when nothing listens.
3. The ``redis_memory_*`` MCP handlers return a clean error dict when
   the backend cannot reach a server.
"""

from unittest.mock import patch

import pytest

from attune.memory.features import FeatureStatus, MemoryFeatures


class TestCoreDepsPresent:
    """The packaging half of D6: deps ship with the standard install."""

    def test_redis_client_is_importable(self):
        import redis  # noqa: F401

    def test_agent_memory_client_is_importable(self):
        import agent_memory_client  # noqa: F401


class TestNoServerAvailabilityChecks:
    """Availability checks must return False / guidance, not raise."""

    def test_is_redis_running_unreachable_port_returns_false(self):
        # Port 1 is never a Redis server; must come back False within
        # the 1s connect timeout without raising.
        assert MemoryFeatures.is_redis_running(host="127.0.0.1", port=1) is False

    def test_redis_feature_reports_server_guidance_when_down(self):
        with (
            patch.object(MemoryFeatures, "is_redis_available", return_value=True),
            patch.object(MemoryFeatures, "is_redis_running", return_value=False),
        ):
            info = MemoryFeatures.get_feature_status("short_term")
        assert info.status == FeatureStatus.NOT_CONFIGURED
        assert "server" in info.message.lower()
        # Guidance points at installing/starting a server, not pip.
        assert info.install_command and "redis" in info.install_command.lower()


class TestMcpToolsDegradeCleanly:
    """redis_memory_* handlers return an error dict, never raise."""

    async def test_store_returns_clean_error_when_backend_unreachable(self):
        import redis as redis_lib

        from attune_redis.mcp_tools import handle_redis_memory_store

        class _DeadBackend:
            def stash(self, *args, **kwargs):
                raise redis_lib.ConnectionError("Connection refused")

        class _Server:
            _redis_backend = _DeadBackend()

        result = await handle_redis_memory_store(_Server(), {"key": "k", "value": "v"})
        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]

    async def test_retrieve_returns_clean_error_when_backend_unreachable(self):
        import redis as redis_lib

        from attune_redis.mcp_tools import handle_redis_memory_retrieve

        class _DeadBackend:
            def retrieve(self, *args, **kwargs):
                raise redis_lib.ConnectionError("Connection refused")

        class _Server:
            _redis_backend = _DeadBackend()

        result = await handle_redis_memory_retrieve(_Server(), {"key": "k"})
        assert result["success"] is False
        assert isinstance(result.get("error"), str) and result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
