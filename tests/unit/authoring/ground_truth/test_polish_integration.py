"""Integration tests: polish prompt + ground-truth context wiring."""

from __future__ import annotations

from attune.authoring.ground_truth import ANCHORING_CLAUSE
from attune.authoring.polish import build_polish_prompt


def test_build_polish_prompt_no_anchor_by_default() -> None:
    system, user = build_polish_prompt(
        content="# Template\n\nBody",
        feature_name="demo",
        source_summary="def thing()",
        template_type="concept",
    )
    assert ANCHORING_CLAUSE not in system
    assert "## Source info" in user


def test_build_polish_prompt_appends_anchor_when_flag_set() -> None:
    """The system prompt grows by exactly the anchoring clause when requested."""
    base_system, _ = build_polish_prompt(
        content="x",
        feature_name="demo",
        source_summary="",
        template_type="concept",
    )
    augmented_system, _ = build_polish_prompt(
        content="x",
        feature_name="demo",
        source_summary="",
        template_type="concept",
        include_ground_truth_anchor=True,
    )
    assert augmented_system == base_system + ANCHORING_CLAUSE


def test_build_polish_prompt_embeds_augmented_context_in_user_message() -> None:
    ground_truth = (
        "## Ground-truth context\n\n" "<cli_help>\nUsage: attune ops --read-only\n</cli_help>\n"
    )
    _, user = build_polish_prompt(
        content="# Template\n",
        feature_name="demo",
        source_summary="def thing()",
        template_type="concept",
        augmented_context=ground_truth,
        include_ground_truth_anchor=True,
    )
    assert "<cli_help>" in user
    assert "attune ops --read-only" in user
    assert user.find("<cli_help>") < user.find("## Source info")


def test_anchoring_clause_mentions_sentinel_tags() -> None:
    """Regression guard: the clause must reference the three sentinel tags."""
    assert "<cli_help>" in ANCHORING_CLAUSE
    assert "<public_api>" in ANCHORING_CLAUSE
    assert "<dataclasses>" in ANCHORING_CLAUSE
