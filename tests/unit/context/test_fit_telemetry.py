"""Ladder-outcome telemetry for TokenBudgetAllocator.fit_source.

Roundtable q-context-mgmt-features-001 consensus item 1 (the
evidence base): every fit_source call records which rung of the
budget ladder fired — on the instance (``last_fit``) and as a
``context_fit`` log line — so budget starvation and truncation
frequency are measurable instead of folklore.
"""

import logging

from attune.context import TokenBudgetAllocator

PY_SOURCE = '''
def alpha(x: int) -> int:
    """Adds one."""
    return x + 1


def beta(y: int) -> int:
    """Doubles."""
    return y * 2
'''


class TestFitTelemetry:
    """Each ladder rung records an accurate last_fit outcome."""

    def test_no_call_yet_is_none(self):
        assert TokenBudgetAllocator().last_fit is None

    def test_full_rung(self):
        allocator = TokenBudgetAllocator()
        result = allocator.fit_source(PY_SOURCE, token_limit=4000)
        assert result == PY_SOURCE
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "full"
        assert allocator.last_fit["token_limit"] == 4000
        assert allocator.last_fit["source_tokens"] == len(PY_SOURCE) // 4
        assert allocator.last_fit["result_tokens"] == allocator.last_fit["source_tokens"]

    def test_skeleton_rung(self):
        allocator = TokenBudgetAllocator()
        big = PY_SOURCE + "\n" + ("# pad\n" * 200)
        limit = (len(big) // 4) - 1
        result = allocator.fit_source(big, token_limit=limit)
        assert result != big
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "skeleton"
        assert allocator.last_fit["source_tokens"] > limit
        assert allocator.last_fit["result_tokens"] <= limit

    def test_truncated_skeleton_rung(self):
        allocator = TokenBudgetAllocator()
        many = "\n".join(
            f'def f{i}(x: int) -> int:\n    """Doc {i}."""\n    return x' for i in range(200)
        )
        result = allocator.fit_source(many, token_limit=50)
        assert "truncated at token limit 50" in result
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "truncated_skeleton"

    def test_plain_truncation_rung_for_non_python(self):
        allocator = TokenBudgetAllocator()
        prose = "word " * 500
        result = allocator.fit_source(prose, token_limit=20)
        assert "truncated at token limit 20" in result
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "plain_truncation"

    def test_context_fit_log_line_emitted(self, caplog):
        allocator = TokenBudgetAllocator()
        with caplog.at_level(logging.INFO, logger="attune.context.allocator"):
            allocator.fit_source(PY_SOURCE, token_limit=4000)
        fit_records = [r for r in caplog.records if "context_fit" in r.getMessage()]
        assert len(fit_records) == 1
        message = fit_records[0].getMessage()
        assert "rung=full" in message
        assert "token_limit=4000" in message

    def test_last_fit_overwritten_per_call(self):
        allocator = TokenBudgetAllocator()
        allocator.fit_source(PY_SOURCE, token_limit=4000)
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "full"
        allocator.fit_source("word " * 500, token_limit=20)
        assert allocator.last_fit["rung"] == "plain_truncation"


class TestFitEventStream:
    """Fit outcomes append to the durable local telemetry stream.

    Chair ruling (context-compaction-retirement D3, 2026-08-19):
    ``last_fit`` is unreachable for production callers (throwaway
    allocator instances), so each fit also appends one JSONL record to
    ``$ATTUNE_HOME/telemetry/context_fit.jsonl`` — the surface budget
    decisions read.
    """

    def _stream(self, tmp_path, monkeypatch):
        import json as _json
        from pathlib import Path

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        path = Path(tmp_path) / "telemetry" / "context_fit.jsonl"
        return path, _json

    def test_each_fit_appends_one_record(self, tmp_path, monkeypatch):
        path, _json = self._stream(tmp_path, monkeypatch)
        allocator = TokenBudgetAllocator()
        allocator.fit_source(PY_SOURCE, token_limit=4000)
        allocator.fit_source("word " * 500, token_limit=20)

        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        first, second = (_json.loads(line) for line in lines)
        assert first["rung"] == "full"
        assert first["token_limit"] == 4000
        assert "ts" in first
        assert second["rung"] == "plain_truncation"

    def test_env_kill_switch_disables_stream(self, tmp_path, monkeypatch):
        path, _ = self._stream(tmp_path, monkeypatch)
        monkeypatch.setenv("ATTUNE_CONTEXT_FIT_TELEMETRY", "0")
        TokenBudgetAllocator().fit_source(PY_SOURCE, token_limit=4000)
        assert not path.exists()

    def test_unserializable_payload_never_raises(self, tmp_path, monkeypatch):
        """Regression (library-review R5): a TypeError from an
        unserializable payload is swallowed like an OSError — the
        docstring's never-raises promise holds for both."""
        self._stream(tmp_path, monkeypatch)
        from attune.context.allocator import _append_fit_event

        _append_fit_event({"rung": object()})  # must not raise

    def test_append_failure_never_breaks_fit(self, tmp_path, monkeypatch):
        """An unwritable stream degrades to the log line, never raises."""
        self._stream(tmp_path, monkeypatch)

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr("attune.context.allocator.Path.open", boom)
        allocator = TokenBudgetAllocator()
        result = allocator.fit_source(PY_SOURCE, token_limit=4000)
        assert result == PY_SOURCE
        assert allocator.last_fit is not None
        assert allocator.last_fit["rung"] == "full"
