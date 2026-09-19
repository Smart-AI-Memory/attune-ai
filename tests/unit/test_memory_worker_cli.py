"""Optional worker routing retains legacy CLI paths and avoids global notices."""

import builtins
import json

import pytest

from attune import cli_minimal
from attune.cli_commands.memory_worker import cmd_memory_worker


def test_existing_memory_verbs_and_worker_parser_remain():
    parser = cli_minimal.create_parser()
    assert parser.parse_args(["memory", "recall", "Aurora"]).memory_command == "recall"
    assert parser.parse_args(["memory", "status"]).memory_command == "status"
    assert parser.parse_args(["memory", "worker"]).memory_command == "worker"
    assert parser.parse_args(["memory-agent", "help"]).command == "memory-agent"


@pytest.mark.parametrize("prefix", [[], ["--verbose"], ["-v"]])
def test_worker_dispatch_is_lazy_and_bypasses_legacy_notices(monkeypatch, prefix):
    from attune.cli_commands import memory_worker

    received = []
    monkeypatch.setattr(memory_worker, "cmd_memory_worker", lambda argv: received.append(argv) or 7)
    monkeypatch.setattr(
        cli_minimal, "first_run_memory_notice", lambda *a: pytest.fail("legacy notice")
    )
    assert cli_minimal.main(prefix + ["memory", "worker", "--help"]) == 7
    assert received == [["--help"]]


def test_missing_optional_package_is_truthful_and_still_suppresses_usage(monkeypatch, capsys):
    original = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name.startswith("attune_harness"):
            raise ImportError("synthetic absence")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    monkeypatch.setenv("ATTUNE_USAGE_PING", "1")
    assert cmd_memory_worker(["--help"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable"
    from attune.telemetry.usage_ping import is_enabled

    assert not is_enabled(True)
    assert cli_minimal.create_parser().parse_args(["memory", "status"]).memory_command == "status"


def test_disabled_worker_is_separate_from_existing_memory(monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_MEMORY_WORKER", "0")
    assert cli_minimal.main(["memory", "worker"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "disabled"
    assert cli_minimal.create_parser().parse_args(["memory", "topics"]).memory_command == "topics"
