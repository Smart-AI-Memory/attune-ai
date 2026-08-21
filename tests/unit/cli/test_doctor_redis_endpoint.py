"""``attune doctor`` must report on the CONFIGURED Redis, not localhost.

Class H1 — the split-brain reachability oracle — in the one command whose
whole job is telling the truth about the environment. ``redis.Redis()``
with no host/port silently defaults to ``localhost:6379`` regardless of
``REDIS_URL``, so doctor used to answer about a server the user does not
run. Observed live on 2026-08-21: with ``REDIS_URL`` naming a reachable
server, the old probe dialled 6379, hit an ``AuthenticationError`` there,
and reported "Redis server not reachable" while the real client was
connected and working.

These tests use a REAL listening socket speaking REAL RESP
(``tests/support/redis_stub.RespStub``), never a patched client — per the
class-M ruling, a test that mocks the connection cannot see a defect
about *which endpoint gets dialled*.

**Why two directions.** Each is decisive in the environment the other is
blind to, and together they cover both:

- ``test_reports_reachable_for_configured_endpoint`` fails against
  pre-fix source on any machine with nothing on 6379 (probe finds
  nothing, reports unreachable, while the configured stub is up).
- ``test_reports_unreachable_for_configured_dead_endpoint`` fails against
  pre-fix source on any machine that DOES have Redis on 6379 (probe finds
  it, reports reachable, while the configured endpoint is dead).

Neither alone is a receipt; the pair is.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from attune.cli_commands.utility_commands import cmd_doctor  # noqa: E402
from tests.support.redis_stub import RespStub, closed_port  # noqa: E402

#: Every env var that can redirect the resolver, cleared so the test's own
#: REDIS_URL is the only input. A stray ATTUNE_REDIS_URL on a developer
#: machine would otherwise silently decide the outcome.
_REDIS_ENV = (
    "REDIS_URL",
    "ATTUNE_REDIS_URL",
    "REDIS_PASSWORD",
    "ATTUNE_REDIS_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
)


def _run_doctor(monkeypatch: pytest.MonkeyPatch, url: str, capsys) -> str:
    for name in _REDIS_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REDIS_URL", url)
    cmd_doctor(Namespace())
    return capsys.readouterr().out


def _redis_line(output: str) -> str:
    for line in output.splitlines():
        if "Redis server" in line:
            return line
    return ""


def test_reports_reachable_for_configured_endpoint(monkeypatch, capsys) -> None:
    """A live server at the CONFIGURED endpoint must read as reachable."""
    stub = RespStub()
    try:
        out = _run_doctor(monkeypatch, f"redis://127.0.0.1:{stub.port}/0", capsys)
    finally:
        stub.close()

    line = _redis_line(out)
    assert line, f"doctor printed no Redis line:\n{out}"
    assert "not reachable" not in line, (
        "doctor reported the CONFIGURED endpoint unreachable while a real "
        f"server was answering PING on it (class H1):\n  {line}"
    )


def test_reports_unreachable_for_configured_dead_endpoint(monkeypatch, capsys) -> None:
    """A dead CONFIGURED endpoint must not be masked by a live localhost."""
    dead = closed_port()
    out = _run_doctor(monkeypatch, f"redis://127.0.0.1:{dead}/0", capsys)

    line = _redis_line(out)
    assert line, f"doctor printed no Redis line:\n{out}"
    assert "not reachable" in line, (
        "doctor reported Redis reachable while the CONFIGURED endpoint had "
        "nothing listening — it dialled some other server (class H1):\n"
        f"  {line}"
    )


def test_reachable_line_names_the_endpoint_it_probed(monkeypatch, capsys) -> None:
    """The success line must say WHICH endpoint answered.

    A bare "Redis server reachable" is what let the split brain hide: the
    user cannot tell which server the answer is about. The URL is printed
    redacted, so a password in REDIS_URL never reaches the terminal.
    """
    stub = RespStub()
    try:
        out = _run_doctor(monkeypatch, f"redis://127.0.0.1:{stub.port}/0", capsys)
    finally:
        stub.close()

    line = _redis_line(out)
    assert str(stub.port) in line, f"success line does not name the probed endpoint:\n  {line}"


def test_password_in_redis_url_is_not_printed(monkeypatch, capsys) -> None:
    """Printing the endpoint must not leak the password with it."""
    stub = RespStub()
    try:
        out = _run_doctor(monkeypatch, f"redis://user:sup3rsecret@127.0.0.1:{stub.port}/0", capsys)
    finally:
        stub.close()

    assert "sup3rsecret" not in out, "doctor leaked the Redis password to stdout"
