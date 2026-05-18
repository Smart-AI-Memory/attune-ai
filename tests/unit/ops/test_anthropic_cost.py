"""Tests for the Anthropic admin cost-report client (Phase 1).

Covers:

- Key loader: env var, KEY=VALUE file form, bare-key file form, missing file
- Currency conversion edge cases
- Summarize aggregation (today/7d/MTD/30d windows, by_day/by_model/by_cost_type)
- HTTP fetch: 200 happy path, 401, 429, timeout, network error, malformed JSON, 5xx
- Cache: hit returns cached source="cached", miss triggers fetch, refresh bypasses
- Cache fallback: 429 with stale entry returns the stale value
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

pytest.importorskip("httpx")

import httpx  # noqa: E402

from attune.ops import anthropic_cost  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache_each_test():
    """Reset the module-level cache between tests."""
    anthropic_cost.clear_cache()
    yield
    anthropic_cost.clear_cache()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Strip the admin-key env var so tests start from a known state."""
    monkeypatch.delenv("ANTHROPIC_ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_COST_CACHE_TTL_SECONDS", raising=False)


# ---------------------------------------------------------------
# Currency conversion
# ---------------------------------------------------------------


def test_cost_usd_converts_cents_decimal_to_dollars():
    assert anthropic_cost._cost_usd("12345") == 123.45
    assert anthropic_cost._cost_usd("40055.123") == pytest.approx(400.55, rel=1e-4)
    assert anthropic_cost._cost_usd("0") == 0.0
    assert anthropic_cost._cost_usd("100") == 1.0


def test_cost_usd_returns_zero_for_malformed_input():
    assert anthropic_cost._cost_usd(None) == 0.0
    assert anthropic_cost._cost_usd("") == 0.0
    assert anthropic_cost._cost_usd("not-a-number") == 0.0
    assert anthropic_cost._cost_usd("12.34.56") == 0.0


# ---------------------------------------------------------------
# Key loader
# ---------------------------------------------------------------


def test_load_admin_key_returns_env_var_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-fromenv")
    # Even if the file is missing, env wins.
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", tmp_path / "missing.env")
    assert anthropic_cost.load_admin_key() == "sk-ant-admin01-fromenv"


def test_load_admin_key_reads_canonical_key_equals_value_form(monkeypatch, tmp_path):
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text(
        "# comment line\n" "ANTHROPIC_ADMIN_API_KEY=sk-ant-admin01-fromfile\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() == "sk-ant-admin01-fromfile"


def test_load_admin_key_tolerates_bare_key_form(monkeypatch, tmp_path):
    """Convenience: a file containing just the key with no label."""
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text("sk-ant-admin01-bare\n", encoding="utf-8")
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() == "sk-ant-admin01-bare"


def test_load_admin_key_handles_quoted_value(monkeypatch, tmp_path):
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text(
        'ANTHROPIC_ADMIN_API_KEY="sk-ant-admin01-quoted"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() == "sk-ant-admin01-quoted"


def test_load_admin_key_returns_none_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", tmp_path / "does-not-exist.env")
    assert anthropic_cost.load_admin_key() is None


def test_load_admin_key_returns_none_for_empty_file(monkeypatch, tmp_path):
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() is None


def test_load_admin_key_skips_comment_only_file(monkeypatch, tmp_path):
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text("# Just a comment\n# No key here\n", encoding="utf-8")
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() is None


def test_load_admin_key_skips_empty_value_and_unknown_lines(monkeypatch, tmp_path):
    """A KEY= with empty value falls through; unrelated lines are skipped.

    Exercises the loop-continuation branches for both the empty-value
    case (after stripping quotes) and a line matching neither prefix.
    """
    env_file = tmp_path / "anthropic-admin.env"
    env_file.write_text(
        'ANTHROPIC_ADMIN_API_KEY=""\n'
        "some-unrelated-line\n"
        "ANTHROPIC_ADMIN_API_KEY=sk-ant-admin01-real\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", env_file)
    assert anthropic_cost.load_admin_key() == "sk-ant-admin01-real"


def test_load_admin_key_returns_none_on_oserror(monkeypatch, tmp_path, caplog):
    """A non-FileNotFoundError OSError (e.g. PermissionError) returns None.

    The function must log the path but never the key material and must
    never raise.
    """
    target = tmp_path / "anthropic-admin.env"
    target.write_text("ANTHROPIC_ADMIN_API_KEY=sk-ant-admin01-test\n", encoding="utf-8")
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", target)

    def _raise_permission(self, *args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("pathlib.Path.read_text", _raise_permission)

    with caplog.at_level("WARNING", logger="attune.ops.anthropic_cost"):
        result = anthropic_cost.load_admin_key()

    assert result is None
    assert any("cannot read" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------
# Aggregation (_summarize)
# ---------------------------------------------------------------


def _bucket(starting_at: str, *rows: dict) -> dict:
    """Helper to build a fake cost_report bucket."""
    return {
        "starting_at": starting_at + "T00:00:00Z",
        "ending_at": starting_at + "T23:59:59Z",
        "results": list(rows),
    }


def _row(amount_cents: str, *, cost_type: str = "tokens", model: str = "claude-sonnet-5") -> dict:
    return {"amount": amount_cents, "cost_type": cost_type, "model": model}


def test_summarize_today_window():
    today = date(2026, 5, 18)
    payload = {"data": [_bucket("2026-05-18", _row("1500"))]}
    s = anthropic_cost._summarize(payload, today=today)
    assert s.today_usd == 15.0
    assert s.seven_day_usd == 15.0
    assert s.month_to_date_usd == 15.0
    assert s.thirty_day_usd == 15.0


def test_summarize_seven_day_window_excludes_older():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket("2026-05-18", _row("1000")),  # today
            _bucket("2026-05-12", _row("2000")),  # 6 days ago — IN 7d window
            _bucket("2026-05-11", _row("3000")),  # 7 days ago — OUT
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.today_usd == 10.0
    assert s.seven_day_usd == 30.0  # 10 + 20, not 60
    assert s.thirty_day_usd == 60.0  # all three


def test_summarize_month_to_date_resets_at_month_boundary():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket("2026-05-01", _row("5000")),  # MTD: yes
            _bucket("2026-04-30", _row("9000")),  # MTD: no (April)
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.month_to_date_usd == 50.0
    assert s.thirty_day_usd == 140.0


def test_summarize_groups_by_model_descending():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket(
                "2026-05-18",
                _row("1000", model="claude-haiku-4-5"),
                _row("5000", model="claude-opus-4-7"),
                _row("3000", model="claude-sonnet-5"),
            )
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.by_model == [
        ("claude-opus-4-7", 50.0),
        ("claude-sonnet-5", 30.0),
        ("claude-haiku-4-5", 10.0),
    ]


def test_summarize_groups_by_cost_type_descending():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket(
                "2026-05-18",
                _row("1000", cost_type="web_search"),
                _row("9000", cost_type="tokens"),
                _row("500", cost_type="code_execution"),
            )
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.by_cost_type == [
        ("tokens", 90.0),
        ("web_search", 10.0),
        ("code_execution", 5.0),
    ]


def test_summarize_by_day_ascending():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket("2026-05-16", _row("3000")),
            _bucket("2026-05-15", _row("2000")),
            _bucket("2026-05-17", _row("1000")),
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.by_day == [
        (date(2026, 5, 15), 20.0),
        (date(2026, 5, 16), 30.0),
        (date(2026, 5, 17), 10.0),
    ]


def test_summarize_skips_malformed_bucket_dates():
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket("not-a-date", _row("9999")),
            _bucket("2026-05-18", _row("1000")),
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    # Malformed bucket dropped; valid one counted.
    assert s.today_usd == 10.0


def test_summarize_empty_payload():
    today = date(2026, 5, 18)
    s = anthropic_cost._summarize({"data": []}, today=today)
    assert s.today_usd == 0.0
    assert s.by_day == []
    assert s.source == "live"


def test_summarize_excludes_buckets_older_than_thirty_days():
    """A bucket beyond the 30-day window contributes to no totals."""
    today = date(2026, 5, 18)
    payload = {
        "data": [
            _bucket("2026-05-18", _row("1000")),  # today
            _bucket("2026-03-01", _row("9999")),  # >30 days ago — OUT
        ]
    }
    s = anthropic_cost._summarize(payload, today=today)
    assert s.today_usd == 10.0
    assert s.seven_day_usd == 10.0
    assert s.month_to_date_usd == 10.0
    assert s.thirty_day_usd == 10.0  # older bucket excluded


# ---------------------------------------------------------------
# fetch_summary — happy path + failure modes
# ---------------------------------------------------------------


def _mock_response(*, status_code: int, json_body=None) -> httpx.Response:
    """Build a fake httpx.Response with the given status + JSON body."""
    if json_body is None:
        json_body = {"data": [], "has_more": False}
    return httpx.Response(
        status_code=status_code,
        json=json_body,
        request=httpx.Request("GET", anthropic_cost._COST_REPORT_URL),
    )


def _install_mock_client(monkeypatch, response_or_exc):
    """Patch httpx.Client.get to return a mock response or raise.

    ``response_or_exc`` is either an httpx.Response or an Exception
    instance; in the latter case ``Client.get`` raises it.
    """

    def fake_get(self, url, **kwargs):
        if isinstance(response_or_exc, Exception):
            raise response_or_exc
        return response_or_exc

    monkeypatch.setattr(httpx.Client, "get", fake_get)


def test_fetch_summary_returns_no_key_when_key_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(anthropic_cost, "ADMIN_KEY_PATH", tmp_path / "missing.env")
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error is not None
    assert error.kind == "no_key"


def test_fetch_summary_happy_path(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")

    today_iso = datetime.now(timezone.utc).date().isoformat()
    _install_mock_client(
        monkeypatch,
        _mock_response(
            status_code=200,
            json_body={
                "data": [
                    {
                        "starting_at": f"{today_iso}T00:00:00Z",
                        "ending_at": f"{today_iso}T23:59:59Z",
                        "results": [
                            {
                                "amount": "12345",
                                "cost_type": "tokens",
                                "model": "claude-sonnet-5",
                            }
                        ],
                    }
                ],
                "has_more": False,
            },
        ),
    )

    summary, error = anthropic_cost.fetch_summary()
    assert error is None
    assert summary is not None
    assert summary.today_usd == 123.45
    assert summary.source == "live"


def test_fetch_summary_401_returns_auth_failed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-bad")
    _install_mock_client(monkeypatch, _mock_response(status_code=401, json_body={"error": "x"}))
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error is not None
    assert error.kind == "auth_failed"
    # The bad key MUST NOT appear in the user-facing message.
    assert "sk-ant-admin01-bad" not in error.message


def test_fetch_summary_403_also_returns_auth_failed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    _install_mock_client(monkeypatch, _mock_response(status_code=403))
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "auth_failed"


def test_fetch_summary_429_returns_rate_limited_when_no_cache(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    _install_mock_client(monkeypatch, _mock_response(status_code=429))
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "rate_limited"


def test_fetch_summary_429_returns_cached_when_available(monkeypatch):
    """The 429 path is the one place we prefer stale cache over error.

    First call seeds the cache; second call (429) returns the cached
    value with source="cached" rather than an error.
    """
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")

    # First call: 200 → cache populated.
    today_iso = datetime.now(timezone.utc).date().isoformat()
    happy = _mock_response(
        status_code=200,
        json_body={
            "data": [
                {
                    "starting_at": f"{today_iso}T00:00:00Z",
                    "results": [{"amount": "5000", "cost_type": "tokens", "model": "m"}],
                }
            ],
            "has_more": False,
        },
    )
    rate_limited = _mock_response(status_code=429)
    responses = iter([happy, rate_limited])

    def fake_get(self, url, **kwargs):
        return next(responses)

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    s1, e1 = anthropic_cost.fetch_summary()
    assert s1 is not None and e1 is None
    assert s1.today_usd == 50.0
    assert s1.source == "live"

    # Second call should hit cache (TTL not expired) → never hits the
    # rate_limited response. Force a refresh to actually trigger the
    # 429 and exercise the fallback.
    s2, e2 = anthropic_cost.fetch_summary(refresh=True)
    assert e2 is None
    assert s2 is not None
    assert s2.today_usd == 50.0  # from cache
    assert s2.source == "cached"


def test_fetch_summary_timeout_returns_network_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    timeout = httpx.TimeoutException("read timeout")
    _install_mock_client(monkeypatch, timeout)
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "network"
    assert "timed out" in error.message.lower()


def test_fetch_summary_connection_error_returns_network(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    conn_err = httpx.ConnectError("DNS failure")
    _install_mock_client(monkeypatch, conn_err)
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "network"


def test_fetch_summary_5xx_returns_network(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    _install_mock_client(monkeypatch, _mock_response(status_code=503))
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "network"


def test_fetch_summary_unknown_status_code_returns_unknown(monkeypatch):
    """A status that's not 200/401/403/429/5xx maps to kind='unknown'."""
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    _install_mock_client(monkeypatch, _mock_response(status_code=418))
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error is not None
    assert error.kind == "unknown"
    assert "418" in error.message


def test_fetch_summary_malformed_json_returns_unknown(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    # Build a response whose json() will raise ValueError.
    response = httpx.Response(
        status_code=200,
        content=b"not-json",
        request=httpx.Request("GET", anthropic_cost._COST_REPORT_URL),
    )
    _install_mock_client(monkeypatch, response)
    summary, error = anthropic_cost.fetch_summary()
    assert summary is None
    assert error.kind == "unknown"


# ---------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------


def test_cache_hit_skips_http_call(monkeypatch):
    """A second fetch within TTL must not call httpx."""
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")

    call_count = {"n": 0}

    def fake_get(self, url, **kwargs):
        call_count["n"] += 1
        return _mock_response(status_code=200, json_body={"data": [], "has_more": False})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    anthropic_cost.fetch_summary()
    anthropic_cost.fetch_summary()
    anthropic_cost.fetch_summary()
    assert call_count["n"] == 1  # Only the first call hit httpx


def test_refresh_true_bypasses_cache(monkeypatch):
    """refresh=True forces a fresh HTTP call even if cache is warm."""
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")

    call_count = {"n": 0}

    def fake_get(self, url, **kwargs):
        call_count["n"] += 1
        return _mock_response(status_code=200, json_body={"data": [], "has_more": False})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    anthropic_cost.fetch_summary()
    anthropic_cost.fetch_summary(refresh=True)
    assert call_count["n"] == 2


def test_cache_expires_after_ttl(monkeypatch):
    """When the cache entry expires, the next fetch hits the API."""
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", "sk-ant-admin01-test")
    monkeypatch.setenv("ANTHROPIC_COST_CACHE_TTL_SECONDS", "1")

    call_count = {"n": 0}

    def fake_get(self, url, **kwargs):
        call_count["n"] += 1
        return _mock_response(status_code=200, json_body={"data": [], "has_more": False})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    anthropic_cost.fetch_summary()
    # Fast-forward by manipulating the cache entry's expiry directly.
    with anthropic_cost._CACHE_LOCK:
        for _key, entry in anthropic_cost._CACHE.items():
            entry.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    anthropic_cost.fetch_summary()
    assert call_count["n"] == 2


def test_cache_ttl_env_var_invalid_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_COST_CACHE_TTL_SECONDS", "not-a-number")
    assert anthropic_cost._cache_ttl_seconds() == 900


def test_cache_ttl_env_var_negative_clamps_to_one(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_COST_CACHE_TTL_SECONDS", "-5")
    assert anthropic_cost._cache_ttl_seconds() == 1


# ---------------------------------------------------------------
# Key safety — no key material in logged output or error messages
# ---------------------------------------------------------------


def test_auth_failure_message_does_not_leak_key(monkeypatch, caplog):
    """A 401 must not include the rejected key in any user-visible string."""
    secret = "sk-ant-admin01-DO-NOT-LEAK"  # noqa: S105 — test sentinel
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", secret)
    _install_mock_client(monkeypatch, _mock_response(status_code=401))

    with caplog.at_level("DEBUG", logger="attune.ops.anthropic_cost"):
        summary, error = anthropic_cost.fetch_summary()

    assert error is not None
    assert secret not in error.message
    for record in caplog.records:
        assert secret not in record.getMessage()


def test_network_error_message_does_not_leak_key(monkeypatch, caplog):
    secret = "sk-ant-admin01-DO-NOT-LEAK"  # noqa: S105 — test sentinel
    monkeypatch.setenv("ANTHROPIC_ADMIN_API_KEY", secret)
    _install_mock_client(monkeypatch, httpx.ConnectError("dns failure"))

    with caplog.at_level("DEBUG", logger="attune.ops.anthropic_cost"):
        summary, error = anthropic_cost.fetch_summary()

    assert error is not None
    assert secret not in error.message
    for record in caplog.records:
        assert secret not in record.getMessage()
