"""Shared fixtures/config for hook-script tests.

The hook scripts under ``src/attune/hooks/scripts/`` use sibling-relative
imports (``from _sdk_gate import ...``) inside their ``__main__`` block.
Tests that execute a script via ``runpy.run_path(..., run_name="__main__")``
trigger that import, but ``runpy.run_path`` on a file path does NOT add the
script's directory to ``sys.path`` — so ``_sdk_gate`` only resolves if some
earlier test happened to insert that directory. Inserting it here makes the
sibling import resolve regardless of test order (or running a single file in
isolation).
"""

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "hooks" / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
