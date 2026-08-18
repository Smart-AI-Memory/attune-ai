#!/usr/bin/env python3
"""Project session-start hooks to sibling repos from the canonical source.

session-start-integrity R6 (roundtable ``q-context-mgmt-review-001``,
2026-08-18). The motivating bug: ``spec_orient.py`` lived as hand-synced
copies across sibling repos and had ALREADY diverged (help+author on one
hash, rag on another), while attune-forms and attune-lite had no
session-start hooks at all. Hand-edited twins violate collaboration
principle #3 — one source, projected.

The registry (``scripts/session_hook_fleet.json``) names the canonical
directory (``plugin/hooks/``, D3), the projected file set, and the
sibling repos. This projector:

- ``--check``: report missing/divergent files and missing settings
  entries per sibling; exit 1 on any drift. Siblings whose directory
  does not exist on this machine are skipped (CI-safe).
- ``--write``: copy the file set into each present sibling's
  ``.claude/hooks/`` and idempotently ensure the ``SessionStart``
  settings entry; report everything written.

Usage:
    python scripts/sync_session_hooks.py --check
    python scripts/sync_session_hooks.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "scripts" / "session_hook_fleet.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    """Load and structurally validate the fleet registry."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("canonical_dir", "files", "siblings", "settings_command"):
        if key not in data:
            raise ValueError(f"registry missing required key: {key}")
    if not data["files"] or not data["siblings"]:
        raise ValueError("registry files/siblings must be non-empty")
    return data


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_sibling(entry: str) -> Path:
    """Expand a registry sibling entry to a real directory path.

    Entries are ``~``-anchored; the resolved path must stay under the
    user's home directory (no traversal outside it).
    """
    resolved = Path(entry).expanduser().resolve()
    home = Path.home().resolve()
    if not resolved.is_relative_to(home):
        raise ValueError(f"sibling path escapes home: {entry}")
    return resolved


def _settings_has_entry(settings: dict, command: str) -> bool:
    for group in settings.get("hooks", {}).get("SessionStart", []):
        for hook in group.get("hooks", []):
            if command in hook.get("command", ""):
                return True
    return False


def unpushed_hook_commits(sibling: Path) -> int:
    """Count sibling commits touching the hook surface not on upstream.

    WARN-ONLY signal (session-start-integrity D4, chair 2026-08-18):
    unpushed enforcement lives on one disk — surface it every session
    until pushed, but never fail on this legitimate mid-work state.
    Returns 0 on any git error or missing upstream (degrade silently).
    """
    try:
        result = subprocess.run(  # noqa: S603
            [
                "git",
                "log",
                "@{u}..HEAD",
                "--oneline",
                "--",
                ".claude/hooks",
                ".claude/settings.json",
            ],
            cwd=sibling,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.splitlines() if line.strip()])


def check_sibling(sibling: Path, registry: dict) -> list[str]:
    """Return drift findings for one sibling (empty = in sync)."""
    canonical = REPO_ROOT / registry["canonical_dir"]
    findings: list[str] = []
    hooks_dir = sibling / ".claude" / "hooks"
    for name in registry["files"]:
        src = canonical / name
        dst = hooks_dir / name
        if not dst.is_file():
            findings.append(f"missing {dst.relative_to(sibling)}")
        elif _sha(src) != _sha(dst):
            findings.append(f"divergent {dst.relative_to(sibling)}")
    settings_path = sibling / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = {}
    if not _settings_has_entry(settings, "spec_orient.py"):
        findings.append("missing SessionStart settings entry")
    return findings


def write_sibling(sibling: Path, registry: dict) -> list[str]:
    """Project files + settings entry into one sibling; return actions."""
    canonical = REPO_ROOT / registry["canonical_dir"]
    actions: list[str] = []
    hooks_dir = sibling / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in registry["files"]:
        src = canonical / name
        dst = hooks_dir / name
        if not dst.is_file() or _sha(src) != _sha(dst):
            dst.write_bytes(src.read_bytes())
            actions.append(f"wrote {dst.relative_to(sibling)}")

    settings_path = sibling / ".claude" / "settings.json"
    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            # Cross-review F2 (codex, 2026-08-18): never treat a
            # malformed settings.json as empty — rewriting it would
            # destroy the user's (recoverable) content. Leave it alone.
            actions.append(f"REFUSED settings edit — unreadable settings.json ({exc})")
            return actions
    if not _settings_has_entry(settings, "spec_orient.py"):
        entry = {
            "type": "command",
            "command": registry["settings_command"],
            "timeout": registry.get("settings_timeout", 4000),
        }
        hooks = settings.setdefault("hooks", {})
        hooks.setdefault("SessionStart", []).append({"hooks": [entry]})
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        actions.append("added SessionStart settings entry")
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift")
    mode.add_argument("--write", action="store_true", help="project files")
    args = parser.parse_args(argv)

    registry = load_registry()
    drift = False
    for entry in registry["siblings"]:
        sibling = _resolve_sibling(entry)
        if not sibling.is_dir():
            print(f"[skip] {entry} — not present on this machine")
            continue
        if args.check:
            findings = check_sibling(sibling, registry)
            if findings:
                drift = True
                for finding in findings:
                    print(f"[drift] {entry}: {finding}")
            else:
                print(f"[ok] {entry}")
            unpushed = 0 if entry in registry.get("no_push", []) else unpushed_hook_commits(sibling)
            if unpushed:
                print(
                    f"[warn] {entry}: {unpushed} unpushed hook commit(s)"
                    f" — enforcement lives on one disk until pushed"
                    f" (git -C {sibling} push)"
                )
        else:
            actions = write_sibling(sibling, registry)
            if actions:
                for action in actions:
                    print(f"[write] {entry}: {action}")
            else:
                print(f"[ok] {entry} — already in sync")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
