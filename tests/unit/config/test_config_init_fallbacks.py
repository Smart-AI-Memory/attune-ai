"""Tests for attune.config's package-init fallback branches.

``attune/config/__init__.py`` loads the sibling ``config.py`` file via
``importlib.util.spec_from_file_location`` under a synthetic module name,
and separately guards the optional PyYAML import. Both branches only run
once, at first import, and the result is cached in ``sys.modules`` — so
exercising the failure paths (PyYAML missing; spec/loader resolution
failing) requires a fresh subprocess import rather than reloading the
already-imported module in-process.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


def _run(script: str) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in a fresh interpreter, inheriting this process's env.

    Inheriting the environment (rather than a hand-built one) preserves
    PYTHONPATH when this suite runs from a worktree whose editable install
    maps back to the main checkout (see the worktree-PYTHONPATH lesson in
    .claude/lessons.md) while still working unmodified in a normal install.
    """
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestYamlUnavailableFallback:
    """Lines 22-23: the `except ImportError` branch for optional PyYAML."""

    def test_yaml_missing_sets_yaml_available_false(self):
        """When `import yaml` raises, YAML_AVAILABLE lands False, not True."""
        script = (
            "import sys\n"
            "sys.modules['yaml'] = None\n"  # forces ImportError on `import yaml`
            "import attune.config as cfg\n"
            "assert cfg.YAML_AVAILABLE is False, cfg.YAML_AVAILABLE\n"
            "print('OK')\n"
        )
        result = _run(script)
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout


class TestLegacyConfigSpecLoadFailureFallback:
    """Lines 40-43: the `else` branch when spec/spec.loader resolution fails."""

    def test_spec_load_failure_falls_back_to_none(self):
        """A None spec (as if config.py couldn't be located) degrades every
        re-exported legacy symbol to None instead of raising at import time.
        """
        script = (
            "import importlib.util\n"
            "_orig = importlib.util.spec_from_file_location\n"
            "def _patched(name, *args, **kwargs):\n"
            "    if name == 'attune_config_legacy':\n"
            "        return None\n"
            "    return _orig(name, *args, **kwargs)\n"
            "importlib.util.spec_from_file_location = _patched\n"
            "import attune.config as cfg\n"
            "assert cfg.AttuneConfig is None, cfg.AttuneConfig\n"
            "assert cfg.EmpathyConfig is None, cfg.EmpathyConfig\n"
            "assert cfg.load_config is None, cfg.load_config\n"
            "assert cfg.resolve_show_cost is None, cfg.resolve_show_cost\n"
            "print('OK')\n"
        )
        result = _run(script)
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout

    def test_spec_loader_none_falls_back_to_none(self):
        """A spec whose `.loader` is None (unloadable spec) hits the same
        fallback as a wholly-missing spec.
        """
        script = (
            "import importlib.util\n"
            "_orig = importlib.util.spec_from_file_location\n"
            "def _patched(name, *args, **kwargs):\n"
            "    spec = _orig(name, *args, **kwargs)\n"
            "    if name == 'attune_config_legacy' and spec is not None:\n"
            "        spec.loader = None\n"
            "    return spec\n"
            "importlib.util.spec_from_file_location = _patched\n"
            "import attune.config as cfg\n"
            "assert cfg.AttuneConfig is None, cfg.AttuneConfig\n"
            "assert cfg.EmpathyConfig is None, cfg.EmpathyConfig\n"
            "assert cfg.load_config is None, cfg.load_config\n"
            "assert cfg.resolve_show_cost is None, cfg.resolve_show_cost\n"
            "print('OK')\n"
        )
        result = _run(script)
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
