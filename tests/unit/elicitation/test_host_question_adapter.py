# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Receipts for the trusted in-process host-question presentation boundary.

Every batch here is built by the RELEASED attune-forms 0.17.0
``form_to_host_question`` against the installed ``claude-askuserquestion``
profile, not by a hand-rolled stand-in. The adapter under test is a fake,
and a fake proves only the interface — but the objects crossing that
interface are the real ones, so a signature or shape drift in AF-2 fails
here rather than in the routing increment that consumes it.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest
from attune_forms import form_from_dict, installed_profile
from attune_forms.host_question import HostQuestionBatch, form_to_host_question

from attune.elicitation.host_question_adapter import (
    HostAdapterRegistration,
    HostQuestionAdapter,
    HostQuestionCompletion,
    ValidationFeedbackEnvelope,
    derive_validation_feedback,
    present_host_question,
    resolve_host_adapter,
)
from attune.elicitation.surface_policy import SurfaceBinding, SurfaceContextStore
from attune.elicitation.surface_registry import canonical_digest

PROFILE_ID = "claude-askuserquestion"
TARGET_ID = "form.host_question"
ROUTE = f"host-native:{TARGET_ID}"


class FakeHostAdapter:
    """Records what the boundary handed it and returns a scripted completion."""

    def __init__(self, *, result="accept", profile_id=PROFILE_ID, target_id=TARGET_ID):
        self.adapter_id = "fake-host-adapter"
        self.profile_id = profile_id
        self.target_id = target_id
        self._result = result
        self.calls: list[dict] = []

    def present_and_collect(self, challenge, batch, *, feedback=None, deadline_seconds):
        """Capture the arguments, then behave as the scripted result says."""
        self.calls.append(
            {
                "challenge": challenge,
                "batch": batch,
                "feedback": feedback,
                "deadline_seconds": deadline_seconds,
            }
        )
        if self._result == "raise":
            raise RuntimeError("host transport exploded")
        if self._result == "none":
            return None
        if self._result == "foreign_challenge":
            return HostQuestionCompletion(object(), {"action": "accept", "answers": {}})
        if self._result == "not_a_completion":
            return {"action": "accept", "answers": {}}
        if self._result == "abort":
            return HostQuestionCompletion(challenge, {"action": "abort"})
        if self._result == "malformed":
            return HostQuestionCompletion(challenge, {"action": "nonsense"})
        return HostQuestionCompletion(challenge, {"action": "accept", "answers": {"scope": "Wide"}})


@pytest.fixture
def form():
    return form_from_dict(
        {
            "form_id": "demo",
            "title": "Demo",
            "fields": [
                {
                    "id": "scope",
                    "label": "Scope?",
                    "type": "single_select",
                    "options": ["Narrow", "Wide"],
                }
            ],
        }
    )


@pytest.fixture
def batch(form):
    profile = installed_profile(PROFILE_ID)
    assert profile is not None, "the installed profile is the receipt's basis"
    return form_to_host_question(form, profile.host_question)


@pytest.fixture
def store():
    return SurfaceContextStore(b"k" * 32)


@pytest.fixture
def binding(store, form):
    return SurfaceBinding(
        store.server_instance_id,
        "session-1",
        "chain-1",
        "interactive_form",
        "form",
        form.form_id,
        canonical_digest(asdict(form)),
    )


@pytest.fixture
def challenge(store, binding, form, batch):
    return store.begin_challenge(binding, form, batch.payload, ROUTE)


def _registration(adapter):
    return HostAdapterRegistration(adapter, adapter.profile_id, adapter.target_id)


# --- registration identity -------------------------------------------------


def test_registration_binds_adapter_identity_to_profile_and_target():
    adapter = FakeHostAdapter()
    registration = _registration(adapter)
    assert registration.matches(PROFILE_ID, TARGET_ID)
    assert not registration.matches(PROFILE_ID, "other.target")
    assert not registration.matches("other-profile", TARGET_ID)


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"profile_id": "other-profile"}, "profile_id does not match"),
        ({"target_id": "other.target"}, "target_id does not match"),
    ],
)
def test_registration_refuses_identity_contradicting_the_adapter(kwargs, message):
    adapter = FakeHostAdapter(**kwargs)
    with pytest.raises(ValueError, match=message):
        HostAdapterRegistration(adapter, PROFILE_ID, TARGET_ID)


def test_registration_refuses_an_object_that_cannot_present():
    class NotAnAdapter:
        adapter_id = "x"
        profile_id = PROFILE_ID
        target_id = TARGET_ID

    with pytest.raises(TypeError, match="present_and_collect"):
        HostAdapterRegistration(NotAnAdapter(), PROFILE_ID, TARGET_ID)


def test_registration_refuses_a_blank_declared_identity():
    adapter = FakeHostAdapter()
    adapter.adapter_id = ""
    with pytest.raises(ValueError, match="non-empty adapter_id"):
        HostAdapterRegistration(adapter, PROFILE_ID, TARGET_ID)


def test_a_fake_satisfies_the_protocol_and_that_is_all_it_proves():
    assert isinstance(FakeHostAdapter(), HostQuestionAdapter)


# --- resolution, which happens BEFORE rendering ----------------------------


def test_absent_or_mismatched_adapter_resolves_to_none():
    registration = _registration(FakeHostAdapter())
    assert resolve_host_adapter(None, profile_id=PROFILE_ID, target_id=TARGET_ID) is None
    assert (
        resolve_host_adapter(registration, profile_id=PROFILE_ID, target_id="other.target") is None
    )
    assert (
        resolve_host_adapter(registration, profile_id="other-profile", target_id=TARGET_ID) is None
    )
    assert (
        resolve_host_adapter(registration, profile_id=PROFILE_ID, target_id=TARGET_ID)
        is registration
    )


# --- the same-call boundary ------------------------------------------------


def test_same_call_completion_is_consumed_against_the_real_af2_batch(store, challenge, batch, form):
    adapter = FakeHostAdapter()
    result = present_host_question(
        store, _registration(adapter), challenge, batch, deadline_seconds=1800
    )
    assert result["success"] is True
    assert result["provenance_status"] == "server_observed_completion"
    seen = adapter.calls[0]
    assert seen["challenge"] is challenge
    assert isinstance(seen["batch"], HostQuestionBatch)
    assert seen["batch"].answer_bindings[0].question_id == "scope"
    assert seen["deadline_seconds"] == 1800
    assert len(adapter.calls) == 1


def test_the_challenge_handed_to_an_adapter_cannot_be_serialized(challenge):
    import copy
    import pickle

    with pytest.raises(TypeError, match="process-local"):
        pickle.dumps(challenge)
    with pytest.raises(TypeError, match="process-local"):
        copy.deepcopy(challenge)


def test_a_second_completion_is_refused_as_consumed(store, challenge, batch):
    registration = _registration(FakeHostAdapter())
    assert present_host_question(store, registration, challenge, batch, deadline_seconds=1800)[
        "success"
    ]
    again = present_host_question(store, registration, challenge, batch, deadline_seconds=1800)
    assert again == {"success": False, "error": "challenge_consumed"}


def test_session_close_wins_over_a_later_completion(store, challenge, batch, binding):
    store.close_session(binding.session_id)
    result = present_host_question(
        store, _registration(FakeHostAdapter()), challenge, batch, deadline_seconds=1800
    )
    assert result == {"success": False, "error": "session_ended"}


@pytest.mark.parametrize(
    "result", ["raise", "none", "foreign_challenge", "not_a_completion", "malformed"]
)
def test_every_adapter_failure_is_render_failed_and_selects_nothing_else(
    store, challenge, batch, result
):
    outcome = present_host_question(
        store,
        _registration(FakeHostAdapter(result=result)),
        challenge,
        batch,
        deadline_seconds=1800,
    )
    assert outcome == {"success": False, "error": "render_failed"}


def test_a_render_failure_leaves_the_challenge_unusable(store, challenge, batch):
    present_host_question(
        store,
        _registration(FakeHostAdapter(result="raise")),
        challenge,
        batch,
        deadline_seconds=1800,
    )
    retry = present_host_question(
        store, _registration(FakeHostAdapter()), challenge, batch, deadline_seconds=1800
    )
    assert retry["success"] is False


def test_an_adapter_exception_is_logged_before_it_becomes_render_failed(
    store, challenge, batch, caplog
):
    with caplog.at_level("ERROR"):
        present_host_question(
            store,
            _registration(FakeHostAdapter(result="raise")),
            challenge,
            batch,
            deadline_seconds=1800,
        )
    assert "host question adapter fake-host-adapter raised" in caplog.text
    assert "host transport exploded" in caplog.text


def test_a_trusted_abort_is_collected_rather_than_treated_as_failure(store, challenge, batch):
    result = present_host_question(
        store,
        _registration(FakeHostAdapter(result="abort")),
        challenge,
        batch,
        deadline_seconds=1800,
    )
    assert result.get("error") != "render_failed"
    assert result["action"] == "abort"


# --- validation feedback ---------------------------------------------------


def test_derived_feedback_is_intact_and_reaches_the_adapter_unchanged(store, challenge, batch):
    feedback = derive_validation_feedback(2, ("scope: required",))
    assert feedback.intact()
    adapter = FakeHostAdapter()
    present_host_question(
        store, _registration(adapter), challenge, batch, feedback=feedback, deadline_seconds=1800
    )
    assert adapter.calls[0]["feedback"] is feedback


def test_mutated_feedback_is_refused_before_the_adapter_is_called(store, challenge, batch):
    forged = ValidationFeedbackEnvelope(1, ("anything you like",), "not-the-digest")
    assert not forged.intact()
    adapter = FakeHostAdapter()
    result = present_host_question(
        store, _registration(adapter), challenge, batch, feedback=forged, deadline_seconds=1800
    )
    assert result == {"success": False, "error": "render_failed"}
    assert adapter.calls == []


@pytest.mark.parametrize("attempt", [0, -1, True, "2"])
def test_feedback_attempt_must_be_a_positive_integer(attempt):
    with pytest.raises(ValueError, match="positive integer"):
        derive_validation_feedback(attempt, ())


def test_feedback_problems_must_be_a_tuple_of_strings():
    with pytest.raises(TypeError, match="tuple of strings"):
        derive_validation_feedback(1, ["not", "a", "tuple"])
    with pytest.raises(TypeError, match="tuple of strings"):
        derive_validation_feedback(1, (1, 2))


def test_the_first_attempt_counts_toward_the_profile_cap():
    profile = installed_profile(PROFILE_ID)
    assert profile.host_question.max_validation_attempts == 3
    assert derive_validation_feedback(1, ()).attempt == 1
