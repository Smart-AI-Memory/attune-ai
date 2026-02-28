"""File test status dashboard - interactive HTML visualization.

Generates an HTML dashboard showing file-level test results with
filtering, search, and auto-refresh served via a local HTTP server.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import http.server
import socketserver
import webbrowser
from datetime import datetime
from typing import Any


def cmd_file_test_dashboard(args: Any) -> int:
    """Open interactive file test status dashboard in browser.

    Args:
        args: Parsed command-line arguments
            - port: Port to serve on (default: 8765)

    Returns:
        Exit code (0 for success)

    """
    from attune.models.telemetry import get_telemetry_store

    port = getattr(args, "port", 8765)

    def generate_dashboard_html() -> str:
        """Generate the dashboard HTML with current data."""
        store = get_telemetry_store()
        all_records = store.get_file_tests(limit=100000)

        if not all_records:
            return _generate_empty_dashboard()

        # Get latest record per file
        latest_by_file: dict[str, Any] = {}
        for record in all_records:
            existing = latest_by_file.get(record.file_path)
            if existing is None or record.timestamp > existing.timestamp:
                latest_by_file[record.file_path] = record

        records = list(latest_by_file.values())

        # Calculate stats
        total = len(records)
        passed = sum(1 for r in records if r.last_test_result == "passed")
        failed = sum(1 for r in records if r.last_test_result in ("failed", "error"))
        no_tests = sum(1 for r in records if r.last_test_result == "no_tests")
        stale = sum(1 for r in records if r.is_stale)

        # Sort by status priority: failed > stale > no_tests > passed
        def sort_key(r: Any) -> tuple[int, str]:
            if r.last_test_result in ("failed", "error"):
                return (0, r.file_path)
            if r.is_stale:
                return (1, r.file_path)
            if r.last_test_result == "no_tests":
                return (2, r.file_path)
            return (3, r.file_path)

        records.sort(key=sort_key)

        rows_html = _build_table_rows(records)
        return _build_file_test_html(
            total=total,
            passed=passed,
            failed=failed,
            no_tests=no_tests,
            stale=stale,
            rows_html=rows_html,
        )

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        """Custom handler for the dashboard."""

        def do_GET(self) -> None:
            """Handle GET requests."""
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                html = generate_dashboard_html()
                self.wfile.write(html.encode())
            else:
                self.send_error(404)

        def log_message(self, format: str, *args: Any) -> None:
            """Suppress logging."""

    print(f"Starting File Test Dashboard on http://localhost:{port}")
    print("Press Ctrl+C to stop the server")

    # Open browser
    webbrowser.open(f"http://localhost:{port}")

    # Start server
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")

    return 0


def _build_table_rows(records: list[Any]) -> str:
    """Build HTML table rows from file test records.

    Args:
        records: Sorted list of file test records

    Returns:
        HTML string of table rows

    """
    rows_html = ""
    for record in records:
        result = record.last_test_result
        if result == "passed":
            status_class = "passed"
            status_icon = "\u2705"
        elif result in ("failed", "error"):
            status_class = "failed"
            status_icon = "\u274c"
        elif result == "no_tests":
            status_class = "no-tests"
            status_icon = "\u26a0\ufe0f"
        else:
            status_class = "skipped"
            status_icon = "\u23ed\ufe0f"

        stale_badge = '<span class="badge stale">STALE</span>' if record.is_stale else ""

        try:
            dt = datetime.fromisoformat(record.timestamp.rstrip("Z"))
            ts_display = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            ts_display = record.timestamp[:16] if record.timestamp else "-"

        rows_html += f"""
        <tr class="{status_class}">
            <td class="file-path">{record.file_path}</td>
            <td class="status">{status_icon} {result.upper()} {stale_badge}</td>
            <td class="numeric">{record.test_count}</td>
            <td class="numeric passed-count">{record.passed}</td>
            <td class="numeric failed-count">{record.failed + record.errors}</td>
            <td class="numeric">{record.duration_seconds:.1f}s</td>
            <td class="timestamp">{ts_display}</td>
        </tr>
        """
    return rows_html


def _generate_empty_dashboard() -> str:
    """Generate dashboard HTML when no data available."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>File Test Status Dashboard</title>
    <style>
        body {
            font-family: -apple-system, sans-serif;
            background: #ffffff;
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }
        .message { max-width: 500px; }
        h1 { margin-bottom: 20px; color: #333; }
        code {
            background: #f8f9fa;
            color: #333;
            padding: 10px 20px;
            border-radius: 6px;
            display: block;
            margin-top: 20px;
            border: 1px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="message">
        <h1>\U0001f4ca No Test Data Available</h1>
        <p>Run the file test tracker to populate data:</p>
        <code>empathy file-tests --scan</code>
        <p style="margin-top: 20px; color: #888;">Or track individual files:</p>
        <code>python -c "from attune.workflows.test_runner import track_file_tests; track_file_tests('src/your_file.py')"</code>
    </div>
</body>
</html>"""


def _build_file_test_html(
    *,
    total: int,
    passed: int,
    failed: int,
    no_tests: int,
    stale: int,
    rows_html: str,
) -> str:
    """Build the file test dashboard HTML.

    Args:
        total: Total files tracked
        passed: Number passed
        failed: Number failed
        no_tests: Number with no tests
        stale: Number stale
        rows_html: Pre-built table rows HTML

    Returns:
        Complete HTML string

    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Test Status Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #ffffff;
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
        }
        .header h1 { font-size: 28px; color: #333; }
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .refresh-btn:active { transform: translateY(0); }
        .refresh-btn.spinning .icon { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stat-card.passed { border-left: 4px solid #22c55e; }
        .stat-card.failed { border-left: 4px solid #ef4444; }
        .stat-card.no-tests { border-left: 4px solid #f59e0b; }
        .stat-card.stale { border-left: 4px solid #8b5cf6; }
        .stat-card.total { border-left: 4px solid #3b82f6; }
        .stat-value { font-size: 36px; font-weight: bold; }
        .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
        .stat-card.passed .stat-value { color: #22c55e; }
        .stat-card.failed .stat-value { color: #ef4444; }
        .stat-card.no-tests .stat-value { color: #f59e0b; }
        .stat-card.stale .stat-value { color: #8b5cf6; }
        .stat-card.total .stat-value { color: #3b82f6; }
        .filter-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .filter-btn {
            background: #f8f9fa;
            color: #666;
            border: 1px solid #e0e0e0;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-btn:hover, .filter-btn.active {
            background: #667eea;
            color: #fff;
            border-color: #667eea;
        }
        .search-input {
            flex: 1;
            min-width: 200px;
            background: #fff;
            border: 1px solid #e0e0e0;
            color: #333;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
        }
        .search-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        th, td { padding: 12px 16px; text-align: left; }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
            position: sticky;
            top: 0;
            border-bottom: 2px solid #e0e0e0;
        }
        tr { border-bottom: 1px solid #f0f0f0; }
        tr:hover { background: #f8f9fa; }
        tr.failed { background: rgba(239, 68, 68, 0.08); }
        tr.no-tests { background: rgba(245, 158, 11, 0.05); }
        .file-path { font-family: 'Monaco', 'Menlo', monospace; font-size: 13px; color: #333; }
        .numeric { text-align: right; font-family: monospace; }
        .passed-count { color: #22c55e; }
        .failed-count { color: #ef4444; }
        .timestamp { color: #888; font-size: 12px; }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 8px;
        }
        .badge.stale { background: #8b5cf6; color: #fff; }
        .hidden { display: none; }
        .last-updated { color: #888; font-size: 12px; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>\U0001f4ca File Test Status Dashboard</h1>
            <button class="refresh-btn" onclick="refreshData()">
                <span class="icon">\U0001f504</span>
                <span>Refresh</span>
            </button>
        </div>

        <div class="stats">
            <div class="stat-card total">
                <div class="stat-value">"""
        + str(total)
        + """</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card passed">
                <div class="stat-value">"""
        + str(passed)
        + """</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">"""
        + str(failed)
        + """</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card no-tests">
                <div class="stat-value">"""
        + str(no_tests)
        + """</div>
                <div class="stat-label">No Tests</div>
            </div>
            <div class="stat-card stale">
                <div class="stat-value">"""
        + str(stale)
        + """</div>
                <div class="stat-label">Stale</div>
            </div>
        </div>

        <div class="filter-bar">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="passed">\u2705 Passed</button>
            <button class="filter-btn" data-filter="failed">\u274c Failed</button>
            <button class="filter-btn" data-filter="no-tests">\u26a0\ufe0f No Tests</button>
            <button class="filter-btn" data-filter="stale">\U0001f504 Stale</button>
            <input type="text" class="search-input" placeholder="Search files..." id="searchInput">
        </div>

        <table id="fileTable">
            <thead>
                <tr>
                    <th>File Path</th>
                    <th>Status</th>
                    <th>Tests</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Duration</th>
                    <th>Last Run</th>
                </tr>
            </thead>
            <tbody>
                """
        + rows_html
        + """
            </tbody>
        </table>

        <div class="last-updated">
            Last updated: """
        + now_str
        + """
        </div>
    </div>

    <script>
        // Filter functionality
        const filterBtns = document.querySelectorAll('.filter-btn');
        const rows = document.querySelectorAll('#fileTable tbody tr');
        const searchInput = document.getElementById('searchInput');

        let currentFilter = 'all';

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                applyFilters();
            });
        });

        searchInput.addEventListener('input', applyFilters);

        function applyFilters() {
            const searchTerm = searchInput.value.toLowerCase();
            rows.forEach(row => {
                const filePath = row.querySelector('.file-path').textContent.toLowerCase();
                const matchesSearch = filePath.includes(searchTerm);
                const matchesFilter = currentFilter === 'all' ||
                    (currentFilter === 'passed' && row.classList.contains('passed')) ||
                    (currentFilter === 'failed' && row.classList.contains('failed')) ||
                    (currentFilter === 'no-tests' && row.classList.contains('no-tests')) ||
                    (currentFilter === 'stale' && row.innerHTML.includes('STALE'));

                row.classList.toggle('hidden', !(matchesSearch && matchesFilter));
            });
        }

        // Refresh functionality
        function refreshData() {
            const btn = document.querySelector('.refresh-btn');
            btn.classList.add('spinning');
            btn.disabled = true;

            // Reload the page to get fresh data
            setTimeout(() => {
                window.location.reload();
            }, 500);
        }
    </script>
</body>
</html>"""
    )
