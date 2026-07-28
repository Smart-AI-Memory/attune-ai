"""CI spend guard — the real Anthropic key never rides per-push/PR CI.

History: on 2026-06-10 the repo's dead ``ANTHROPIC_API_KEY`` secret was
replaced with a live one, and ``tests.yml`` — which passed the secret to
every push/PR run x 12 matrix lanes — burned ~$1,200 in ~6 hours.
Mismarked key-gated tests, real-SDK spawners, and keyed summary paths
all make real API calls the moment a valid key appears. The workflow
config had been "safe" for weeks only because the key was dead.

The fix (keyless per-push CI) is currently held by convention — YAML
comments and a lesson in ``.claude/lessons.md``. This module makes it
structural: a NEW workflow that references the real secret fails these
tests unless it is deliberately allowlisted here, with schedule/dispatch
triggers and a verified spend control.

Policy enforced:

1. Any workflow referencing ``secrets.ANTHROPIC_API_KEY`` must be in
   ``KEYED_ALLOWLIST`` (adding one is a reviewed, deliberate act).
2. Allowlisted workflows may only trigger on ``schedule`` /
   ``workflow_dispatch`` — never ``push`` / ``pull_request`` /
   ``pull_request_target`` / ``workflow_run``.
3. Every other workflow that sets ``ANTHROPIC_API_KEY`` at all must set
   it to the empty string (CI-keyless convention: ``""`` both blocks
   dotenv injection and fires the ``skipif`` gates — see the
   "keyless-CI-faithful" lesson).
4. Each allowlisted workflow's spend control is verified for what it
   actually is: ``integration-auth.yml`` caps spend via
   ``ATTUNE_MAX_BUDGET_USD``. (``help-freshness.yml`` was de-keyed
   2026-07-27 — report-only since author-consolidation T4 retired the
   in-CI regen path.)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / ".github" / "workflows"

#: The ONLY workflows allowed to reference the real Anthropic secret.
#: Value = short reason shown in failure messages. Adding an entry is a
#: spend decision: the workflow must be schedule/dispatch-only and carry
#: a spend control verified by a test in this module.
KEYED_ALLOWLIST: dict[str, str] = {
    "integration-auth.yml": "weekly live-key canary, ATTUNE_MAX_BUDGET_USD-capped",
    "windows-payload-capture.yml": (
        "one-shot Windows hook-payload diagnostic, dispatch-only, "
        "ATTUNE_MAX_BUDGET_USD-capped + --max-turns bounded"
    ),
}

#: Triggers that fire automatically at code-event scale. A live key on
#: any of these is the $1,200 failure mode.
AUTOMATIC_TRIGGERS = {"push", "pull_request", "pull_request_target", "workflow_run"}

_SECRET_REF = re.compile(r"secrets\.ANTHROPIC_API_KEY")
#: Any `ANTHROPIC_API_KEY:` assignment line, capturing its value.
_KEY_ASSIGNMENT = re.compile(r"^\s*ANTHROPIC_API_KEY\s*:\s*(.*?)\s*(?:#.*)?$", re.MULTILINE)


def _workflow_files() -> list[Path]:
    files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    assert files, f"no workflow files found under {WORKFLOWS_DIR}"
    return files


def _triggers(path: Path) -> set[str]:
    """Trigger names for a workflow file.

    PyYAML (YAML 1.1) parses the bare ``on:`` key as boolean ``True``,
    so look under both.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on or {})


def _keyed_files() -> list[Path]:
    return [p for p in _workflow_files() if _SECRET_REF.search(p.read_text(encoding="utf-8"))]


def test_keyed_workflows_are_allowlisted():
    """No workflow references the real secret unless deliberately listed.

    If this fails on a workflow you just added: per-push/PR test lanes
    get ``ANTHROPIC_API_KEY: ""`` ALWAYS. A live key at CI scale burned
    ~$1,200 in 6 hours on 2026-06-10. If the workflow genuinely needs
    the real key, make it schedule/dispatch-only, give it a spend
    control, add it to KEYED_ALLOWLIST, and add a control-verifying
    test below.
    """
    offenders = [p.name for p in _keyed_files() if p.name not in KEYED_ALLOWLIST]
    assert not offenders, (
        f"workflows reference secrets.ANTHROPIC_API_KEY without being "
        f"allowlisted: {offenders}. See this module's docstring for the "
        f"policy (2026-06-10 $1,200 burn)."
    )


def test_allowlist_entries_still_exist_and_still_keyed():
    """A stale allowlist entry is a hole — prune it when a workflow stops
    using the key (or is deleted), so the list stays a true inventory."""
    keyed_names = {p.name for p in _keyed_files()}
    stale = [name for name in KEYED_ALLOWLIST if name not in keyed_names]
    assert not stale, (
        f"KEYED_ALLOWLIST entries no longer reference the secret (or the "
        f"file is gone): {stale}. Remove them so the allowlist stays an "
        f"accurate inventory of keyed workflows."
    )


@pytest.mark.parametrize("name", sorted(KEYED_ALLOWLIST))
def test_keyed_workflows_never_run_automatically(name: str):
    """Allowlisted keyed workflows are schedule/dispatch-only."""
    path = WORKFLOWS_DIR / name
    if not path.exists():  # covered by the stale-allowlist test
        pytest.skip(f"{name} absent")
    auto = _triggers(path) & AUTOMATIC_TRIGGERS
    assert not auto, (
        f"{name} carries the real ANTHROPIC_API_KEY but has automatic "
        f"trigger(s) {sorted(auto)} — that is the exact 2026-06-10 "
        f"$1,200 configuration. Keyed workflows run on schedule/"
        f"workflow_dispatch only."
    )


def test_unkeyed_workflows_set_key_empty_if_at_all():
    """Outside the allowlist, ANTHROPIC_API_KEY is only ever ``""``.

    Catches both a direct secret reference (redundant with the
    allowlist test) and the rename dodge — e.g. passing
    ``secrets.SOME_OTHER_NAME`` into the ANTHROPIC_API_KEY env var.
    """
    bad: list[str] = []
    for path in _workflow_files():
        if path.name in KEYED_ALLOWLIST:
            continue
        for match in _KEY_ASSIGNMENT.finditer(path.read_text(encoding="utf-8")):
            value = match.group(1).strip()
            if value not in ('""', "''"):
                bad.append(f"{path.name}: ANTHROPIC_API_KEY: {value!r}")
    assert not bad, (
        f"non-allowlisted workflows assign ANTHROPIC_API_KEY a non-empty "
        f"value: {bad}. Per-push/PR CI is keyless by policy — set it to "
        f'"" (empty string, not unset: empty blocks dotenv injection AND '
        f"fires the skipif gates)."
    )


def test_integration_auth_caps_spend():
    """The live-key canary must keep its ATTUNE_MAX_BUDGET_USD cap."""
    path = WORKFLOWS_DIR / "integration-auth.yml"
    if not path.exists():
        pytest.skip("integration-auth.yml absent")
    text = path.read_text(encoding="utf-8")
    assert "ATTUNE_MAX_BUDGET_USD" in text, (
        "integration-auth.yml uses the real ANTHROPIC_API_KEY but no "
        "longer sets ATTUNE_MAX_BUDGET_USD — the budget cap is its "
        "allowlist condition. Restore the cap or de-key the workflow."
    )


def test_windows_payload_capture_caps_spend():
    """The Windows payload diagnostic keeps both of its spend bounds.

    Its allowlist conditions: ATTUNE_MAX_BUDGET_USD caps SDK-side
    spend, and every headless `claude -p` invocation is bounded by
    --max-turns so a runaway agentic loop can't accumulate cost.
    """
    path = WORKFLOWS_DIR / "windows-payload-capture.yml"
    if not path.exists():
        pytest.skip("windows-payload-capture.yml absent")
    text = path.read_text(encoding="utf-8")
    assert "ATTUNE_MAX_BUDGET_USD" in text, (
        "windows-payload-capture.yml uses the real ANTHROPIC_API_KEY "
        "but no longer sets ATTUNE_MAX_BUDGET_USD — restore the cap or "
        "de-key the workflow."
    )
    claude_invocations = re.findall(r"claude -p(?:[^\n]*\\\n)*[^\n]*", text)
    assert claude_invocations, (
        "windows-payload-capture.yml no longer invokes `claude -p` — "
        "re-point this test at wherever the keyed invocation moved."
    )
    unbounded = [inv for inv in claude_invocations if "--max-turns" not in inv]
    assert not unbounded, (
        f"windows-payload-capture.yml has `claude -p` invocation(s) "
        f"without --max-turns: {unbounded} — the turn bound is part of "
        f"this workflow's spend control."
    )
