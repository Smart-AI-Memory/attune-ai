"""One-Shot Example Constants for XML-Enhanced Prompts.

Curated input/output pairs that anchor LLM response format and severity
calibration. Each workflow gets one example (true one-shot) to minimise
token cost while still demonstrating the expected output shape.

Derived from the ground-truth samples in benchmarks/xml_vs_plain/samples.py.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

SECURITY_AUDIT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "def calculate(expression: str) -> float:\n"
            '    """Calculate a math expression from user input."""\n'
            "    result = eval(expression)\n"
            "    return float(result)\n"
            "\n"
            "def run_command(cmd: str) -> str:\n"
            '    """Execute a shell command."""\n'
            "    import subprocess\n"
            "    return subprocess.check_output(cmd, shell=True).decode()"
        ),
        "output": (
            "Finding 1: eval() on untrusted input (CWE-95)\n"
            "Severity: critical\n"
            "Line: 3\n"
            "Impact: Arbitrary code execution via user-controlled expression\n"
            "Remediation: Use ast.literal_eval() for safe literal evaluation\n"
            "\n"
            "Finding 2: Shell injection via subprocess (CWE-78)\n"
            "Severity: critical\n"
            "Line: 9\n"
            "Impact: OS command injection through user-controlled cmd argument\n"
            "Remediation: Use subprocess.run() with shell=False and a command list"
        ),
    },
]

CODE_REVIEW_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "def process_data(filepath):\n"
            "    data = open(filepath).read()\n"
            "    result = json.loads(data)\n"
            "    for item in result:\n"
            '        item["processed"] = True\n'
            "    return result\n"
            "\n"
            "def risky_operation():\n"
            "    try:\n"
            "        do_something()\n"
            "    except:\n"
            "        pass"
        ),
        "output": (
            "Issue 1: Missing type hints\n"
            "Severity: medium\n"
            "Location: process_data\n"
            "Recommendation: Add type annotations — "
            "def process_data(filepath: str) -> list[dict]:\n"
            "\n"
            "Issue 2: No error handling on file/JSON operations\n"
            "Severity: high\n"
            "Location: process_data, lines 2-3\n"
            "Recommendation: Wrap open() and json.loads() in try/except "
            "for FileNotFoundError, json.JSONDecodeError\n"
            "\n"
            "Issue 3: Bare except clause\n"
            "Severity: high\n"
            "Location: risky_operation, line 11\n"
            "Recommendation: Catch specific exceptions and log before handling\n"
            "\n"
            "Verdict: request_changes"
        ),
    },
]

BUG_PREDICT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "Pattern: dangerous_eval\n"
            "File: src/calc.py\n"
            "Line: 12\n"
            "Match: eval(user_input)\n"
            "Impact: high\n"
            "\n"
            "Pattern: broad_exception\n"
            "File: src/handler.py\n"
            "Line: 45\n"
            "Match: except:\n"
            "Impact: medium"
        ),
        "output": (
            "Recommendation 1: Replace eval() with safe alternative\n"
            "Priority: critical\n"
            "File: src/calc.py:12\n"
            "Risk: Arbitrary code execution — attacker-controlled input "
            "passed directly to eval()\n"
            "Fix: Use ast.literal_eval() or a dedicated expression parser\n"
            "Prevention: Add bandit S307 check to CI pipeline\n"
            "\n"
            "Recommendation 2: Replace bare except with specific handler\n"
            "Priority: medium\n"
            "File: src/handler.py:45\n"
            "Risk: Masks all errors including KeyboardInterrupt and SystemExit\n"
            "Fix: Catch specific exceptions (e.g., ValueError, IOError) "
            "and log with logger.exception()\n"
            "Prevention: Enable ruff BLE001 rule in pre-commit"
        ),
    },
]

RELEASE_PREP_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "Health Score: 72/100\n"
            "Security Issues: 3\n"
            "High Severity: 2\n"
            "Medium Severity: 1\n"
            "Commit Count: 14\n"
            'Blockers: ["2 high-severity security findings unresolved"]\n'
            'Warnings: ["Low test count: 8"]'
        ),
        "output": (
            "Verdict: NO-GO\n"
            "Confidence: high\n"
            "\n"
            "Blockers (must resolve before release):\n"
            "1. 2 high-severity security findings — unresolved vulnerabilities "
            "pose direct risk to production users\n"
            "   Remediation: Run security-audit workflow, fix findings, re-scan\n"
            "\n"
            "Warnings (recommend addressing):\n"
            "1. Low test count (8) — increases regression risk\n"
            "   Remediation: Add tests for critical paths before release\n"
            "\n"
            "Positive signals:\n"
            "- 14 commits with clear changelog\n"
            "- Health score 72/100 (acceptable once blockers resolved)\n"
            "\n"
            "Next steps: Fix 2 security findings, add test coverage, re-run release-prep"
        ),
    },
]

DEPENDENCY_CHECK_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "Total Dependencies: 42\n"
            "Risk Score: 65/100\n"
            "Risk Level: high\n"
            "\n"
            "Vulnerabilities (2):\n"
            "- requests@2.28.0: CVE-2023-32681 (high)\n"
            "- pillow@9.3.0: CVE-2023-44271 (critical)\n"
            "\n"
            "Severity Summary:\n"
            "- Critical: 1\n"
            "- High: 1\n"
            "- Medium: 0"
        ),
        "output": (
            "Remediation 1: Upgrade pillow\n"
            "Severity: critical\n"
            "Package: pillow 9.3.0 -> 10.1.0\n"
            "CVE: CVE-2023-44271 (denial of service via large image)\n"
            "Breaking changes: Removed deprecated Image.ANTIALIAS — "
            "use Image.LANCZOS instead\n"
            "Timeline: Immediate — critical severity\n"
            "\n"
            "Remediation 2: Upgrade requests\n"
            "Severity: high\n"
            "Package: requests 2.28.0 -> 2.31.0\n"
            "CVE: CVE-2023-32681 (unintended credential leak on redirects)\n"
            "Breaking changes: None expected — minor version bump\n"
            "Timeline: Within 1 week — high severity"
        ),
    },
]

REFACTOR_PLAN_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "Total Debt Items: 23\n"
            "Trajectory: increasing\n"
            "Velocity: 3 items/snapshot\n"
            "\n"
            "High Priority Items (3):\n"
            "- src/api/handler.py:45 [TODO] Extract validation logic\n"
            "- src/api/handler.py:120 [FIXME] God function — 250 lines\n"
            "- src/models/user.py:80 [TODO] Split into separate modules\n"
            "\n"
            'Hotspot Files: ["src/api/handler.py", "src/models/user.py"]'
        ),
        "output": (
            "Phase 1: Break up hotspot files (Effort: medium, Impact: high)\n"
            "Target: src/api/handler.py\n"
            "Strategy: Extract the 250-line god function into focused handlers — "
            "ValidationHandler, TransformHandler, PersistenceHandler\n"
            "Milestone: handler.py under 100 lines, each new module under 80\n"
            "\n"
            "Phase 2: Separate model concerns (Effort: medium, Impact: medium)\n"
            "Target: src/models/user.py\n"
            "Strategy: Split into user.py (data model), user_service.py (business "
            "logic), user_validators.py (input validation)\n"
            "Milestone: No file over 120 lines in models/\n"
            "\n"
            "Phase 3: Prevention (Effort: low, Impact: high)\n"
            "Strategy: Add max-function-length lint rule (50 lines), "
            "add max-file-length CI check (200 lines)\n"
            "Milestone: Zero new debt items for 2 consecutive sprints"
        ),
    },
]

PERF_AUDIT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": (
            "def get_users_with_orders():\n"
            '    users = db.query("SELECT * FROM users")\n'
            "    result = []\n"
            "    for user in users:\n"
            "        orders = db.query(\n"
            "            f\"SELECT * FROM orders WHERE user_id = {user['id']}\"\n"
            "        )\n"
            '        user["orders"] = orders\n'
            "        result.append(user)\n"
            "    return result\n"
            "\n"
            "def process_large_file(filepath: str) -> list[str]:\n"
            "    with open(filepath) as f:\n"
            "        lines = f.readlines()\n"
            "    results = []\n"
            "    for line in lines:\n"
            "        results.append(line.strip().upper())\n"
            "    return results"
        ),
        "output": (
            "Hotspot 1: N+1 query pattern\n"
            "Severity: high\n"
            "Location: get_users_with_orders\n"
            "Complexity: O(n) database round-trips where n = number of users\n"
            "Fix: Use a JOIN query — "
            "SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id\n"
            "Expected impact: ~10x speedup for 100+ users\n"
            "\n"
            "Hotspot 2: Unbounded file read into memory\n"
            "Severity: medium\n"
            "Location: process_large_file\n"
            "Complexity: O(n) memory where n = file size\n"
            "Fix: Stream with generator — "
            "yield line.strip().upper() for line in f\n"
            "Expected impact: Constant memory regardless of file size"
        ),
    },
]
