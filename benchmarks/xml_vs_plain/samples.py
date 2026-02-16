"""Benchmark sample corpus.

Code samples drawn from realistic patterns for security-audit, code-review,
and perf-audit workflows. Each sample has known expected findings for
automated quality evaluation.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from benchmarks.xml_vs_plain.config import BenchmarkSample, ExpectedFinding


def get_samples(workflow: str, max_samples: int = 10) -> list[BenchmarkSample]:
    """Get benchmark samples for a workflow.

    Args:
        workflow: Workflow name ("security-audit", "code-review", "perf-audit").
        max_samples: Maximum number of samples to return.

    Returns:
        List of BenchmarkSample objects.
    """
    all_samples = {
        "security-audit": _security_samples(),
        "code-review": _code_review_samples(),
        "perf-audit": _perf_audit_samples(),
    }
    samples = all_samples.get(workflow, [])
    return samples[:max_samples]


# ---------------------------------------------------------------------------
# Security audit samples
# ---------------------------------------------------------------------------


def _security_samples() -> list[BenchmarkSample]:
    return [
        # --- Easy: obvious vulnerabilities ---
        BenchmarkSample(
            id="sec-001",
            workflow="security-audit",
            name="eval() on user input",
            difficulty="easy",
            input_code='''\
def calculate(expression: str) -> float:
    """Calculate a math expression from user input."""
    result = eval(expression)
    return float(result)

def run_command(cmd: str) -> str:
    """Execute a shell command."""
    import subprocess
    return subprocess.check_output(cmd, shell=True).decode()
''',
            expected_findings=[
                ExpectedFinding("eval_usage", "critical", "line 3", required=True),
                ExpectedFinding("shell_injection", "critical", "line 8", required=True),
            ],
        ),
        BenchmarkSample(
            id="sec-002",
            workflow="security-audit",
            name="SQL injection in query builder",
            difficulty="easy",
            input_code='''\
import sqlite3

def get_user(username: str) -> dict | None:
    """Fetch user by username."""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_record(table: str, record_id: int) -> None:
    """Delete a record from any table."""
    conn = sqlite3.connect("app.db")
    conn.execute(f"DELETE FROM {table} WHERE id = {record_id}")
    conn.commit()
    conn.close()
''',
            expected_findings=[
                ExpectedFinding("sql_injection", "critical", "line 7", required=True),
                ExpectedFinding("sql_injection", "critical", "line 16", required=True),
            ],
        ),
        BenchmarkSample(
            id="sec-003",
            workflow="security-audit",
            name="Hardcoded credentials and path traversal",
            difficulty="easy",
            input_code='''\
import os

API_KEY = "sk-ant-api03-REAL_KEY_HERE_abc123"  # pragma: allowlist secret
DB_PASSWORD = "admin123"  # pragma: allowlist secret

def read_file(filename: str) -> str:
    """Read a file from the uploads directory."""
    path = os.path.join("/var/uploads", filename)
    with open(path, "r") as f:
        return f.read()

def write_config(user_path: str, data: str) -> None:
    """Write config data to user-specified path."""
    with open(user_path, "w") as f:
        f.write(data)
''',
            expected_findings=[
                ExpectedFinding("hardcoded_secret", "high", "line 3", required=True),
                ExpectedFinding("hardcoded_secret", "high", "line 4", required=True),
                ExpectedFinding("path_traversal", "high", "line 8", required=True),
                ExpectedFinding("arbitrary_write", "high", "line 14", required=True),
            ],
        ),
        BenchmarkSample(
            id="sec-004",
            workflow="security-audit",
            name="Insecure deserialization and weak crypto",
            difficulty="easy",
            input_code='''\
import pickle
import hashlib

def load_session(data: bytes) -> dict:
    """Load user session from cookie."""
    return pickle.loads(data)

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return hashlib.md5(password.encode()).hexdigest()

def verify_token(token: str, secret: str) -> bool:
    """Verify auth token."""
    import hmac
    expected = hmac.new(secret.encode(), digestmod="md5").hexdigest()
    return token == expected
''',
            expected_findings=[
                ExpectedFinding("insecure_deserialization", "critical", "line 6", required=True),
                ExpectedFinding("weak_crypto", "high", "line 10", required=True),
                ExpectedFinding("weak_crypto", "medium", "line 15", required=True),
            ],
        ),
        # --- Medium: subtle issues ---
        BenchmarkSample(
            id="sec-005",
            workflow="security-audit",
            name="SSRF and open redirect",
            difficulty="medium",
            input_code='''\
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

@app.route("/fetch")
def fetch_url():
    """Proxy endpoint to fetch external URLs."""
    url = request.args.get("url")
    response = requests.get(url)
    return response.text

@app.route("/redirect")
def redirect_handler():
    """Handle login redirects."""
    next_url = request.args.get("next", "/")
    return redirect(next_url)

@app.route("/upload", methods=["POST"])
def upload():
    """Handle file uploads."""
    file = request.files.get("file")
    file.save(f"/tmp/uploads/{file.filename}")
    return "OK"
''',
            expected_findings=[
                ExpectedFinding("ssrf", "high", "fetch_url", required=True),
                ExpectedFinding("open_redirect", "medium", "redirect_handler", required=True),
                ExpectedFinding("path_traversal", "high", "upload", required=True),
            ],
        ),
        BenchmarkSample(
            id="sec-006",
            workflow="security-audit",
            name="Race condition and timing attack",
            difficulty="medium",
            input_code='''\
import os
import time

balance_file = "/tmp/balance.txt"

def check_and_withdraw(amount: float) -> bool:
    """Check balance and withdraw if sufficient."""
    with open(balance_file) as f:
        balance = float(f.read().strip())
    if balance >= amount:
        time.sleep(0.01)  # simulate processing
        new_balance = balance - amount
        with open(balance_file, "w") as f:
            f.write(str(new_balance))
        return True
    return False

def verify_api_key(provided: str, stored: str) -> bool:
    """Verify API key matches."""
    return provided == stored
''',
            expected_findings=[
                ExpectedFinding("race_condition", "high", "check_and_withdraw", required=True),
                ExpectedFinding("timing_attack", "medium", "verify_api_key", required=True),
            ],
        ),
        BenchmarkSample(
            id="sec-007",
            workflow="security-audit",
            name="Improper error handling leaks info",
            difficulty="medium",
            input_code='''\
import traceback
from flask import Flask, jsonify

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_error(e):
    """Global error handler."""
    return jsonify({
        "error": str(e),
        "traceback": traceback.format_exc(),
        "type": type(e).__name__,
    }), 500

@app.route("/login", methods=["POST"])
def login():
    """Login endpoint."""
    from flask import request
    username = request.form["username"]
    password = request.form["password"]
    user = db.query(f"SELECT * FROM users WHERE name='{username}'")
    if user and user.password == password:
        return jsonify({"token": user.generate_token()})
    return jsonify({"error": f"Login failed for {username}"}), 401
''',
            expected_findings=[
                ExpectedFinding("info_disclosure", "high", "handle_error", required=True),
                ExpectedFinding("sql_injection", "critical", "login", required=True),
                ExpectedFinding("plaintext_password", "high", "login", required=False),
            ],
        ),
        # --- Hard: clean code (tests false positive rate) ---
        BenchmarkSample(
            id="sec-008",
            workflow="security-audit",
            name="Clean: properly validated file operations",
            difficulty="hard",
            input_code='''\
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ALLOWED_DIR = Path("/var/app/data")

def _validate_path(user_path: str) -> Path:
    """Validate file path against directory traversal."""
    if not user_path or not isinstance(user_path, str):
        raise ValueError("path must be a non-empty string")
    if "\\x00" in user_path:
        raise ValueError("path contains null bytes")
    resolved = Path(user_path).resolve()
    resolved.relative_to(ALLOWED_DIR)
    return resolved

def save_config(filepath: str, data: dict) -> Path:
    """Save config with validation."""
    validated = _validate_path(filepath)
    try:
        with validated.open("w") as f:
            json.dump(data, f, indent=2)
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise
    return validated
''',
            expected_findings=[],  # Clean code — any finding is a false positive
        ),
        BenchmarkSample(
            id="sec-009",
            workflow="security-audit",
            name="Clean: parameterized queries and bcrypt",
            difficulty="hard",
            input_code='''\
import bcrypt
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db():
    """Database connection context manager."""
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_user(username: str) -> dict | None:
    """Fetch user with parameterized query."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())
''',
            expected_findings=[],  # Clean code
        ),
        BenchmarkSample(
            id="sec-010",
            workflow="security-audit",
            name="Clean: safe subprocess and env vars",
            difficulty="hard",
            input_code='''\
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

ALLOWED_COMMANDS = {"git", "npm", "python"}

def run_tool(command: list[str], cwd: str | None = None) -> str:
    """Run an allowed tool safely."""
    if not command or command[0] not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not allowed: {command[0] if command else 'empty'}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
            check=False,
        )
        return result.stdout
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Command timed out: {e}")
        return ""

def get_api_key() -> str:
    """Get API key from environment."""
    key = os.environ.get("API_KEY", "")
    if not key:
        raise RuntimeError("API_KEY environment variable not set")
    return key
''',
            expected_findings=[],  # Clean code
        ),
    ]


# ---------------------------------------------------------------------------
# Code review samples
# ---------------------------------------------------------------------------


def _code_review_samples() -> list[BenchmarkSample]:
    return [
        # --- Easy: obvious issues ---
        BenchmarkSample(
            id="review-001",
            workflow="code-review",
            name="Missing error handling and bare except",
            difficulty="easy",
            input_code="""\
def process_data(filepath):
    data = open(filepath).read()
    result = json.loads(data)
    for item in result:
        item["processed"] = True
    return result

def risky_operation():
    try:
        do_something()
    except:
        pass

def calc(x, y):
    return x / y
""",
            expected_findings=[
                ExpectedFinding("missing_type_hints", "medium", "process_data", required=True),
                ExpectedFinding("no_error_handling", "high", "process_data", required=True),
                ExpectedFinding("bare_except", "high", "risky_operation", required=True),
                ExpectedFinding("division_by_zero", "medium", "calc", required=True),
            ],
        ),
        BenchmarkSample(
            id="review-002",
            workflow="code-review",
            name="Resource leak and mutable default",
            difficulty="easy",
            input_code="""\
class DataProcessor:
    def __init__(self, items=[]):
        self.items = items
        self.conn = sqlite3.connect("db.sqlite")

    def add(self, item):
        self.items.append(item)

    def process_all(self):
        results = []
        for item in self.items:
            result = self.conn.execute(
                f"SELECT * FROM cache WHERE key = '{item}'"
            ).fetchone()
            results.append(result)
        return results
""",
            expected_findings=[
                ExpectedFinding("mutable_default", "high", "__init__", required=True),
                ExpectedFinding("resource_leak", "medium", "__init__", required=True),
                ExpectedFinding("sql_injection", "high", "process_all", required=True),
            ],
        ),
        BenchmarkSample(
            id="review-003",
            workflow="code-review",
            name="God function and magic numbers",
            difficulty="easy",
            input_code="""\
def handle_request(request):
    if request.type == 1:
        data = request.body
        if len(data) > 10485760:
            return {"error": "too large"}
        result = process(data)
        if result.status == 0:
            db.save(result)
            cache.set(result.id, result, 3600)
            notify(result.owner)
            log(result)
            return {"ok": True, "id": result.id}
        elif result.status == 1:
            retry_queue.add(result, delay=300)
            return {"ok": False, "retry": True}
        else:
            error_db.save(result)
            alert(result, level=2)
            return {"ok": False, "error": result.message}
    elif request.type == 2:
        return handle_type_2(request)
    elif request.type == 3:
        return handle_type_3(request)
    return {"error": "unknown type"}
""",
            expected_findings=[
                ExpectedFinding("magic_numbers", "medium", "handle_request", required=True),
                ExpectedFinding("god_function", "medium", "handle_request", required=True),
                ExpectedFinding("missing_type_hints", "low", "handle_request", required=False),
            ],
        ),
        BenchmarkSample(
            id="review-004",
            workflow="code-review",
            name="Diff: adding retry logic",
            difficulty="easy",
            input_type="diff",
            input_code="""\
--- a/src/client.py
+++ b/src/client.py
@@ -15,8 +15,19 @@ class APIClient:
     def __init__(self, base_url: str, api_key: str):
         self.base_url = base_url
         self.api_key = api_key
+        self.max_retries = 3

-    def request(self, method: str, path: str, **kwargs) -> dict:
+    def request(self, method: str, path: str, **kwargs) -> dict:
+        for attempt in range(self.max_retries):
+            try:
+                return self._do_request(method, path, **kwargs)
+            except Exception:
+                if attempt == self.max_retries - 1:
+                    raise
+                import time
+                time.sleep(attempt * 2)
+
+    def _do_request(self, method: str, path: str, **kwargs) -> dict:
         url = f"{self.base_url}/{path}"
         headers = {"Authorization": f"Bearer {self.api_key}"}
         resp = requests.request(method, url, headers=headers, **kwargs)
""",
            expected_findings=[
                ExpectedFinding("broad_exception", "medium", "request", required=True),
                ExpectedFinding("no_backoff_jitter", "low", "request", required=False),
            ],
        ),
        # --- Medium: subtle issues ---
        BenchmarkSample(
            id="review-005",
            workflow="code-review",
            name="Async antipatterns",
            difficulty="medium",
            input_code='''\
import asyncio
import aiohttp

async def fetch_all(urls: list[str]) -> list[str]:
    """Fetch all URLs."""
    results = []
    for url in urls:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                results.append(await resp.text())
    return results

async def process_items(items: list[dict]) -> None:
    """Process items concurrently."""
    for item in items:
        await process_one(item)

async def get_or_compute(key: str) -> str:
    cache = {}
    if key in cache:
        return cache[key]
    value = await expensive_compute(key)
    cache[key] = value
    return value
''',
            expected_findings=[
                ExpectedFinding("session_per_request", "medium", "fetch_all", required=True),
                ExpectedFinding("sequential_async", "medium", "process_items", required=True),
                ExpectedFinding("local_cache_useless", "medium", "get_or_compute", required=True),
            ],
        ),
        BenchmarkSample(
            id="review-006",
            workflow="code-review",
            name="Thread safety issues",
            difficulty="medium",
            input_code="""\
import threading

class Counter:
    def __init__(self):
        self.value = 0
        self._cache = {}

    def increment(self):
        self.value += 1

    def get_cached(self, key: str) -> str | None:
        if key in self._cache:
            return self._cache[key]
        value = self._compute(key)
        self._cache[key] = value
        return value

    def _compute(self, key: str) -> str:
        import time
        time.sleep(0.1)
        return f"computed-{key}"

# Usage
counter = Counter()
threads = [threading.Thread(target=counter.increment) for _ in range(100)]
for t in threads:
    t.start()
for t in threads:
    t.join()
""",
            expected_findings=[
                ExpectedFinding("race_condition", "high", "increment", required=True),
                ExpectedFinding("race_condition", "medium", "get_cached", required=True),
            ],
        ),
        BenchmarkSample(
            id="review-007",
            workflow="code-review",
            name="API design issues",
            difficulty="medium",
            input_code='''\
from dataclasses import dataclass

@dataclass
class UserService:
    db: Database
    cache: Cache
    mailer: Mailer
    logger: Logger
    metrics: Metrics
    config: Config

    def create_user(self, name, email, password, role="user",
                    send_welcome=True, notify_admin=True,
                    create_workspace=True, sync_ldap=False) -> dict:
        """Create a new user with all the fixings."""
        user = self.db.insert("users", {
            "name": name, "email": email,
            "password": hash(password), "role": role
        })
        if send_welcome:
            self.mailer.send("welcome", email)
        if notify_admin:
            self.mailer.send("new_user", "admin@co.com")
        if create_workspace:
            self.db.insert("workspaces", {"owner": user["id"]})
        if sync_ldap:
            ldap_sync(user)
        self.cache.invalidate("users")
        self.metrics.increment("users.created")
        self.logger.info(f"Created user {name}")
        return user
''',
            expected_findings=[
                ExpectedFinding("too_many_parameters", "medium", "create_user", required=True),
                ExpectedFinding("too_many_dependencies", "medium", "UserService", required=False),
                ExpectedFinding("god_function", "medium", "create_user", required=True),
            ],
        ),
        # --- Hard: clean code ---
        BenchmarkSample(
            id="review-008",
            workflow="code-review",
            name="Clean: well-structured service",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class Repository(Protocol):
    """Repository interface."""
    def get(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> str: ...


@dataclass(frozen=True)
class CreateItemRequest:
    """Validated request for creating an item."""
    name: str
    category: str
    price: float

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 200:
            raise ValueError("name must be 1-200 characters")
        if self.price < 0:
            raise ValueError("price must be non-negative")


class ItemService:
    """Service for managing items."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def create(self, request: CreateItemRequest) -> str:
        """Create a new item.

        Args:
            request: Validated creation request.

        Returns:
            ID of the created item.

        Raises:
            ValueError: If request is invalid.
        """
        entity = {
            "name": request.name,
            "category": request.category,
            "price": request.price,
        }
        item_id = self._repo.save(entity)
        logger.info("Created item %s", item_id)
        return item_id

    def get(self, item_id: str) -> dict | None:
        """Get an item by ID."""
        return self._repo.get(item_id)
''',
            expected_findings=[],  # Clean code
        ),
        BenchmarkSample(
            id="review-009",
            workflow="code-review",
            name="Clean: proper async with error handling",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class HTTPClient:
    """Async HTTP client with connection pooling and retries."""

    def __init__(self, base_url: str, max_retries: int = 3) -> None:
        self._base_url = base_url
        self._max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self._base_url)
        return self._session

    async def get(self, path: str) -> dict[str, Any]:
        """GET request with retries and exponential backoff."""
        session = await self._get_session()
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with session.get(path) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except aiohttp.ClientError as e:
                last_error = e
                delay = 2 ** attempt
                logger.warning("Request failed (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(delay)
        raise ConnectionError(f"Failed after {self._max_retries} retries") from last_error

    async def close(self) -> None:
        """Close the underlying session."""
        if self._session and not self._session.closed:
            await self._session.close()
''',
            expected_findings=[],  # Clean code
        ),
        BenchmarkSample(
            id="review-010",
            workflow="code-review",
            name="Clean: data pipeline with validation",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Record:
    """A validated data record."""
    id: str
    value: float
    label: str


def parse_csv(path: Path) -> Iterator[Record]:
    """Parse CSV file yielding validated records.

    Args:
        path: Path to CSV file.

    Yields:
        Validated Record objects.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            try:
                yield Record(
                    id=row["id"].strip(),
                    value=float(row["value"]),
                    label=row["label"].strip(),
                )
            except (KeyError, ValueError) as e:
                logger.warning("Skipping row %d: %s", row_num, e)
                continue


def summarize(records: Iterator[Record]) -> dict[str, float]:
    """Summarize records by label."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for record in records:
        totals[record.label] = totals.get(record.label, 0.0) + record.value
        counts[record.label] = counts.get(record.label, 0) + 1
    return {label: totals[label] / counts[label] for label in totals}
''',
            expected_findings=[],  # Clean code
        ),
    ]


# ---------------------------------------------------------------------------
# Performance audit samples
# ---------------------------------------------------------------------------


def _perf_audit_samples() -> list[BenchmarkSample]:
    return [
        # --- Easy: obvious performance issues ---
        BenchmarkSample(
            id="perf-001",
            workflow="perf-audit",
            name="N+1 queries and unbounded list",
            difficulty="easy",
            input_code='''\
def get_users_with_orders():
    """Get all users and their orders."""
    users = db.query("SELECT * FROM users")
    result = []
    for user in users:
        orders = db.query(f"SELECT * FROM orders WHERE user_id = {user['id']}")
        user["orders"] = orders
        result.append(user)
    return result

def process_large_file(filepath: str) -> list[str]:
    """Process a large file."""
    with open(filepath) as f:
        lines = f.readlines()
    results = []
    for line in lines:
        results.append(line.strip().upper())
    return results
''',
            expected_findings=[
                ExpectedFinding("n_plus_one", "high", "get_users_with_orders", required=True),
                ExpectedFinding("unbounded_read", "medium", "process_large_file", required=True),
            ],
        ),
        BenchmarkSample(
            id="perf-002",
            workflow="perf-audit",
            name="Quadratic algorithm and repeated computation",
            difficulty="easy",
            input_code='''\
def find_duplicates(items: list[str]) -> list[str]:
    """Find duplicate items in a list."""
    duplicates = []
    for i, item in enumerate(items):
        for j, other in enumerate(items):
            if i != j and item == other and item not in duplicates:
                duplicates.append(item)
    return duplicates

def calculate_stats(data: list[dict]) -> dict:
    """Calculate statistics for each category."""
    categories = list(set(item["category"] for item in data))
    result = {}
    for cat in categories:
        cat_items = [item for item in data if item["category"] == cat]
        result[cat] = {
            "count": len(cat_items),
            "total": sum(item["value"] for item in data if item["category"] == cat),
            "avg": sum(item["value"] for item in data if item["category"] == cat) / len(cat_items),
        }
    return result
''',
            expected_findings=[
                ExpectedFinding("quadratic_algorithm", "high", "find_duplicates", required=True),
                ExpectedFinding("repeated_iteration", "medium", "calculate_stats", required=True),
            ],
        ),
        BenchmarkSample(
            id="perf-003",
            workflow="perf-audit",
            name="Synchronous I/O in async and global state",
            difficulty="easy",
            input_code='''\
import json
import time

_cache = {}

async def fetch_data(url: str) -> dict:
    """Fetch data from URL with caching."""
    if url in _cache:
        return _cache[url]
    import requests
    response = requests.get(url)  # synchronous in async!
    data = response.json()
    _cache[url] = data
    return data

def expensive_search(items: list[dict], query: str) -> list[dict]:
    """Search items by query."""
    results = []
    for item in items:
        if query.lower() in json.dumps(item).lower():
            results.append(item)
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
''',
            expected_findings=[
                ExpectedFinding("sync_in_async", "high", "fetch_data", required=True),
                ExpectedFinding("inefficient_search", "medium", "expensive_search", required=True),
            ],
        ),
        BenchmarkSample(
            id="perf-004",
            workflow="perf-audit",
            name="String concatenation in loop and sorted slice",
            difficulty="easy",
            input_code='''\
def build_report(records: list[dict]) -> str:
    """Build a text report from records."""
    report = ""
    for record in records:
        report += f"ID: {record['id']}\\n"
        report += f"  Name: {record['name']}\\n"
        report += f"  Value: {record['value']}\\n"
        report += "---\\n"
    return report

def get_top_10(items: list[dict]) -> list[dict]:
    """Get top 10 items by score."""
    return sorted(items, key=lambda x: x["score"], reverse=True)[:10]

def count_words(text: str) -> dict[str, int]:
    """Count word frequency."""
    words = text.split()
    counts = {}
    for word in words:
        if word in counts:
            counts[word] = counts[word] + 1
        else:
            counts[word] = 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
''',
            expected_findings=[
                ExpectedFinding("string_concat_loop", "medium", "build_report", required=True),
                ExpectedFinding("sorted_slice", "low", "get_top_10", required=True),
            ],
        ),
        # --- Medium: subtle issues ---
        BenchmarkSample(
            id="perf-005",
            workflow="perf-audit",
            name="Memory leak and connection exhaustion",
            difficulty="medium",
            input_code='''\
import functools
import sqlite3

class DataStore:
    _instances = []

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        DataStore._instances.append(self)

    @functools.lru_cache(maxsize=None)
    def get_item(self, item_id: str) -> dict | None:
        """Get item by ID with unbounded cache."""
        cursor = self.conn.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_items(self) -> list[dict]:
        """Get all items."""
        cursor = self.conn.execute("SELECT * FROM items")
        return [dict(row) for row in cursor.fetchall()]
''',
            expected_findings=[
                ExpectedFinding("unbounded_cache", "medium", "get_item", required=True),
                ExpectedFinding("memory_leak", "high", "_instances", required=True),
                ExpectedFinding("no_connection_close", "medium", "DataStore", required=True),
            ],
        ),
        BenchmarkSample(
            id="perf-006",
            workflow="perf-audit",
            name="Regex compilation in loop and redundant copies",
            difficulty="medium",
            input_code='''\
import re

def validate_emails(emails: list[str]) -> list[str]:
    """Validate a list of emails."""
    valid = []
    for email in emails:
        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")
        if pattern.match(email):
            valid.append(email)
    return valid

def deduplicate(items: list[str]) -> list[str]:
    """Remove duplicates preserving order."""
    return list(set(items))

def get_top_n(items: list[dict], n: int) -> list[dict]:
    """Get top N items by score."""
    copied = list(items)
    copied.sort(key=lambda x: x["score"], reverse=True)
    return copied[:n]
''',
            expected_findings=[
                ExpectedFinding("regex_in_loop", "medium", "validate_emails", required=True),
                ExpectedFinding("order_lost_dedup", "low", "deduplicate", required=True),
                ExpectedFinding("sorted_slice", "low", "get_top_n", required=False),
            ],
        ),
        BenchmarkSample(
            id="perf-007",
            workflow="perf-audit",
            name="Blocking event loop and excessive logging",
            difficulty="medium",
            input_code='''\
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

async def process_batch(items: list[dict]) -> list[dict]:
    """Process a batch of items."""
    results = []
    for item in items:
        logger.debug(f"Processing item: {item}")
        time.sleep(0.01)  # blocking sleep in async
        result = transform(item)
        logger.debug(f"Result: {result}")
        results.append(result)
        logger.info(f"Processed {len(results)}/{len(items)}")
    return results

async def poll_status(url: str, timeout: int = 60) -> str:
    """Poll a URL until ready."""
    start = time.time()
    while time.time() - start < timeout:
        status = await check_status(url)
        if status == "ready":
            return status
        await asyncio.sleep(0.1)  # aggressive polling
    raise TimeoutError("Polling timed out")
''',
            expected_findings=[
                ExpectedFinding("blocking_in_async", "high", "process_batch", required=True),
                ExpectedFinding("excessive_logging", "low", "process_batch", required=False),
                ExpectedFinding("aggressive_polling", "medium", "poll_status", required=True),
            ],
        ),
        # --- Hard: clean code ---
        BenchmarkSample(
            id="perf-008",
            workflow="perf-audit",
            name="Clean: efficient data processing pipeline",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import heapq
import re
from collections import defaultdict
from typing import Iterator

# Pre-compiled pattern
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")


def validate_emails(emails: Iterator[str]) -> Iterator[str]:
    """Validate emails using pre-compiled regex."""
    return (email for email in emails if _EMAIL_PATTERN.match(email))


def get_top_n(items: list[dict], n: int, key: str = "score") -> list[dict]:
    """Get top N items efficiently with heapq."""
    return heapq.nlargest(n, items, key=lambda x: x.get(key, 0))


def group_and_summarize(records: Iterator[dict]) -> dict[str, float]:
    """Group records by category and compute averages."""
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        cat = record["category"]
        totals[cat] += record["value"]
        counts[cat] += 1
    return {cat: totals[cat] / counts[cat] for cat in totals}


def deduplicate_ordered(items: list[str]) -> list[str]:
    """Deduplicate preserving insertion order."""
    return list(dict.fromkeys(items))
''',
            expected_findings=[],  # Clean code
        ),
        BenchmarkSample(
            id="perf-009",
            workflow="perf-audit",
            name="Clean: proper async with connection pooling",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import aiohttp

logger = logging.getLogger(__name__)


class AsyncHTTPPool:
    """Connection-pooled async HTTP client."""

    def __init__(self, base_url: str, pool_size: int = 10) -> None:
        self._base_url = base_url
        self._connector = aiohttp.TCPConnector(limit=pool_size)
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self._base_url,
                connector=self._connector,
            )
        return self._session

    async def fetch_many(self, paths: list[str]) -> list[dict[str, Any]]:
        """Fetch multiple paths concurrently with connection pooling."""
        session = await self._ensure_session()
        tasks = [self._fetch_one(session, path) for path in paths]
        return await asyncio.gather(*tasks)

    async def _fetch_one(
        self, session: aiohttp.ClientSession, path: str
    ) -> dict[str, Any]:
        async with session.get(path) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
''',
            expected_findings=[],  # Clean code
        ),
        BenchmarkSample(
            id="perf-010",
            workflow="perf-audit",
            name="Clean: cached computation with bounded LRU",
            difficulty="hard",
            input_code='''\
from __future__ import annotations

import functools
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=256)
def compute_file_hash(path: str, mtime: float) -> str:
    """Compute file hash with mtime-based cache invalidation.

    Args:
        path: File path.
        mtime: File modification time (for cache key).

    Returns:
        SHA-256 hex digest.
    """
    import hashlib
    content = Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()


def get_file_hash(path: str) -> str:
    """Get file hash with automatic cache invalidation."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    mtime = p.stat().st_mtime
    return compute_file_hash(str(p.resolve()), mtime)


def build_report(records: list[dict]) -> str:
    """Build report using string builder pattern."""
    parts: list[str] = []
    for record in records:
        parts.append(f"ID: {record['id']}")
        parts.append(f"  Name: {record['name']}")
        parts.append(f"  Value: {record['value']}")
        parts.append("---")
    return "\\n".join(parts)
''',
            expected_findings=[],  # Clean code
        ),
    ]
