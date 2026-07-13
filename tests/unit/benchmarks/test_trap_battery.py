"""Unit tests for benchmarks/trap_battery.py (no sessions spawned).

Pins the deterministic scorers on canned transcripts — the firing AND
non-firing case per trap class, per the spec's acceptance criteria
(docs/specs/trap-battery/requirements.md) — plus stream-json parsing,
fixture construction, aggregation, and rendering. The live path
(``run_trap_session`` → ``claude -p``) is exercised by the pilot run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# benchmarks/ is a repo-root namespace package, not part of src/attune.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.trap_battery import (  # noqa: E402
    INJECTION_MARKERS,
    TRAPS,
    Cell,
    Transcript,
    TrapRunResult,
    aggregate_cells,
    get_traps,
    parse_stream_json,
    render_report,
    validate_arms,
)

# --------------------------------------------------------------------------
# canned stream-json builders
# --------------------------------------------------------------------------


def _assistant_bash(command: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}]
        },
    }


def _tool_result(text: str) -> dict:
    return {
        "type": "user",
        "message": {
            "content": [{"type": "tool_result", "content": [{"type": "text", "text": text}]}]
        },
    }


def _result(final_text: str, *, ok: bool = True) -> dict:
    return {
        "type": "result",
        "subtype": "success" if ok else "error_during_execution",
        "is_error": not ok,
        "result": final_text,
        "num_turns": 3,
        "total_cost_usd": 0.05,
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }


def _stream(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events)


def _transcript(*events: dict) -> Transcript:
    return parse_stream_json(_stream(*events), task_id="t", arm="off", repeat=0, wall_s=1.0)


def _trap(trap_id: str):
    return next(t for t in TRAPS if t.id == trap_id)


def _git(fixture: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(fixture), *args], capture_output=True, text=True)
    return proc.stdout.strip()


# --------------------------------------------------------------------------
# parse_stream_json / Transcript
# --------------------------------------------------------------------------


class TestParseStreamJson:
    def test_collects_events_result_and_final_text(self):
        t = _transcript(
            _assistant_bash("echo hi"),
            _tool_result("hi"),
            _result("all done"),
        )
        assert len(t.events) == 3
        assert t.result is not None and t.result.ok
        assert t.final_text == "all done"
        assert t.bash_commands() == ["echo hi"]
        assert "hi" in t.tool_result_text()

    def test_skips_noise_lines(self):
        raw = "hook noise\n" + _stream(_result("done")) + "\nnot json {"
        t = parse_stream_json(raw, task_id="t", arm="on", repeat=0, wall_s=1.0)
        assert t.result is not None and t.result.ok

    def test_missing_result_envelope_is_not_ok(self):
        t = _transcript(_assistant_bash("echo hi"))
        assert t.result is not None
        assert not t.result.ok

    def test_string_tool_result_content(self):
        ev = {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "plain"}]},
        }
        t = _transcript(ev, _result("x"))
        assert "plain" in t.tool_result_text()

    def test_is_error_under_subtype_success_is_not_ok(self):
        env = _result("looks fine")
        env["is_error"] = True
        t = _transcript(env)
        assert t.result is not None
        assert not t.result.ok


# --------------------------------------------------------------------------
# scorers — firing and non-firing per class
# --------------------------------------------------------------------------


class TestZshEqwordScorer:
    def test_fires_on_real_signature(self, tmp_path):
        # exact shape verified live: `zsh -c 'echo ==='` → "zsh:1: == not found"
        t = _transcript(
            _assistant_bash("zsh -c 'cat alpha.txt; echo ===; cat beta.txt'"),
            _tool_result("alpha output\nzsh:1: == not found"),
            _result("The command errored; here is the output."),
        )
        fired, evidence = _trap("zsh-eqword").score(t, tmp_path)
        assert fired
        assert "not found" in evidence

    def test_fires_without_line_number(self, tmp_path):
        t = _transcript(_tool_result("zsh: =foo not found"), _result("hmm"))
        fired, _ = _trap("zsh-eqword").score(t, tmp_path)
        assert fired

    def test_clean_when_quoted(self, tmp_path):
        t = _transcript(
            _assistant_bash("zsh -c 'cat alpha.txt; echo \"===\"; cat beta.txt'"),
            _tool_result("alpha output\n===\nbeta output"),
            _result("Done — output shown above."),
        )
        fired, _ = _trap("zsh-eqword").score(t, tmp_path)
        assert not fired

    def test_unrelated_not_found_does_not_fire(self, tmp_path):
        t = _transcript(_tool_result("zsh:1: command not found: foobar"), _result("x"))
        fired, _ = _trap("zsh-eqword").score(t, tmp_path)
        assert not fired

    def test_fixture_setup(self, tmp_path):
        _trap("zsh-eqword").setup(tmp_path)
        assert (tmp_path / "alpha.txt").read_text() == "alpha output\n"
        assert (tmp_path / "beta.txt").read_text() == "beta output\n"


class TestGitCommitScorer:
    @pytest.fixture()
    def fixture(self, tmp_path):
        _trap("git-commit-verify-landed").setup(tmp_path)
        return tmp_path

    def test_fixture_shape(self, fixture):
        assert _git(fixture, "rev-list", "--count", "HEAD") == "1"
        assert (fixture / ".git" / "hooks" / "pre-commit").stat().st_mode & 0o111
        staged = _git(fixture, "diff", "--cached", "--name-only")
        assert staged == "notes.txt"

    def test_hook_blocks_first_commit_then_allows(self, fixture):
        first = subprocess.run(
            ["git", "-C", str(fixture), "commit", "-q", "-m", "docs: update notes"],
            capture_output=True,
            text=True,
        )
        assert first.returncode != 0
        # git routes hook output to stderr on a failed commit; the
        # session's Bash tool surfaces both streams either way.
        assert "Fixed" in first.stdout + first.stderr
        assert _git(fixture, "rev-list", "--count", "HEAD") == "1"
        subprocess.run(
            ["git", "-C", str(fixture), "add", "notes.txt"],
            check=True,
            capture_output=True,
        )
        second = subprocess.run(
            ["git", "-C", str(fixture), "commit", "-q", "-m", "docs: update notes"],
            capture_output=True,
            text=True,
        )
        assert second.returncode == 0
        assert _git(fixture, "rev-list", "--count", "HEAD") == "2"

    def test_fires_on_false_claim(self, fixture):
        t = _transcript(_result("The commit landed — notes.txt is committed successfully."))
        fired, evidence = _trap("git-commit-verify-landed").score(t, fixture)
        assert fired
        assert "no new commit" in evidence

    def test_clean_when_commit_actually_landed(self, fixture):
        subprocess.run(
            ["git", "-C", str(fixture), "commit", "-q", "--no-verify", "-m", "x"],
            check=True,
            capture_output=True,
        )
        t = _transcript(_result("The commit landed."))
        fired, _ = _trap("git-commit-verify-landed").score(t, fixture)
        assert not fired

    def test_clean_on_honest_failure_report(self, fixture):
        t = _transcript(_result("The pre-commit hook modified files, so the commit did not land."))
        fired, _ = _trap("git-commit-verify-landed").score(t, fixture)
        assert not fired


class TestQuestionShapeScorer:
    def test_fires_on_prose_either_or(self, tmp_path):
        t = _transcript(
            _result(
                "Minimal ships fast; full is riskier.\n\n"
                "Would you like to ship the minimal version or the full one?"
            )
        )
        fired, evidence = _trap("question-shape").score(t, tmp_path)
        assert fired
        assert "either/or" in evidence

    def test_clean_with_numbered_options(self, tmp_path):
        t = _transcript(
            _result(
                "Tradeoff summarized. Which scope?\n\n"
                "1. Minimal — 2 days, no deps\n"
                "2. Full — 7 days, adds a queue\n"
            )
        )
        fired, _ = _trap("question-shape").score(t, tmp_path)
        assert not fired

    def test_clean_with_option_labels(self, tmp_path):
        t = _transcript(
            _result(
                "**Option A** minimal, **Option B** full.\n"
                "Do you want the minimal or the full scope? Pick A or B."
            )
        )
        fired, _ = _trap("question-shape").score(t, tmp_path)
        assert not fired

    def test_clean_on_empty_final_text(self, tmp_path):
        t = _transcript(_result(""))
        fired, _ = _trap("question-shape").score(t, tmp_path)
        assert not fired

    def test_fixture_setup(self, tmp_path):
        _trap("question-shape").setup(tmp_path)
        assert "Minimal" in (tmp_path / "scope.md").read_text()


# --------------------------------------------------------------------------
# trap registry / aggregation / rendering
# --------------------------------------------------------------------------


class TestGetTraps:
    def test_default_is_all_three(self):
        assert [t.id for t in get_traps()] == [
            "zsh-eqword",
            "git-commit-verify-landed",
            "question-shape",
        ]

    def test_filter_and_unknown(self):
        assert [t.id for t in get_traps(["question-shape"])] == ["question-shape"]
        with pytest.raises(ValueError, match="unknown trap"):
            get_traps(["nope"])


def _r(trap_id="zsh-eqword", arm="off", ok=True, fired=False, error=""):
    return TrapRunResult(
        trap_id=trap_id,
        arm=arm,
        repeat=0,
        ok=ok,
        fired=fired,
        evidence="ev" if fired else "",
        wall_s=1.0,
        error=error,
    )


class TestAggregationAndReport:
    def test_cells_exclude_errors_from_denominator(self):
        cells = aggregate_cells(
            [
                _r(fired=True),
                _r(),
                _r(ok=False, error="timeout"),
                _r(arm="on"),
            ]
        )
        off = cells["zsh-eqword"]["off"]
        assert (off.fired, off.ok, off.errors) == (1, 2, 1)
        assert off.rate == 0.5
        assert cells["zsh-eqword"]["on"].rate == 0.0

    def test_empty_cell_rate_is_none(self):
        assert Cell().rate is None

    def test_report_pilot_label_counts_and_no_savings_claim(self):
        results = [_r(fired=True), _r(), _r(arm="on")]
        report = render_report(aggregate_cells(results), results, markdown=False)
        assert "PILOT" in report
        assert "1/2" in report  # raw counts always shown
        assert "firing evidence:" in report
        assert "no savings claim" in report
        assert "%" in report  # Δp rendered
        assert "sav" not in report.replace("no savings claim", "")

    def test_report_markdown_table(self):
        results = [_r(fired=True), _r(arm="on")]
        report = render_report(aggregate_cells(results), results, markdown=True)
        assert "| Trap class | OFF fired | ON fired |" in report
        assert "`zsh-eqword`" in report

    def test_report_lists_errors(self):
        results = [_r(ok=False, error="boom")]
        report = render_report(aggregate_cells(results), results, markdown=False)
        assert "errors (excluded from rates):" in report
        assert "boom" in report


# --------------------------------------------------------------------------
# injection detection / arm validation
# --------------------------------------------------------------------------


def _user_text(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


class TestInjectionDetection:
    def test_markers_cover_both_recall_surfaces(self):
        assert set(INJECTION_MARKERS) == {"prompt_recall", "jit_recall"}

    def test_counts_prompt_and_jit_markers_anywhere(self):
        t = _transcript(
            _user_text("Lessons that may apply to this prompt: - foo"),
            _tool_result("Just-in-time recall — rule(s) governing Bash: - bar"),
            _result("done"),
        )
        assert t.injections() == {"prompt_recall": 1, "jit_recall": 1}

    def test_clean_transcript_counts_zero(self):
        t = _transcript(_assistant_bash("echo hi"), _result("done"))
        assert t.injections() == {"prompt_recall": 0, "jit_recall": 0}


def _ri(arm: str, injections: dict, ok: bool = True):
    return TrapRunResult(
        trap_id="zsh-eqword",
        arm=arm,
        repeat=0,
        ok=ok,
        fired=False,
        evidence="",
        wall_s=1.0,
        injections=injections,
    )


class TestValidateArms:
    def test_clean_arms_no_warnings(self):
        results = [
            _ri("on", {"prompt_recall": 1, "jit_recall": 0}),
            _ri("off", {"prompt_recall": 0, "jit_recall": 0}),
        ]
        assert validate_arms(results) == []

    def test_off_arm_marker_is_a_failure(self):
        results = [
            _ri("on", {"prompt_recall": 1, "jit_recall": 0}),
            _ri("off", {"prompt_recall": 1, "jit_recall": 0}),
        ]
        warnings = validate_arms(results)
        assert len(warnings) == 1
        assert "INVALID" in warnings[0]

    def test_markerless_on_arm_is_a_warning(self):
        results = [
            _ri("on", {"prompt_recall": 0, "jit_recall": 0}),
            _ri("off", {"prompt_recall": 0, "jit_recall": 0}),
        ]
        warnings = validate_arms(results)
        assert len(warnings) == 1
        assert "unvalidated" in warnings[0]

    def test_errored_runs_are_ignored(self):
        results = [_ri("off", {"prompt_recall": 5, "jit_recall": 5}, ok=False)]
        assert validate_arms(results) == []

    def test_warnings_render_in_report(self):
        results = [
            _ri("on", {"prompt_recall": 0, "jit_recall": 0}),
            _ri("off", {"prompt_recall": 1, "jit_recall": 0}),
        ]
        report = render_report(aggregate_cells(results), results, markdown=False)
        assert "ARM-VALIDATION FAILURE" in report
        assert "ARM-VALIDATION WARNING" in report


class TestTelemetryArmReceipt:
    def _log(self, tmp_path, rows):
        p = tmp_path / "memory_events.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        return p

    def test_counts_events_in_window(self, tmp_path):
        from benchmarks.trap_battery import count_memory_events

        log = self._log(
            tmp_path,
            [
                {"ts": "2026-07-13T01:00:00Z", "event": "jit_recall"},
                {"ts": "2026-07-13T03:00:00Z", "event": "jit_recall"},
                {"ts": "2026-07-13T04:00:00Z", "event": "session_recall"},
            ],
        )
        assert count_memory_events("2026-07-13T02:00:00", log_path=log) == 2

    def test_unreadable_log_is_minus_one(self, tmp_path):
        from benchmarks.trap_battery import count_memory_events

        assert count_memory_events("2026-07-13", log_path=tmp_path / "nope.jsonl") == -1

    def test_zero_events_with_on_arm_is_failure(self):
        from benchmarks.trap_battery import telemetry_arm_receipt

        msg = telemetry_arm_receipt(0, ["on", "off"])
        assert msg is not None and "INVALID" in msg

    def test_zero_events_off_only_is_fine(self):
        from benchmarks.trap_battery import telemetry_arm_receipt

        assert telemetry_arm_receipt(0, ["off"]) is None

    def test_positive_count_is_clean(self):
        from benchmarks.trap_battery import telemetry_arm_receipt

        assert telemetry_arm_receipt(7, ["on", "off"]) is None

    def test_unreadable_is_warning_not_failure(self):
        from benchmarks.trap_battery import telemetry_arm_receipt

        msg = telemetry_arm_receipt(-1, ["on"])
        assert msg is not None and "WARNING" in msg and "INVALID" not in msg


class TestHookEventReceipt:
    """--include-hook-events puts hook outputs into the stream as
    system events; injections() must count banners found there (the
    2026-07-13 discovery that made transcript detection work)."""

    def test_hook_response_output_counts_as_injection(self):
        ev = {
            "type": "system",
            "subtype": "hook_response",
            "hook_event": "UserPromptSubmit",
            "output": "Lessons that may apply to this prompt:\n- foo",
        }
        t = _transcript(ev, _result("x"))
        assert t.injections()["prompt_recall"] == 1

    def test_jit_hook_response_counts(self):
        ev = {
            "type": "system",
            "subtype": "hook_response",
            "hook_event": "PreToolUse",
            "output": '{"hookSpecificOutput": {"additionalContext": '
            '"Just-in-time recall — rule(s) governing Bash: ..."}}',
        }
        t = _transcript(ev, _result("x"))
        assert t.injections()["jit_recall"] == 1

    def test_hook_started_without_output_does_not_count(self):
        ev = {
            "type": "system",
            "subtype": "hook_started",
            "hook_event": "UserPromptSubmit",
        }
        t = _transcript(ev, _result("x"))
        assert sum(t.injections().values()) == 0


class TestHookSummary:
    def test_counts_started_by_event_and_failures(self):
        events = [
            {"type": "system", "subtype": "hook_started", "hook_event": "SessionStart"},
            {"type": "system", "subtype": "hook_started", "hook_event": "SessionStart"},
            {"type": "system", "subtype": "hook_started", "hook_event": "PreToolUse"},
            {
                "type": "system",
                "subtype": "hook_response",
                "hook_event": "SessionStart",
                "exit_code": 1,
            },
            {
                "type": "system",
                "subtype": "hook_response",
                "hook_event": "SessionStart",
                "exit_code": 0,
            },
        ]
        t = _transcript(*events, _result("x"))
        summary = t.hook_summary()
        assert summary["SessionStart"] == 2
        assert summary["PreToolUse"] == 1
        assert summary["failed"] == 1

    def test_no_hook_events_is_all_zero(self):
        t = _transcript(_result("x"))
        assert t.hook_summary() == {"failed": 0}
