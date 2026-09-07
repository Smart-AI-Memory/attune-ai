"""Mutation checks that reject misleading native receipts after real SDK exchanges."""

import pytest

from attune.elicitation import surface_native_evidence as native
from attune.elicitation.surface_registry import SurfaceRegistryError


@pytest.mark.parametrize(
    "case, corruption, message",
    [
        ("accept", "responses", "validated answers changed"),
        ("accept", "provenance", "provenance lost"),
        ("accept", "renderer_count", "projection count changed"),
        ("abort", "action", "cancel did not abort"),
        ("timeout", "error", "timeout created receipt"),
    ],
)
async def test_corrupt_completion_cannot_be_published_as_native_evidence(
    monkeypatch, case, corruption, message
):
    original = native._present_native

    async def corrupt(*args, **kwargs):
        result = await original(*args, **kwargs)
        if corruption == "responses":
            result["completion"]["responses"] = {}
        elif corruption == "provenance":
            result["completion"]["provenance_status"] = "unverified"
        elif corruption == "renderer_count":
            result["decision_summary"]["renderer_attempt_count"] = 2
        elif corruption == "action":
            result["completion"]["action"] = "accept"
        else:
            result["error"] = "wrong_disposition"
        return result

    monkeypatch.setattr(native, "_present_native", corrupt)
    with pytest.raises(SurfaceRegistryError, match=message):
        await native._exchange(case)


@pytest.mark.parametrize(
    "case, affected_keys",
    [
        (
            "accept",
            {
                "route:surface-runtime-route-form:mcp-native:surface-native-elicitation:production_projection",
                "lifecycle:subject:surface-runtime-route-form:accept",
            },
        ),
        ("abort", {"lifecycle:subject:surface-native-elicitation:abort"}),
        ("timeout", {"lifecycle:subject:surface-native-elicitation:timeout"}),
        (
            "feedback",
            {"lifecycle:subject:surface-native-elicitation:validation_feedback_delivery"},
        ),
    ],
)
async def test_receipt_assembly_binds_each_observation_only_to_its_obligations(
    monkeypatch, case, affected_keys
):
    """Synthetic observations test assembly, never authorize a production route."""
    from attune.elicitation.surface_bootstrap import packaged_inventory

    registry, _ = packaged_inventory()
    observations = {
        name: {"fixture_revision": 0} for name in ("accept", "abort", "timeout", "feedback")
    }
    calls = []

    async def exchange(name):
        calls.append(name)
        return observations[name]

    monkeypatch.setattr(native, "_exchange", exchange)
    before, _ = await native.replay_native_evidence(registry)
    observations[case] = {"fixture_revision": 1}
    after, evidence = await native.replay_native_evidence(registry)

    assert calls == ["accept", "abort", "timeout", "feedback"] * 2
    prior = {row["key"]: row for row in before}
    current = {row["key"]: row for row in after}
    assert len(prior) == len(current) == 5
    assert {key for key in current if current[key] != prior[key]} == affected_keys
    for key in affected_keys:
        old = dict(prior[key])
        new = dict(current[key])
        old_result_digest = old.pop("result_digest")
        new_result_digest = new.pop("result_digest")
        assert old_result_digest != new_result_digest
        assert old == new  # Source, implementation, normalization and owner bindings are stable.
        assert evidence[current[key]["id"]]["result_digest"] == current[key]["result_digest"]
