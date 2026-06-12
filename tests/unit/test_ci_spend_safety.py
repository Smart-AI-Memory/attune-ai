"""Spend-safety guard: per-push/PR CI must never pass a live ANTHROPIC_API_KEY.

On 2026-06-10 a CI secret going live burned ~$1200 in ~6h: a per-push workflow
passed ``secrets.ANTHROPIC_API_KEY`` to a 12-lane matrix and mismarked tests
then made real API calls at CI scale. This test turns that incident into an
enforceable guard — any workflow triggered by ``push`` or ``pull_request``
must set ``ANTHROPIC_API_KEY`` to ``""`` (keyless). The live secret is allowed
ONLY in deliberately-triggered (schedule / workflow_dispatch), budget-capped
workflows such as ``integration-auth.yml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_WF_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"
_WORKFLOWS = sorted({*_WF_DIR.glob("*.yml"), *_WF_DIR.glob("*.yaml")})


def _triggers(parsed: dict) -> set[str]:
    """The set of trigger names. PyYAML parses ``on:`` as the bool True (YAML
    1.1), so look under both ``"on"`` and ``True``."""
    on = parsed.get("on")
    if on is None:
        on = parsed.get(True)
    if on is None:
        return set()
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {str(x) for x in on}
    if isinstance(on, dict):
        return {str(k) for k in on}
    return set()


def _anthropic_key_values(node: object) -> list[str]:
    """Every value assigned to an ``ANTHROPIC_API_KEY`` key, recursively."""
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "ANTHROPIC_API_KEY" and isinstance(value, str):
                out.append(value)
            else:
                out.extend(_anthropic_key_values(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_anthropic_key_values(item))
    return out


def test_workflows_dir_found():
    """Guard against path drift silently matching zero workflows."""
    assert _WORKFLOWS, f"no workflow files under {_WF_DIR}"


@pytest.mark.parametrize("wf", _WORKFLOWS, ids=lambda p: p.name)
def test_per_push_workflow_is_keyless(wf):
    parsed = yaml.safe_load(wf.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        pytest.skip("workflow is not a mapping")

    if not ({"push", "pull_request"} & _triggers(parsed)):
        return  # deliberately-triggered workflows may use the real secret

    for value in _anthropic_key_values(parsed):
        assert "secrets." not in value, (
            f"{wf.name} is push/pull_request-triggered but passes a live "
            f'ANTHROPIC_API_KEY ({value!r}). It must be "" (keyless) — the '
            f"real secret belongs only in schedule/dispatch-only workflows. "
            f"See the 2026-06-10 ~$1200 CI-spend incident."
        )
