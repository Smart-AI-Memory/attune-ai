"""Local, disposable browser host for real MCP workspace timing.

Uses installed packages and the public stdio server. No model calls or external
board writes occur: seven synthetic candidates live only in this server process.
The host creates a private receipt directory; the browser drives real controls.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import mkdtemp

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

ROOT = Path(mkdtemp(prefix="attune-latency-host-")).resolve()
PAGE = Path(__file__).with_name("browser_host.html").resolve()
current: dict = {}
condition = ""


def unpack(result):
    """Read the public tool result without depending on text wrapping."""
    if result.isError:
        raise ValueError(str(result.content))
    data = result.structuredContent
    if not data:
        data = json.loads(next(block.text for block in result.content if block.type == "text"))
    if not data.get("success"):
        raise ValueError(str(data))
    return data


async def serve():
    """Keep a real stdio session alive while the loopback UI performs actions."""
    global current, condition
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "attune.mcp.server"],
        cwd=str(ROOT),
        env={
            **get_default_environment(),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "ANTHROPIC_API_KEY": "",
            "ATTUNE_FORMS_HOME": str(ROOT),
            "ATTUNE_HOME": str(ROOT),
            "ATTUNE_FORMS_TELEMETRY": "1",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            loop = asyncio.get_running_loop()

            async def call(name, args):
                return unpack(await session.call_tool(name, args))

            async def start(mode):
                global current, condition
                if mode not in {"baseline", "batched"}:
                    raise ValueError("Unknown condition")
                condition = mode
                current = await call(
                    "command_workspace_open",
                    {
                        "adapter_id": "roundtable",
                        "intake": {
                            "question": "Synthetic latency comparison",
                            "thread_id": "latency-test",
                            "expected_rounds": 1,
                            "max_invocations": 3,
                        },
                    },
                )

                # Titles come from the exact current rendered document.
                async def accept(name):
                    title = re.search(r'data-workspace-title="([^"]+)"', current["html"]).group(1)
                    payload = {
                        "__elicitation_response__": True,
                        "title": title,
                        "view": current["view"],
                        "action": name,
                        "confirmed": True,
                        **{
                            k: current[k]
                            for k in ("workspace_id", "revision", "action_nonce", "contract_hash")
                        },
                    }
                    return await call("command_workspace_collect_action", {"response": payload})

                current = await accept("start_roundtable")
                current = await call(
                    "command_workspace_publish",
                    {
                        "workspace_id": current["workspace_id"],
                        "event": {
                            "kind": "round_complete",
                            "receipts": [
                                {
                                    "seat": seat,
                                    "status": "complete",
                                    "message_id": i,
                                    "detail": "Synthetic fixture; no provider invoked",
                                    "compiler_clean": True,
                                }
                                for i, seat in enumerate(("claude", "antigravity", "codex"), 1)
                            ],
                        },
                    },
                )
                current = await accept("synthesize")
                current = await call(
                    "command_workspace_publish",
                    {
                        "workspace_id": current["workspace_id"],
                        "event": {
                            "kind": "synthesis",
                            "body": "Seven synthetic candidates; decline all in both conditions.",
                            "candidates": [
                                {
                                    "message_id": i,
                                    "title": f"Candidate {i}",
                                    "detail": "Test data only",
                                }
                                for i in range(10, 17)
                            ],
                        },
                    },
                )
                return current

            async def submit(payload):
                global current
                expected = "decline" if condition == "baseline" else "apply_rulings"
                if payload.get("action") != expected:
                    raise ValueError(f"This test condition requires {expected}")
                if payload.get("workspace_id") != current.get("workspace_id"):
                    raise ValueError("Wrong test workspace")
                if expected == "apply_rulings" and any(
                    value != "decline" for value in payload.get("responses", {}).values()
                ):
                    raise ValueError("The paired fixture requires decline for every candidate")
                current = await call("command_workspace_collect_action", {"response": payload})
                return current

            class Handler(BaseHTTPRequestHandler):
                """Bounded loopback-only adapter; request data never names files or tools."""

                def log_message(self, *args):
                    pass

                def reply(self, status, data, mime="application/json"):
                    body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
                    self.send_response(status)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def do_GET(self):
                    if self.path == "/":
                        self.reply(200, PAGE.read_text(), "text/html; charset=utf-8")
                    else:
                        self.reply(404, {})

                def do_POST(self):
                    try:
                        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
                        if self.headers.get("Origin") != expected_origin:
                            return self.reply(403, {"error": "Same-origin browser requests only"})
                        size = int(self.headers.get("Content-Length", "0"))
                        if not 0 < size <= 65536:
                            return self.reply(413, {})
                        data = json.loads(self.rfile.read(size))
                        if self.path == "/receipt":
                            # One append-only file in the private, server-created directory.
                            with (ROOT / "browser-receipts.jsonl").open("a") as stream:
                                stream.write(json.dumps(data) + "\n")
                            return self.reply(200, {"saved": True})
                        if self.path not in {"/start", "/submit"}:
                            return self.reply(404, {})
                        coro = (
                            start(data.get("condition")) if self.path == "/start" else submit(data)
                        )
                        result = asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)
                        self.reply(200, result)
                    except (ValueError, KeyError, TypeError, TimeoutError) as exc:
                        self.reply(400, {"error": str(exc)})

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            print(
                json.dumps(
                    {"url": f"http://127.0.0.1:{server.server_port}", "receipts": str(ROOT)}
                ),
                flush=True,
            )
            await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(serve())
