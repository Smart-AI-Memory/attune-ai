"""AMS readback boundary receipts against a fixture-owned HTTP service.

The real client serializes writes and reads records back over HTTP. A write
acknowledgment without persistence must fail the backend's readback check.
No running AMS, embedding model, credentials or availability probe is needed.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from tests._inference_guard import loopback_http_fixture

pytestmark = pytest.mark.integration


@pytest.fixture
def backend():
    from attune_redis.config import RedisPluginConfig
    from attune_redis.memory import AMSMemoryBackend

    records = {}
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body):
            payload = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            calls.append(("POST", self.path))
            if self.path != "/v1/long-term-memory/":
                self.reply(404, {"detail": "unknown fixture endpoint"})
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert payload["deduplicate"] is False
            for record in payload["memories"]:
                records[record["id"]] = record
            self.reply(200, {"status": "ok"})

        def do_GET(self):
            calls.append(("GET", self.path))
            record = records.get(self.path.removeprefix("/v1/long-term-memory/"))
            self.reply(200 if record else 404, record or {"detail": "Memory not found"})

        def do_DELETE(self):
            calls.append(("DELETE", self.path))
            for mid in parse_qs(urlsplit(self.path).query).get("memory_ids", []):
                records.pop(mid, None)
            self.reply(200, {"status": "ok"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = RedisPluginConfig(ams_base_url=f"http://127.0.0.1:{server.server_port}")
    be = AMSMemoryBackend(config)
    be._namespace = f"itest-readback-{uuid.uuid4().hex[:8]}"
    try:
        with loopback_http_fixture(server.socket):
            yield be, records, calls
    finally:
        be.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_live_write_reads_back(backend):
    from attune_redis.memory import _run_sync

    be, records, calls = backend
    mid = f"itest-{uuid.uuid4().hex}"
    try:
        assert be.remember("HTTP readback receipt", memory_id=mid) is True
        rec = _run_sync(be._client.get_long_term_memory(mid))
        assert rec.id == mid
        assert rec.text == records[mid]["text"] == "HTTP readback receipt"
        assert calls == [
            ("POST", "/v1/long-term-memory/"),
            ("GET", f"/v1/long-term-memory/{mid}"),
            ("GET", f"/v1/long-term-memory/{mid}"),
        ]
    finally:
        be.forget([mid])
    assert mid not in records


def test_live_unpersisted_write_is_not_a_success(backend, monkeypatch):
    """An acked-but-absent record produces a real HTTP 404 and returns False."""
    be, records, calls = backend

    async def _ack_without_write(*args, **kwargs):
        return None

    monkeypatch.setattr(be._client, "create_long_term_memory", _ack_without_write)
    mid = f"itest-{uuid.uuid4().hex}"
    assert be.remember("never persisted", memory_id=mid) is False
    assert mid not in records
    assert calls == [("GET", f"/v1/long-term-memory/{mid}")] * 3
