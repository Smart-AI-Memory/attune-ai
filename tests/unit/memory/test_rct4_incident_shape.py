"""R4 incident shape through every migrated consumer — rct-4 AC.

The 2026-08-08 incident: password-less ``REDIS_URL`` + ``REDIS_PASSWORD``
set. Pre-migration, most consumers ignored the password and read as
"Redis down". Post-migration every consumer derives its connection from
the canonical resolver, so the merged credential reaches each one.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

INCIDENT_PW = "hunter2"  # pragma: allowlist secret
INCIDENT_URL_BARE = "redis://127.0.0.1:6379/0"
INCIDENT_URL_MERGED = f"redis://:{INCIDENT_PW}@127.0.0.1:6379/0"


@pytest.fixture()
def incident_env(monkeypatch):
    """Hermetic incident shape: bare URL + password, nothing else."""
    for var in (
        "REDIS_PRIVATE_URL",
        "REDIS_PUBLIC_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_USER",
        "REDIS_MODE",
        "ATTUNE_REDIS_MOCK",
        "EMPATHY_REDIS_MOCK",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("REDIS_URL", INCIDENT_URL_BARE)
    monkeypatch.setenv("REDIS_PASSWORD", INCIDENT_PW)
    yield


def test_redis_config_delegator_carries_password(incident_env):
    from attune.redis_config import get_redis_config

    cfg = get_redis_config()
    assert cfg.password == INCIDENT_PW
    assert cfg.host == "127.0.0.1"
    assert cfg.use_mock is False


def test_memory_config_dict_carries_password(incident_env):
    from attune.memory.config import get_redis_config as get_dict

    cfg = get_dict()
    assert cfg["password"] == INCIDENT_PW


def test_recall_redis_url_carries_password(incident_env):
    from attune.memory import recall_redis

    assert recall_redis.resolve_url() == INCIDENT_URL_MERGED


def test_unified_memory_config_url_carries_password(incident_env):
    from attune.memory.unified import MemoryConfig

    cfg = MemoryConfig.from_environment()
    assert cfg.redis_url == INCIDENT_URL_MERGED


def test_plugin_config_url_carries_password(incident_env):
    from attune_redis.config import RedisPluginConfig

    cfg = RedisPluginConfig.from_env()
    assert cfg.redis_url == INCIDENT_URL_MERGED


def test_board_connects_with_merged_url(incident_env):
    fake_redis = MagicMock()
    fake_redis.RedisError = Exception
    with patch.dict(sys.modules, {"redis": fake_redis}):
        from attune.roundtable.board import Board

        Board()
    call = fake_redis.Redis.from_url.call_args
    assert call.args[0] == INCIDENT_URL_MERGED


@pytest.mark.parametrize(
    "module_name",
    [
        "attune.memory.features",
        "attune.memory.redis_auto_detect",
        "attune.memory.redis_bootstrap",
    ],
)
def test_probe_helpers_resolve_password(incident_env, module_name):
    """The three ping probes source their password from the resolver."""
    import importlib

    mod = importlib.import_module(module_name)
    assert mod._resolved_password() == INCIDENT_PW
