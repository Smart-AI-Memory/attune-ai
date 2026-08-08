"""Tests for the ``attune.memory.short_term`` package-init redis fallback.

The package ``__init__`` re-exports the ``redis`` module for test-patching
compatibility, degrading to ``None`` when redis is not installed. That
``except ImportError`` branch only runs at (re)import time, so these tests
reload the package in-process — which, unlike a subprocess import, is
visible to coverage measurement.
"""

from __future__ import annotations

import importlib
import sys

import pytest

import attune.memory.short_term as short_term

pytestmark = pytest.mark.unit


class TestRedisImportFallback:
    """The `except ImportError: redis = None` branch in __init__.py."""

    def test_redis_missing_degrades_to_none(self):
        """Blocking `import redis` leaves the re-export as None, not an error."""
        real = sys.modules.get("redis")
        sys.modules["redis"] = None  # forces ImportError on `import redis`
        try:
            importlib.reload(short_term)
            assert short_term.redis is None
        finally:
            if real is not None:
                sys.modules["redis"] = real
            else:
                sys.modules.pop("redis", None)
            importlib.reload(short_term)
        # Restored state must match the environment again.
        if real is not None:
            assert short_term.redis is real

    def test_all_exports_resolve_after_reload(self):
        """Every name in __all__ is importable — the facade wiring is intact."""
        for name in short_term.__all__:
            assert getattr(short_term, name, None) is not None, name
