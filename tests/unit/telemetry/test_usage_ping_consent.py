"""Tests for the first-run usage-ping consent prompt.

`maybe_prompt_consent` is the opt-in lever for usage-signals: it asks
once, interactively, default-No, and must never block or break the CLI
in a non-interactive context.
"""

from __future__ import annotations

import pytest

from attune.config.sections.telemetry import TelemetryConfig
from attune.telemetry import usage_ping


class _FakeConfig:
    def __init__(self, telemetry: TelemetryConfig) -> None:
        self.telemetry = telemetry


class _FakeLoader:
    def __init__(self, config: _FakeConfig) -> None:
        self._config = config
        self.saved = False

    def load(self) -> _FakeConfig:
        return self._config

    def save(self, config: _FakeConfig, path: object = None) -> object:
        self._config = config
        self.saved = True
        return path


def _loader(**tele: object) -> _FakeLoader:
    return _FakeLoader(_FakeConfig(TelemetryConfig(**tele)))


class _FakeStream:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture
def tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force an interactive terminal for the prompt path."""
    monkeypatch.setattr(usage_ping, "_is_interactive", lambda: True)


# --- the prompt outcomes ---------------------------------------------------


def test_yes_opts_in(tty: None) -> None:
    loader = _loader()
    result = usage_ping.maybe_prompt_consent(loader=loader, env={}, input_fn=lambda _p: "y")
    tele = loader.load().telemetry
    assert result is True
    assert tele.usage_ping is True
    assert tele.usage_ping_consented is True
    assert tele.install_id  # an anonymous id was minted


@pytest.mark.parametrize("answer", ["n", "no", "", "   ", "nope", "maybe"])
def test_non_yes_opts_out_but_records_consent(tty: None, answer: str) -> None:
    loader = _loader()
    result = usage_ping.maybe_prompt_consent(loader=loader, env={}, input_fn=lambda _p: answer)
    tele = loader.load().telemetry
    assert result is False
    assert tele.usage_ping is False
    assert tele.usage_ping_consented is True  # so we never ask again


def test_yes_is_case_insensitive(tty: None) -> None:
    loader = _loader()
    assert usage_ping.maybe_prompt_consent(loader=loader, env={}, input_fn=lambda _p: "  YES  ")


# --- when it must NOT prompt ----------------------------------------------


def test_already_consented_does_not_prompt(tty: None) -> None:
    loader = _loader(usage_ping_consented=True)
    calls: list[str] = []
    result = usage_ping.maybe_prompt_consent(
        loader=loader, env={}, input_fn=lambda p: calls.append(p) or "y"
    )
    assert result is None
    assert calls == []  # input never called
    assert loader.saved is False


def test_non_interactive_does_not_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usage_ping, "_is_interactive", lambda: False)
    loader = _loader()
    calls: list[str] = []
    result = usage_ping.maybe_prompt_consent(
        loader=loader, env={}, input_fn=lambda p: calls.append(p) or "y"
    )
    assert result is None
    assert calls == []
    # The one-shot is NOT burned — a later interactive run can still ask.
    assert loader.load().telemetry.usage_ping_consented is False


@pytest.mark.parametrize(
    "env",
    [
        {"DO_NOT_TRACK": "1"},
        {"DO_NOT_TRACK": "true"},
        {"ATTUNE_USAGE_PING": "0"},
        {"ATTUNE_USAGE_PING": "1"},
    ],
)
def test_env_signal_skips_prompt(tty: None, env: dict[str, str]) -> None:
    loader = _loader()
    calls: list[str] = []
    result = usage_ping.maybe_prompt_consent(
        loader=loader, env=env, input_fn=lambda p: calls.append(p) or "y"
    )
    assert result is None
    assert calls == []
    assert loader.load().telemetry.usage_ping_consented is False  # not recorded


def test_do_not_track_falsey_still_prompts(tty: None) -> None:
    """DO_NOT_TRACK=0 is treated as 'not set' — the prompt still fires."""
    loader = _loader()
    assert usage_ping.maybe_prompt_consent(
        loader=loader, env={"DO_NOT_TRACK": "0"}, input_fn=lambda _p: "y"
    )


def test_aborted_prompt_records_no_consent(tty: None) -> None:
    loader = _loader()

    def abort(_p: str) -> str:
        raise EOFError

    result = usage_ping.maybe_prompt_consent(loader=loader, env={}, input_fn=abort)
    assert result is None
    # Aborting ("not now") must NOT burn the one-shot.
    assert loader.load().telemetry.usage_ping_consented is False


# --- _is_interactive -------------------------------------------------------


def test_is_interactive_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", _FakeStream(True))
    monkeypatch.setattr("sys.stdout", _FakeStream(True))
    assert usage_ping._is_interactive() is True


def test_is_interactive_false_when_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", _FakeStream(True))
    monkeypatch.setattr("sys.stdout", _FakeStream(False))
    assert usage_ping._is_interactive() is False


def test_is_interactive_false_on_closed_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Boom:
        def isatty(self) -> bool:
            raise ValueError("I/O operation on closed file")

    monkeypatch.setattr("sys.stdin", _Boom())
    monkeypatch.setattr("sys.stdout", _Boom())
    assert usage_ping._is_interactive() is False


# --- best-effort: never crashes the CLI -----------------------------------


def test_config_load_failure_is_swallowed(tty: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """If the config can't be read, the prompt skips quietly (no raise)."""

    def boom(_loader: object) -> object:
        raise OSError("config unreadable")

    monkeypatch.setattr(usage_ping, "_open_user_config", boom)
    assert usage_ping.maybe_prompt_consent(env={}, input_fn=lambda _p: "y") is None


def test_persist_failure_is_swallowed(tty: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure while saving the choice must not crash the CLI."""

    def boom(_loader: object = None) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(usage_ping, "enable", boom)
    loader = _loader()
    assert usage_ping.maybe_prompt_consent(loader=loader, env={}, input_fn=lambda _p: "y") is None
