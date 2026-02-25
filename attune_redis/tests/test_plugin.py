"""Tests for the RedisPlugin class."""

from attune.plugins import BasePlugin, PluginMetadata
from attune_redis.plugin import RedisPlugin


class TestRedisPlugin:
    """Tests for RedisPlugin registration and metadata."""

    def test_is_base_plugin(self):
        """RedisPlugin must be a BasePlugin subclass."""
        plugin = RedisPlugin()
        assert isinstance(plugin, BasePlugin)

    def test_metadata_fields(self):
        """Metadata must have required fields."""
        plugin = RedisPlugin()
        meta = plugin.get_metadata()

        assert isinstance(meta, PluginMetadata)
        assert meta.name == "Attune Redis"
        assert meta.domain == "redis"
        assert meta.version == "0.1.0"
        assert "agent-memory-client" in str(meta.dependencies)

    def test_register_workflows_returns_dict(self):
        """register_workflows must return a dict."""
        plugin = RedisPlugin()
        wf = plugin.register_workflows()

        assert isinstance(wf, dict)

    def test_on_activate_succeeds(self):
        """on_activate must not raise."""
        plugin = RedisPlugin()
        plugin.on_activate()
