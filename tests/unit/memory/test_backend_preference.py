"""Memory backend preference and the resolver honoring it (redis-config-truth D5).

Redis stays bundled and zero-config; the user's recorded choice —
``auto`` / ``file`` / ``redis`` — is persisted in the user config and
honored by ``resolve_backend`` and ``backend_status``. Every test here
runs against a temporary ``ATTUNE_HOME`` and fake entry points: no real
backend, no server, no network.
"""

from __future__ import annotations

import importlib.metadata as md
import json

import pytest

from attune.memory import preference as pref
from attune.memory import session_stash as ss


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.delenv(pref.ENV_VAR, raising=False)
    monkeypatch.delenv(pref.NOTICE_ENV_VAR, raising=False)


class _Backend:
    """Duck-typed searchable backend; records whether it was probed."""

    def __init__(self, name: str, *, fallback: bool = False, connected: bool = True):
        self.name = name
        self.is_fallback = fallback
        self._connected = connected
        self.probed = 0

    def is_connected(self) -> bool:
        self.probed += 1
        return self._connected

    def search(self, *a, **k):  # pragma: no cover - duck typing only
        return []

    def stash(self, *a, **k):  # pragma: no cover - duck typing only
        return None


class _EP:
    def __init__(self, name: str, instance: _Backend):
        self.name = name
        self._instance = instance

    def load(self):
        return lambda: self._instance


def _install(monkeypatch, *backends: _Backend) -> None:
    eps = [_EP(b.name, b) for b in backends]
    monkeypatch.setattr(md, "entry_points", lambda group=None: eps)


# --- the store ---------------------------------------------------------------


def test_default_is_auto_and_nothing_recorded() -> None:
    assert pref.get_backend_preference() == "auto"
    assert pref.preference_recorded() is False
    assert pref.notice_shown() is False


def test_set_round_trips_and_preserves_other_config_keys(tmp_path) -> None:
    path = pref.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"telemetry": {"usage_ping_consented": True}}), encoding="utf-8")
    written = pref.set_backend_preference("file")
    assert written.resolve() == path.resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["memory"]["backend"] == "file"
    assert data["telemetry"] == {"usage_ping_consented": True}, "sibling keys must survive"
    assert pref.get_backend_preference() == "file"
    assert pref.preference_recorded() is True
    assert not list(path.parent.glob("*.tmp")), "atomic write leaves no temp file"


@pytest.mark.parametrize("bad", ["", "redis-please", "FILE", "both"])
def test_invalid_values_are_rejected(bad) -> None:
    with pytest.raises(ValueError, match="must be one of"):
        pref.set_backend_preference(bad)


def test_env_override_wins_but_does_not_count_as_recorded(monkeypatch) -> None:
    pref.set_backend_preference("file")
    monkeypatch.setenv(pref.ENV_VAR, "redis")
    assert pref.get_backend_preference() == "redis"
    monkeypatch.setenv(pref.ENV_VAR, "nonsense")
    assert pref.get_backend_preference() == "file", "an invalid override is ignored"


def test_unreadable_or_non_object_config_means_no_choice() -> None:
    path = pref.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")
    assert pref.get_backend_preference() == "auto"
    path.write_text("{not json", encoding="utf-8")
    assert pref.preference_recorded() is False


def test_notice_shown_flag_round_trips() -> None:
    pref.mark_notice_shown()
    assert pref.notice_shown() is True
    assert pref.preference_recorded() is False, "the notice flag is not a choice"


def test_notice_enabled_honors_env(monkeypatch) -> None:
    assert pref.notice_enabled() is True
    for value in ("0", "false", "off", "no", ""):
        monkeypatch.setenv(pref.NOTICE_ENV_VAR, value)
        assert pref.notice_enabled() is False


# --- the resolver ------------------------------------------------------------


def test_auto_prefers_a_connected_upgrade(monkeypatch) -> None:
    file_tier, upgrade = _Backend("file", fallback=True), _Backend("redis")
    _install(monkeypatch, file_tier, upgrade)
    assert ss.resolve_backend() is upgrade


def test_file_preference_never_probes_the_upgrade(monkeypatch) -> None:
    pref.set_backend_preference("file")
    file_tier, upgrade = _Backend("file", fallback=True), _Backend("redis")
    _install(monkeypatch, file_tier, upgrade)
    assert ss.resolve_backend() is file_tier
    assert upgrade.probed == 0, "a chosen file tier must not cost a connectivity probe"
    status = ss.backend_status()
    assert status["preference"] == "file"
    assert status["unreachable_upgrade"] is None, "an unprobed upgrade is not 'dark'"
    assert status["fallback"] is True


def test_redis_preference_degrades_to_file_and_reports_the_dark_upgrade(monkeypatch) -> None:
    pref.set_backend_preference("redis")
    file_tier, upgrade = _Backend("file", fallback=True), _Backend("redis", connected=False)
    _install(monkeypatch, file_tier, upgrade)
    assert ss.resolve_backend() is file_tier
    status = ss.backend_status()
    assert status["preference"] == "redis"
    assert status["unreachable_upgrade"] == "redis"


def test_redis_preference_uses_the_upgrade_when_reachable(monkeypatch) -> None:
    pref.set_backend_preference("redis")
    file_tier, upgrade = _Backend("file", fallback=True), _Backend("redis")
    _install(monkeypatch, file_tier, upgrade)
    assert ss.resolve_backend() is upgrade
    assert ss.backend_status()["backend"] == "_Backend"


def test_env_override_reaches_the_resolver(monkeypatch) -> None:
    monkeypatch.setenv(pref.ENV_VAR, "file")
    file_tier, upgrade = _Backend("file", fallback=True), _Backend("redis")
    _install(monkeypatch, file_tier, upgrade)
    assert ss.resolve_backend() is file_tier
    assert upgrade.probed == 0
