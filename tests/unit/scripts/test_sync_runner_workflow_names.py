"""Tests for scripts/sync_runner_workflow_names.py.

Conversion 2 of drift-guards-to-generators: the ops dashboard's
``WORKFLOW_NAMES`` JS array is generated from
``attune.ops.data.list_workflows()`` rather than hand-edited.

Covers the generator logic in isolation (monkeypatching the canonical
source so these stay fast and free of the [ops] extra):
- ``render_block`` shape — markers, 4-per-line, no trailing comma;
- ``apply`` idempotency — a freshly generated file checks clean;
- ``apply`` drift detection — an out-of-sync array fails ``--check``
  and is rewritten in write mode;
- missing markers abort with exit 1.

Loads the script via importlib (matches the existing scripts-test
pattern).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_runner_workflow_names.py"

NAMES = ["alpha", "bravo", "charlie", "delta", "echo"]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_sync_runner_wf", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_sync_runner_wf"] = m
    try:
        spec.loader.exec_module(m)
        yield m
    finally:
        sys.modules.pop("_sync_runner_wf", None)


def _runner_stub(block: str) -> str:
    """Wrap a generated block in minimal surrounding JS."""
    return f"(function () {{\n{block}\n  var OTHER = 1;\n}})();\n"


def test_render_block_shape(mod):
    block = mod.render_block(NAMES)
    assert block.startswith(mod.BEGIN)
    assert block.rstrip().endswith(mod.END)
    assert "var WORKFLOW_NAMES = [" in block
    # All names present, quoted.
    for n in NAMES:
        assert f'"{n}"' in block
    # No trailing comma on the final entry (clean JS).
    assert '"echo",' not in block
    assert '"echo"' in block


def test_render_block_four_per_line(mod):
    block = mod.render_block(NAMES)
    array_lines = [ln for ln in block.splitlines() if ln.strip().startswith('"')]
    # 5 names at 4 per line → first row has 4, second has 1.
    assert array_lines[0].count('"') == 8  # 4 names × 2 quotes
    assert array_lines[1].count('"') == 2  # 1 name × 2 quotes


def test_apply_idempotent_when_in_sync(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_canonical_names", lambda: NAMES)
    runner = tmp_path / "runner.js"
    runner.write_text(_runner_stub(mod.render_block(NAMES)), encoding="utf-8")
    assert mod.apply(runner, check=True) == 0
    assert mod.apply(runner, check=False) == 0  # nothing to rewrite


def test_apply_detects_and_rewrites_drift(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_canonical_names", lambda: NAMES)
    runner = tmp_path / "runner.js"
    # Seed with a stale block (missing "echo").
    stale = mod.render_block(NAMES[:-1])
    runner.write_text(_runner_stub(stale), encoding="utf-8")

    # --check fails on drift.
    assert mod.apply(runner, check=True) == 1
    # Write mode repairs it.
    assert mod.apply(runner, check=False) == 0
    # Now in sync.
    assert mod.apply(runner, check=True) == 0
    assert '"echo"' in runner.read_text(encoding="utf-8")


def test_apply_missing_markers_aborts(mod, tmp_path):
    runner = tmp_path / "runner.js"
    runner.write_text("(function () {\n  var WORKFLOW_NAMES = [];\n})();\n", encoding="utf-8")
    assert mod.apply(runner, check=True) == 1
    assert mod.apply(runner, check=False) == 1
