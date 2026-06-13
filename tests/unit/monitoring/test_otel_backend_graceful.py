"""Regression tests for OTELBackend graceful degradation without [otel] extra.

These tests deliberately have NO module-level skip on opentelemetry — the bug
they guard against (PR #837) manifests precisely in environments WITHOUT the
optional opentelemetry packages installed, which is exactly where the rest of
test_otel_backend.py is skipped. They simulate the missing dependency by making
importlib.util.find_spec raise ModuleNotFoundError, the way it does when a
submodule's parent package is absent.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import importlib.util
from unittest.mock import patch

import pytest

from attune.monitoring.otel_backend import OTELBackend


@pytest.mark.unit
class TestOTELBackendGracefulDegradation:
    """OTELBackend must construct without crashing when [otel] is absent."""

    def test_construct_does_not_raise_when_find_spec_raises_module_not_found(self):
        """Constructor degrades gracefully when find_spec raises ModuleNotFoundError.

        importlib.util.find_spec("opentelemetry.trace") raises (not returns None)
        when the parent 'opentelemetry' package is not installed, because it
        imports the parent to read its __path__. _check_otel_installed must
        catch this and report False rather than letting __init__ crash.
        """
        with patch.object(
            importlib.util,
            "find_spec",
            side_effect=ModuleNotFoundError("No module named 'opentelemetry'"),
        ):
            backend = OTELBackend(endpoint="http://x:4317")

        assert backend.is_available() is False
        assert backend._otel_available is False

    def test_construct_does_not_raise_when_find_spec_raises_value_error(self):
        """find_spec can also raise ValueError (e.g. for malformed module names)."""
        with patch.object(
            importlib.util,
            "find_spec",
            side_effect=ValueError("bad module spec"),
        ):
            backend = OTELBackend(endpoint="http://x:4317")

        assert backend.is_available() is False
        assert backend._otel_available is False

    def test_check_otel_installed_returns_false_when_dependency_missing(self):
        """_check_otel_installed returns False instead of propagating the error."""
        backend = OTELBackend.__new__(OTELBackend)  # skip __init__

        with patch.object(
            importlib.util,
            "find_spec",
            side_effect=ModuleNotFoundError("No module named 'opentelemetry'"),
        ):
            assert backend._check_otel_installed() is False
