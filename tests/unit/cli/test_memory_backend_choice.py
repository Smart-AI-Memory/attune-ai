"""The three choosing surfaces for the memory backend (redis-config-truth D5).

- ``attune memory use <auto|file|redis>`` records the preference and shows the
  live status; invalid values and unwritable configs fail with a message.
- The one-time terminal notice fires only on an interactive terminal, only
  before a choice, only once, never for the choosing commands, and never
  blocks a command with a prompt.
- ``attune setup`` asks once on a terminal, prints the pointer otherwise, and
  never fails on EOF, an unknown answer, or an unwritable config.

Everything runs against a temporary ``ATTUNE_HOME``; ``backend_status`` is
intercepted so no backend, server, or network is touched.
"""

from __future__ import annotations

import io
import json
from argparse import Namespace

import pytest

from attune.cli_commands import memory_commands as mc
from attune.cli_commands import utility_commands as uc
from attune.memory import preference as pref
from attune.memory import session_stash

_FILE_STATUS = {
    "backend": "FileStashBackend",
    "fallback": True,
    "unreachable_upgrade": None,
    "ok": True,
    "transport": "file",
    "reachability": "reachable",
    "reason": None,
    "preference": "auto",
}


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.delenv(pref.ENV_VAR, raising=False)
    monkeypatch.delenv(pref.NOTICE_ENV_VAR, raising=False)
    monkeypatch.setattr(session_stash, "backend_status", lambda: dict(_FILE_STATUS))


# --- attune memory use -------------------------------------------------------


@pytest.mark.parametrize("backend", ["auto", "file", "redis"])
def test_memory_use_records_and_shows_status(backend, capsys) -> None:
    code = mc.cmd_memory_use(Namespace(backend=backend))
    out = capsys.readouterr().out
    assert code == 0
    assert f"Memory backend preference: {backend}" in out
    assert "Recorded in" in out and "Preference:" in out and "Memory backend:" in out
    assert json.loads(pref.config_path().read_text())["memory"]["backend"] == backend
    if backend == "redis":
        assert "enhanced memory features using Redis's open-source options" in out


def test_memory_use_rejects_an_invalid_value(capsys) -> None:
    assert mc.cmd_memory_use(Namespace(backend="both")) == 1
    assert "must be one of" in capsys.readouterr().out
    assert pref.preference_recorded() is False


def test_memory_use_reports_an_unwritable_config(monkeypatch, capsys) -> None:
    def _boom(value: str):
        raise OSError(13, "Permission denied", "config.json")

    monkeypatch.setattr(pref, "set_backend_preference", _boom)
    assert mc.cmd_memory_use(Namespace(backend="file")) == 1
    assert "Permission denied" in capsys.readouterr().out


def test_status_prints_the_preference_line(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        session_stash, "backend_status", lambda: {**_FILE_STATUS, "preference": "file"}
    )
    assert mc.cmd_memory_status(Namespace(json=False)) == 0
    out = capsys.readouterr().out
    assert out.startswith("Preference: file")
    assert "attune memory use auto|file|redis" in out


# --- the one-time terminal notice --------------------------------------------


def test_notice_fires_once_on_a_tty_before_any_choice() -> None:
    first, second = _Tty(), _Tty()
    assert mc.first_run_memory_notice("doctor", stream=first) is True
    assert "local file tier" in first.getvalue()
    assert "enhanced memory features using Redis's open-source options" in first.getvalue()
    assert "attune memory use auto|file|redis" in first.getvalue()
    assert pref.notice_shown() is True
    assert mc.first_run_memory_notice("doctor", stream=second) is False
    assert second.getvalue() == ""


def test_notice_is_silent_off_a_tty_and_for_the_choosing_commands() -> None:
    assert mc.first_run_memory_notice("doctor", stream=io.StringIO()) is False
    for command in ("memory", "setup"):
        assert mc.first_run_memory_notice(command, stream=_Tty()) is False
    assert pref.notice_shown() is False


def test_notice_is_silent_once_a_choice_exists_or_when_disabled(monkeypatch) -> None:
    pref.set_backend_preference("auto")
    assert mc.first_run_memory_notice("doctor", stream=_Tty()) is False
    monkeypatch.setenv(pref.ENV_VAR, "")  # no env override; config choice stands
    monkeypatch.setattr(pref, "preference_recorded", lambda: False)
    monkeypatch.setenv(pref.NOTICE_ENV_VAR, "0")
    assert mc.first_run_memory_notice("doctor", stream=_Tty()) is False


def test_notice_survives_an_unwritable_home(monkeypatch) -> None:
    def _boom():
        raise OSError("read-only home")

    monkeypatch.setattr(pref, "mark_notice_shown", _boom)
    stream = _Tty()
    assert mc.first_run_memory_notice("doctor", stream=stream) is True
    assert "local file tier" in stream.getvalue()


def test_cli_main_calls_the_notice(monkeypatch) -> None:
    from attune import cli_minimal

    seen: list = []
    monkeypatch.setattr(
        cli_minimal, "first_run_memory_notice", lambda command, stream=None: seen.append(command)
    )
    monkeypatch.setattr(cli_minimal, "_dispatch_subcommand", lambda args, command: 0, raising=False)
    try:
        cli_minimal.main(["memory", "status"])
    except SystemExit:
        pass
    assert seen == ["memory"]


# --- attune setup prompt -----------------------------------------------------


def _tty_stdio(monkeypatch, answer: str | None) -> None:
    monkeypatch.setattr(uc.sys, "stdin", _Tty())
    monkeypatch.setattr(uc.sys, "stdout", _Tty())
    if answer is None:
        monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError()))
    else:
        monkeypatch.setattr("builtins.input", lambda prompt="": answer)


def test_setup_prompt_records_a_terminal_answer(monkeypatch) -> None:
    _tty_stdio(monkeypatch, "redis")
    uc._memory_backend_setup_prompt()
    out = uc.sys.stdout.getvalue()
    assert "Memory backend preference: redis" in out
    assert pref.get_backend_preference() == "redis"


def test_setup_prompt_defaults_to_auto_on_empty_answer(monkeypatch) -> None:
    _tty_stdio(monkeypatch, "")
    uc._memory_backend_setup_prompt()
    assert pref.get_backend_preference() == "auto" and pref.preference_recorded() is True


def test_setup_prompt_ignores_an_unknown_answer_and_eof(monkeypatch) -> None:
    _tty_stdio(monkeypatch, "cloud")
    uc._memory_backend_setup_prompt()
    assert "leaving it at auto" in uc.sys.stdout.getvalue()
    assert pref.preference_recorded() is False
    _tty_stdio(monkeypatch, None)
    uc._memory_backend_setup_prompt()
    assert pref.preference_recorded() is False


def test_setup_prompt_prints_pointer_off_a_tty(monkeypatch) -> None:
    monkeypatch.setattr(uc.sys, "stdin", io.StringIO())
    monkeypatch.setattr(uc.sys, "stdout", io.StringIO())
    uc._memory_backend_setup_prompt()
    out = uc.sys.stdout.getvalue()
    assert "Choose later with: attune memory use" in out
    assert pref.preference_recorded() is False


def test_setup_prompt_is_silent_once_chosen(monkeypatch) -> None:
    pref.set_backend_preference("file")
    _tty_stdio(monkeypatch, "redis")
    uc._memory_backend_setup_prompt()
    assert uc.sys.stdout.getvalue() == ""
    assert pref.get_backend_preference() == "file"


def test_setup_prompt_reports_an_unwritable_config(monkeypatch) -> None:
    _tty_stdio(monkeypatch, "file")
    monkeypatch.setattr(
        pref, "set_backend_preference", lambda v: (_ for _ in ()).throw(OSError("read-only"))
    )
    uc._memory_backend_setup_prompt()
    assert "Could not record the choice" in uc.sys.stdout.getvalue()
