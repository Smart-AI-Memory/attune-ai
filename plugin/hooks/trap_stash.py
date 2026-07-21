"""PostToolUse trap-stash hook — deterministic failure capture.

Watches Bash tool results for pre-commit rejections and pytest
failures and stashes structured findings through the existing
session-stash pipeline (spec: docs/specs/self-healing-traps/, D1/D2).

Per-session dedupe: each stashed trap's signature is recorded in
``~/.attune/trap_stash/<session>.json``; a red TDD loop re-hitting the
same failure stashes once (R3). ``ATTUNE_TRAP_STASH=0`` disables.
Degrades silently on every failure path — this hook never blocks a
tool call and always exits 0 (R4).

Claude Code Protocol:
    stdin: JSON with tool_name, tool_input, tool_result, session_id
    exit 0 always.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOK_DIR))

from _bootstrap import ensure_utf8_stdio, read_stdin_utf8  # noqa: E402

_MAX_SIGNATURES_PER_SESSION = 200


def _load_processor():
    """Import process_bash_result from the installed package or repo src/."""
    try:
        from attune.telemetry.lessons import process_bash_result

        return process_bash_result
    except ImportError:
        pass

    src = Path.cwd() / "src"
    if (src / "attune" / "__init__.py").is_file():
        sys.path.insert(0, str(src))
        try:
            from attune.telemetry.lessons import process_bash_result

            return process_bash_result
        except ImportError:
            return None
    return None


def _result_text(tool_result: object) -> str:
    if isinstance(tool_result, str):
        return tool_result
    if isinstance(tool_result, dict):
        parts = [str(tool_result.get(k, "")) for k in ("stdout", "stderr", "output")]
        return "\n".join(p for p in parts if p)
    return ""


def _dedupe_file(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", session_id) or "default"
    return Path.home() / ".attune" / "trap_stash" / f"{safe}.json"


def _seen_signatures(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _record_signature(path: Path, seen: list[str], signature: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        seen = (seen + [signature])[-_MAX_SIGNATURES_PER_SESSION:]
        path.write_text(json.dumps(seen), encoding="utf-8")
    except OSError:
        pass  # dedupe is best-effort; worst case is a duplicate stash


def main() -> int:
    """Process one PostToolUse payload; always returns 0."""
    ensure_utf8_stdio()

    if os.environ.get("ATTUNE_TRAP_STASH") == "0":
        return 0

    try:
        payload = json.loads(read_stdin_utf8(500_000))
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    output = _result_text(payload.get("tool_result", ""))
    if not command or not output:
        return 0

    processor = _load_processor()
    if processor is None:
        return 0

    session_id = str(payload.get("session_id", "") or "default")
    dedupe_path = _dedupe_file(session_id)
    seen = _seen_signatures(dedupe_path)

    # Cheap pre-check: extraction is deterministic, so run it via the
    # processor and dedupe on the returned signature.
    try:
        from attune.telemetry.lessons import extract_trap

        event = extract_trap(command, output)
    except Exception:  # noqa: BLE001 — hook must never crash a tool call
        return 0
    if event is None or event.signature in seen:
        return 0

    signature = processor(
        command=command,
        output=output,
        session_id=session_id,
        cwd=os.getcwd(),
    )
    if signature:
        _record_signature(dedupe_path, seen, signature)
        print(f"[trap-stash] captured {event.family} → /recall")
    return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
