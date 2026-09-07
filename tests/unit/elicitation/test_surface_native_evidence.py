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
