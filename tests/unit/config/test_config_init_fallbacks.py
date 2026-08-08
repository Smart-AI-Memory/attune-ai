"""Tests for attune.config's optional-PyYAML import fallback.

``attune/config/legacy.py`` guards the optional PyYAML import and
exposes ``YAML_AVAILABLE``, which the package ``__init__`` re-exports.
The branch only runs once, at first import, and the result is cached in
``sys.modules`` — so exercising the failure path (PyYAML missing)
requires a fresh subprocess import. Reloading the already-imported
module in-process is NOT an option: ``importlib.reload`` mutates the
legacy module's dict in place, silently repointing the globals of
functions other test modules imported earlier (isinstance breakage at
a distance).

(The spec/loader-failure fallback tests that used to live here were
retired when the synthetic ``spec_from_file_location`` loader was
replaced by a normal ``attune.config.legacy`` submodule import — see
tests/unit/config/test_legacy_module_identity.py for the regression
guard on that change.)
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
    """The `except ImportError` branch for optional PyYAML."""

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
