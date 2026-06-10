#!/usr/bin/env python3
"""Probe claude-agent-sdk subprocess-environment semantics.

Phase-0 probe for the sdk-subprocess-isolation spec
(docs/specs/sdk-subprocess-isolation/). Re-run after any
claude-agent-sdk bump; if any check FLIPS, the spec's findings are
stale and the hook gate / adapter isolation need re-validation.

Checks (introspection, no API spend):

1. ``ClaudeAgentOptions`` exposes ``setting_sources`` and ``env``.
2. The subprocess transport stamps ``CLAUDE_CODE_ENTRYPOINT=sdk-py``
   and filters ``CLAUDECODE`` from the inherited env.
3. The ``skills`` trap: setting ``options.skills`` with
   ``setting_sources=None`` forces ``["user", "project"]`` back on.

With ``--live``, additionally verifies the installed ``claude`` CLI
accepts an empty ``--setting-sources=`` value (one ``-p`` call with
``--max-turns 1``; needs auth, costs one tiny turn).

Usage:
    python scripts/probe_sdk_subprocess_env.py [--live]
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import shutil
import subprocess
import sys


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def probe_introspection() -> bool:
    """Run the no-spend introspection checks. Returns True if all pass."""
    import claude_agent_sdk
    from claude_agent_sdk import ClaudeAgentOptions
    from claude_agent_sdk._internal.transport import subprocess_cli

    version = getattr(claude_agent_sdk, "__version__", "?")
    print(f"claude-agent-sdk {version}\n")

    fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
    ok = _check(
        "ClaudeAgentOptions has setting_sources + env",
        {"setting_sources", "env"} <= fields,
        f"fields present: {sorted({'setting_sources', 'env'} & fields)}",
    )

    transport_src = inspect.getsource(subprocess_cli)
    ok &= _check(
        "transport stamps CLAUDE_CODE_ENTRYPOINT",
        '"CLAUDE_CODE_ENTRYPOINT": "sdk-py"' in transport_src,
    )
    ok &= _check(
        "transport filters CLAUDECODE from inherited env",
        'k != "CLAUDECODE"' in transport_src,
    )
    ok &= _check(
        "--setting-sources only emitted when not None",
        "if effective_setting_sources is not None" in transport_src,
    )
    ok &= _check(
        "skills trap present (forces user+project when skills set)",
        'setting_sources = ["user", "project"]' in transport_src,
        "adapter must never set skills without explicit setting_sources",
    )
    return ok


def probe_live() -> bool:
    """Verify the CLI parses an empty --setting-sources= value."""
    cli = shutil.which("claude")
    if cli is None:
        return _check("live: claude CLI on PATH", False)
    try:
        result = subprocess.run(  # noqa: S603
            [cli, "-p", "Reply with exactly: ok", "--setting-sources=", "--max-turns", "1"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            input="",
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _check("live: empty --setting-sources= accepted", False, "timeout")
    detail = (result.stderr or result.stdout or "").strip()[:120]
    return _check(
        "live: empty --setting-sources= accepted",
        result.returncode == 0,
        f"exit={result.returncode} {detail}",
    )


def main() -> int:
    """Run the probe; exit non-zero if any check fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="also run the one-turn CLI flag-parse check (needs auth)",
    )
    args = parser.parse_args()

    ok = probe_introspection()
    if args.live:
        ok &= probe_live()
    print("\nall checks passed" if ok else "\nFAILURES — spec findings are stale")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
