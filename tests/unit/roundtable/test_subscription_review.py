"""Subscription review launches use fake credentials and intercepted processes."""

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from attune.roundtable import subscription_review as sub

AUTH = {
    "loggedIn": True,
    "authMethod": "claude.ai",
    "apiProvider": "firstParty",
    "subscriptionType": "max",
}


def response(payload, code=0):
    return SimpleNamespace(stdout=json.dumps(payload), returncode=code)


@pytest.fixture
def launch(monkeypatch):
    calls = Mock(side_effect=[response(AUTH), response({"result": "NO FINDINGS"})])
    monkeypatch.setattr(sub.subprocess, "run", calls)
    monkeypatch.setattr(sub.session_ledger, "record", Mock())
    monkeypatch.setattr(sub.session_ledger, "check", Mock(side_effect=AssertionError("API route")))
    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
    return calls


def test_verified_max_uses_same_clean_environment_and_stdin(launch, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")  # pragma: allowlist secret
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://fixture.invalid")
    monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fixture-token")  # pragma: allowlist secret
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/fixture/profile")
    brief = "x" * 200000
    assert sub.invoke_subscription_review(brief) == (0, "NO FINDINGS")
    probe, review = launch.call_args_list
    assert probe.args[0] == ["claude", "--safe-mode", "--strict-mcp-config", "auth", "status"]
    env = review.kwargs["env"]
    assert env == probe.kwargs["env"]
    assert not any(key.startswith(("ANTHROPIC_", "CLAUDE")) for key in env)
    assert env["ATTUNE_SESSION_SPEND_CAP_USD"] == "0"
    assert sub.os.environ["ANTHROPIC_API_KEY"] == "fixture-key"  # pragma: allowlist secret
    argv = review.args[0]
    assert "--safe-mode" in argv and "--strict-mcp-config" in argv
    assert argv[argv.index("--tools") + 1] == ""
    assert json.loads(argv[argv.index("--mcp-config") + 1]) == {"mcpServers": {}}
    assert "--no-session-persistence" in argv
    assert brief not in argv and review.kwargs["input"] == brief
    sub.session_ledger.record.assert_called_once_with("seat:claude:subscription", 0.0)


@pytest.mark.parametrize(
    "change",
    [
        {"loggedIn": False},
        {"loggedIn": 1},
        {"authMethod": "api_key"},
        {"apiProvider": "bedrock"},
        {"subscriptionType": None},
        {"subscriptionType": "enterprise"},
        {"apiKeySource": "apiKeyHelper"},
        {"apiKeySource": "ANTHROPIC_API_KEY"},
    ],
)
def test_unverified_auth_never_launches_inference(launch, change):
    launch.side_effect = [response({**AUTH, **change})]
    with pytest.raises(sub.SubscriptionReviewError):
        sub.invoke_subscription_review("review")
    assert launch.call_count == 1
    sub.session_ledger.record.assert_not_called()


@pytest.mark.parametrize("value", [None, [], "max", {}, {**AUTH, "subscriptionType": "unknown"}])
def test_malformed_auth_never_launches(launch, value):
    launch.side_effect = [response(value)]
    with pytest.raises(sub.SubscriptionReviewError):
        sub.invoke_subscription_review("review")
    assert launch.call_count == 1


@pytest.mark.parametrize("failure", [OSError("missing"), subprocess.TimeoutExpired("claude", 15)])
def test_auth_probe_failure_is_closed(launch, failure):
    launch.side_effect = failure
    with pytest.raises(sub.SubscriptionReviewError):
        sub.invoke_subscription_review("review")
    assert launch.call_count == 1


@pytest.mark.parametrize(
    "probe", [SimpleNamespace(stdout="not-json", returncode=0), response(AUTH, 1)]
)
def test_bad_auth_response_is_closed(launch, probe):
    launch.side_effect = [probe]
    with pytest.raises(sub.SubscriptionReviewError):
        sub.invoke_subscription_review("review")
    assert launch.call_count == 1


@pytest.mark.parametrize("failure", [OSError("missing"), subprocess.TimeoutExpired("claude", 300)])
def test_review_process_failure_never_falls_back(launch, failure):
    launch.side_effect = [response(AUTH), failure]
    code, message = sub.invoke_subscription_review("review")
    assert code != 0 and "unavailable" in message
    assert launch.call_count == 2


@pytest.mark.parametrize(
    "payload", [None, [], {"is_error": True}, {}, {"result": 3}, {"result": " "}]
)
def test_incomplete_result_is_not_clean(launch, payload):
    launch.side_effect = [response(AUTH), response(payload)]
    assert sub.invoke_subscription_review("review")[0] != 0
    assert launch.call_count == 2


def test_invalid_result_json(launch):
    launch.side_effect = [response(AUTH), SimpleNamespace(stdout="not-json", returncode=0)]
    assert sub.invoke_subscription_review("review")[0] != 0


def test_nonzero_cli_does_not_fall_back_or_expose_output(launch):
    launch.side_effect = [response(AUTH), response("private output", 7)]
    code, message = sub.invoke_subscription_review("review")
    assert code == 7 and "private output" not in message
    assert launch.call_count == 2


def test_reply_is_never_silently_truncated(launch):
    launch.side_effect = [response(AUTH), response({"result": "NO FINDINGS plus omitted finding"})]
    code, message = sub.invoke_subscription_review("review", reply_chars=11)
    assert code != 0 and "not truncated" in message


def test_pro_is_a_verified_subscription(launch):
    launch.side_effect = [
        response({**AUTH, "subscriptionType": "pro"}),
        response({"result": "NO FINDINGS"}),
    ]
    assert sub.invoke_subscription_review("review") == (0, "NO FINDINGS")
