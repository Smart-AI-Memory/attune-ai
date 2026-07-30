"""Contract tests for the ops package's lazy re-export layer.

``attune.ops`` deliberately avoids importing FastAPI at package
import (the dashboard deps are heavy); ``__main__`` is the
``python -m attune.ops`` entry. The contract: the lazy wrappers
delegate to the real factories with arguments intact, and the
``__main__`` module binds the real CLI entry point.
"""

from __future__ import annotations

import importlib

import attune.ops as ops_pkg


def test_main_module_binds_cli_entry() -> None:
    main_mod = importlib.import_module("attune.ops.__main__")
    from attune.ops.cli import main as cli_main

    assert main_mod.main is cli_main


def test_create_app_delegates_lazily(monkeypatch) -> None:
    import attune.ops.server as server_mod

    seen: list[tuple] = []
    monkeypatch.setattr(server_mod, "create_app", lambda *a, **k: seen.append((a, k)) or "APP")
    assert ops_pkg.create_app("cfg", flag=True) == "APP"
    assert seen == [(("cfg",), {"flag": True})]


def test_build_config_delegates_lazily(monkeypatch) -> None:
    import attune.ops.config as config_mod

    seen: list[tuple] = []
    monkeypatch.setattr(config_mod, "build_config", lambda *a, **k: seen.append((a, k)) or "CFG")
    assert ops_pkg.build_config(port=1234) == "CFG"
    assert seen == [((), {"port": 1234})]


def test_config_getattr_resolves_real_class() -> None:
    from attune.ops.config import Config as real_config

    assert ops_pkg.Config is real_config
