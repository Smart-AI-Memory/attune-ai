"""Session spend ledger — the hard-refusal contract.

Spec: docs/specs/session-spend-ledger/. The load-bearing tests are
the refusal ones: a launcher call AT the cap raises (R2), and a cap
that is already ``<= 0`` refuses the FIRST call (R3 — the known
``__post_init__`` budget-latch bug class: naive cap-then-record
logic grants one free call).
"""

from __future__ import annotations

import json
import math

import pytest

from attune.gates import session_ledger
from attune.gates.session_ledger import (
    DEFAULT_CAP_USD,
    WINDOW_SECONDS,
    SessionSpendCapError,
    check,
    get_cap_usd,
    ledger_off,
    record,
    seat_estimate_usd,
    spent_usd,
)

NOW = 1_700_000_000.0


@pytest.fixture(autouse=True)
def _clean_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_SESSION_LEDGER_PATH", str(tmp_path / "session_spend.jsonl"))
    monkeypatch.delenv("ATTUNE_SESSION_SPEND_CAP_USD", raising=False)
    monkeypatch.delenv("ATTUNE_SESSION_LEDGER", raising=False)
    monkeypatch.delenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", raising=False)


@pytest.fixture()
def ledger(tmp_path):
    return tmp_path / "session_spend.jsonl"


class TestNoFreeFirstCall:
    """R3 — the budget-latch regression class."""

    def test_cap_zero_refuses_the_first_call(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        with pytest.raises(SessionSpendCapError, match="no free first call"):
            check("probe:security-audit", now=NOW, path=ledger)

    def test_negative_cap_refuses_the_first_call(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "-5")
        with pytest.raises(SessionSpendCapError):
            check("seat:claude", now=NOW, path=ledger)

    def test_already_at_cap_refuses_the_first_check(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "2")
        record("probe:a", 2.0, now=NOW, path=ledger)
        with pytest.raises(SessionSpendCapError, match=r"\$2\.00 already spent"):
            check("probe:b", now=NOW, path=ledger)


class TestHardRefusalAtCap:
    """R2 — refusal, not a warning."""

    def test_under_cap_proceeds_and_returns_remaining(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "10")
        record("probe:a", 4.0, now=NOW, path=ledger)
        assert check("probe:b", now=NOW, path=ledger) == pytest.approx(6.0)

    def test_crossing_the_cap_refuses_the_next_call(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "10")
        record("probe:a", 9.99, now=NOW, path=ledger)
        check("probe:b", now=NOW, path=ledger)  # still under
        record("probe:b", 0.02, now=NOW, path=ledger)
        with pytest.raises(SessionSpendCapError, match="Raise ATTUNE_SESSION_SPEND_CAP_USD"):
            check("probe:c", now=NOW, path=ledger)

    def test_spend_accumulates_across_launcher_labels(self, monkeypatch, ledger) -> None:
        """The point of the ledger: probes + seats share one cap."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "1.0")
        record("probe:security-audit", 0.6, now=NOW, path=ledger)
        record("seat:claude", 0.25, now=NOW, path=ledger)
        record("seat:claude", 0.25, now=NOW, path=ledger)
        with pytest.raises(SessionSpendCapError):
            check("routine:clean-run", now=NOW, path=ledger)


class TestSessionWindow:
    def test_entries_older_than_the_window_roll_out(self, ledger) -> None:
        record("probe:old", 50.0, now=NOW - WINDOW_SECONDS - 1, path=ledger)
        record("probe:recent", 1.0, now=NOW, path=ledger)
        assert spent_usd(now=NOW, path=ledger) == pytest.approx(1.0)
        # The old $50 no longer blocks the next launch.
        assert check("probe:next", now=NOW, path=ledger) > 0


class TestOffSwitch:
    def test_off_bypasses_even_a_zero_cap(self, monkeypatch, ledger) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
        monkeypatch.setenv("ATTUNE_SESSION_LEDGER", "off")
        assert math.isinf(check("probe:a", now=NOW, path=ledger))

    def test_record_ignores_the_off_switch(self, monkeypatch, ledger) -> None:
        """D4: the audit trail survives an override."""
        monkeypatch.setenv("ATTUNE_SESSION_LEDGER", "off")
        record("probe:a", 1.5, now=NOW, path=ledger)
        assert spent_usd(now=NOW, path=ledger) == pytest.approx(1.5)

    def test_unrelated_env_value_keeps_checking(self, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_LEDGER", "on")
        assert not ledger_off()


class TestDegradeTowardEnforcement:
    """R7 — failures never widen the budget."""

    def test_missing_file_is_zero_spent(self, ledger) -> None:
        assert spent_usd(now=NOW, path=ledger) == 0.0

    def test_corrupt_lines_are_skipped_valid_lines_counted(self, ledger) -> None:
        record("probe:a", 2.0, now=NOW, path=ledger)
        with open(ledger, "a", encoding="utf-8") as handle:
            handle.write("{torn write\n")
            handle.write(json.dumps({"ts": "not-a-number", "cost_usd": 1}) + "\n")
        record("probe:b", 3.0, now=NOW, path=ledger)
        assert spent_usd(now=NOW, path=ledger) == pytest.approx(5.0)

    def test_malformed_cap_env_falls_back_to_default_not_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "plenty")
        assert get_cap_usd() == DEFAULT_CAP_USD

    @pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
    def test_non_finite_cap_env_falls_back_to_default(self, monkeypatch, raw) -> None:
        """D11 lane finding: NaN made both refusal comparisons False —
        an unlimited cap through the back door."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", raw)
        assert get_cap_usd() == DEFAULT_CAP_USD

    def test_existing_but_unreadable_ledger_fails_closed(self, monkeypatch, tmp_path) -> None:
        """D11 lane finding: an unreadable ledger read as $0 would
        silently disable enforcement. A directory in the ledger's
        place raises OSError-not-FileNotFoundError on every platform."""
        monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "10")
        dir_as_ledger = tmp_path / "ledger-is-a-dir"
        dir_as_ledger.mkdir()
        with pytest.raises(SessionSpendCapError, match="cannot be read"):
            check("probe:a", now=NOW, path=dir_as_ledger)

    def test_unwritable_ledger_logs_but_does_not_raise(self, tmp_path) -> None:
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where a directory must go", encoding="utf-8")
        record("probe:a", 1.0, now=NOW, path=blocker / "ledger.jsonl")


class TestRecord:
    def test_negative_cost_raises(self, ledger) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            record("probe:a", -0.01, now=NOW, path=ledger)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_non_finite_cost_raises(self, ledger, bad) -> None:
        with pytest.raises(ValueError, match="finite"):
            record("probe:a", bad, now=NOW, path=ledger)

    def test_appends_parseable_jsonl(self, ledger) -> None:
        record("seat:claude", 0.25, now=NOW, path=ledger)
        record("probe:test-gen", 1.2345, now=NOW + 1, path=ledger)
        entries = [json.loads(line) for line in ledger.read_text().splitlines()]
        assert [e["label"] for e in entries] == ["seat:claude", "probe:test-gen"]
        assert entries[0]["cost_usd"] == pytest.approx(0.25)
        assert entries[1]["ts"] == pytest.approx(NOW + 1)

    def test_env_path_override_is_honored(self, tmp_path, monkeypatch) -> None:
        override = tmp_path / "elsewhere" / "spend.jsonl"
        monkeypatch.setenv("ATTUNE_SESSION_LEDGER_PATH", str(override))
        record("probe:a", 0.5, now=NOW)
        assert spent_usd(now=NOW) == pytest.approx(0.5)
        assert override.exists()


class TestSeatEstimate:
    def test_default(self) -> None:
        assert seat_estimate_usd() == pytest.approx(0.25)

    def test_env_override(self, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", "0.4")
        assert seat_estimate_usd() == pytest.approx(0.4)

    def test_malformed_override_falls_back(self, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", "cheap")
        assert seat_estimate_usd() == pytest.approx(0.25)

    def test_negative_override_clamps_to_zero(self, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", "-1")
        assert seat_estimate_usd() == 0.0


def test_error_is_importable_from_the_package_root() -> None:
    from attune.gates import SessionSpendCapError as exported

    assert exported is session_ledger.SessionSpendCapError
