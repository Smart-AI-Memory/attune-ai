"""Tests for the opt-in usage-ping sync layer (Phase 2a).

Covers the privacy-critical invariants: the payload is frozen to an
exact key set, no forbidden local-record fields ever leak, enablement
defaults OFF with the documented override precedence, and transport is
truly fire-and-forget (never raises, never sends when disabled).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.config.sections.telemetry import TelemetryConfig
from attune.telemetry import usage_ping


class _FakeConfig:
    """Minimal stand-in for UnifiedConfig (only .telemetry is used)."""

    def __init__(self, telemetry: TelemetryConfig) -> None:
        self.telemetry = telemetry


# --------------------------------------------------------------------------- #
# Frozen payload — the privacy contract's load-bearing test
# --------------------------------------------------------------------------- #


def test_build_payload_has_exactly_frozen_keys():
    payload = usage_ping.build_payload(
        {"workflow": "security_audit", "ts": "2026-06-15T00:00:00.000000Z"},
        install_id="abc",
        version="9.9.9",
        os_name="linux",
        py_version="3.12",
    )
    assert set(payload) == usage_ping.PAYLOAD_KEYS


def test_build_payload_carries_no_forbidden_fields():
    """A record full of sensitive fields must yield a clean payload."""
    record = {
        "workflow": "deep_review",
        "ts": "2026-06-15T00:00:00.000000Z",
        "user_id": "deadbeefcafe1234",
        "cost": 1.23,
        "tokens": 4567,
        "model": "claude-opus-4-8",
        "provider": "anthropic",
        "tier": "premium",
        "stage": "analysis",
        "duration_ms": 999,
        "prompt_cache": {"hit": True},
        "cache": {"hit": False},
        "seq": 42,
    }
    payload = usage_ping.build_payload(record, install_id="id", version="1.0")
    leaked = usage_ping.FORBIDDEN_RECORD_FIELDS & set(payload)
    assert not leaked, f"forbidden fields leaked: {leaked}"
    assert payload["event"] == "workflow.deep_review"
    # Values, not just keys: no sensitive value should appear anywhere.
    blob = json.dumps(payload)
    for forbidden in ("deadbeefcafe1234", "claude-opus-4-8", "1.23", "4567"):
        assert forbidden not in blob


def test_build_payload_defaults_unknown_workflow():
    payload = usage_ping.build_payload({"ts": "t"}, install_id="i", version="v")
    assert payload["event"] == "workflow.unknown"


def test_payload_schema_version_matches_payload():
    payload = usage_ping.build_payload({"workflow": "x"}, install_id="i", version="v")
    assert payload["schema"] == usage_ping.PAYLOAD_SCHEMA_VERSION


# --------------------------------------------------------------------------- #
# Enablement precedence — DO_NOT_TRACK > ATTUNE_USAGE_PING > config
# --------------------------------------------------------------------------- #


def test_is_enabled_defaults_off():
    assert usage_ping.is_enabled(False, env={}) is False


def test_is_enabled_config_flag_on():
    assert usage_ping.is_enabled(True, env={}) is True


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE", " On "])
def test_is_enabled_env_override_truthy(val):
    assert usage_ping.is_enabled(False, env={"ATTUNE_USAGE_PING": val}) is True


@pytest.mark.parametrize("val", ["0", "false", "no", "", "off"])
def test_is_enabled_env_override_falsy_beats_config(val):
    assert usage_ping.is_enabled(True, env={"ATTUNE_USAGE_PING": val}) is False


def test_do_not_track_always_wins():
    env = {"DO_NOT_TRACK": "1", "ATTUNE_USAGE_PING": "1"}
    assert usage_ping.is_enabled(True, env=env) is False


def test_do_not_track_zero_is_not_optout():
    assert usage_ping.is_enabled(True, env={"DO_NOT_TRACK": "0"}) is True


# --------------------------------------------------------------------------- #
# Endpoint resolution & scheme guard
# --------------------------------------------------------------------------- #


def test_resolve_endpoint_default_is_production():
    # Phase 2b wired the production ingest endpoint as the default. The
    # trailing slash is required (site runs trailingSlash: true) so a
    # POST lands directly instead of via a 308 redirect.
    assert usage_ping.resolve_endpoint(env={}) == "https://smartaimemory.com/api/usage/"


def test_resolve_endpoint_env_override():
    url = "https://example.com/api/usage"
    assert usage_ping.resolve_endpoint(env={"ATTUNE_USAGE_ENDPOINT": url}) == url


def test_sync_no_endpoint_is_noop():
    calls = []
    sent = usage_ping.sync(
        [{"workflow": "a", "ts": "t"}],
        endpoint="",
        install_id="i",
        version="v",
        poster=lambda *a: calls.append(a) or True,
    )
    assert sent == 0
    assert calls == []


def test_sync_rejects_non_http_scheme():
    calls = []
    sent = usage_ping.sync(
        [{"workflow": "a", "ts": "t"}],
        endpoint="file:///etc/passwd",
        install_id="i",
        version="v",
        poster=lambda *a: calls.append(a) or True,
    )
    assert sent == 0
    assert calls == []


# --------------------------------------------------------------------------- #
# sync() transport behavior — batching, failure, fire-and-forget
# --------------------------------------------------------------------------- #


def test_sync_sends_all_records_on_success():
    posted = []

    def poster(url, batch, timeout):
        posted.extend(batch)
        return True

    records = [{"workflow": f"w{i}", "ts": f"t{i}"} for i in range(5)]
    sent = usage_ping.sync(
        records, endpoint="https://x/api", install_id="i", version="v", poster=poster
    )
    assert sent == 5
    assert len(posted) == 5
    assert all(set(p) == usage_ping.PAYLOAD_KEYS for p in posted)


def test_sync_batches_by_batch_size():
    batches = []
    sent = usage_ping.sync(
        [{"workflow": "w", "ts": str(i)} for i in range(5)],
        endpoint="https://x/api",
        install_id="i",
        version="v",
        batch_size=2,
        poster=lambda url, batch, timeout: batches.append(len(batch)) or True,
    )
    assert sent == 5
    assert batches == [2, 2, 1]


def test_sync_stops_at_first_failed_batch():
    attempts = {"n": 0}

    def poster(url, batch, timeout):
        attempts["n"] += 1
        return attempts["n"] == 1  # first batch ok, second fails

    sent = usage_ping.sync(
        [{"workflow": "w", "ts": str(i)} for i in range(4)],
        endpoint="https://x/api",
        install_id="i",
        version="v",
        batch_size=2,
        poster=poster,
    )
    assert sent == 2  # only the first batch confirmed


def test_sync_swallows_poster_exception():
    def boom(url, batch, timeout):
        raise RuntimeError("network down")

    sent = usage_ping.sync(
        [{"workflow": "w", "ts": "t"}],
        endpoint="https://x/api",
        install_id="i",
        version="v",
        poster=boom,
    )
    assert sent == 0  # never raises


# --------------------------------------------------------------------------- #
# Cursor + record reading
# --------------------------------------------------------------------------- #


def test_cursor_roundtrip(tmp_path):
    assert usage_ping.read_cursor(tmp_path) == ""
    usage_ping.write_cursor(tmp_path, "2026-06-15T00:00:00.000000Z")
    assert usage_ping.read_cursor(tmp_path) == "2026-06-15T00:00:00.000000Z"


def test_records_since_filters_and_sorts(tmp_path):
    lines = [
        {"workflow": "a", "ts": "2026-06-15T00:00:01.000000Z"},
        {"workflow": "b", "ts": "2026-06-15T00:00:03.000000Z"},
        {"workflow": "c", "ts": "2026-06-15T00:00:02.000000Z"},
    ]
    (tmp_path / "usage.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8"
    )
    got = usage_ping.records_since(tmp_path, "2026-06-15T00:00:01.000000Z")
    assert [r["workflow"] for r in got] == ["c", "b"]  # > cursor, ts-sorted


def test_records_since_skips_malformed_lines(tmp_path):
    (tmp_path / "usage.jsonl").write_text(
        'not json\n{"workflow":"a","ts":"t2"}\n\n', encoding="utf-8"
    )
    got = usage_ping.records_since(tmp_path, "t1")
    assert [r["workflow"] for r in got] == ["a"]


def test_records_since_reads_rotated_files(tmp_path):
    (tmp_path / "usage.jsonl").write_text(
        json.dumps({"workflow": "new", "ts": "t3"}) + "\n", encoding="utf-8"
    )
    (tmp_path / "usage.2026-06-14.jsonl").write_text(
        json.dumps({"workflow": "old", "ts": "t2"}) + "\n", encoding="utf-8"
    )
    got = usage_ping.records_since(tmp_path, "t1")
    assert {r["workflow"] for r in got} == {"new", "old"}


# --------------------------------------------------------------------------- #
# run_sync orchestration
# --------------------------------------------------------------------------- #


def test_run_sync_disabled_returns_zero(tmp_path):
    config = _FakeConfig(TelemetryConfig(usage_ping=False))
    sent = usage_ping.run_sync(config, telemetry_dir=tmp_path, version="v", env={})
    assert sent == 0


def test_run_sync_enabled_no_install_id_returns_zero(tmp_path):
    config = _FakeConfig(TelemetryConfig(usage_ping=True, install_id=""))
    sent = usage_ping.run_sync(config, telemetry_dir=tmp_path, version="v", env={})
    assert sent == 0


def test_run_sync_no_endpoint_returns_zero(tmp_path, monkeypatch):
    # With the default endpoint blanked (and no env override), run_sync
    # must short-circuit to a no-op.
    monkeypatch.setattr(usage_ping, "DEFAULT_ENDPOINT", "")
    config = _FakeConfig(TelemetryConfig(usage_ping=True, install_id="id"))
    sent = usage_ping.run_sync(config, telemetry_dir=tmp_path, version="v", env={})
    assert sent == 0


def test_run_sync_happy_path_advances_cursor(tmp_path):
    (tmp_path / "usage.jsonl").write_text(
        "\n".join(
            json.dumps({"workflow": "w", "ts": f"2026-06-15T00:00:0{i}.000000Z"}) for i in range(3)
        )
        + "\n",
        encoding="utf-8",
    )
    config = _FakeConfig(TelemetryConfig(usage_ping=True, install_id="id"))
    posted = []
    sent = usage_ping.run_sync(
        config,
        telemetry_dir=tmp_path,
        version="v",
        env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"},
        poster=lambda url, batch, timeout: posted.extend(batch) or True,
    )
    assert sent == 3
    assert usage_ping.read_cursor(tmp_path) == "2026-06-15T00:00:02.000000Z"
    # A second pass has nothing new.
    assert (
        usage_ping.run_sync(
            config,
            telemetry_dir=tmp_path,
            version="v",
            env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"},
            poster=lambda url, batch, timeout: True,
        )
        == 0
    )


# --------------------------------------------------------------------------- #
# Config glue (enable / disable / reset) via an injected loader
# --------------------------------------------------------------------------- #


class _FakeLoader:
    """Loader stub that holds a config in memory."""

    def __init__(self, config):
        self._config = config
        self.saved = False

    def load(self):
        return self._config

    def save(self, config, path=None):
        self._config = config
        self.saved = True
        return path


def test_enable_mints_install_id_and_sets_flags():
    loader = _FakeLoader(_FakeConfig(TelemetryConfig()))
    install_id = usage_ping.enable(loader=loader)
    tele = loader.load().telemetry
    assert tele.usage_ping is True
    assert tele.usage_ping_consented is True
    assert tele.install_id == install_id and install_id
    assert loader.saved


def test_enable_keeps_existing_install_id():
    loader = _FakeLoader(_FakeConfig(TelemetryConfig(install_id="keep-me")))
    assert usage_ping.enable(loader=loader) == "keep-me"


def test_disable_sets_flag_off_and_consented():
    loader = _FakeLoader(_FakeConfig(TelemetryConfig(usage_ping=True, install_id="x")))
    usage_ping.disable(loader=loader)
    tele = loader.load().telemetry
    assert tele.usage_ping is False
    assert tele.usage_ping_consented is True


def test_reset_install_id_rotates():
    loader = _FakeLoader(_FakeConfig(TelemetryConfig(install_id="old")))
    new = usage_ping.reset_install_id(loader=loader)
    assert new != "old" and new
    assert loader.load().telemetry.install_id == new


def test_example_payload_shape():
    config = _FakeConfig(TelemetryConfig(install_id="id"))
    payload = usage_ping.example_payload(config, version="1.2.3")
    assert set(payload) == usage_ping.PAYLOAD_KEYS
    assert payload["install_id"] == "id"


def test_config_roundtrip_preserves_new_fields():
    tele = TelemetryConfig(usage_ping=True, install_id="abc", usage_ping_consented=True)
    restored = TelemetryConfig.from_dict(tele.to_dict())
    assert restored.usage_ping is True
    assert restored.install_id == "abc"
    assert restored.usage_ping_consented is True


# --------------------------------------------------------------------------- #
# Real transport (_urllib_post) via a mocked urlopen
# --------------------------------------------------------------------------- #


class _FakeResp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def getcode(self):
        return self.status


def test_urllib_post_builds_request_and_reads_2xx(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data)
        captured["ct"] = req.headers.get("Content-type")
        return _FakeResp(204)

    monkeypatch.setattr(usage_ping.urllib.request, "urlopen", fake_urlopen)
    ok = usage_ping._urllib_post("https://x/api", [{"a": 1}], 2.0)
    assert ok is True
    assert captured["method"] == "POST"
    assert captured["url"] == "https://x/api"
    assert captured["body"] == {"events": [{"a": 1}]}
    assert captured["ct"] == "application/json"


def test_urllib_post_non_2xx_returns_false(monkeypatch):
    monkeypatch.setattr(usage_ping.urllib.request, "urlopen", lambda req, timeout: _FakeResp(500))
    assert usage_ping._urllib_post("https://x/api", [], 2.0) is False


def test_sync_default_poster_round_trips(monkeypatch):
    """Exercise sync() with the real default poster over a mocked socket."""
    seen = []

    def fake_urlopen(req, timeout):
        seen.append(json.loads(req.data))
        return _FakeResp(200)

    monkeypatch.setattr(usage_ping.urllib.request, "urlopen", fake_urlopen)
    sent = usage_ping.sync(
        [{"workflow": "w", "ts": "t"}],
        endpoint="https://x/api",
        install_id="i",
        version="v",
    )
    assert sent == 1
    assert seen and set(seen[0]["events"][0]) == usage_ping.PAYLOAD_KEYS


def test_write_cursor_swallows_oserror(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise OSError("read-only fs")

    monkeypatch.setattr(usage_ping.Path, "write_text", boom)
    # Must not raise.
    usage_ping.write_cursor(tmp_path, "2026-06-15T00:00:00Z")


def test_records_since_swallows_unreadable_file(monkeypatch, tmp_path):
    """An OSError opening a matched file is skipped, not raised."""
    (tmp_path / "usage.jsonl").write_text(
        json.dumps({"workflow": "w", "ts": "t2"}) + "\n", encoding="utf-8"
    )

    def boom(*a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr("builtins.open", boom)
    assert usage_ping.records_since(tmp_path, "t1") == []


# --------------------------------------------------------------------------- #
# run_sync default-path branches (no injected telemetry_dir / version)
# --------------------------------------------------------------------------- #


def test_run_sync_uses_default_dir_and_version(monkeypatch):
    """With telemetry_dir/version omitted, run_sync resolves defaults.

    Real disk is isolated by stubbing the reader functions, so this
    exercises the default-path branches without touching ~/.attune.
    """
    monkeypatch.setattr(usage_ping, "read_cursor", lambda d: "")
    monkeypatch.setattr(usage_ping, "records_since", lambda d, c: [])
    config = _FakeConfig(TelemetryConfig(usage_ping=True, install_id="id"))
    sent = usage_ping.run_sync(
        config,
        env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"},
        poster=lambda url, batch, timeout: True,
    )
    assert sent == 0  # no records, but default dir + version were resolved


# --------------------------------------------------------------------------- #
# _open_user_config — the real (non-injected) USER-config path
# --------------------------------------------------------------------------- #


def test_open_user_config_creates_loader_for_missing_home(monkeypatch, tmp_path):
    """No loader + no existing user config → fresh defaults at the home path."""
    from attune.config.loader import ConfigLoader

    home = tmp_path / "config.json"  # does not exist
    monkeypatch.setattr(ConfigLoader, "get_default_config_path", staticmethod(lambda: home))
    loader, config, save_path = usage_ping._open_user_config(None)
    assert isinstance(loader, ConfigLoader)
    assert config is not None
    assert save_path == home


def test_open_user_config_opens_existing_home(monkeypatch, tmp_path):
    """No loader + existing user config → load from that home path."""
    from attune.config.loader import ConfigLoader
    from attune.config.unified import UnifiedConfig

    home = tmp_path / "config.json"
    # Write directly to the temp path — never call ConfigLoader.save(),
    # whose path=None fallback resolves to the REAL ~/.attune/config.json.
    home.write_text(json.dumps(UnifiedConfig().to_dict()), encoding="utf-8")
    monkeypatch.setattr(ConfigLoader, "get_default_config_path", staticmethod(lambda: home))
    loader, config, save_path = usage_ping._open_user_config(None)
    assert isinstance(loader, ConfigLoader)
    assert config is not None
    assert save_path == home


# --------------------------------------------------------------------------- #
# run_sync_at_exit — the atexit/Stop entry point gating (Phase 2b)
# --------------------------------------------------------------------------- #


def test_run_sync_at_exit_respects_do_not_track(monkeypatch):
    """DO_NOT_TRACK short-circuits before any config load or delegation."""
    called = []
    monkeypatch.setattr(usage_ping, "run_sync", lambda *a, **k: called.append(1) or 5)
    assert usage_ping.run_sync_at_exit(env={"DO_NOT_TRACK": "1"}) == 0
    assert called == []


def test_run_sync_at_exit_respects_explicit_disable(monkeypatch):
    """ATTUNE_USAGE_PING=0 short-circuits regardless of config."""
    called = []
    monkeypatch.setattr(usage_ping, "run_sync", lambda *a, **k: called.append(1) or 5)
    assert usage_ping.run_sync_at_exit(env={"ATTUNE_USAGE_PING": "0"}) == 0
    assert called == []


def test_run_sync_at_exit_no_endpoint_is_noop(monkeypatch):
    """With the endpoint blanked and no override, it never delegates."""
    monkeypatch.setattr(usage_ping, "DEFAULT_ENDPOINT", "")
    called = []
    monkeypatch.setattr(usage_ping, "run_sync", lambda *a, **k: called.append(1) or 5)
    assert usage_ping.run_sync_at_exit(env={}) == 0
    assert called == []


def test_run_sync_at_exit_no_user_config_is_noop(monkeypatch, tmp_path):
    """A user who never created a config never opted in -> no-op."""
    from attune.config.loader import ConfigLoader

    missing = tmp_path / "nope.json"
    monkeypatch.setattr(ConfigLoader, "get_default_config_path", staticmethod(lambda: missing))
    called = []
    monkeypatch.setattr(usage_ping, "run_sync", lambda *a, **k: called.append(1) or 5)
    assert usage_ping.run_sync_at_exit(env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"}) == 0
    assert called == []


def test_run_sync_at_exit_delegates_when_gates_pass(monkeypatch, tmp_path):
    """Gates clear (no opt-out, endpoint set, config exists) -> run_sync."""
    from attune.config.loader import ConfigLoader

    cfg = tmp_path / "config.json"
    cfg.write_text("{}", encoding="utf-8")
    fake_config = _FakeConfig(TelemetryConfig(usage_ping=True, install_id="id"))
    monkeypatch.setattr(ConfigLoader, "get_default_config_path", staticmethod(lambda: cfg))
    monkeypatch.setattr(ConfigLoader, "load", lambda self: fake_config)
    captured: dict = {}
    monkeypatch.setattr(
        usage_ping,
        "run_sync",
        lambda config, **kw: captured.update(config=config, kw=kw) or 7,
    )
    sent = usage_ping.run_sync_at_exit(env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"})
    assert sent == 7
    assert captured["config"] is fake_config


def test_run_sync_at_exit_swallows_all_errors(monkeypatch, tmp_path):
    """Any failure in the chain returns 0, never raises into teardown."""
    from attune.config.loader import ConfigLoader

    cfg = tmp_path / "config.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ConfigLoader, "get_default_config_path", staticmethod(lambda: cfg))

    def _boom(self):
        raise RuntimeError("config blew up")

    monkeypatch.setattr(ConfigLoader, "load", _boom)
    assert usage_ping.run_sync_at_exit(env={"ATTUNE_USAGE_ENDPOINT": "https://x/api"}) == 0


class TestIsDoNotTrack:
    """The single opt-out predicate (deduplicated from three call sites)."""

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", " on "])
    def test_set_to_truthy_opts_out(self, value):
        assert usage_ping._is_do_not_track({"DO_NOT_TRACK": value}) is True

    @pytest.mark.parametrize("value", ["", "0", "false", "FALSE", " "])
    def test_empty_or_false_does_not_opt_out(self, value):
        assert usage_ping._is_do_not_track({"DO_NOT_TRACK": value}) is False

    def test_unset_does_not_opt_out(self):
        assert usage_ping._is_do_not_track({}) is False
