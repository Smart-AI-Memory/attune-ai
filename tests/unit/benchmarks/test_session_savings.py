"""Unit tests for benchmarks/session_savings.py (pure functions only).

The live path (``run_session`` → ``claude -p``) is exercised manually;
these tests pin the parsing, arm-env, aggregation, and rendering logic
so the harness's numbers can be trusted without spending LLM usage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# benchmarks/ is a repo-root namespace package, not part of src/attune.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.session_savings import (  # noqa: E402
    ARM_ENV,
    DEFAULT_TASKS,
    RunResult,
    aggregate,
    build_env,
    load_tasks,
    parse_result_json,
    render_markdown,
    render_table,
    summary_rows,
)

RESULT_ENVELOPE = {
    "type": "result",
    "subtype": "success",
    "duration_ms": 42_000,
    "duration_api_ms": 30_500,
    "num_turns": 7,
    "total_cost_usd": 0.1234,
    "usage": {
        "input_tokens": 1_000,
        "cache_creation_input_tokens": 9_000,
        "cache_read_input_tokens": 250_000,
        "output_tokens": 2_500,
    },
}


def _kw(**over):
    kw = {"task_id": "t", "arm": "on", "repeat": 0, "wall_s": 45.0}
    kw.update(over)
    return kw


class TestParseResultJson:
    def test_success_envelope(self):
        r = parse_result_json(json.dumps(RESULT_ENVELOPE), **_kw())
        assert r.ok
        assert r.uncached_input == 10_000
        assert r.cache_read_tokens == 250_000
        assert r.output_tokens == 2_500
        assert r.num_turns == 7
        assert r.api_s == pytest.approx(30.5)
        assert r.cost_usd == pytest.approx(0.1234)

    def test_noise_before_envelope(self):
        raw = "some hook chatter\n" + json.dumps(RESULT_ENVELOPE)
        r = parse_result_json(raw, **_kw())
        assert r.ok

    def test_error_subtype_not_ok(self):
        env = dict(RESULT_ENVELOPE, subtype="error_max_turns")
        r = parse_result_json(json.dumps(env), **_kw())
        assert not r.ok
        assert r.error == "error_max_turns"

    def test_garbage_is_failure_not_crash(self):
        r = parse_result_json("not json at all", **_kw())
        assert not r.ok
        assert "unparseable" in r.error

    def test_missing_usage_defaults_zero(self):
        env = {k: v for k, v in RESULT_ENVELOPE.items() if k != "usage"}
        r = parse_result_json(json.dumps(env), **_kw())
        assert r.ok
        assert r.uncached_input == 0


class TestBuildEnv:
    def test_arms_differ_only_in_kill_switches(self):
        base = {"PATH": "/usr/bin", "ATTUNE_JIT_RECALL": "1"}
        on = build_env("on", base)
        off = build_env("off", base)
        assert on["ATTUNE_JIT_RECALL"] == "1"
        assert off["ATTUNE_JIT_RECALL"] == "0"
        assert off["ATTUNE_LESSON_RECALL"] == "0"
        changed = {k for k in set(on) | set(off) if on.get(k) != off.get(k)}
        assert changed == set(ARM_ENV["on"])

    def test_base_env_preserved(self):
        assert build_env("off", {"HOME": "/x"})["HOME"] == "/x"


class TestLoadTasks:
    def test_default_tasks_valid(self):
        tasks = load_tasks(None)
        assert tasks is DEFAULT_TASKS
        assert len({t["id"] for t in tasks}) == len(tasks)

    def test_file_roundtrip(self, tmp_path):
        p = tmp_path / "tasks.json"
        p.write_text(json.dumps([{"id": "a", "prompt": "do a"}]))
        assert load_tasks(p) == [{"id": "a", "prompt": "do a"}]

    @pytest.mark.parametrize(
        "payload",
        [
            [],
            {"id": "a"},
            [{"id": "a"}],
            [{"prompt": "p"}],
            [{"id": "a", "prompt": "p"}, {"id": "a", "prompt": "q"}],
        ],
    )
    def test_bad_shapes_rejected(self, tmp_path, payload):
        p = tmp_path / "tasks.json"
        p.write_text(json.dumps(payload))
        with pytest.raises(ValueError):
            load_tasks(p)


def _result(arm: str, *, ok: bool = True, uncached: int = 10_000, wall: float = 40.0) -> RunResult:
    return RunResult(
        task_id="t",
        arm=arm,
        repeat=0,
        ok=ok,
        wall_s=wall,
        input_tokens=uncached,
        cache_creation_tokens=0,
        cache_read_tokens=100,
        output_tokens=50,
        num_turns=3,
        api_s=wall * 0.8,
        cost_usd=0.01,
    )


class TestAggregateAndRender:
    def test_failures_excluded_from_medians(self):
        results = [
            _result("on", uncached=10_000),
            _result("on", ok=False, uncached=999_999),
            _result("off", uncached=8_000),
        ]
        arms = aggregate(results)
        assert arms["on"].failures == 1
        assert arms["on"].uncached_input == [10_000]

    def test_delta_direction(self):
        # memory-on costs 10k, off costs 8k → +25% overhead reported
        arms = aggregate([_result("on", uncached=10_000), _result("off", uncached=8_000)])
        rows = {m: d for m, _, _, d in summary_rows(arms)}
        assert rows["uncached input tok (median/task)"] == "+25.0%"

    def test_empty_off_arm_renders_na(self):
        arms = aggregate([_result("on")])
        table = render_table(arms, [_result("on")])
        assert "n/a" in table or "—" in table

    def test_small_n_warning_present(self):
        results = [_result("on"), _result("off")]
        table = render_table(aggregate(results), results)
        assert "directional" in table

    def test_markdown_has_all_metrics(self):
        results = [_result("on"), _result("off")]
        md = render_markdown(aggregate(results))
        assert md.count("|") >= 9 * 5  # header + separator + 7 metric rows
        assert "uncached input tok" in md
        assert "wall-clock s" in md
