"""Regression guard: the base CLI must import without the `[ops]` extra.

A default ``pip install attune-ai`` does NOT install the `[ops]` extra
(fastapi / uvicorn / jinja2). The base ``attune`` CLI must therefore
import and run without fastapi present.

This regressed silently before 8.6.0: ``attune.cli_minimal`` ->
``attune.cli_commands.curator`` -> ``attune.curator.sources.specs``
imported ``SpecRecord`` / ``_list_specs_in_root`` from the FastAPI web
route module ``attune.ops.routes.specs``, so ``attune --help`` crashed
with ``ModuleNotFoundError: No module named 'fastapi'`` on every default
install. CI never caught it because CI always installs the dev/ops
extras (fastapi is present), so the pure unit suite imported fine.

The fix moved the pure spec-listing data layer to the framework-free
``attune.ops.specs_data`` module. These tests simulate the
no-``[ops]``-extra environment by blocking ``fastapi`` at import time in
a subprocess (a subprocess so the block can't leak into the rest of the
suite, where fastapi is legitimately installed).
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

# Imports that MUST succeed in a default (no-[ops]) install.
_BASE_IMPORTS = (
    "import attune.cli_minimal",
    "import attune.curator.sources.specs",
    "from attune.ops.specs_data import SpecRecord, _list_specs_in_root",
)

_BLOCK_FASTAPI = """
import sys, importlib.abc

class _FastapiBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == "fastapi" or name.startswith("fastapi."):
            raise ModuleNotFoundError("No module named 'fastapi' (simulated no-[ops] install)")
        return None

sys.meta_path.insert(0, _FastapiBlocker())
"""


def _run_with_fastapi_blocked(body: str) -> subprocess.CompletedProcess:
    code = textwrap.dedent(_BLOCK_FASTAPI) + body + '\nprint("IMPORT_OK")\n'
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )


def test_fastapi_is_actually_blocked() -> None:
    """Sanity-check the blocker: `import fastapi` must fail under it."""
    result = _run_with_fastapi_blocked("import fastapi")
    assert result.returncode != 0
    assert "fastapi" in result.stderr


def test_base_cli_imports_without_fastapi() -> None:
    """`attune.cli_minimal` and the curator spec source import with no fastapi."""
    result = _run_with_fastapi_blocked("\n".join(_BASE_IMPORTS))
    assert result.returncode == 0, (
        "The base CLI failed to import without the [ops] extra (fastapi). "
        "A base-CLI import path is pulling in fastapi again.\n\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout


def test_specs_data_is_framework_free() -> None:
    """attune.ops.specs_data must not transitively import fastapi."""
    result = _run_with_fastapi_blocked(
        "from attune.ops import specs_data\n"
        "r = specs_data._resolved_roots(type('C', (), {'specs_roots': (), 'project_root': __import__('pathlib').Path('.')})())\n"
        "assert isinstance(r, list)"
    )
    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout
