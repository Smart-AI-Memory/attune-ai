"""Behavioral receipts for server-owned context and deferred form collection."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest

from attune.elicitation import form_from_dict
from attune.elicitation.surface_policy import (
    CapabilitySnapshot,
    SurfaceBinding,
    SurfaceContextStore,
)
from attune.elicitation.surface_registry import canonical_digest


@pytest.fixture
def state():
    now = [10000.0]
    store = SurfaceContextStore(b"x" * 32, clock=lambda: now[0], server_instance_id="server")
    binding = SurfaceBinding(
        "server", "session", "chain", "interactive_form", "form", "schema", "digest"
    )
    return store, binding, now


def test_context_first_match_and_retention(state):
    store, binding, now = state
    assert store.context_reason(None, replace(binding, subject_id="")) == "empty_form_id"
    assert store.context_reason(None, binding) == "missing_receipt"
    assert store.context_reason("forged", binding) == "invalid_receipt"
    receipt = store.issue(binding)
    assert store.context_reason(receipt, binding) == "warm"
    now[0] += 3599.999
    assert store.context_reason(receipt, binding) == "warm"
    now[0] += 0.001
    assert store.context_reason(receipt, binding) == "expired"
    assert store.context_reason(receipt, replace(binding, session_id="other")) == "session_mismatch"
    now[0] = 17199.999
    assert store.context_reason(receipt, binding) == "expired"
    now[0] = 17200
    assert store.context_reason(receipt, binding) == "foreign_receipt"


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("server_instance_id", "other", "server_instance_mismatch"),
        ("session_id", "other", "session_mismatch"),
        ("chain_id", "other", "chain_mismatch"),
        ("subject_id", "other", "subject_mismatch"),
        ("schema_id", "other", "schema_mismatch"),
        ("schema_digest", "other", "schema_mismatch"),
        ("workspace", ("forbidden",), "record_shape_mismatch"),
        ("subject_kind", "unknown", "record_shape_mismatch"),
    ],
)
def test_context_binding_rejects_mismatch(state, field, value, reason):
    store, binding, _ = state
    receipt = store.issue(binding)
    assert store.context_reason(receipt, replace(binding, **{field: value})) == reason


def test_restart_authentication_and_injected_foreign_record(state):
    store, binding, _ = state
    receipt = store.issue(binding)
    restarted = SurfaceContextStore(b"x" * 32)
    assert restarted.context_reason(receipt, binding) == "foreign_receipt"
    assert SurfaceContextStore(b"y" * 32).context_reason(receipt, binding) == "invalid_receipt"
    assert (
        store.context_reason(receipt, replace(binding, server_instance_id="new"))
        == "server_instance_mismatch"
    )


@pytest.mark.parametrize(
    "index,reason",
    list(
        enumerate(
            [
                "workspace_mismatch",
                "adapter_id_mismatch",
                "adapter_version_mismatch",
                "revision_mismatch",
                "event_sequence_mismatch",
                "contract_hash_mismatch",
                "action_nonce_mismatch",
            ]
        )
    ),
)
def test_workspace_binding_order(state, index, reason):
    store, base, _ = state
    values = ("workspace", "adapter", 1, 0, 0, "hash", "nonce")
    binding = replace(base, subject_kind="interactive_workspace", workspace=values)
    receipt = store.issue(binding)
    changed = list(values)
    changed[index] = changed[index] + 1 if isinstance(changed[index], int) else "changed"
    assert store.context_reason(receipt, replace(binding, workspace=tuple(changed))) == reason


@pytest.mark.parametrize(
    "workspace",
    [
        None,
        (),
        ("w", "a", True, 0, 0, "h", "n"),
        ("w", "a", 0, 0, 0, "h", "n"),
        ("w", "a", 1, -1, 0, "h", "n"),
        ("", "a", 1, 0, 0, "h", "n"),
    ],
)
def test_invalid_workspace_fails_closed(state, workspace):
    store, binding, _ = state
    with pytest.raises(ValueError, match="binding"):
        store.issue(replace(binding, subject_kind="interactive_workspace", workspace=workspace))


def test_future_timestamp_and_tombstone_age(state):
    store, binding, now = state
    receipt = store.issue(binding)
    now[0] -= 1
    assert store.context_reason(receipt, binding) == "future_timestamp"
    now[0] += 100
    store.close_session(binding.session_id)
    now[0] += 7199.999
    assert store.context_reason(receipt, replace(binding, schema_id="other")) == "session_ended"
    now[0] += 0.001
    assert store.context_reason(receipt, binding) == "foreign_receipt"
    with pytest.raises(ValueError, match="session_ended"):
        store.issue(binding)


def test_rotation_and_terminal_race(state):
    store, binding, _ = state
    receipt = store.issue(binding)
    assert store.issue(binding) == receipt
    successor = store.issue(replace(binding, schema_digest="new"))
    assert successor != receipt
    assert store.context_reason(receipt, binding) == "superseded_receipt"
    current = replace(binding, schema_digest="new")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: store.transition(successor, current, terminal=True), range(2))
        )
    assert sorted(r[0] for r in results) == ["committed", "terminal"]


@pytest.fixture
def presented(state):
    store, binding, now = state
    form = form_from_dict(
        {
            "title": "Planning",
            "fields": [
                {
                    "id": "outcome",
                    "text": "Desired outcome",
                    "type": "text_input",
                    "required": True,
                },
            ],
        }
    )
    binding = replace(binding, schema_id=form.form_id, schema_digest=canonical_digest(asdict(form)))
    receipt, submission = store.present_form(binding, form, {"payload": "original"}, "PORTABLE")
    return store, binding, form, receipt, submission, now


def test_collection_retry_returns_identical_result_without_second_validation(
    presented, monkeypatch
):
    store, binding, _, receipt, submission, _ = presented
    raw = {"action": "accept", "answers": {"outcome": "A working form"}}
    first = store.collect_form(receipt, submission, raw, session_id=binding.session_id)
    assert first["success"] and first["responses"] == raw["answers"]
    assert first["provenance_status"] == "unverified_transport"
    monkeypatch.setattr(
        "attune.elicitation.collect_form_response",
        lambda *a, **k: pytest.fail("duplicate validation"),
    )
    assert store.collect_form(receipt, submission, raw, session_id=binding.session_id) == first
    raw["answers"]["outcome"] = "changed"
    assert (
        store.collect_form(receipt, submission, raw, session_id=binding.session_id)["error"]
        == "submission_conflict"
    )


def test_rejection_rotates_authority_and_valid_answer_continues(presented):
    store, binding, _, receipt, submission, _ = presented
    result = store.collect_form(
        receipt, submission, {"action": "accept", "answers": {}}, session_id=binding.session_id
    )
    assert not result["success"] and result["problems"]
    assert store.context_reason(receipt, binding) == "superseded_receipt"
    assert store.context_reason(result["receipt_id"], binding) == "warm"
    accepted = store.collect_form(
        result["receipt_id"],
        result["submission_id"],
        {"action": "accept", "answers": {"outcome": "plan"}},
        session_id=binding.session_id,
    )
    assert accepted["success"] and accepted["receipt_id"] is None


@pytest.mark.parametrize("action", ["abort", "timeout"])
def test_terminal_action_and_two_presentations(presented, action):
    store, binding, form, receipt, submission, _ = presented
    same_receipt, second = store.present_form(binding, form, {"payload": "original"}, "PORTABLE")
    assert same_receipt == receipt and second != submission
    assert store.collect_form(
        receipt, submission, {"action": action}, session_id=binding.session_id
    )["success"]
    assert (
        store.collect_form(receipt, second, {"action": action}, session_id=binding.session_id)[
            "error"
        ]
        == "terminal"
    )


def test_session_end_expiry_and_cross_binding(presented):
    store, binding, _, receipt, submission, now = presented
    raw = {"action": "abort"}
    assert (
        store.collect_form(receipt, "forged", raw, session_id=binding.session_id)["error"]
        == "invalid_submission"
    )
    assert (
        store.collect_form("other", submission, raw, session_id=binding.session_id)["error"]
        == "submission_mismatch"
    )
    assert (
        store.collect_form(receipt, submission, raw, session_id="other")["error"]
        == "submission_mismatch"
    )
    now[0] += 3600
    assert (
        store.collect_form(receipt, submission, raw, session_id=binding.session_id)["error"]
        == "expired"
    )
    store.close_session(binding.session_id)
    assert (
        store.collect_form(receipt, submission, raw, session_id=binding.session_id)["error"]
        == "session_ended"
    )
    now[0] += 7200
    assert (
        store.collect_form(receipt, submission, raw, session_id=binding.session_id)["error"]
        == "foreign_receipt"
    )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {"action": "other"},
        {"action": "abort", "answers": {}},
        {"action": "accept", "form": {}},
        {"action": "accept", "answers": []},
        {"action": "accept", "answers": {"outcome": object()}},
    ],
)
def test_invalid_response_does_not_consume(presented, raw):
    store, binding, _, receipt, submission, _ = presented
    assert (
        store.collect_form(receipt, submission, raw, session_id=binding.session_id)["error"]
        == "invalid_response"
    )
    assert store.context_reason(receipt, binding) == "warm"


def test_negative_negotiation_beats_cache_and_cache_never_invents_mcp():
    caps = CapabilitySnapshot(
        "snapshot",
        (("RICH", False),),
        (("PORTABLE", False),),
        (("RICH", True), ("PORTABLE", True), ("HEADLESS", True), ("mcp-native:native", True)),
    )
    assert not caps.supports("RICH")
    assert not caps.supports("PORTABLE")
    assert not caps.supports("mcp-native:native")
    assert caps.supports("HEADLESS")


@pytest.fixture
def policy_registry():
    # Synthetic evidence exercises selection only; it never enables production.
    routes = ["RICH", "mcp-native:native", "PORTABLE", "HEADLESS"]
    targets = [{"id": r.lower(), "surface": r} for r in ("RICH", "PORTABLE", "HEADLESS")]
    return {
        "host_profiles": [],
        "renderers": [{"id": "renderer", "targets": targets}],
        "subjects": [
            {
                "id": "form",
                "subject_kind": "interactive_form",
                "targets": targets,
                "cold_routes": routes[1:],
                "warm_routes": routes,
                "route_transport_refs": {r: {"kind": "subject", "id": "transport"} for r in routes},
            },
            {
                "id": "transport",
                "subject_kind": "interaction_transport",
                "transport_id": "native",
                "form_subject_ids": ["form"],
            },
        ],
    }


@pytest.mark.parametrize(
    "context,hard,noninteractive,expected",
    [
        ("missing_receipt", None, False, "mcp-native:native"),
        ("schema_mismatch", None, False, "mcp-native:native"),
        ("warm", None, False, "RICH"),
        ("warm", "PORTABLE", False, "PORTABLE"),
        ("warm", "unavailable", False, None),
        ("warm", None, True, "HEADLESS"),
    ],
)
def test_selection_precedence_without_trial_render(
    policy_registry, context, hard, noninteractive, expected
):
    from attune.elicitation.surface_policy import select_surface
    from attune.elicitation.surface_registry import InventoryReport, required_obligations

    keys = frozenset(required_obligations(policy_registry))
    report = InventoryReport(
        keys, keys, frozenset(), frozenset(), canonical_digest(policy_registry)
    )
    caps = CapabilitySnapshot(
        "test",
        (("RICH", True), ("mcp-native:native", True)),
        (("PORTABLE", True), ("HEADLESS", True)),
        hard_surface=hard,
        noninteractive=noninteractive,
    )
    decision = select_surface(
        policy_registry,
        report,
        "form",
        caps,
        context_reason=context,
        deliverable_routes=frozenset({"RICH", "mcp-native:native", "PORTABLE", "HEADLESS"}),
    )
    assert decision.selected_route == expected
    assert decision.renderer_attempt_count == decision.presentation_attempt_count == 0
    assert set(decision.summary()) == {
        "context_reason",
        "selection_elapsed_ms",
        "renderer_attempt_count",
        "presentation_attempt_count",
    }


def test_missing_evidence_and_missing_adapter_do_not_render(policy_registry):
    from attune.elicitation.surface_policy import select_surface
    from attune.elicitation.surface_registry import InventoryReport, required_obligations

    keys = frozenset(required_obligations(policy_registry))
    absent = "route:form:PORTABLE:production_projection"
    report = InventoryReport(
        keys, keys - {absent}, frozenset({absent}), frozenset(), canonical_digest(policy_registry)
    )
    caps = CapabilitySnapshot(
        "test", (("mcp-native:native", True),), (("PORTABLE", True), ("HEADLESS", True))
    )
    decision = select_surface(
        policy_registry,
        report,
        "form",
        caps,
        context_reason="missing_receipt",
        deliverable_routes=frozenset({"PORTABLE", "HEADLESS"}),
    )
    assert decision.selected_route == "HEADLESS"
    assert decision.candidates == (
        ("mcp-native:native", "missing_adapter"),
        ("PORTABLE", "missing_evidence"),
        ("HEADLESS", "selected"),
    )


def test_store_rejects_short_key_invalid_binding_and_kind_change(state):
    with pytest.raises(ValueError, match="installation key"):
        SurfaceContextStore(b"short")
    store, binding, _ = state
    store.issue(binding)
    for bad in (replace(binding, session_id=1), replace(binding, chain_id="")):
        with pytest.raises(ValueError, match="binding"):
            store.issue(bad)
    with pytest.raises(ValueError, match="kind cannot change"):
        store.issue(
            replace(
                binding,
                subject_kind="interactive_workspace",
                workspace=("w", "a", 1, 0, 0, "h", "n"),
            )
        )


def test_presentation_cannot_substitute_canonical_form(presented):
    store, binding, form, _, _, _ = presented
    for bad, message in [
        (replace(binding, subject_kind="interactive_workspace"), "form binding"),
        (replace(binding, schema_digest="forged"), "schema"),
        (replace(binding, schema_id="other"), "identity"),
    ]:
        with pytest.raises(ValueError, match=message):
            store.present_form(bad, form, {}, "PORTABLE")


def test_server_retains_copy_of_form_and_result(presented):
    store, binding, form, receipt, submission, _ = presented
    form.questions.clear()
    result = store.collect_form(
        receipt, submission, {"action": "accept", "answers": {}}, session_id=binding.session_id
    )
    assert not result["success"]
    result["problems"].clear()
    replay = store.collect_form(
        receipt, submission, {"action": "accept", "answers": {}}, session_id=binding.session_id
    )
    assert replay["problems"]


def test_terminal_chain_cannot_be_reopened(presented):
    store, binding, form, receipt, submission, _ = presented
    store.collect_form(receipt, submission, {"action": "abort"}, session_id=binding.session_id)
    with pytest.raises(ValueError, match="terminal"):
        store.present_form(binding, form, {}, "PORTABLE")
    # Another interaction in the same session remains allowed.
    store.present_form(replace(binding, chain_id="new-chain"), form, {}, "PORTABLE")


@pytest.mark.parametrize("valid", [True, False])
def test_expiry_during_validation_cannot_commit(presented, monkeypatch, valid):
    from attune.elicitation import collect_form_response

    store, binding, _, receipt, submission, now = presented

    def crossing_deadline(*args, **kwargs):
        now[0] += 3600
        return collect_form_response(*args, **kwargs)

    monkeypatch.setattr("attune.elicitation.collect_form_response", crossing_deadline)
    result = store.collect_form(
        receipt,
        submission,
        {"action": "accept", "answers": {"outcome": "plan"} if valid else {}},
        session_id=binding.session_id,
    )
    assert result == {"success": False, "error": "expired"}
    assert None not in store._interactions
    assert store._submissions[submission] == (receipt, None, None)


def test_anonymous_form_stays_cold_but_rerender_preserves_authority(presented):
    store, binding, form, _, _, _ = presented
    anonymous = replace(binding, subject_id="", chain_id="anonymous")
    first, token = store.present_form(anonymous, form, {}, "PORTABLE")
    second, other_token = store.present_form(anonymous, form, {}, "PORTABLE")
    assert first == second and token != other_token
    assert store.context_reason(first, anonymous) == "empty_form_id"
    assert store.collect_form(first, token, {"action": "abort"}, session_id=binding.session_id)[
        "success"
    ]


def test_native_challenge_is_single_use_and_does_not_issue_before_completion(presented):
    store, binding, form, _, _, _ = presented
    native = replace(binding, chain_id="native")
    challenge = store.begin_challenge(native, form, {}, "mcp-native:native")
    assert (native.session_id, native.chain_id) not in store._active
    first = store.complete_challenge(
        challenge, {"action": "accept", "answers": {"outcome": "plan"}}
    )
    assert first["success"] and first["provenance_status"] == "server_observed_completion"
    assert store.complete_challenge(challenge, {"action": "abort"}) == {
        "success": False,
        "error": "challenge_consumed",
    }


@pytest.mark.parametrize(
    "stop,expected",
    [
        ("close", "session_ended"),
        ("invalidate", "challenge_invalidated"),
        ("expire", "challenge_invalidated"),
    ],
)
def test_late_native_completion_preserves_predecessor(presented, stop, expected):
    store, binding, form, receipt, _, now = presented
    challenge = store.begin_challenge(binding, form, {}, "mcp-native:native")
    if stop == "close":
        store.close_session(binding.session_id)
    elif stop == "invalidate":
        store.invalidate_challenge(challenge)
    else:
        now[0] += 3600
    assert store.complete_challenge(challenge, {"action": "abort"}) == {
        "success": False,
        "error": expected,
    }
    assert len(store._records) == 1
    assert (
        store.context_reason(receipt, binding)
        == {"close": "session_ended", "invalidate": "warm", "expire": "expired"}[stop]
    )


def test_challenge_is_identity_bound_and_not_serializable(presented):
    import pickle

    from attune.elicitation.surface_policy import PresentationChallenge

    store, binding, form, _, _, _ = presented
    challenge = store.begin_challenge(binding, form, {}, "mcp-native:native")
    assert (
        store.complete_challenge(PresentationChallenge(), {"action": "abort"})["error"]
        == "challenge_invalidated"
    )
    with pytest.raises(TypeError, match="process-local"):
        pickle.dumps(challenge)
