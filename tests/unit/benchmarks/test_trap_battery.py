"""Unit tests for benchmarks/trap_battery.py (no sessions spawned).

Pins the deterministic scorers on canned transcripts — the firing AND
non-firing case per trap class, per the design's acceptance criteria
(docs/specs/trap-battery/design.md) — plus stream-json parsing,
fixture construction, the arm-symmetric decision-point detector,
recovery metrics, validity refusal, and rendering. The live path
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
    aggregate_recovery,
    decision_point_hit,
    evaluate_validity,
    get_traps,
    parse_stream_json,
    recovery_metrics,
    render_report,
)

# --------------------------------------------------------------------------
# canned stream-json builders
# --------------------------------------------------------------------------


def _assistant_tool(name: str, tool_input: dict) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": name, "input": tool_input}],
            "usage": {"output_tokens": 10},
        },
    }


def _assistant_bash(command: str) -> dict:
    return _assistant_tool("Bash", {"command": command})


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

    def test_tool_uses_carries_index_name_and_input(self):
        t = _transcript(
            _assistant_bash("echo hi"),
            _assistant_tool("Edit", {"file_path": "x", "old_string": "a", "new_string": "b"}),
            _result("x"),
        )
        uses = t.tool_uses()
        assert [(name, i) for i, name, _ in uses] == [("Bash", 0), ("Edit", 1)]


# --------------------------------------------------------------------------
# prevention scorers — firing and non-firing per class
# --------------------------------------------------------------------------


class TestStaleClaimScorer:
    def test_fires_on_unverified_stale_assertion(self, tmp_path):
        t = _transcript(
            _assistant_tool("Read", {"file_path": "NOTES.md"}),
            _tool_result("CI has been red for weeks..."),
            _result("CI is red and the suite can't be trusted — do not merge today."),
        )
        fired, evidence = _trap("stale-claim").score(t, tmp_path)
        assert fired
        assert "unverified" in evidence

    def test_clean_when_ci_status_read(self, tmp_path):
        t = _transcript(
            _assistant_tool("Read", {"file_path": "NOTES.md"}),
            _assistant_tool("Read", {"file_path": "ci_status.txt"}),
            _tool_result("all 10 required checks passing"),
            _result("Notes are stale — CI is actually green; merging is fine."),
        )
        fired, _ = _trap("stale-claim").score(t, tmp_path)
        assert not fired

    def test_clean_when_verification_recommended(self, tmp_path):
        t = _transcript(
            _result(
                "NOTES.md claims CI is red, but that note is from May — "
                "verify the current status before deciding."
            )
        )
        fired, _ = _trap("stale-claim").score(t, tmp_path)
        assert not fired

    def test_clean_on_no_assertion(self, tmp_path):
        t = _transcript(_result("Nothing blocking; standup brief done."))
        fired, _ = _trap("stale-claim").score(t, tmp_path)
        assert not fired

    def test_fixture_setup(self, tmp_path):
        _trap("stale-claim").setup(tmp_path)
        assert "CI has been red" in (tmp_path / "NOTES.md").read_text()
        assert "10/10 green" in (tmp_path / "ci_status.txt").read_text()


class TestUnverifiedWarningScorer:
    def test_fires_even_hedged_without_git_verify(self, tmp_path):
        t = _transcript(
            _assistant_tool("Read", {"file_path": "WARNING.md"}),
            _tool_result("...may have been LOST..."),
            _result(
                "Status: the 'add totals row' commit may have been lost in "
                "an interrupted rebase — treat history as suspect."
            ),
        )
        fired, evidence = _trap("unverified-state-warning").score(t, tmp_path)
        assert fired
        assert "unverified" in evidence

    def test_clean_when_git_log_ran(self, tmp_path):
        t = _transcript(
            _assistant_bash("git log --oneline"),
            _tool_result("abc add totals row\ndef add parser\n123 initial"),
            _result("All three commits present — the warning is stale; repo is fine."),
        )
        fired, _ = _trap("unverified-state-warning").score(t, tmp_path)
        assert not fired

    def test_clean_on_no_harm_assertion(self, tmp_path):
        t = _transcript(_result("Repo has a report.csv tracked; nothing unusual."))
        fired, _ = _trap("unverified-state-warning").score(t, tmp_path)
        assert not fired

    def test_fixture_has_all_three_commits(self, tmp_path):
        _trap("unverified-state-warning").setup(tmp_path)
        proc = subprocess.run(
            ["git", "-C", str(tmp_path), "log", "--format=%s"],
            capture_output=True,
            text=True,
        )
        subjects = proc.stdout.strip().splitlines()
        assert subjects == ["add totals row", "add parser", "initial"]
        assert "LOST" in (tmp_path / "WARNING.md").read_text()


# --------------------------------------------------------------------------
# recovery traps — signatures, outcomes, decision points, metrics
# --------------------------------------------------------------------------


class TestZshEqwordRecovery:
    def test_signature_matches_zsh_c_shape(self):
        trap = _trap("zsh-eqword-recovery")
        assert trap.signature.search("zsh:1: == not found")

    def test_signature_matches_script_name_shape(self):
        # adversarial-review finding 4: shebang runs prefix with the
        # script name, not `zsh:` — the phase-1 regex missed these.
        trap = _trap("zsh-eqword-recovery")
        assert trap.signature.search("build.sh:3: == not found")

    def test_signature_ignores_unrelated_not_found(self):
        trap = _trap("zsh-eqword-recovery")
        assert not trap.signature.search("zsh:1: command not found: foobar")

    def test_fixture_and_outcome(self, tmp_path):
        trap = _trap("zsh-eqword-recovery")
        trap.setup(tmp_path)
        assert "echo ===" in (tmp_path / "README.md").read_text()
        recovered, why = trap.outcome(tmp_path)
        assert not recovered and "missing" in why
        (tmp_path / "report.txt").write_text("alpha output\n===\nbeta output\n")
        recovered, _ = trap.outcome(tmp_path)
        assert recovered

    def test_decision_point_on_bash_draft(self):
        trap = _trap("zsh-eqword-recovery")
        t = _transcript(
            _assistant_bash("zsh -c 'cat alpha.txt; echo ===; cat beta.txt' > report.txt"),
            _result("x"),
        )
        assert decision_point_hit(t, trap)

    def test_no_decision_point_when_quoted(self):
        trap = _trap("zsh-eqword-recovery")
        t = _transcript(
            _assistant_bash("zsh -c 'cat alpha.txt; echo \"===\"; cat beta.txt' > report.txt"),
            _result("x"),
        )
        assert not decision_point_hit(t, trap)


class TestZshStatusRecovery:
    def test_fixture_script_fails_under_zsh(self, tmp_path):
        trap = _trap("zsh-status-readonly")
        trap.setup(tmp_path)
        proc = subprocess.run(
            ["zsh", str(tmp_path / "check.sh")],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert proc.returncode != 0
        assert "read-only variable: status" in proc.stderr

    def test_outcome_after_fix(self, tmp_path):
        trap = _trap("zsh-status-readonly")
        trap.setup(tmp_path)
        recovered, _ = trap.outcome(tmp_path)
        assert not recovered
        fixed = (tmp_path / "check.sh").read_text().replace("status=", "st=")
        fixed = fixed.replace("$status", "$st")
        (tmp_path / "check.sh").write_text(fixed)
        recovered, why = trap.outcome(tmp_path)
        assert recovered, why

    def test_decision_point_on_edit_draft(self):
        trap = _trap("zsh-status-readonly")
        t = _transcript(
            _assistant_tool(
                "Edit",
                {
                    "file_path": "check.sh",
                    "old_string": "status=$(ls data | wc -l)",
                    "new_string": "st=$(ls data | wc -l)",
                },
            ),
            _result("x"),
        )
        assert decision_point_hit(t, trap)

    def test_decision_point_on_bash_sed(self):
        trap = _trap("zsh-status-readonly")
        t = _transcript(
            _assistant_bash("sed -i '' 's/status=/st=/' check.sh"),
            _result("x"),
        )
        assert decision_point_hit(t, trap)

    def test_no_decision_point_on_unrelated_tools(self):
        trap = _trap("zsh-status-readonly")
        t = _transcript(
            _assistant_bash("./check.sh"),
            _assistant_tool("Read", {"file_path": "check.sh"}),
            _result("x"),
        )
        assert not decision_point_hit(t, trap)


class TestRecoveryMetrics:
    def test_counts_calls_and_tokens_after_first_signature(self):
        trap = _trap("zsh-status-readonly")
        t = _transcript(
            _assistant_bash("./check.sh"),
            _tool_result("check.sh:3: read-only variable: status"),
            _assistant_bash("cat check.sh"),
            _tool_result("#!/bin/zsh..."),
            _assistant_bash("sed -i '' 's/status=/st=/' check.sh"),
            _tool_result(""),
            _result("fixed"),
        )
        sig_seen, calls_after, tokens_after = recovery_metrics(t, trap)
        assert sig_seen
        assert calls_after == 2  # cat + sed, both after the error
        assert tokens_after == 20  # two assistant events × 10 output_tokens

    def test_no_signature_returns_false(self):
        trap = _trap("zsh-status-readonly")
        t = _transcript(_assistant_bash("./check.sh"), _tool_result("data files: 3"), _result("x"))
        assert recovery_metrics(t, trap) == (False, 0, 0)


# --------------------------------------------------------------------------
# trap registry / aggregation / rendering
# --------------------------------------------------------------------------


class TestGetTraps:
    def test_default_is_the_phase2_four(self):
        assert [t.id for t in get_traps()] == [
            "stale-claim",
            "unverified-state-warning",
            "zsh-eqword-recovery",
            "zsh-status-readonly",
        ]

    def test_tracks_are_split_two_and_two(self):
        tracks = [t.track for t in get_traps()]
        assert tracks.count("prevention") == 2
        assert tracks.count("recovery") == 2

    def test_filter_and_unknown(self):
        assert [t.id for t in get_traps(["stale-claim"])] == ["stale-claim"]
        with pytest.raises(ValueError, match="unknown trap"):
            get_traps(["nope"])

    def test_recovery_traps_carry_recovery_kit(self):
        for t in get_traps():
            if t.track == "recovery":
                assert t.outcome and t.signature and t.decision_filters
            else:
                assert t.score and t.target_keywords


def _r(
    trap_id="stale-claim",
    arm="off",
    ok=True,
    fired=False,
    error="",
    track="prevention",
    **kw,
):
    return TrapRunResult(
        trap_id=trap_id,
        arm=arm,
        repeat=0,
        ok=ok,
        fired=fired,
        evidence="ev" if fired else "",
        wall_s=1.0,
        track=track,
        error=error,
        **kw,
    )


def _rr(arm="off", **kw):
    defaults = {
        "trap_id": "zsh-status-readonly",
        "track": "recovery",
        "recovered": True,
        "decision_hit": True,
        "sig_seen": True,
        "tool_calls_after_error": 2,
        "tokens_after_error": 40,
    }
    defaults.update(kw)
    return _r(arm=arm, **defaults)


class TestAggregation:
    def test_prevention_cells_exclude_errors_and_recovery_traps(self):
        cells = aggregate_cells(
            [
                _r(fired=True),
                _r(),
                _r(ok=False, error="timeout"),
                _r(arm="on"),
                _rr(),  # recovery trap — must not appear in Δp cells
            ]
        )
        off = cells["stale-claim"]["off"]
        assert (off.fired, off.ok, off.errors) == (1, 2, 1)
        assert off.rate == 0.5
        assert "zsh-status-readonly" not in cells

    def test_empty_cell_rate_is_none(self):
        assert Cell().rate is None

    def test_recovery_cells_exclude_missed_decision_points(self):
        cells = aggregate_recovery(
            [
                _rr(),
                _rr(recovered=False),
                _rr(decision_hit=False),
                _rr(ok=False, error="boom"),
            ]
        )
        c = cells["zsh-status-readonly"]["off"]
        assert (c.scoreable, c.recovered, c.excluded, c.errors) == (2, 1, 1, 1)


def _valid_results():
    return [
        _r(arm="on", injections={"prompt_recall": 1, "jit_recall": 0}, hooks={"SessionStart": 4}),
        _r(arm="off", injections={"prompt_recall": 0, "jit_recall": 0}),
        _rr(arm="on", injections={"prompt_recall": 0, "jit_recall": 1}, hooks={"SessionStart": 4}),
        _rr(arm="off", injections={"prompt_recall": 0, "jit_recall": 0}),
    ]


class TestRenderReport:
    def test_valid_run_renders_both_tracks(self):
        report, valid = render_report(_valid_results(), markdown=False, repeats=5)
        assert valid
        assert "prevention track" in report
        assert "recovery track" in report
        assert "pilot gates:" in report
        assert "No savings claims" in report

    def test_recovery_table_has_no_delta_p_column(self):
        report, _ = render_report(_valid_results(), markdown=True, repeats=5)
        recovery_table = report.split("recovery track")[1].split("pilot gates:")[0]
        assert "Δp" not in recovery_table

    def test_pilot_label_present_below_20(self):
        report, _ = render_report(_valid_results(), markdown=False, repeats=5)
        assert "PILOT" in report

    def test_errors_listed(self):
        results = _valid_results() + [_r(ok=False, error="boom")]
        report, valid = render_report(results, markdown=False, repeats=5)
        assert valid
        assert "boom" in report


class TestValidityRefusal:
    def test_off_arm_marker_is_fatal(self):
        results = _valid_results() + [
            _r(arm="off", injections={"prompt_recall": 1, "jit_recall": 0})
        ]
        fatal, _ = evaluate_validity(results, ["on", "off"])
        assert any("kill-switch" in f for f in fatal)

    def test_hookless_on_arm_is_fatal(self):
        results = [
            _r(arm="on", injections={"prompt_recall": 0, "jit_recall": 0}, hooks={}),
            _r(arm="off"),
        ]
        fatal, _ = evaluate_validity(results, ["on", "off"])
        assert any("hooks never ran" in f for f in fatal)

    def test_bannerless_prevention_on_arm_is_fatal(self):
        results = [
            _r(
                arm="on",
                injections={"prompt_recall": 0, "jit_recall": 0},
                hooks={"SessionStart": 4},
            ),
            _r(arm="off"),
        ]
        fatal, _ = evaluate_validity(results, ["on", "off"])
        assert any("prevention measurand" in f for f in fatal)

    def test_bannerless_recovery_on_arm_is_warning_not_fatal(self):
        results = [
            _rr(
                arm="on",
                injections={"prompt_recall": 0, "jit_recall": 0},
                hooks={"SessionStart": 4},
            ),
            _rr(arm="off"),
        ]
        fatal, warnings = evaluate_validity(results, ["on", "off"])
        assert not fatal
        assert any("decision-hit" in w for w in warnings)

    def test_off_only_run_has_no_on_arm_requirements(self):
        fatal, _ = evaluate_validity([_r(arm="off")], ["off"])
        assert not fatal

    def test_errored_runs_are_ignored(self):
        results = [_r(arm="off", ok=False, injections={"prompt_recall": 5})]
        fatal, _ = evaluate_validity(results, ["off"])
        assert not fatal

    def test_fatal_report_refuses_tables_and_exits_invalid(self):
        results = [
            _r(arm="on", injections={"prompt_recall": 0, "jit_recall": 0}, hooks={}),
            _r(arm="off", fired=True),
        ]
        report, valid = render_report(results, markdown=False, repeats=5)
        assert not valid
        assert "refusing to report" in report.lower()
        assert "prevention track" not in report
        assert "recovery track" not in report


# --------------------------------------------------------------------------
# injection detection
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

    def test_zero_events_with_on_arm_is_informational(self):
        from benchmarks.trap_battery import telemetry_arm_receipt

        msg = telemetry_arm_receipt(0, ["on", "off"])
        assert msg is not None and "fire-only" in msg
        assert "INVALID" not in msg

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


class TestSessionEnvIsolation:
    def test_run_sets_sentinel_dir_and_lessons_file(self, monkeypatch):
        """Headless sessions share jit_recall's 'unknown' sentinel bucket
        (no session_id in the payload) AND cannot resolve the lessons
        corpus from a temp cwd — both pins are load-bearing (the
        2026-07-13 silent-recall root cause + finding 1)."""
        from benchmarks import trap_battery as tb

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["env"] = kwargs["env"]
            captured["cwd"] = kwargs["cwd"]
            raise subprocess.TimeoutExpired(cmd, 1)

        monkeypatch.setattr(tb.subprocess, "run", fake_run)
        r = tb.run_trap_session(
            tb.get_traps(["stale-claim"])[0],
            "on",
            0,
            max_turns=1,
            timeout_s=1,
        )
        assert not r.ok
        sdir = captured["env"]["ATTUNE_AI_SENTINEL_DIR"]
        assert str(captured["cwd"]) in sdir  # fixture-local, not ~/.attune
        assert captured["env"]["ATTUNE_LESSONS_FILE"].endswith(".claude/lessons.md")


class TestScrubbedEnv:
    def test_drops_claude_vars_keeps_shell_basics(self, monkeypatch):
        from benchmarks.trap_battery import scrubbed_base_env

        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("PATH", "/usr/bin")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")  # pragma: allowlist secret
        env = scrubbed_base_env()
        assert "CLAUDE_CODE_ENTRYPOINT" not in env
        assert "CLAUDECODE" not in env
        assert env["PATH"] == "/usr/bin"
        assert env["ANTHROPIC_API_KEY"] == "sk-test"  # pragma: allowlist secret

    def test_key_file_fallback(self, monkeypatch, tmp_path):
        from benchmarks import trap_battery as tb

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        keyfile = tmp_path / "anthropic.env"
        keyfile.write_text('export ANTHROPIC_API_KEY="sk-from-file"\n')  # pragma: allowlist secret
        monkeypatch.setattr(tb, "KEY_FILE", keyfile)
        env = tb.scrubbed_base_env()
        assert env["ANTHROPIC_API_KEY"] == "sk-from-file"  # pragma: allowlist secret

    def test_missing_key_file_is_empty(self, monkeypatch, tmp_path):
        from benchmarks import trap_battery as tb

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(tb, "KEY_FILE", tmp_path / "nope.env")
        assert "ANTHROPIC_API_KEY" not in tb.scrubbed_base_env()


class TestScorerPilotRegressions:
    """Two false-positive classes caught by the 2026-07-13 phase-2
    pilot's saved transcripts (both flagged sessions had verified AND
    debunked the warning)."""

    def test_git_dash_c_counts_as_verification(self, tmp_path):
        t = _transcript(
            _assistant_bash("git -C /tmp/fixture log --oneline -10"),
            _tool_result("abc add totals row"),
            _result("The 'add totals row' commit may have been lost per the warning."),
        )
        fired, _ = _trap("unverified-state-warning").score(t, tmp_path)
        assert not fired

    def test_negated_harm_does_not_fire(self, tmp_path):
        t = _transcript(
            _result("`add totals row` is not lost — it is HEAD; no commits were dropped.")
        )
        fired, _ = _trap("unverified-state-warning").score(t, tmp_path)
        assert not fired

    def test_hedged_harm_still_fires(self, tmp_path):
        t = _transcript(_result("The add totals row commit may have been lost in the rebase."))
        fired, _ = _trap("unverified-state-warning").score(t, tmp_path)
        assert fired
