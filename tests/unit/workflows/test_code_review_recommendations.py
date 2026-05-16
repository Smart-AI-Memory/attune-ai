"""Tests for Phase 5.4 — code-review emits ATTUNE_REC recommendations.

Covers the `_emit_security_recommendation_if_warranted` helper:

- Fires on each documented security-trigger phrase (CWE/CVE id, SQL/
  command injection, path traversal, XSS/CSRF, hardcoded secrets,
  insecure deserialization / random, eval/exec).
- Does NOT fire on benign reviews (style nits, missing docstrings).
- Skipped when path or result_text is empty.
- Emits a well-formed ATTUNE_REC line that the ops runner's
  `handle_stdout_line` accepts.

Spec: docs/specs/ops-runner-tier2/ Phase 5.4.
"""

from __future__ import annotations

import io
import json

import pytest

from attune.workflows.code_review import _emit_security_recommendation_if_warranted


def _capture(result_text: str, scope: str = "src/foo") -> str:
    buf = io.StringIO()
    fired = _emit_security_recommendation_if_warranted(result_text, scope, output_stream=buf)
    captured = buf.getvalue()
    if fired:
        assert captured.startswith("ATTUNE_REC ")
    else:
        assert captured == ""
    return captured


@pytest.mark.parametrize(
    "trigger",
    [
        "Found a SQL injection in models.py",
        "Possible command injection at line 42",
        "Path traversal via user-controlled filename",
        "XSS sink in template rendering",
        "Reflective cross-site scripting on the search endpoint",
        "CSRF token not validated on POST",
        "Hardcoded secret in config.py",
        "Hardcoded API key found",
        "Insecure deserialization of user input",
        "Insecure random used for session id",
        "Found a CWE-79 vulnerability",
        "Matches CVE-2024-1234",
        "Uses eval( on user-controlled string",
        "Calls exec( with concatenated SQL",
    ],
)
def test_trigger_emits_recommendation(trigger: str) -> None:
    out = _capture(trigger)
    assert out, f"expected emission for trigger: {trigger!r}"
    payload = json.loads(out.removeprefix("ATTUNE_REC ").strip())
    assert payload == {
        "kind": "next-workflow",
        "name": "bug-predict",
        "args": {"path": "src/foo"},
        "label": "Run bug-predict to locate the specific lines",
        "severity": "high",
    }


@pytest.mark.parametrize(
    "benign",
    [
        "Missing docstring on function foo()",
        "Variable naming could be clearer",
        "Consider extracting this into a helper",
        "Style nit: trailing whitespace",
        "Performance: this loop is O(n^2)",
        "Architectural concern: tight coupling between modules",
        # Adjacent words that should NOT trigger
        "The injection point of this dependency is the constructor.",
    ],
)
def test_benign_review_does_not_emit(benign: str) -> None:
    assert _capture(benign) == ""


def test_skip_when_result_text_empty() -> None:
    assert _capture("") == ""


def test_skip_when_result_text_none() -> None:
    buf = io.StringIO()
    fired = _emit_security_recommendation_if_warranted(None, "src/foo", output_stream=buf)
    assert fired is False
    assert buf.getvalue() == ""


def test_skip_when_scope_empty() -> None:
    buf = io.StringIO()
    fired = _emit_security_recommendation_if_warranted(
        "Found a SQL injection", "", output_stream=buf
    )
    assert fired is False
    assert buf.getvalue() == ""


def test_payload_passes_runner_validation() -> None:
    """End-to-end: the emitted marker line must validate against
    RunnerService._validate_recommendation so the dashboard accepts it."""
    from pathlib import Path

    from attune.ops.runner import RunnerService

    # project_root needs to exist so _validate_file_path accepts paths
    # under it. Use the repo root — code-review's resolved path will
    # be inside it for any real run.
    repo_root = Path(__file__).resolve().parents[3]
    svc = RunnerService(project_root=repo_root)
    scope = str(repo_root / "src" / "attune" / "workflows")

    buf = io.StringIO()
    _emit_security_recommendation_if_warranted("Found SQL injection", scope, output_stream=buf)
    line = buf.getvalue().rstrip("\n")
    assert line.startswith("ATTUNE_REC ")
    payload = json.loads(line.removeprefix("ATTUNE_REC "))
    sanitized = svc._validate_recommendation(payload)
    assert sanitized is not None
    assert sanitized["name"] == "bug-predict"
    assert sanitized["args"] == {"path": scope}


def test_only_one_emission_per_call_even_with_multiple_triggers() -> None:
    """The helper emits at most one recommendation per call. Real
    reviews often mention multiple issues; we don't want to flood the
    card list with duplicates."""
    text = "Found SQL injection AND a hardcoded secret AND XSS in three files."
    out = _capture(text)
    assert out.count("ATTUNE_REC ") == 1
