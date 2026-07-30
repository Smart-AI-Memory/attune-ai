"""Contract test for the cli_meta_workflows backward-compat shim.

The module exists only to re-export the cli_commands package's
public surface under the legacy import path. The contract: every
name in ``__all__`` resolves, and each is the SAME object the
package exports — a drifted or dropped re-export would silently
break legacy imports.
"""

from __future__ import annotations

from attune.meta_workflows import cli_commands, cli_meta_workflows


def test_all_reexports_resolve_to_package_objects() -> None:
    assert cli_meta_workflows.__all__  # non-empty by contract
    for name in cli_meta_workflows.__all__:
        shim_obj = getattr(cli_meta_workflows, name)
        assert shim_obj is getattr(cli_commands, name), name


def test_typer_app_is_exported() -> None:
    assert "meta_workflow_app" in cli_meta_workflows.__all__
