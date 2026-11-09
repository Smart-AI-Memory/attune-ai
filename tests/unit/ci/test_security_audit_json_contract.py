"""Exercise the security JSON contract in the coverage controller process.

The sealed CLI tests remain independent. These tests replace the SDK query
and host services, while exercising the real result collector and exporter.
"""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest


class _UnexpectedHostAccess(BaseException):
    """Fail outside Exception handlers when a forbidden dependency is reached."""


def _structured():
    return {
        "summary": {"text": "Audit complete — café 🔐", "score": 100},
        "findings": {},
        "suggestions": [],
        "audit_complete": True,
    }


def _finding(severity="HIGH", line=7):
    return {"file": "src/café.py", "line": line, "severity": severity, "description": "Inspect 🔐"}


@pytest.fixture
def contract(monkeypatch):
    # Block dotenv discovery before lazy project imports. The controller also
    # starts in the suite's keyless environment before conftest collection.
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.delenv("ATTUNE_SDK_STREAM_DUMP", raising=False)
    monkeypatch.setenv("ATTUNE_SDK_ERROR_PROBE", "0")

    from attune.models import sdk_adapter, sdk_errors
    from attune.workflows import security_audit, security_audit_json
    from attune.workflows.config import WorkflowConfig

    def unexpected_query(**kwargs):
        raise _UnexpectedHostAccess("A test must install its synthetic SDK stream")

    def unexpected_probe(*args, **kwargs):
        raise _UnexpectedHostAccess("Contract tests must not probe the native CLI")

    monkeypatch.setattr(security_audit.claude_agent_sdk, "query", unexpected_query)
    monkeypatch.setattr(sdk_errors, "capture_subprocess_failure", unexpected_probe)
    # Exercise the real no-capability fallback without invoking the CLI probe.
    monkeypatch.setattr(sdk_adapter, "_CLI_SUPPORTS_TASK_BUDGET", False)
    cls = security_audit.SecurityAuditWorkflow
    monkeypatch.setattr(cls, "_init_telemetry", lambda *args, **kwargs: None)
    monkeypatch.setattr(cls, "_track_sdk_run_telemetry", lambda *args, **kwargs: None)
    monkeypatch.setattr(cls, "_emit_workflow_telemetry", lambda *args, **kwargs: None)
    transcript_reads = []
    transcripts = {}

    async def read_transcripts(session_id):
        transcript_reads.append(session_id)
        return deepcopy(transcripts)

    monkeypatch.setattr(security_audit, "collect_subagent_transcripts", read_transcripts)
    # Supply dependencies to the real constructor: no CostTracker disk store,
    # WorkflowConfig.load(), provider discovery, or telemetry store creation.
    workflow = cls(cost_tracker=object(), config=WorkflowConfig(), provider="anthropic")
    return SimpleNamespace(
        module=security_audit,
        exporter=security_audit_json,
        adapter=sdk_adapter,
        errors=sdk_errors,
        sdk=security_audit.claude_agent_sdk,
        workflow=workflow,
        transcripts=transcripts,
        transcript_reads=transcript_reads,
    )


def _run_result(contract, data, **signals):
    fields = {
        "result_text": "## Summary\nHuman report must not become the JSON payload.",
        "structured_output": data,
        "subtype": "success",
        "is_error": False,
        "stop_reason": "end_turn",
        "errors": None,
    }
    fields.update(signals)
    return contract.adapter.AgentRunResult(**fields)


def _terminal(contract, data, **signals):
    fields = {
        "subtype": "success",
        "duration_ms": 9,
        "duration_api_ms": 4,
        "is_error": False,
        "num_turns": 1,
        "session_id": "offline-contract-session",
        "stop_reason": "end_turn",
        "total_cost_usd": 0.0,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "result": "## Summary\nHuman report",
        "structured_output": data,
        "terminal_reason": "completed",
    }
    fields.update(signals)
    return contract.sdk.ResultMessage(**fields)


def _query(monkeypatch, contract, messages, error=None):
    calls = []

    async def query(*, prompt, options):
        calls.append((prompt, options))
        for message in messages:
            yield message
        if error is not None:
            raise error

    monkeypatch.setattr(contract.sdk, "query", query)
    return calls


@pytest.mark.parametrize("stop_reason", [None, "end_turn"])
@pytest.mark.parametrize("score", [None, 0, 100])
def test_completed_empty_audit_is_explicit_and_preserves_unicode(contract, stop_reason, score):
    data = _structured()
    if score is None:
        del data["summary"]["score"]
    else:
        data["summary"]["score"] = score
    before = deepcopy(data)
    encoded = contract.exporter.security_audit_json(
        _run_result(contract, data, stop_reason=stop_reason, errors=[])
    )
    assert "café 🔐" in encoded
    assert json.loads(encoded) == {
        "schema_version": "security-audit/v1",
        "workflow": "security-audit",
        "success": True,
        "audit_complete": True,
        "sdk_completion": {"subtype": "success", "is_error": False, "stop_reason": stop_reason},
        "summary": data["summary"],
        "findings": [],
        "suggestions": [],
    }
    assert data == before


def test_findings_retain_every_item_category_order_and_severity(contract):
    data = _structured()
    data["findings"] = {
        "vulnerabilities": [_finding("HIGH", 7), _finding("CRITICAL", 8)],
        "secrets": [_finding("medium", 9), _finding("low", 10)],
        "empty-category": [],
    }
    data["suggestions"] = [
        {"description": "Rotate 🔐", "priority": "high"},
        {"description": "Review"},
    ]
    before = deepcopy(data)
    payload = json.loads(contract.exporter.security_audit_json(_run_result(contract, data)))
    assert payload["findings"] == [
        {**_finding("high", 7), "category": "vulnerabilities", "type": "vulnerabilities"},
        {**_finding("critical", 8), "category": "vulnerabilities", "type": "vulnerabilities"},
        {**_finding("medium", 9), "category": "secrets", "type": "secrets"},
        {**_finding("low", 10), "category": "secrets", "type": "secrets"},
    ]
    assert len(payload["findings"]) == 4
    assert sum(item["severity"] in {"high", "critical"} for item in payload["findings"]) == 2
    assert payload["suggestions"] == data["suggestions"]
    assert data == before


@pytest.mark.parametrize(
    "signals",
    [
        {"subtype": None},
        {"subtype": "error_max_turns"},
        {"is_error": True},
        {"is_error": 0},
        {"errors": ["partial audit"]},
        {"errors": ""},
        {"stop_reason": "max_tokens"},
    ],
)
def test_terminal_errors_cannot_become_completed_empty_audits(contract, signals):
    with pytest.raises(ValueError, match="successful, error-free terminal result"):
        contract.exporter.security_audit_json(_run_result(contract, _structured(), **signals))


@pytest.mark.parametrize(
    "data", [None, "{}", {"result": _structured()}, {}, {**_structured(), "extra": 1}]
)
def test_only_complete_structured_objects_are_accepted(contract, data):
    with pytest.raises(ValueError, match="complete structured output object"):
        contract.exporter.security_audit_json(_run_result(contract, data))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("audit_complete", False, "affirm completion"),
        ("audit_complete", 1, "affirm completion"),
        ("summary", "complete", "summary is malformed"),
        ("summary", {}, "summary is malformed"),
        ("summary", {"text": " "}, "summary is malformed"),
        ("summary", {"text": "complete", "extra": 1}, "summary is malformed"),
        ("summary", {"text": "complete", "score": True}, "score must be an integer"),
        ("summary", {"text": "complete", "score": 1.5}, "score must be an integer"),
        ("summary", {"text": "complete", "score": -1}, "score must be an integer"),
        ("summary", {"text": "complete", "score": 101}, "score must be an integer"),
        ("findings", [], "category-to-list object"),
        ("findings", {" ": []}, "category is malformed"),
        ("findings", {"security": {}}, "category is malformed"),
        ("suggestions", {}, "suggestions are malformed"),
        ("suggestions", ["repair"], "suggestions are malformed"),
        ("suggestions", [{}], "suggestions are malformed"),
        ("suggestions", [{"description": " "}], "suggestions are malformed"),
        ("suggestions", [{"description": "repair", "extra": 1}], "suggestions are malformed"),
        ("suggestions", [{"description": "repair", "priority": 1}], "suggestions are malformed"),
        (
            "suggestions",
            [{"description": "repair", "priority": "urgent"}],
            "suggestions are malformed",
        ),
    ],
)
def test_malformed_fields_fail_closed(contract, field, value, message):
    data = _structured()
    data[field] = value
    with pytest.raises(ValueError, match=message):
        contract.exporter.security_audit_json(_run_result(contract, data))


@pytest.mark.parametrize(
    "finding",
    [
        None,
        {},
        {**_finding(), "extra": 1},
        {**_finding(), "file": " "},
        {**_finding(), "line": True},
        {**_finding(), "line": 0},
        {**_finding(), "description": " "},
        {**_finding(), "severity": None},
        {**_finding(), "severity": "urgent"},
    ],
)
def test_invalid_findings_are_rejected_instead_of_dropped(contract, finding):
    data = _structured()
    data["findings"] = {"security": [_finding(), finding]}
    with pytest.raises(ValueError, match="finding is incomplete or has an unsupported severity"):
        contract.exporter.security_audit_json(_run_result(contract, data))


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_serializer_failure_is_reported_without_changing_global_json(
    monkeypatch, contract, error_type
):
    failure = error_type("synthetic serializer failure")
    calls = []

    def dumps(payload, **kwargs):
        calls.append((payload, kwargs))
        raise failure

    monkeypatch.setattr(contract.exporter, "json", SimpleNamespace(dumps=dumps))
    with pytest.raises(ValueError, match="not serializable JSON") as raised:
        contract.exporter.security_audit_json(_run_result(contract, _structured()))
    assert raised.value.__cause__ is failure
    assert len(calls) == 1
    assert calls[0][0]["audit_complete"] is True
    assert calls[0][1] == {"ensure_ascii": False, "allow_nan": False}
    assert json.loads(json.dumps({"unaffected": True})) == {"unaffected": True}


@pytest.mark.asyncio
async def test_raw_collector_keeps_terminal_metadata_and_json_options(
    monkeypatch, contract, tmp_path
):
    data = _structured()
    data["findings"] = {"security": [_finding("CRITICAL")]}
    message = _terminal(contract, data)
    calls = _query(monkeypatch, contract, [message])
    result = await contract.workflow._run_agent_audit(
        str(tmp_path), 10, "quick", max_budget_usd=0.25, json_mode=True
    )
    assert isinstance(result, contract.adapter.AgentRunResult)
    assert result.structured_output == data
    assert (result.subtype, result.is_error, result.stop_reason, result.errors) == (
        "success",
        False,
        "end_turn",
        None,
    )
    assert (result.session_id, result.num_turns, result.duration_ms, result.duration_api_ms) == (
        "offline-contract-session",
        1,
        9,
        4,
    )
    assert result.result_text == "## Summary\nHuman report"
    assert len(calls) == 1
    prompt, options = calls[0]
    assert str(tmp_path) in prompt
    assert options.output_format == contract.exporter.SECURITY_AUDIT_JSON_SCHEMA
    assert contract.exporter.SECURITY_AUDIT_JSON_INSTRUCTION in options.system_prompt
    assert options.max_turns == 10
    assert options.max_budget_usd == 0.25
    assert options.setting_sources == []
    assert options.allowed_tools == ["Read", "Glob", "Grep", "Agent"]
    payload = json.loads(contract.exporter.security_audit_json(result))
    assert payload["findings"][0]["severity"] == "critical"
    assert contract.transcript_reads == []


@pytest.mark.asyncio
async def test_nonterminal_assistant_text_does_not_count_as_a_terminal(
    monkeypatch, contract, tmp_path
):
    data = _structured()
    assistant_text = (
        "Detailed assistant analysis remains available after the short terminal summary."
    )
    assistant = contract.sdk.AssistantMessage(
        content=[contract.sdk.types.TextBlock(text=assistant_text)],
        model="synthetic-contract-model",
    )
    terminal = _terminal(contract, data, result="Done.")
    calls = _query(monkeypatch, contract, [assistant, terminal])
    result = await contract.workflow._run_agent_audit(str(tmp_path), 20, json_mode=True)
    # build_result_text chooses the longer assistant text over this short summary.
    assert result.result_text == assistant_text
    assert result.structured_output == data
    assert result.subtype == "success"
    assert result.errors is None
    payload = json.loads(contract.exporter.security_audit_json(result))
    assert payload["success"] is True
    assert payload["audit_complete"] is True
    assert payload["sdk_completion"] == {
        "subtype": "success",
        "is_error": False,
        "stop_reason": "end_turn",
    }
    assert payload["summary"] == data["summary"]
    assert payload["findings"] == []
    assert len(calls) == 1
    assert contract.transcript_reads == []


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 2])
async def test_raw_collector_requires_exactly_one_terminal_result(
    monkeypatch, contract, tmp_path, count
):
    _query(monkeypatch, contract, [_terminal(contract, _structured()) for _ in range(count)])
    result = await contract.workflow._run_agent_audit(str(tmp_path), 20, json_mode=True)
    assert result.subtype == "error_terminal_result_count"
    assert result.errors == ["Security audit requires exactly one terminal SDK result"]
    with pytest.raises(ValueError, match="successful, error-free terminal result"):
        contract.exporter.security_audit_json(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "signals",
    [
        {"terminal_reason": None},
        {"terminal_reason": "aborted_streaming"},
        {"origin": {"kind": "task-notification"}},
        {"origin": {"kind": "human"}},
        {"api_error_status": 429},
        {
            "deferred_tool_use": {
                "id": "deferred",
                "name": "Read",
                "input": {"file_path": "src/a.py"},
            }
        },
    ],
)
async def test_raw_provenance_failure_reaches_execute_as_incomplete(
    monkeypatch, contract, tmp_path, signals
):
    signals = deepcopy(signals)
    if "deferred_tool_use" in signals:
        signals["deferred_tool_use"] = contract.sdk.types.DeferredToolUse(
            **signals["deferred_tool_use"]
        )
    _query(monkeypatch, contract, [_terminal(contract, _structured(), **signals)])
    result = await contract.workflow.execute(path=str(tmp_path), output_format="json")
    assert result.success is False
    assert "Incomplete security audit JSON" in result.error
    assert json.loads(result.final_output) == {
        "success": False,
        "audit_complete": False,
        "error": result.error,
    }
    assert contract.transcript_reads == []


@pytest.mark.asyncio
@pytest.mark.parametrize("severity", [None, "HIGH", "CRITICAL"])
@pytest.mark.parametrize("report", [None, "## Summary\nHuman report"])
async def test_execute_keeps_structured_json_despite_human_transcripts(
    monkeypatch, contract, tmp_path, severity, report
):
    data = _structured()
    if severity is not None:
        data["findings"] = {"security": [_finding(severity)]}
    contract.transcripts["agent-a"] = ["Human transcript enrichment"]
    calls = _query(monkeypatch, contract, [_terminal(contract, data, result=report)])
    result = await contract.workflow.execute(
        path=str(tmp_path), output_format="json", depth="deep", max_budget_usd=0.25
    )
    assert result.success is True
    payload = json.loads(result.final_output)
    assert payload["audit_complete"] is True
    assert len(payload["findings"]) == (0 if severity is None else 1)
    if severity is not None:
        assert payload["findings"][0] == {
            **_finding(severity.lower()),
            "category": "security",
            "type": "security",
        }
    assert payload["summary"] == data["summary"]
    assert "Human transcript enrichment" not in result.final_output
    assert "Human transcript enrichment" in result.metadata["raw_result_text"]
    assert result.metadata["path"] == str(tmp_path.resolve())
    assert result.metadata["max_turns"] == 40
    assert contract.transcript_reads == ["offline-contract-session"]
    assert len(calls) == 1
    assert calls[0][1].output_format == contract.exporter.SECURITY_AUDIT_JSON_SCHEMA


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [None, {**_structured(), "audit_complete": False}])
async def test_execute_refuses_partial_structured_output(monkeypatch, contract, tmp_path, data):
    _query(monkeypatch, contract, [_terminal(contract, data)])
    result = await contract.workflow.execute(path=str(tmp_path), output_format="json")
    assert result.success is False
    assert "Incomplete security audit JSON" in result.error
    assert json.loads(result.final_output) == {
        "success": False,
        "audit_complete": False,
        "error": result.error,
    }
    assert contract.transcript_reads == []


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [ImportError, ConnectionError, TimeoutError])
async def test_execute_preserves_query_failure(monkeypatch, contract, tmp_path, error_type):
    calls = _query(monkeypatch, contract, [], error=error_type("synthetic query failure"))
    result = await contract.workflow.execute(path=str(tmp_path), output_format="json")
    assert result.success is False
    assert "synthetic query failure" in result.error
    assert result.final_output is None
    assert len(calls) == 1
    assert contract.transcript_reads == []


@pytest.mark.asyncio
async def test_execute_preserves_classified_sdk_failure_without_reprobe(
    monkeypatch, contract, tmp_path
):
    error = contract.errors.SdkSubprocessError(
        message="Synthetic auth refusal", stderr="synthetic stderr", kind="auth"
    )
    _query(monkeypatch, contract, [], error=error)
    result = await contract.workflow.execute(path=str(tmp_path), output_format="json")
    assert result.success is False
    assert result.error == (
        "Synthetic auth refusal\n\n" "Full stderr is available on /runs/<id>/view."
    )
    assert result.final_output is None
    assert result.metadata == {"sdk_stderr": "synthetic stderr", "sdk_error_kind": "auth"}
    assert contract.transcript_reads == []


@pytest.mark.asyncio
async def test_execute_refuses_missing_path_before_query(contract):
    result = await contract.workflow.execute(output_format="json")
    assert result.success is False
    assert result.error == "path argument is required"
    assert result.final_output is None
    assert contract.transcript_reads == []


@pytest.mark.asyncio
async def test_human_mode_retains_report_without_json_completion_contract(
    monkeypatch, contract, tmp_path
):
    calls = _query(monkeypatch, contract, [_terminal(contract, None, terminal_reason=None)])
    result = await contract.workflow.execute(path=str(tmp_path), depth="quick")
    assert result.success is True
    assert result.final_output == "## Summary\nHuman report"
    assert contract.transcript_reads == ["offline-contract-session"]
    assert len(calls) == 1
    assert calls[0][1].output_format == contract.module.WORKFLOW_OUTPUT_SCHEMA
    assert contract.exporter.SECURITY_AUDIT_JSON_INSTRUCTION not in calls[0][1].system_prompt
