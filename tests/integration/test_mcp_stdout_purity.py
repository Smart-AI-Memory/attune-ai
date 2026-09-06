"""Regression: the MCP server's stdout must carry ONLY JSON-RPC frames.

Transport receipt 6 (cross-provider-memory-transport, 2026-07-27) found
structlog's default stdout PrintLogger interleaving sanitizer debug lines
(``pii_scrubbed`` etc.) with protocol frames during
``session_memory_capture``. Lenient clients (Claude Code) tolerated it;
Antigravity's strict client failed the call with "invalid trailing data
at the end of stream". This test spawns the REAL server process, drives a
PII-bearing capture through the real sanitizer, and fails if any stdout
line is not valid JSON.
"""

import json
import os
import subprocess
import sys
import threading

import pytest

CANARY = "STDOUT-PURITY-CANARY: contact test@example.com re protocol"


def _rpc(obj: dict) -> str:
    return json.dumps(obj) + "\n"


class _LineReader:
    """Collect stdout lines on a thread so reads can time out portably."""

    def __init__(self, stream) -> None:
        self.lines: list[str] = []
        self._stream = stream
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        for line in self._stream:
            self.lines.append(line.rstrip("\n"))

    def wait_for_id(self, rpc_id: int, timeout: float) -> dict | None:
        deadline = threading.Event()
        self._thread.join(timeout=0)  # ensure started
        import time

        end = time.time() + timeout
        while time.time() < end:
            for line in list(self.lines):
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("id") == rpc_id:
                    return msg
            if deadline.wait(0.1):
                break
        return None


@pytest.mark.integration
def test_session_memory_capture_keeps_stdout_json_only(tmp_path):
    env = dict(os.environ)
    env["ATTUNE_REDIS_REQUIRED"] = "false"
    env["ATTUNE_MEMORY_BACKEND"] = "file"
    # Keep the stash inside the test sandbox: HOME redirects the file
    # fallback, and the explicit file preference avoids probing AMS/Redis
    # on machines where a real local Redis is running (otherwise the
    # canary lands in the developer's live store — observed 2026-07-27).
    env["HOME"] = str(tmp_path)
    env["AMS_BASE_URL"] = "http://127.0.0.1:1"
    env["REDIS_URL"] = "redis://127.0.0.1:1/0"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, "-m", "attune.mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        reader = _LineReader(proc.stdout)
        assert proc.stdin is not None
        proc.stdin.write(
            _rpc(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "stdout-purity", "version": "0"},
                    },
                }
            )
        )
        proc.stdin.flush()
        assert reader.wait_for_id(1, 30) is not None, "no initialize response"

        proc.stdin.write(_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        proc.stdin.write(
            _rpc(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "session_memory_capture",
                        "arguments": {"content": CANARY, "type": "note"},
                    },
                }
            )
        )
        proc.stdin.flush()
        response = reader.wait_for_id(2, 60)
        assert response is not None, "no tools/call response"
        assert "error" not in response, response
        assert not response["result"].get("isError", False), response

        non_json = [line for line in reader.lines if line and not _parses(line)]
        assert non_json == [], (
            "stdout carried non-JSON lines alongside the protocol stream "
            f"(strict MCP clients reject the frame): {non_json[:5]}"
        )
    finally:
        proc.kill()
        proc.wait(timeout=10)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


def _parses(line: str) -> bool:
    try:
        json.loads(line)
    except ValueError:
        return False
    return True
