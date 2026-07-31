"""Drift-guard tests for `PATH_ARG_REGISTRY`.

The registry maps workflow name → kwarg name the workflow's `execute()`
actually consumes. The ops runner uses it to rewrite the CLI's uniform
`--path` into whatever kwarg each workflow expects.

These tests catch drift in two directions:

1. **Coverage drift** — every workflow returned by the workflow registry
   has a `PATH_ARG_REGISTRY` entry. A new workflow added without a
   registry entry fails the suite.
2. **Kwarg drift** — every registry entry's kwarg name actually appears
   in the workflow source's `execute()` body. A silent rename in a
   workflow (e.g., `project_root` → `root_dir`) fails the suite.

Source: docs/specs/ops-runner-tier2/audit.md (Phase 1 audit) and
docs/specs/ops-runner-tier2/tasks.md task 1.3.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from attune.ops.data import PATH_ARG_REGISTRY, PathArgSpec


def _workflow_source(workflow_name: str) -> str:
    """Return the source of the workflow's class file.

    The CLI workflow registry exposes `name -> "module.path:ClassName"`.
    We import the class and read its module's source via `inspect`.
    """
    from attune.workflows import get_workflow

    cls = get_workflow(workflow_name)
    return inspect.getsource(inspect.getmodule(cls))


def _registered_workflow_names() -> list[str]:
    """Return the names every consumer sees from `list_workflows()`."""
    from attune.workflows import list_workflows

    return sorted(entry["name"] for entry in list_workflows())


# ---------------------------------------------------------------------------
# Coverage drift — every registered workflow has a registry entry
# ---------------------------------------------------------------------------


class TestRegistryCoverage:
    """Every workflow exposed via `attune workflow list` must appear in the registry."""

    def test_every_registered_workflow_has_a_registry_entry(self) -> None:
        registered = set(_registered_workflow_names())
        registry = set(PATH_ARG_REGISTRY)
        missing = registered - registry
        assert not missing, (
            f"Workflows missing PATH_ARG_REGISTRY entries: {sorted(missing)}. "
            "Add an entry per docs/specs/ops-runner-tier2/audit.md."
        )

    def test_no_orphan_registry_entries(self) -> None:
        registered = set(_registered_workflow_names())
        registry = set(PATH_ARG_REGISTRY)
        orphans = registry - registered
        assert not orphans, (
            f"PATH_ARG_REGISTRY entries with no matching workflow: "
            f"{sorted(orphans)}. Likely a renamed/retired workflow — "
            "remove the entry."
        )


# ---------------------------------------------------------------------------
# Kwarg drift — each entry's kwarg actually appears in the workflow source
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "workflow_name,spec",
    sorted(PATH_ARG_REGISTRY.items()),
    ids=sorted(PATH_ARG_REGISTRY),
)
class TestRegistryKwargMatchesSource:
    """Each registered kwarg must actually be consumed by the workflow source."""

    def test_kwarg_appears_in_execute_source(self, workflow_name: str, spec: PathArgSpec) -> None:
        source = _workflow_source(workflow_name)
        kwarg = spec.kwarg

        # Acceptable patterns:
        # - kwargs.get("<kwarg>"  / kwargs.pop("<kwarg>"  / kwargs["<kwarg>"]
        # - <kwarg>: <type>      (explicit signature parameter)
        # - <kwarg>=             (explicit keyword in a call)
        patterns = (
            f'kwargs.get("{kwarg}"',
            f'kwargs.pop("{kwarg}"',
            f'kwargs["{kwarg}"]',
            f"{kwarg}: str",
            f"{kwarg}: Path",
            f"{kwarg}=",
        )
        assert any(p in source for p in patterns), (
            f"PATH_ARG_REGISTRY claims {workflow_name!r} consumes "
            f"kwarg {kwarg!r}, but none of the expected source patterns "
            f"appear in the workflow's module. Patterns checked: "
            f"{patterns!r}. Either update the registry to match the "
            "workflow's actual kwarg name, or update the workflow to "
            "accept the registered name."
        )


# ---------------------------------------------------------------------------
# Sanity checks on the dataclass + categorization
# ---------------------------------------------------------------------------


class TestRegistryShape:
    """Spot-check the registry's invariants."""

    def test_required_only_set_when_actually_required(self) -> None:
        # test-audit's src_path is the only currently-required entry; the
        # audit established that. If a new required entry is added, this
        # test stays passing — it's a forward-reference, not a cap.
        required = {n for n, spec in PATH_ARG_REGISTRY.items() if spec.required}
        assert "test-audit" in required, (
            "test-audit's src_path is required (errors if missing). "
            "Registry must mark it required=True so the ops runner can "
            "block scope-less submissions."
        )

    def test_kwarg_values_are_known_names(self) -> None:
        # Defense against typos like "paht" or "Path". Add new kwarg
        # names here as legitimate workflow patterns expand.
        # `scope_paths` (outcome-first-fix Phase 2) is the first entry
        # where the path is an EDIT BOUNDARY rather than a scan root —
        # the workflow refuses to run without it.
        known = {"path", "project_root", "src_path", "cwd", "scope_paths"}
        used = {spec.kwarg for spec in PATH_ARG_REGISTRY.values()}
        unknown = used - known
        assert not unknown, (
            f"PATH_ARG_REGISTRY uses unrecognized kwarg names: "
            f"{sorted(unknown)}. If a new pattern is intentional, add "
            "it to the `known` set in this test."
        )

    def test_data_module_exports_registry(self) -> None:
        # Belt-and-suspenders: confirm the registry is reachable as
        # `from attune.ops.data import PATH_ARG_REGISTRY`. Catches the
        # accidental-rename failure mode where a downstream import
        # breaks silently.
        mod = importlib.import_module("attune.ops.data")
        assert hasattr(mod, "PATH_ARG_REGISTRY")
        assert hasattr(mod, "PathArgSpec")


# ---------------------------------------------------------------------------
# Documentation pointer — these tests are the contract for the audit
# ---------------------------------------------------------------------------


def test_audit_doc_exists() -> None:
    """The audit doc backing this registry should be in the repo."""
    repo_root = Path(__file__).resolve().parents[3]
    audit = repo_root / "docs" / "specs" / "archive" / "ops-runner-tier2" / "audit.md"
    assert audit.is_file(), (
        f"Expected audit doc at {audit} — it's the source of truth for "
        "PATH_ARG_REGISTRY's three-way categorization. If the audit is "
        "renamed, update this test's path."
    )
