"""adaptive-session-interactions T2 — the review-choice guidance and its seams.

T2 tightened guidance at the pilot consumer (the Spec workspace's
``review`` stage) for ASI-1, ASI-2 and ASI-5 and added no code. These
tests pin the four behavioral cases the task names — phase-independent
choice, no redundant question, genuine alternatives, persistent versus
one-time override — where each actually lives: the consumer's canonical
behavior for the first three, and the skill masters (plus their tracked
mirrors) for the guidance that has no code seam. If a later edit drops a
rule from a skill, or the review stage stops being a two-alternative,
non-consequential choice, the pilot's premise is gone and this fails.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.mcp.server import AttuneMCPServer
from attune.spec.workspace import SpecWorkspaceAdapter

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_SKILL = _ROOT / "plugin" / "skills" / "spec" / "SKILL.md"
_ELICIT_SKILL = _ROOT / "plugin" / "skills" / "elicit" / "SKILL.md"
_SPEC_MIRROR = _ROOT / ".agents" / "skills" / "spec" / "SKILL.md"
_ELICIT_MIRROR = _ROOT / ".agents" / "skills" / "elicit" / "SKILL.md"

# One sentence per behavioral case, quoted from the masters. The guidance
# is prose, so the pin is the sentence — rewording it deliberately means
# updating the pin in the same PR.
_SPEC_RULES = {
    "phase-independent": "Select by need, not by phase.",
    "override-vs-session": "A one-time override does\n   not rewrite the stored preference.",
    "transcribe-not-act": "A conversational answer is transcribed, never acted on directly.",
    "no-redundant-question": "Never re-ask a settled choice.",
    "authority-unchanged": "Presentation never changes authority.",
    "session-store": "`interaction_preference`",
}
_ELICIT_RULES = {
    "override-scope": "Honor it for this\n  interaction only; it does not rewrite anything stored.",
    "session-store": "`interaction_preference`",
    "precedence": "explicit override for this interaction → explicit session\npreference → the router's default",
    "keyboard-not-preference": "Keyboard mode is NOT this preference",
    "text-lane-keeps-fields": "The text lane keeps every field.",
    "markdown-surface": "`form_to_markdown(form)`",
}


@pytest.mark.parametrize("rule", sorted(_SPEC_RULES))
def test_spec_skill_master_carries_the_review_choice_rules(rule: str) -> None:
    assert _SPEC_RULES[rule] in _SPEC_SKILL.read_text(encoding="utf-8"), rule


@pytest.mark.parametrize("rule", sorted(_ELICIT_RULES))
def test_elicit_skill_master_carries_the_scoped_preference_rules(rule: str) -> None:
    assert _ELICIT_RULES[rule] in _ELICIT_SKILL.read_text(encoding="utf-8"), rule


@pytest.mark.parametrize(
    ("master", "mirror", "rules"),
    [(_SPEC_SKILL, _SPEC_MIRROR, _SPEC_RULES), (_ELICIT_SKILL, _ELICIT_MIRROR, _ELICIT_RULES)],
    ids=["spec", "elicit"],
)
def test_tracked_mirror_carries_the_same_rules(master: Path, mirror: Path, rules: dict) -> None:
    # The mirror is what Codex reads; a master edited without reprojection
    # leaves the other provider on the old guidance.
    text = mirror.read_text(encoding="utf-8")
    missing = [name for name, sentence in rules.items() if sentence not in text]
    assert (
        not missing
    ), f"{mirror.relative_to(_ROOT)} lacks {missing}; run sync_agents_skills --write"


# --- consumer behavior the guidance relies on --------------------------------


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "attune" / "alpha").mkdir(parents=True)
    (repo / "src" / "attune" / "alpha" / "__init__.py").write_text("")
    (repo / "docs" / "specs").mkdir(parents=True)
    (repo / ".claude" / "plans").mkdir(parents=True)
    (repo / ".git").mkdir()
    return repo


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


async def _to_review(host: CommandWorkspaceHost):
    preview = await host.open(
        "spec",
        {
            "route": "new",
            "outcome": "A pilot exists.",
            "done_when": "The review choice is answered.",
            "area": "src/attune/alpha",
            "slug": "pilot",
        },
    )
    creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
    gate = await host.publish(
        creating.record.workspace_id,
        {
            "kind": "artifacts_created",
            "plan_path": ".claude/plans/pilot.md",
            "artifacts": [{"path": ".claude/plans/pilot.md", "kind": "plan"}],
            "task_ids": ["1"],
            "probes": ["pytest -q"],
        },
    )
    return await host.publish(
        gate.record.workspace_id,
        {
            "kind": "lifecycle_gate",
            "boundary": "tasks",
            "receipts": [{"gate_id": "g", "boundary": "tasks", "state": "PASS", "detail": "ok"}],
        },
    )


@pytest.mark.asyncio
async def test_review_stage_is_a_two_alternative_non_consequential_choice(tmp_path: Path) -> None:
    # ASI-5's pilot premise: genuine alternatives, no manufactured approval gate.
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(_repo(tmp_path)))
    review = await _to_review(host)
    actions = review.record.view.actions
    assert [a.id for a in actions] == ["redo_plan", "approve_plan"]
    assert all(not a.requires_explicit_choice for a in actions)
    assert all(not a.consequence for a in actions)


@pytest.mark.asyncio
async def test_markdown_skeleton_carries_the_binding_for_transcription(tmp_path: Path) -> None:
    # The text lane the guidance names: a spoken "approve" is transcribed into
    # THIS skeleton and submitted; the skeleton must carry the bound fields.
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(_repo(tmp_path)))
    review = await _to_review(host)
    md = review.render.markdown
    for key in ("workspace_id", "revision", "action_nonce", "contract_hash", "title", "view"):
        assert f'"{key}"' in md, key
    assert review.record.action_nonce in md
    assert review.record.contract_hash in md


@pytest.mark.asyncio
async def test_settled_choice_cannot_be_asked_again(tmp_path: Path) -> None:
    # "Never re-ask a settled choice": once approve_plan is accepted the review
    # render is superseded, and re-submitting it is rejected rather than
    # producing a second answer to the same question.
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(_repo(tmp_path)))
    review = await _to_review(host)
    approval = await host.collect(_payload(review, "approve_plan"))
    assert approval.record.state.stage == "approval"
    with pytest.raises(CommandWorkspaceError):
        await host.collect(_payload(review, "approve_plan"))


@pytest.mark.asyncio
async def test_session_preference_store_round_trips_and_is_process_scoped() -> None:
    # The facility T2 named for the session-wide preference: the MCP server's
    # session context. Round trip through the public tools; a fresh server
    # instance starts empty (the "dies with the session" lifetime).
    server = AttuneMCPServer()
    unset = await server.call_tool("context_get", {"key": "interaction_preference"})
    assert unset["found"] is False
    stored = await server.call_tool(
        "context_set", {"key": "interaction_preference", "value": "conversation"}
    )
    assert stored["success"] is True
    got = await server.call_tool("context_get", {"key": "interaction_preference"})
    assert (got["found"], got["value"]) == (True, "conversation")
    fresh = await AttuneMCPServer().call_tool("context_get", {"key": "interaction_preference"})
    assert fresh["found"] is False
