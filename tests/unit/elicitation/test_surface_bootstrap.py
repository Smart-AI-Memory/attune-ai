"""Executed bootstrap evidence and mutations that must prevent activation."""

import copy
import os
from pathlib import Path

import pytest

from attune.elicitation import surface_bootstrap as bootstrap
from attune.elicitation import surface_native_evidence as native
from attune.elicitation.surface_registry import (
    SurfaceRegistryError,
    canonical_digest,
    route_evidence_missing,
)
from attune.elicitation.surface_runtime import NATIVE_ROUTE


async def test_packaged_evidence_enables_only_the_receipted_route(tmp_path):
    if os.name != "posix":
        pytest.skip("private key storage awaits Windows adapter")
    runtime = await bootstrap.create_surface_runtime(tmp_path)
    assert not route_evidence_missing(
        runtime._registry, runtime._report, native.SUBJECT_ID, NATIVE_ROUTE
    )
    assert route_evidence_missing(runtime._registry, runtime._report, native.SUBJECT_ID, "RICH")
    assert not runtime._report.complete
    assert len(runtime._report.pending_keys) == 159
    assert (tmp_path / "surface-auth/receipt.key").is_file()
    assert not runtime.store._records  # Canonical fixture state never enters production.


@pytest.mark.parametrize("mutation", ["implementation", "result", "mapping", "missing"])
async def test_changed_or_missing_native_evidence_never_creates_key(
    tmp_path, monkeypatch, mutation
):
    registry, baseline = bootstrap.packaged_inventory()
    registry = copy.deepcopy(registry)
    row = next(r for r in registry["receipts"] if r["key"].startswith("route:surface-runtime"))
    if mutation in {"implementation", "result"}:
        row[f"{mutation}_digest"] = "0" * 64
    elif mutation == "mapping":
        owner = next(s for s in registry["subjects"] if s["id"] == native.SUBJECT_ID)
        owner["route_projection_targets"][NATIVE_ROUTE] = "rich"
    else:
        registry["receipts"].remove(row)
        registry["pending_obligations"].append(
            {"key": row["key"], "owner": "fixture", "reason": "missing", "next_increment": 3}
        )
    monkeypatch.setattr(bootstrap, "packaged_inventory", lambda: (registry, baseline))
    with pytest.raises(SurfaceRegistryError):
        await bootstrap.create_surface_runtime(tmp_path)
    assert not (tmp_path / "surface-auth").exists()


async def test_executable_semantic_regression_invalidates_receipt(monkeypatch):
    import attune.elicitation.surface_runtime as runtime_module

    original = runtime_module.form_to_elicitation_schema

    def broken(form):
        schema = original(form)
        schema["properties"]["minutes"]["maximum"] = 121
        return schema

    monkeypatch.setattr(runtime_module, "form_to_elicitation_schema", broken)
    with pytest.raises(SurfaceRegistryError, match="range changed"):
        await native._exchange("accept")


async def test_replayed_receipts_are_stable_and_bind_current_mapping():
    registry, _ = bootstrap.packaged_inventory()
    rows, first = await native.replay_native_evidence(registry)
    _, second = await native.replay_native_evidence(registry)
    assert first == second
    assert len(rows) == 5
    owner = next(s for s in registry["subjects"] if s["id"] == native.SUBJECT_ID)
    owner["route_projection_targets"]["PORTABLE"] = "headless"
    with pytest.raises(SurfaceRegistryError, match="wrong projection surface"):
        await native.replay_native_evidence(registry)


def test_runtime_package_files_are_exact_source_projections():
    root = Path(__file__).resolve().parents[3]
    registry, baseline = bootstrap.packaged_inventory()
    import json

    for name, projected in (
        ("parity-registry.json", registry),
        ("producer_baseline.json", baseline),
    ):
        source = json.loads((root / "docs/specs/host-surface-parity" / name).read_text())
        assert canonical_digest(projected) == canonical_digest(source)


async def test_native_evidence_leaves_no_callback_tasks():
    import asyncio

    before = set(asyncio.all_tasks())
    await native._exchange("timeout")
    await native._exchange("feedback")
    await asyncio.sleep(0)
    assert set(asyncio.all_tasks()) <= before


@pytest.mark.parametrize(
    "failure", [KeyError("missing"), AttributeError("changed API"), ValueError("stale evidence")]
)
async def test_stdio_bootstrap_failure_keeps_server_available(tmp_path, monkeypatch, failure):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    import attune.mcp.server as server

    app = SimpleNamespace(_surface_runtime=None)
    called = []

    async def failed(home):
        raise failure

    @asynccontextmanager
    async def streams():
        yield None, None

    async def run(*args):
        called.append(True)

    monkeypatch.setattr(bootstrap, "create_surface_runtime", failed)
    monkeypatch.setattr(server, "_app", app)
    monkeypatch.setattr(server, "stdio_server", streams)
    monkeypatch.setattr(server._mcp_server, "run", run)
    await server._run_stdio()
    assert called == [True]
    assert app._surface_runtime is None


async def test_bootstrap_normalizes_sdk_schema_failure(tmp_path, monkeypatch):
    from jsonschema.exceptions import ValidationError

    def failed():
        raise ValidationError("fixture schema failure")

    monkeypatch.setattr(bootstrap, "replay_renderer_evidence", failed)
    with pytest.raises(SurfaceRegistryError, match="native evidence execution failed"):
        await bootstrap.create_surface_runtime(tmp_path)
    assert not (tmp_path / "surface-auth").exists()
