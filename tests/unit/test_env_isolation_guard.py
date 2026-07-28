"""Drift guard: the suite must be hermetic against ambient ``ATTUNE_*``.

Companion to ``tests/conftest.py``'s ``_scrub_attune_env_at_import`` and
``_scrub_attune_env``. Origin (2026-07-28): a clean-run routine fired
from a shell exporting ``ATTUNE_MAX_BUDGET_USD=10.00`` reported
``keyless-unit-suite: FAIL`` on a healthy tree, and the round-table
seats then reasoned correctly from that poisoned brief to "the tree is
not healthy". A sweep with every value-override var set failed 22 tests
across 6 files. CI exports none of these, so CI can never catch a
regression here — that is exactly why this guard exists.
"""

import os
import subprocess
import sys
from pathlib import Path

from tests.conftest import _SUITE_MANAGED_ENV


def test_no_ambient_attune_overrides_visible_to_tests():
    """No ``ATTUNE_*`` override reaches a test except the suite-managed ones."""
    leaked = {k for k in os.environ if k.startswith("ATTUNE_")} - set(_SUITE_MANAGED_ENV)
    assert not leaked, (
        f"ambient ATTUNE_* overrides leaked into the suite: {sorted(leaked)}. "
        "conftest's scrub should have removed them; a developer shell "
        "exporting these would turn a healthy tree red."
    )


def test_suite_managed_vars_survive_the_scrub():
    """The scrub must NOT eat the vars other autouse fixtures own.

    Scrubbing ``ATTUNE_HOME`` pointed the default telemetry store at the
    developer's real ``~/.attune`` and tripped the RC-4 isolation drift
    guard — the exclusion set is load-bearing, not decorative.
    """
    assert os.environ.get("ATTUNE_HOME"), "ATTUNE_HOME must stay set by its fixture"
    assert "ATTUNE_HOME" in _SUITE_MANAGED_ENV


def test_import_time_override_does_not_reach_module_constants():
    """An exported override must not survive into import-time constants.

    ``release_models.MODEL_CONFIG`` resolves the premium tier at IMPORT
    time and ``base_agent`` binds that dict, so a per-test fixture is too
    late — the scrub has to run before the first ``attune`` import. This
    spawns a real subprocess with the override set, which is the only way
    to prove the ordering holds.
    """
    env = {**os.environ, "ATTUNE_MODEL_PREMIUM": "claude-opus-5", "ANTHROPIC_API_KEY": ""}
    # Absolute node id + explicit cwd: lanes do not all invoke pytest from
    # the repo root (the coverage job notably does not), and a relative
    # path would make this guard fail for the wrong reason.
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "tests" / "unit" / "agents" / "release" / "test_release_models.py"
    node_id = f"{target}::TestModuleConstants::test_model_config_uses_current_model_ids"
    proc = subprocess.run(  # nosec B603 — fixed argv, shell=False
        [sys.executable, "-m", "pytest", node_id, "-q", "--no-header", "-o", "addopts="],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo_root),
        timeout=300,
    )
    assert proc.returncode == 0, (
        "an exported ATTUNE_MODEL_PREMIUM reached an import-time constant — "
        f"conftest's import-time scrub regressed.\n{proc.stdout[-2000:]}"
    )
