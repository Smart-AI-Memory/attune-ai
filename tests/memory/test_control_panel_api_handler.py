"""Behavioral tests for MemoryAPIHandler (control_panel_api).

The handler subclasses http.server.BaseHTTPRequestHandler, which is
awkward to test against a real socket. Instead, _Recorder overrides the
three socket-touching primitives (send_response / send_header /
end_headers) to capture the status + headers, writes the body to an
in-memory BytesIO, and skips BaseHTTPRequestHandler.__init__ (which
would try to service a live request). Every do_* method and helper is
then driven directly with a fake panel.

This is PR 1 of the control_panel_api effort (handler); run_api_server
bootstrap is covered separately. Module was at 16% with no test file.
"""

import io
import json
from dataclasses import dataclass

from attune.memory.control_panel_api import MemoryAPIHandler

# ===========================================================================
# Fakes
# ===========================================================================


@dataclass
class _Stats:
    total_patterns: int = 5
    short_term_keys: int = 2


class _RedisMethod:
    value = "docker"


class _RedisStatus:
    def __init__(self, available=True):
        self.available = available
        self.method = _RedisMethod()


class _FakePanel:
    """Stand-in for MemoryControlPanel exposing only what the handler calls."""

    def __init__(self, redis_available=True, stop_ok=True, delete_ok=True):
        self._redis_available = redis_available
        self._stop_ok = stop_ok
        self._delete_ok = delete_ok
        self.cleared: list[str] = []
        self.deleted: list[str] = []
        self._patterns = [
            {"pattern_id": "patternone", "classification": "PUBLIC"},
            {"pattern_id": "patterntwo", "classification": "SENSITIVE"},
        ]

    def status(self):
        return {"ok": True}

    def get_statistics(self):
        return _Stats()

    def health_check(self):
        return {"healthy": True}

    def list_patterns(self, classification=None, limit=100):
        items = self._patterns
        if classification:
            items = [p for p in items if p["classification"] == classification]
        return items[:limit]

    def start_redis(self, verbose=False):
        return _RedisStatus(available=self._redis_available)

    def stop_redis(self):
        return self._stop_ok

    def clear_short_term(self, agent_id):
        self.cleared.append(agent_id)
        return 3

    def delete_pattern(self, pattern_id):
        self.deleted.append(pattern_id)
        return self._delete_ok


class _FakeAuth:
    def __init__(self, enabled=True, valid_token="secret"):
        self.enabled = enabled
        self._valid = valid_token

    def is_valid(self, token):
        return token == self._valid


class _FakeLimiter:
    def __init__(self, allow=True):
        self.allow = allow
        self.max_requests = 100

    def is_allowed(self, ip):
        return self.allow

    def get_remaining(self, ip):
        return 42


class _Recorder(MemoryAPIHandler):
    """MemoryAPIHandler that records responses instead of using a socket."""

    def __init__(
        self,
        path="/",
        body=b"",
        headers=None,
        client_ip="9.9.9.9",
        panel=None,
        rate_limiter=None,
        api_auth=None,
        allowed_origins=None,
    ):
        # Deliberately skip BaseHTTPRequestHandler.__init__.
        self.path = path
        self.client_address = (client_ip, 5555)
        self.headers = headers or {}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = None
        self.resp_headers = {}
        self.panel = panel
        self.rate_limiter = rate_limiter
        self.api_auth = api_auth
        self.allowed_origins = allowed_origins

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, key, value):
        self.resp_headers[key] = value

    def end_headers(self):
        pass

    def json_body(self):
        raw = self.wfile.getvalue()
        return json.loads(raw) if raw else None


def make(**kwargs):
    """Build a _Recorder, defaulting panel to a fresh _FakePanel."""
    kwargs.setdefault("panel", _FakePanel())
    return _Recorder(**kwargs)


# ===========================================================================
# Origin / client-IP / CORS helpers
# ===========================================================================


def test_sanitize_origin_strips_control_chars():
    """CRLF and other control chars are removed (response-splitting guard)."""
    assert MemoryAPIHandler._sanitize_origin("http://x\r\n\x00.com") == "http://x.com"


def test_client_ip_trusts_forwarded_only_from_localhost():
    """X-Forwarded-For is honored only when the direct peer is localhost."""
    local = make(client_ip="127.0.0.1", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
    assert local._get_client_ip() == "1.2.3.4"

    remote = make(client_ip="8.8.8.8", headers={"X-Forwarded-For": "1.2.3.4"})
    assert remote._get_client_ip() == "8.8.8.8"


def test_cors_default_echoes_localhost_else_fallback():
    """With no allow-list, localhost origins echo; others get the default."""
    h = make(headers={"Origin": "http://localhost:3000"})
    assert h._get_cors_origin() == "http://localhost:3000"

    h2 = make(headers={"Origin": "http://evil.example"})
    assert h2._get_cors_origin() == "http://localhost:8765"


def test_cors_allowlist_wildcard_and_membership():
    """An explicit allow-list supports '*', membership, and first-fallback."""
    assert make(headers={"Origin": "http://a"}, allowed_origins=["*"])._get_cors_origin() == "*"

    member = make(headers={"Origin": "http://a"}, allowed_origins=["http://a", "http://b"])
    assert member._get_cors_origin() == "http://a"

    nonmember = make(headers={"Origin": "http://z"}, allowed_origins=["http://a", "http://b"])
    assert nonmember._get_cors_origin() == "http://a"  # falls back to first


# ===========================================================================
# Rate limit / auth
# ===========================================================================


def test_rate_limit_none_allows_and_limiter_can_deny():
    assert make()._check_rate_limit() is True  # no limiter
    assert make(rate_limiter=_FakeLimiter(allow=False))._check_rate_limit() is False


def test_auth_disabled_or_absent_allows():
    assert make()._check_auth() is True  # no api_auth
    assert make(api_auth=_FakeAuth(enabled=False))._check_auth() is True


def test_auth_accepts_bearer_and_x_api_key():
    bearer = make(api_auth=_FakeAuth(), headers={"Authorization": "Bearer secret"})
    assert bearer._check_auth() is True

    xkey = make(api_auth=_FakeAuth(), headers={"X-API-Key": "secret"})
    assert xkey._check_auth() is True


def test_auth_rejects_missing_or_wrong_key():
    assert make(api_auth=_FakeAuth(), headers={})._check_auth() is False
    bad = make(api_auth=_FakeAuth(), headers={"Authorization": "Bearer nope"})
    assert bad._check_auth() is False


# ===========================================================================
# do_OPTIONS
# ===========================================================================


def test_options_sets_cors_preflight_headers():
    h = make()
    h.do_OPTIONS()
    assert h.status == 200
    assert "Access-Control-Allow-Methods" in h.resp_headers


# ===========================================================================
# do_GET routing
# ===========================================================================


def test_get_ping_skips_auth_even_when_enabled():
    h = make(path="/api/ping", api_auth=_FakeAuth(), headers={})
    h.do_GET()
    assert h.status == 200
    assert h.json_body()["status"] == "ok"


def test_get_status_stats_health():
    for path, key in [("/api/status", "ok"), ("/api/health", "healthy")]:
        h = make(path=path)
        h.do_GET()
        assert h.status == 200 and key in h.json_body()

    stats = make(path="/api/stats")
    stats.do_GET()
    assert stats.json_body()["total_patterns"] == 5  # asdict of dataclass


def test_get_patterns_list_and_classification_filter():
    h = make(path="/api/patterns", body=b"")
    h.path = "/api/patterns?classification=PUBLIC"
    h.do_GET()
    assert h.status == 200
    assert [p["pattern_id"] for p in h.json_body()] == ["patternone"]


def test_get_patterns_invalid_classification_is_400():
    h = _Recorder(path="/api/patterns?classification=BOGUS", panel=_FakePanel())
    h.do_GET()
    assert h.status == 400


def test_get_patterns_limit_clamped(monkeypatch):
    h = _Recorder(path="/api/patterns?limit=99999", panel=_FakePanel())
    captured = {}
    orig = h.panel.list_patterns

    def spy(classification=None, limit=100):
        captured["limit"] = limit
        return orig(classification=classification, limit=limit)

    h.panel.list_patterns = spy
    h.do_GET()
    assert captured["limit"] == 1000  # clamped to max


def test_get_patterns_export():
    h = _Recorder(path="/api/patterns/export", panel=_FakePanel())
    h.do_GET()
    body = h.json_body()
    assert body["pattern_count"] == 2
    assert "exported_at" in body["export_data"]


def test_get_pattern_by_id_found_and_missing():
    found = _Recorder(path="/api/patterns/patternone", panel=_FakePanel())
    found.do_GET()
    assert found.status == 200 and found.json_body()["pattern_id"] == "patternone"

    missing = _Recorder(path="/api/patterns/patternzzz", panel=_FakePanel())
    missing.do_GET()
    assert missing.status == 404


def test_get_pattern_by_id_invalid_is_400():
    h = _Recorder(path="/api/patterns/..", panel=_FakePanel())
    h.do_GET()
    assert h.status == 400


def test_get_unknown_path_is_404():
    h = make(path="/api/nope")
    h.do_GET()
    assert h.status == 404


def test_get_rate_limited_is_429():
    h = make(path="/api/ping", rate_limiter=_FakeLimiter(allow=False))
    h.do_GET()
    assert h.status == 429


def test_get_unauthorized_is_401():
    h = make(path="/api/status", api_auth=_FakeAuth(), headers={})
    h.do_GET()
    assert h.status == 401


# ===========================================================================
# _read_json_body
# ===========================================================================


def test_read_json_body_empty_returns_dict():
    h = make(headers={"Content-Length": "0"})
    assert h._read_json_body() == {}


def test_read_json_body_too_large_is_413():
    h = make(headers={"Content-Length": str(2 * 1024 * 1024)})
    assert h._read_json_body() is None
    assert h.status == 413


def test_read_json_body_invalid_json_is_400():
    raw = b"{not json"
    h = make(body=raw, headers={"Content-Length": str(len(raw))})
    assert h._read_json_body() is None
    assert h.status == 400


# ===========================================================================
# do_POST
# ===========================================================================


def test_post_redis_start_reports_success():
    h = make(path="/api/redis/start", headers={"Content-Length": "0"})
    h.do_POST()
    assert h.status == 200 and h.json_body()["success"] is True


def test_post_redis_stop():
    h = make(path="/api/redis/stop", headers={"Content-Length": "0"})
    h.do_POST()
    assert h.json_body()["success"] is True


def test_post_memory_clear_valid_agent():
    panel = _FakePanel()
    body = json.dumps({"agent_id": "alice"}).encode()
    h = _Recorder(
        path="/api/memory/clear",
        body=body,
        headers={"Content-Length": str(len(body))},
        panel=panel,
    )
    h.do_POST()
    assert h.json_body()["keys_deleted"] == 3
    assert panel.cleared == ["alice"]


def test_post_memory_clear_invalid_agent_is_400():
    body = json.dumps({"agent_id": "bad/agent"}).encode()
    h = _Recorder(
        path="/api/memory/clear",
        body=body,
        headers={"Content-Length": str(len(body))},
        panel=_FakePanel(),
    )
    h.do_POST()
    assert h.status == 400


def test_post_unknown_path_is_404():
    h = make(path="/api/redis/teleport", headers={"Content-Length": "0"})
    h.do_POST()
    assert h.status == 404


def test_post_rate_limited_and_unauthorized():
    rl = make(path="/api/redis/stop", rate_limiter=_FakeLimiter(allow=False))
    rl.do_POST()
    assert rl.status == 429

    ua = make(path="/api/redis/stop", api_auth=_FakeAuth(), headers={})
    ua.do_POST()
    assert ua.status == 401


# ===========================================================================
# do_DELETE
# ===========================================================================


def test_delete_pattern_valid():
    panel = _FakePanel()
    h = _Recorder(path="/api/patterns/patternone", panel=panel)
    h.do_DELETE()
    assert h.json_body()["success"] is True
    assert panel.deleted == ["patternone"]


def test_delete_pattern_invalid_id_is_400():
    h = _Recorder(path="/api/patterns/..", panel=_FakePanel())
    h.do_DELETE()
    assert h.status == 400


def test_delete_unknown_path_is_404():
    h = make(path="/api/other")
    h.do_DELETE()
    assert h.status == 404


def test_delete_rate_limited_and_unauthorized():
    rl = make(path="/api/patterns/patternone", rate_limiter=_FakeLimiter(allow=False))
    rl.do_DELETE()
    assert rl.status == 429

    ua = make(path="/api/patterns/patternone", api_auth=_FakeAuth(), headers={})
    ua.do_DELETE()
    assert ua.status == 401


# ===========================================================================
# _send_json rate-limit headers
# ===========================================================================


def test_send_json_includes_rate_limit_headers_when_limiter_present():
    h = make(path="/api/ping", rate_limiter=_FakeLimiter(allow=True))
    h.do_GET()
    assert h.resp_headers["X-RateLimit-Remaining"] == "42"
    assert h.resp_headers["X-RateLimit-Limit"] == "100"


# ===========================================================================
# Remaining handler edges
# ===========================================================================


def test_log_message_does_not_raise():
    """The structlog log_message override runs without touching stderr."""
    make().log_message("%s %s", "GET", "/api/ping")  # no exception = covered


def test_get_patterns_non_int_limit_falls_back_to_100():
    """A non-integer limit is tolerated, defaulting to 100."""
    h = _Recorder(path="/api/patterns?limit=abc", panel=_FakePanel())
    captured = {}
    orig = h.panel.list_patterns

    def spy(classification=None, limit=100):
        captured["limit"] = limit
        return orig(classification=classification, limit=limit)

    h.panel.list_patterns = spy
    h.do_GET()
    assert captured["limit"] == 100


def test_get_patterns_export_invalid_classification_is_400():
    h = _Recorder(path="/api/patterns/export?classification=BOGUS", panel=_FakePanel())
    h.do_GET()
    assert h.status == 400


def test_post_bad_body_returns_early_without_routing():
    """When _read_json_body fails, do_POST stops at the 400 (no route hit)."""
    panel = _FakePanel()
    raw = b"{broken"
    h = _Recorder(
        path="/api/memory/clear",
        body=raw,
        headers={"Content-Length": str(len(raw))},
        panel=panel,
    )
    h.do_POST()
    assert h.status == 400
    assert panel.cleared == []  # routing never reached
