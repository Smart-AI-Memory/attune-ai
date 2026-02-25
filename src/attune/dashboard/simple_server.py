"""Simple Dashboard Server - Zero External Dependencies.

Uses only Python standard library (http.server, json) to serve the dashboard.
No FastAPI, Flask, or other web frameworks required.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from attune.telemetry import (
    ApprovalGate,
    CoordinationSignals,
    EventStreamer,
    FeedbackLoop,
    HeartbeatCoordinator,
)

logger = logging.getLogger(__name__)


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard."""

    _memory = None
    _memory_lock = threading.Lock()

    @classmethod
    def get_memory(cls):
        """Get or create shared RedisShortTermMemory instance.

        Uses lazy initialization with thread-safe locking. Recreates
        the instance if the connection is lost.
        """
        from attune.memory.short_term import RedisShortTermMemory

        if cls._memory is not None:
            try:
                cls._memory.ping()
                return cls._memory
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Connection lost, recreate below
                logger.warning(
                    "dashboard_memory_reconnect", message="Redis connection lost, recreating"
                )
                cls._memory = None

        with cls._memory_lock:
            # Double-check after acquiring lock
            if cls._memory is None:
                cls._memory = RedisShortTermMemory()
            return cls._memory

    # MIME types for static asset serving
    MIME_TYPES = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }

    def _has_react_build(self) -> bool:
        """Check if the React build exists."""
        react_dir = Path(__file__).parent / "static" / "react"
        return (react_dir / "index.html").exists()

    def _serve_react_asset(self, asset_path: str) -> bool:
        """Serve a file from the React build directory.

        Returns True if the file was found and served.
        """
        react_dir = Path(__file__).parent / "static" / "react"
        # Prevent path traversal
        try:
            full_path = (react_dir / asset_path.lstrip("/")).resolve()
            full_path.relative_to(react_dir.resolve())
        except (ValueError, OSError):
            return False

        if not full_path.is_file():
            return False

        suffix = full_path.suffix.lower()
        content_type = self.MIME_TYPES.get(suffix, "application/octet-stream")

        try:
            content = full_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            # Cache hashed assets aggressively
            if "/assets/" in asset_path:
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(content)
            return True
        except OSError:
            return False

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Route requests — API endpoints first
        if path == "/api/health":
            self.api_health()
        elif path == "/api/agents":
            self.api_agents()
        elif path.startswith("/api/agents/"):
            agent_id = path.split("/")[-1]
            self.api_agent_detail(agent_id)
        elif path == "/api/signals":
            limit = int(query.get("limit", [50])[0])
            self.api_signals(limit)
        elif path == "/api/events":
            event_type = query.get("event_type", [None])[0]
            limit = int(query.get("limit", [100])[0])
            self.api_events(event_type, limit)
        elif path == "/api/approvals":
            self.api_approvals()
        elif path == "/api/feedback/workflows":
            self.api_feedback_workflows()
        elif path == "/api/feedback/underperforming":
            threshold = float(query.get("threshold", [0.7])[0])
            self.api_underperforming(threshold)
        elif path == "/api/system/services":
            self.api_system_services()
        # Static files — try React build first, then legacy
        elif self._has_react_build():
            # Serve React hashed assets (e.g. /assets/index-abc123.js)
            if path.startswith("/assets/"):
                if not self._serve_react_asset(path):
                    self.send_error(404, "Not Found")
            else:
                # SPA fallback: serve React index.html for all non-API routes
                self._serve_react_asset("index.html")
        else:
            # Legacy static file serving (vanilla HTML/CSS/JS dashboard)
            if path == "/" or path == "/index.html":
                self.serve_file("index.html", "text/html")
            elif path == "/static/style.css":
                self.serve_file("style.css", "text/css")
            elif path == "/static/app.js":
                self.serve_file("app.js", "application/javascript")
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Get request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        data = json.loads(body.decode("utf-8")) if body else {}

        # Route requests
        if "/approve" in path:
            request_id = path.split("/")[-2]
            self.api_approve(request_id, data.get("reason", "Approved via dashboard"))
        elif "/reject" in path:
            request_id = path.split("/")[-2]
            self.api_reject(request_id, data.get("reason", "Rejected via dashboard"))
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, filename: str, content_type: str):
        """Serve static file."""
        try:
            static_dir = Path(__file__).parent / "static"
            file_path = static_dir / filename

            if not file_path.exists():
                self.send_error(404, f"File not found: {filename}")
                return

            content = file_path.read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logger.error(f"Failed to serve file {filename}: {e}")
            self.send_error(500, str(e))

    def send_json(self, data: dict | list, status: int = 200):
        """Send JSON response."""
        try:
            content = json.dumps(data).encode("utf-8")

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")  # CORS
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logger.error(f"Failed to send JSON: {e}")
            self.send_error(500, str(e))

    # ========================================================================
    # API Endpoints
    # ========================================================================

    def api_health(self):
        """System health endpoint."""
        try:
            memory = self.get_memory()
            has_redis = memory._client is not None

            coordinator = HeartbeatCoordinator(memory=memory)
            active_agents = len(coordinator.get_active_agents()) if has_redis else 0

            gate = ApprovalGate(memory=memory)
            pending_approvals = len(gate.get_pending_approvals()) if has_redis else 0

            self.send_json(
                {
                    "status": "healthy" if has_redis else "degraded",
                    "redis_available": has_redis,
                    "active_agents": active_agents,
                    "pending_approvals": pending_approvals,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            self.send_json({"status": "error", "error": str(e)}, status=500)

    def api_agents(self):
        """List active agents."""
        try:
            memory = self.get_memory()
            coordinator = HeartbeatCoordinator(memory=memory)
            active_agents = coordinator.get_active_agents()

            result = []
            for agent in active_agents:
                result.append(
                    {
                        "agent_id": agent.agent_id,
                        "display_name": agent.display_name,
                        "status": agent.status,
                        "last_seen": agent.last_beat.isoformat(),
                        "progress": agent.progress,
                        "current_task": agent.current_task,
                    }
                )

            self.send_json(result)
        except Exception as e:
            logger.error(f"Failed to get agents: {e}")
            self.send_json([], status=500)

    def api_agent_detail(self, agent_id: str):
        """Get specific agent details."""
        try:
            memory = self.get_memory()
            coordinator = HeartbeatCoordinator(memory=memory)
            heartbeat = coordinator.get_agent_status(agent_id)

            if not heartbeat:
                self.send_json({"error": f"Agent {agent_id} not found"}, status=404)
                return

            self.send_json(
                {
                    "agent_id": heartbeat.agent_id,
                    "status": heartbeat.status,
                    "last_seen": heartbeat.last_beat.isoformat(),
                    "progress": heartbeat.progress,
                    "current_task": heartbeat.current_task,
                    "metadata": heartbeat.metadata,
                }
            )
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def api_signals(self, limit: int):
        """Get recent coordination signals."""
        try:
            memory = self.get_memory()
            # Use broadcast target to get all signals (not just for dashboard)
            signals = CoordinationSignals(memory=memory, agent_id="*")
            recent = signals.get_pending_signals()[:limit]

            result = [
                {
                    "signal_type": sig.signal_type,
                    "source_agent": sig.source_agent,
                    "target_agent": sig.target_agent,
                    "timestamp": sig.timestamp.isoformat(),
                    "payload": sig.payload,
                }
                for sig in recent
            ]

            self.send_json(result)
        except Exception as e:
            logger.error(f"Failed to get signals: {e}")
            self.send_json([])

    def api_events(self, event_type: str | None, limit: int):
        """Get recent events."""
        try:
            memory = self.get_memory()
            streamer = EventStreamer(memory=memory)

            if event_type:
                events = list(streamer.get_recent_events(event_type, count=limit))
            else:
                # Get events from multiple streams
                all_events = []
                for evt_type in ["agent_heartbeat", "coordination_signal", "workflow_progress"]:
                    events = list(streamer.get_recent_events(evt_type, count=20))
                    all_events.extend(events)

                all_events.sort(key=lambda e: e.timestamp, reverse=True)
                events = all_events[:limit]

            result = [
                {
                    "event_id": evt.event_id,
                    "event_type": evt.event_type,
                    "timestamp": evt.timestamp.isoformat(),
                    "data": evt.data,
                    "source": evt.source,
                }
                for evt in events
            ]

            self.send_json(result)
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            self.send_json([])

    def api_approvals(self):
        """Get pending approvals."""
        try:
            memory = self.get_memory()
            gate = ApprovalGate(memory=memory)
            pending = gate.get_pending_approvals()

            result = [
                {
                    "request_id": req.request_id,
                    "approval_type": req.approval_type,
                    "agent_id": req.agent_id,
                    "context": req.context,
                    "timestamp": req.timestamp.isoformat(),
                    "timeout_seconds": req.timeout_seconds,
                }
                for req in pending
            ]

            self.send_json(result)
        except Exception as e:
            logger.error(f"Failed to get approvals: {e}")
            self.send_json([])

    def api_approve(self, request_id: str, reason: str):
        """Approve request."""
        try:
            memory = self.get_memory()
            gate = ApprovalGate(memory=memory)
            success = gate.respond_to_approval(
                request_id=request_id, approved=True, responder="dashboard", reason=reason
            )

            if success:
                self.send_json({"status": "approved", "request_id": request_id})
            else:
                self.send_json({"error": "Failed to approve"}, status=500)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def api_reject(self, request_id: str, reason: str):
        """Reject request."""
        try:
            memory = self.get_memory()
            gate = ApprovalGate(memory=memory)
            success = gate.respond_to_approval(
                request_id=request_id, approved=False, responder="dashboard", reason=reason
            )

            if success:
                self.send_json({"status": "rejected", "request_id": request_id})
            else:
                self.send_json({"error": "Failed to reject"}, status=500)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def api_feedback_workflows(self):
        """Get workflow quality metrics."""
        try:
            memory = self.get_memory()
            feedback = FeedbackLoop(memory=memory)

            workflows = ["code-review", "test-generation", "refactoring"]
            results = []

            for workflow in workflows:
                for stage in ["analysis", "generation", "validation"]:
                    for tier in ["cheap", "capable", "premium"]:
                        stats = feedback.get_quality_stats(workflow, stage, tier=tier)
                        if stats and stats.sample_count > 0:
                            results.append(
                                {
                                    "workflow_name": workflow,
                                    "stage_name": stage,
                                    "tier": tier,
                                    "avg_quality": stats.avg_quality,
                                    "sample_count": stats.sample_count,
                                    "trend": stats.recent_trend,
                                }
                            )

            self.send_json(results)
        except Exception as e:
            logger.error(f"Failed to get quality metrics: {e}")
            self.send_json([])

    def api_underperforming(self, threshold: float):
        """Get underperforming stages."""
        try:
            memory = self.get_memory()
            feedback = FeedbackLoop(memory=memory)

            workflows = ["code-review", "test-generation", "refactoring"]
            all_underperforming = []

            for workflow in workflows:
                underperforming = feedback.get_underperforming_stages(
                    workflow, quality_threshold=threshold
                )
                for stage_name, stats in underperforming:
                    all_underperforming.append(
                        {
                            "workflow_name": workflow,
                            "stage_name": stage_name,
                            "avg_quality": stats.avg_quality,
                            "sample_count": stats.sample_count,
                            "min_quality": stats.min_quality,
                            "max_quality": stats.max_quality,
                            "trend": stats.recent_trend,
                        }
                    )

            all_underperforming.sort(key=lambda x: float(x["avg_quality"]))
            self.send_json(all_underperforming)
        except Exception as e:
            logger.error(f"Failed to get underperforming: {e}")
            self.send_json([])

    def api_system_services(self):
        """Check real-time health of each system component.

        Returns a list of service status objects, one per component.
        Each check is fast (<10ms) — no expensive scans or Redis ops
        that could block the response.
        """
        import time

        results = []

        # --- helpers ---

        def ms(t0: float) -> int:
            return max(1, int((time.perf_counter() - t0) * 1000))

        def check_redis() -> tuple[str, int | None]:
            t0 = time.perf_counter()
            try:
                memory = self.get_memory()
                if memory._client is None:
                    return "DOWN", None
                memory.ping()
                return "HEALTHY", ms(t0)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: health check must never raise
                return "DOWN", None

        def check_model_router() -> tuple[str, int]:
            t0 = time.perf_counter()
            try:
                from attune.models.registry import MODEL_REGISTRY

                status = "HEALTHY" if MODEL_REGISTRY else "WARNING"
                return status, ms(t0)
            except Exception:  # noqa: BLE001
                return "DOWN", ms(t0)

        def check_cost_tracker() -> tuple[str, int, int]:
            """Returns (status, latency_ms, buffer_size)."""
            t0 = time.perf_counter()
            try:
                from attune.telemetry.usage_tracker import UsageTracker

                tracker = UsageTracker.get_instance()
                tracker.telemetry_dir.stat()
                with tracker._lock:
                    buf = len(tracker._buffer)
                return "HEALTHY", ms(t0), buf
            except Exception:  # noqa: BLE001
                return "WARNING", ms(t0), 0

        def check_wizard_engine() -> tuple[str, int]:
            t0 = time.perf_counter()
            try:
                from attune.wizard_registry import list_wizards

                list_wizards()
                return "HEALTHY", ms(t0)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: wizard engine may not be installed
                return "HEALTHY", ms(t0)

        def check_feedback_loop() -> tuple[str, int, str]:
            """Returns (status, latency_ms, backend_type)."""
            t0 = time.perf_counter()
            try:
                from attune.telemetry.feedback_loop import FeedbackLoop

                loop = FeedbackLoop()
                connected = loop.memory.is_connected()
                backend = loop.memory.get_stats().get("backend", "redis")
                status = "HEALTHY" if connected else "DOWN"
                return status, ms(t0), backend
            except Exception:  # noqa: BLE001
                return "DOWN", ms(t0), "unknown"

        # --- run checks ---

        redis_status, redis_latency = check_redis()
        router_status, router_latency = check_model_router()
        tracker_status, tracker_latency, buf_size = check_cost_tracker()
        wizard_status, wizard_latency = check_wizard_engine()
        feedback_status, feedback_latency, feedback_backend = check_feedback_loop()

        # Event Streamer and Approval Gate require Redis pub/sub
        redis_dep = "HEALTHY" if redis_status == "HEALTHY" else "DOWN"

        results = [
            {
                "name": "Model Router",
                "description": "Intelligent tier selection and escalation",
                "status": router_status,
                "latency_ms": router_latency,
            },
            {
                "name": "Redis Cache",
                "description": "Primary data store and pub/sub",
                "status": redis_status,
                "latency_ms": redis_latency,
            },
            {
                "name": "Redis Agents",
                "description": "Agent heartbeat and state coordination",
                "status": redis_status,
                "latency_ms": redis_latency,
            },
            {
                "name": "Wizard Engine",
                "description": "Multi-step workflow execution runtime",
                "status": wizard_status,
                "latency_ms": wizard_latency,
            },
            {
                "name": "Cost Tracker",
                "description": "Usage telemetry and cost optimization",
                "status": tracker_status,
                "latency_ms": tracker_latency,
                "buffer_size": buf_size,
            },
            {
                "name": "Feedback Loop",
                "description": "Agent-to-LLM quality feedback pipeline",
                "status": feedback_status,
                "latency_ms": feedback_latency,
                "backend": feedback_backend,
            },
            {
                "name": "Event Streamer",
                "description": "Real-time event distribution via Redis streams",
                "status": redis_dep,
                "latency_ms": redis_latency,
            },
            {
                "name": "Approval Gate",
                "description": "Human-in-the-loop approval management",
                "status": redis_dep,
                "latency_ms": redis_latency,
            },
        ]

        self.send_json(results)

    def log_message(self, format, *args):
        """Suppress default logging."""
        # Override to reduce noise - only log errors
        if args[1][0] in ("4", "5"):  # 4xx or 5xx errors
            logger.warning(f"{self.address_string()} - {format % args}")


def run_simple_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """Run dashboard using only Python standard library.

    No external dependencies required (no FastAPI, Flask, etc).

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)

    Example:
        >>> from attune.dashboard.simple_server import run_simple_dashboard
        >>> run_simple_dashboard(host="0.0.0.0", port=8080)
    """
    server = HTTPServer((host, port), DashboardHandler)

    print(f"🚀 Agent Coordination Dashboard running at http://{host}:{port}")
    print(f"📊 Open in browser: http://{host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down dashboard...")
        server.shutdown()


if __name__ == "__main__":
    run_simple_dashboard()
