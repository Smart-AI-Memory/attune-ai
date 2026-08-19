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
