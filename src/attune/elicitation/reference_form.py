"""Canonical reference form exercising every elicitation control type.

This module is the single, code-verified example of a *complete*
declarative form: one field per :class:`~attune.meta_workflows.models.QuestionType`
member, each with realistic example values, plus a matching set of valid
answers. It is deliberately a plain data constant — importable and
copy-from-able — not a template-store entry or a ``form_from_template``
invocation. The V7 template library (:mod:`.template_store`) exists, but
per its promote-on-repeat rule (R5) only *recurring* fork classes earn a
stored template; this reference is documentation, not a recurring ask,
so it stays a constant.

The paired :data:`REFERENCE_FORM` / :data:`EXAMPLE_ANSWERS` round-trip
through the existing seams with no changes:

    >>> from attune.elicitation import form_from_dict, collect_form_response
    >>> form = form_from_dict(REFERENCE_FORM)
    >>> response = collect_form_response(form, EXAMPLE_ANSWERS)
    >>> response.responses["priority"]
    'high'

``tests/unit/elicitation/test_reference_form.py`` asserts the form stays
complete: if a new ``QuestionType`` is added without a field here, CI
fails — the reference cannot silently fall behind the grammar.
"""

from __future__ import annotations

from typing import Any

#: A complete declarative form — exactly one field per control type.
#: The scenario (a small "new feature intake") keeps the example
#: coherent rather than a random grab-bag of controls.
REFERENCE_FORM: dict[str, Any] = {
    "title": "Reference form — every control type",
    "description": "One field per elicitation control, with example values.",
    "fields": [
        {
            # v1: free single-line text
            "id": "feature_name",
            "type": "text_input",
            "text": "What is the feature called?",
            "help_text": "A short human-readable name.",
        },
        {
            # v1: pick exactly one
            "id": "priority",
            "type": "single_select",
            "text": "How urgent is it?",
            "options": ["low", "medium", "high"],
        },
        {
            # v1: pick zero or more — batches N dimensions into one turn
            "id": "concerns",
            "type": "multi_select",
            "text": "Which concerns apply?",
            "options": ["impl", "test", "docs", "migration", "release-notes"],
        },
        {
            # v1: yes / no
            "id": "needs_migration",
            "type": "boolean",
            "text": "Does it require a data migration?",
        },
        {
            # v2.1: bounded number
            "id": "estimated_days",
            "type": "number",
            "text": "Estimated effort in days?",
            "minimum": 0,
            "maximum": 30,
        },
        {
            # v2.1: ISO-8601 date
            "id": "target_date",
            "type": "date",
            "text": "Target ship date?",
        },
        {
            # v2.1: multi-line, length-bounded, optional
            "id": "notes",
            "type": "textarea",
            "text": "Anything else to capture?",
            "max_length": 500,
            "required": False,
        },
        {
            # v3: a recommended single-select with rationale + tradeoffs
            "id": "rollout",
            "type": "decision",
            "text": "How should we roll it out?",
            "options": [
                "Ship behind a feature flag",
                "Ship to everyone at once",
                "Hold for the next release",
            ],
            "recommended": "Ship behind a feature flag",
            "rationale": "A flag lets us dark-launch and roll back without a redeploy.",
            "option_notes": {
                "Ship behind a feature flag": "Safest — gated exposure, instant rollback.",
                "Ship to everyone at once": "Fastest, but no kill switch if it regresses.",
                "Hold for the next release": "Zero risk now, but delays the value.",
            },
        },
        {
            # v4: a pushback — the user's approach vs the agent's alternative
            "id": "branch_strategy",
            "type": "pushback",
            "text": "You proposed a long-lived feature branch.",
            "options": [
                "Long-lived feature branch",
                "Short stacked PRs off main",
            ],
            "user_position": "Long-lived feature branch",
            "recommended": "Short stacked PRs off main",
            "rationale": "Long-lived branches drift from main and make review a big-bang; "
            "small stacked PRs stay mergeable and reviewable.",
        },
        {
            # v5: a status report whose blocked items are a picker
            "id": "blockers",
            "type": "progress",
            "text": "Which blocker should we tackle first?",
            "options": ["Design sign-off", "Staging environment"],
            "progress_items": [
                {"label": "Requirements", "status": "done", "detail": "approved"},
                {"label": "Prototype", "status": "in_flight", "detail": "in review"},
                {"label": "Design sign-off", "status": "blocked", "detail": "awaiting design"},
                {
                    "label": "Staging environment",
                    "status": "blocked",
                    "detail": "infra ticket open",
                },
            ],
        },
    ],
}

#: Valid answers for every field in :data:`REFERENCE_FORM`. Round-trips
#: through ``collect_form_response`` to a successful ``FormResponse``.
EXAMPLE_ANSWERS: dict[str, Any] = {
    "feature_name": "Dark mode toggle",
    "priority": "high",
    "concerns": ["impl", "test", "docs"],
    "needs_migration": "No",
    "estimated_days": 3,
    "target_date": "2026-08-01",
    "notes": "Ship behind a flag, measure, then widen.",
    "rollout": "Ship behind a feature flag",
    "branch_strategy": "Short stacked PRs off main",
    "blockers": "Design sign-off",
}
