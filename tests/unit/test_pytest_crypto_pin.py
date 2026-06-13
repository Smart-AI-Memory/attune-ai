"""Behavioral tests for the ``attune._pytest_crypto_pin`` pytest plugin.

The plugin imports ``cryptography`` once at startup so serial
``pytest --cov=attune.memory.*`` runs don't re-init the PyO3 ``_rust``
extension and disable encryption (see the module for the full writeup).
Its observable contract is a side effect at import time: cryptography is
loaded (when available) and the import never raises.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.unit
def test_pin_loads_cryptography() -> None:
    """Importing the plugin leaves cryptography's PyO3 core loaded.

    Reloading re-runs the module body; cryptography is already cached so
    this is a no-op dict lookup (no PyO3 re-init). After it runs, the
    ``_rust`` extension must be present in ``sys.modules``.
    """
    mod = importlib.import_module("attune._pytest_crypto_pin")
    importlib.reload(mod)

    assert "cryptography.hazmat.bindings._rust" in sys.modules


@pytest.mark.unit
def test_pin_is_best_effort_when_cryptography_unavailable(monkeypatch) -> None:
    """The import guard swallows ImportError when cryptography is absent.

    Simulate a missing dependency with the ``sys.modules[name] = None``
    sentinel (which makes ``import name`` raise ImportError) and confirm
    reloading the plugin does not propagate the error.
    """
    monkeypatch.setitem(sys.modules, "cryptography.exceptions", None)

    mod = importlib.import_module("attune._pytest_crypto_pin")
    # Must not raise even though `import cryptography.exceptions` fails.
    importlib.reload(mod)
