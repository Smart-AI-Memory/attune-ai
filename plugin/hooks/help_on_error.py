"""PostToolUse hook: suggest help when Bash commands fail.

Reads tool result from stdin (JSON with tool_name,
tool_input, tool_result). If the tool is Bash and
the exit code is non-zero, pattern-matches the stderr
against known error signatures and suggests a /learn
topic.

Exits 0 always (informational, never blocks).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import sys

# Map error patterns to help topics.
# Keys are substrings to match in stderr; values are
# topic slugs for /learn.
_ERROR_TOPICS: dict[str, str] = {
    "ModuleNotFoundError": "imports",
    "ImportError": "imports",
    "SyntaxError": "testing",
    "PermissionError": "security-audit",
    "FileNotFoundError": "fix-test",
    "AssertionError": "fix-test",
    "pytest": "smart-test",
    "pre-commit": "code-quality",
    "ruff": "code-quality",
    "black": "code-quality",
    "bandit": "security-audit",
}


def main() -> None:
    """Read PostToolUse payload and suggest help if applicable."""
    try:
        raw = sys.stdin.read(10_000)  # Cap input at 10KB
        if not raw.strip():
            return
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        return

    # Check for non-zero exit code in tool_result
    result = data.get("tool_result", "")
    if isinstance(result, dict):
        stderr = result.get("stderr", "")
    elif isinstance(result, str):
        stderr = result
    else:
        return

    if not stderr:
        return

    # Match against known patterns
    for pattern, topic in _ERROR_TOPICS.items():
        if pattern in stderr:
            print(
                f"attune: see /learn {topic} for help " f"with this error",
                file=sys.stderr,
            )
            return


if __name__ == "__main__":
    main()
