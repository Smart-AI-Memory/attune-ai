"""Memory Control Panel API server.

HTTP API handler and server for the Memory Control Panel REST API.
Provides endpoints for status, statistics, patterns, and Redis management.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from __future__ import annotations

import json
import signal
import ssl
import sys
import time  # noqa: F401 - used by MemoryAPIHandler indirectly
from dataclasses import asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

import structlog

from .control_panel_support import APIKeyAuth, RateLimiter
from .control_panel_validation import (
    _validate_agent_id,
    _validate_classification,
    _validate_pattern_id,
)

if TYPE_CHECKING:
    from .control_panel import MemoryControlPanel

logger = structlog.get_logger(__name__)


class MemoryAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Memory Control Panel API."""

    panel: MemoryControlPanel | None = None  # Set by server
    rate_limiter: RateLimiter | None = None  # Set by server
    api_auth: APIKeyAuth | None = None  # Set by server
    allowed_origins: list[str] | None = None  # Set by server for CORS

    def log_message(self, format, *args):
        """Override to use structlog instead of stderr."""
        logger.debug("api_request", message=format % args)

    def _get_client_ip(self) -> str:
        """Get client IP address, handling proxies."""
        # Check for X-Forwarded-For header (behind proxy)
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        # Fall back to direct connection
        return self.client_address[0]

    def _check_rate_limit(self) -> bool:
        """Check if request should be rate limited."""
        if self.rate_limiter is None:
            return True
        return self.rate_limiter.is_allowed(self._get_client_ip())

    def _check_auth(self) -> bool:
        """Check API key authentication."""
        if self.api_auth is None or not self.api_auth.enabled:
            return True

        # Check Authorization header
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self.api_auth.is_valid(token)

        # Check X-API-Key header
        api_key = self.headers.get("X-API-Key")
        if api_key:
            return self.api_auth.is_valid(api_key)

        return False

    def _get_cors_origin(self) -> str:
        """Get appropriate CORS origin header value."""
        origin = self.headers.get("Origin", "")

        # Prevent HTTP response splitting via CRLF injection
        if "\r" in origin or "\n" in origin:
            return "http://localhost:8765"

        if self.allowed_origins is None:
            # Default: allow localhost only
            if origin.startswith("http://localhost") or origin.startswith("https://localhost"):
                return origin
            return "http://localhost:8765"

        if "*" in self.allowed_origins:
            return "*"

        if origin in self.allowed_origins:
            return origin

        return self.allowed_origins[0] if self.allowed_origins else ""

    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", self._get_cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")

        # Add rate limit headers if available
        if self.rate_limiter:
            remaining = self.rate_limiter.get_remaining(self._get_client_ip())
            self.send_header("X-RateLimit-Remaining", str(remaining))
            self.send_header("X-RateLimit-Limit", str(self.rate_limiter.max_requests))

        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, message: str, status: int = 400):
        """Send error response."""
        self._send_json({"error": message, "status_code": status}, status)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", self._get_cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        # Rate limiting check
        if not self._check_rate_limit():
            self._send_error("Rate limit exceeded. Try again later.", 429)
            return

        # Authentication check (skip for ping endpoint)
        parsed = urlparse(self.path)
        path = parsed.path

        if path != "/api/ping" and not self._check_auth():
            self._send_error("Unauthorized. Provide valid API key.", 401)
            return

        query = parse_qs(parsed.query)

        if path == "/api/ping":
            self._send_json({"status": "ok", "service": "empathy-memory"})

        elif path == "/api/status":
            self._send_json(self.panel.status())

        elif path == "/api/stats":
            stats = self.panel.get_statistics()
            self._send_json(asdict(stats))

        elif path == "/api/health":
            self._send_json(self.panel.health_check())

        elif path == "/api/patterns":
            classification = query.get("classification", [None])[0]

            # Validate classification
            if not _validate_classification(classification):
                self._send_error("Invalid classification. Use PUBLIC, INTERNAL, or SENSITIVE.", 400)
                return

            # Validate and sanitize limit
            try:
                limit = int(query.get("limit", [100])[0])
                limit = max(1, min(limit, 1000))  # Clamp between 1 and 1000
            except (ValueError, TypeError):
                limit = 100

            patterns = self.panel.list_patterns(classification=classification, limit=limit)
            self._send_json(patterns)

        elif path == "/api/patterns/export":
            classification = query.get("classification", [None])[0]

            # Validate classification
            if not _validate_classification(classification):
                self._send_error("Invalid classification. Use PUBLIC, INTERNAL, or SENSITIVE.", 400)
                return

            patterns = self.panel.list_patterns(classification=classification)
            export_data = {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "classification_filter": classification,
                "patterns": patterns,
            }
            self._send_json({"pattern_count": len(patterns), "export_data": export_data})

        elif path.startswith("/api/patterns/"):
            pattern_id = path.split("/")[-1]

            # Validate pattern ID
            if not _validate_pattern_id(pattern_id):
                self._send_error("Invalid pattern ID format", 400)
                return

            patterns = self.panel.list_patterns()
            pattern = next((p for p in patterns if p.get("pattern_id") == pattern_id), None)
            if pattern:
                self._send_json(pattern)
            else:
                self._send_error("Pattern not found", 404)

        else:
            self._send_error("Not found", 404)

    def do_POST(self):
        """Handle POST requests."""
        # Rate limiting check
        if not self._check_rate_limit():
            self._send_error("Rate limit exceeded. Try again later.", 429)
            return

        # Authentication check
        if not self._check_auth():
            self._send_error("Unauthorized. Provide valid API key.", 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        # Read body if present (with size limit to prevent DoS)
        content_length = int(self.headers.get("Content-Length", 0))
        max_body_size = 1024 * 1024  # 1MB limit
        if content_length > max_body_size:
            self._send_error("Request body too large", 413)
            return

        body = {}
        if content_length > 0:
            try:
                body = json.loads(self.rfile.read(content_length).decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_error("Invalid JSON body", 400)
                return

        if path == "/api/redis/start":
            status = self.panel.start_redis(verbose=False)
            self._send_json(
                {
                    "success": status.available,
                    "message": f"Redis {'OK' if status.available else 'failed'} via {status.method.value}",
                },
            )

        elif path == "/api/redis/stop":
            stopped = self.panel.stop_redis()
            self._send_json(
                {
                    "success": stopped,
                    "message": "Redis stopped" if stopped else "Could not stop Redis",
                },
            )

        elif path == "/api/memory/clear":
            agent_id = body.get("agent_id", "admin")

            # Validate agent ID
            if not _validate_agent_id(agent_id):
                self._send_error("Invalid agent ID format", 400)
                return

            deleted = self.panel.clear_short_term(agent_id)
            self._send_json({"keys_deleted": deleted})

        else:
            self._send_error("Not found", 404)

    def do_DELETE(self):
        """Handle DELETE requests."""
        # Rate limiting check
        if not self._check_rate_limit():
            self._send_error("Rate limit exceeded. Try again later.", 429)
            return

        # Authentication check
        if not self._check_auth():
            self._send_error("Unauthorized. Provide valid API key.", 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/patterns/"):
            pattern_id = path.split("/")[-1]

            # Validate pattern ID to prevent path traversal
            if not _validate_pattern_id(pattern_id):
                self._send_error("Invalid pattern ID format", 400)
                return

            deleted = self.panel.delete_pattern(pattern_id)
            self._send_json({"success": deleted})
        else:
            self._send_error("Not found", 404)


def run_api_server(
    panel: MemoryControlPanel,
    host: str = "localhost",
    port: int = 8765,
    api_key: str | None = None,
    enable_rate_limit: bool = True,
    rate_limit_requests: int = 100,
    rate_limit_window: int = 60,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
    allowed_origins: list[str] | None = None,
):
    """Run the Memory API server with security features.

    Args:
        panel: MemoryControlPanel instance
        host: Host to bind to
        port: Port to bind to
        api_key: API key for authentication (or set EMPATHY_MEMORY_API_KEY env var)
        enable_rate_limit: Enable rate limiting
        rate_limit_requests: Max requests per window per IP
        rate_limit_window: Rate limit window in seconds
        ssl_certfile: Path to SSL certificate file for HTTPS
        ssl_keyfile: Path to SSL key file for HTTPS
        allowed_origins: List of allowed CORS origins (None = localhost only)

    """
    # Set up handler class attributes
    MemoryAPIHandler.panel = panel
    MemoryAPIHandler.allowed_origins = allowed_origins

    # Set up rate limiting
    if enable_rate_limit:
        MemoryAPIHandler.rate_limiter = RateLimiter(
            window_seconds=rate_limit_window,
            max_requests=rate_limit_requests,
        )
    else:
        MemoryAPIHandler.rate_limiter = None

    # Set up API key authentication
    MemoryAPIHandler.api_auth = APIKeyAuth(api_key)

    server = HTTPServer((host, port), MemoryAPIHandler)

    # Enable HTTPS if certificates provided
    use_https = False
    if ssl_certfile and ssl_keyfile:
        if Path(ssl_certfile).exists() and Path(ssl_keyfile).exists():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(ssl_certfile, ssl_keyfile)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            use_https = True
        else:
            logger.warning("ssl_cert_not_found", certfile=ssl_certfile, keyfile=ssl_keyfile)

    protocol = "https" if use_https else "http"

    # Graceful shutdown handler
    def shutdown_handler(signum, frame):
        print("\n\nReceived shutdown signal...")
        print("Stopping API server...")
        server.shutdown()
        # Stop Redis if we started it
        if panel.stop_redis():
            print("Stopped Redis")
        print("Shutdown complete.")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print(f"\n{'=' * 50}")
    print("EMPATHY MEMORY API SERVER")
    print(f"{'=' * 50}")
    print(f"\nServer running at {protocol}://{host}:{port}")

    # Security status
    print("\nSecurity:")
    print(f"  HTTPS:        {'✓ Enabled' if use_https else '✗ Disabled'}")
    print(f"  API Key Auth: {'✓ Enabled' if MemoryAPIHandler.api_auth.enabled else '✗ Disabled'}")
    print(
        f"  Rate Limit:   {'✓ Enabled (' + str(rate_limit_requests) + '/min)' if enable_rate_limit else '✗ Disabled'}",
    )
    print(f"  CORS Origins: {allowed_origins or ['localhost']}")

    print("\nEndpoints:")
    print("  GET  /api/ping           Health check (no auth)")
    print("  GET  /api/status         Memory system status")
    print("  GET  /api/stats          Detailed statistics")
    print("  GET  /api/health         Health check with recommendations")
    print("  GET  /api/patterns       List patterns")
    print("  GET  /api/patterns/export Export patterns")
    print("  POST /api/redis/start    Start Redis")
    print("  POST /api/redis/stop     Stop Redis")
    print("  POST /api/memory/clear   Clear short-term memory")

    if MemoryAPIHandler.api_auth.enabled:
        print("\nAuthentication:")
        print("  Add header: Authorization: Bearer <your-api-key>")
        print("  Or header:  X-API-Key: <your-api-key>")

    print("\nPress Ctrl+C to stop\n")

    server.serve_forever()
