"""Shared credential + project-link resolution for the ``vercel_*`` scripts.

Two hazards found 2026-09-05 while dry-running from a git worktree
(``.claude/worktrees/<slug>/``) motivate every rule below:

1. **No parent walk.** ``website/.vercel/project.json`` is gitignored, so a
   fresh worktree has none. The old helpers walked every parent directory
   and landed on the MAIN checkout's ``.vercel/project.json``, which links
   a project that no longer exists on the team. The wrapper then printed
   ``redeploy https://`` (empty URL) with exit 0. Now only
   ``<cwd>/.vercel/project.json`` is honored, the resolved
   ``projectName/projectId`` is returned for every output line, and an
   unlinked cwd raises :class:`VercelSetupError` (exit non-zero).

2. **Token expiry.** ``~/Library/Application Support/com.vercel.cli/auth.json``
   holds an OAuth access token with ``expiresAt`` (seconds) and a
   ``refreshToken``. An expired token turns every API call into a 403
   that the callers used to swallow. Now ``expiresAt`` is checked before
   use; an expired token is refreshed by running ``vercel whoami`` (the
   CLI rewrites the file), and if it is still expired afterwards the
   caller gets a clear error. The token value is never printed.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

AUTH_FILE = Path.home() / "Library" / "Application Support" / "com.vercel.cli" / "auth.json"
#: Treat a token that expires within this many seconds as already expired,
#: so a 900 s redeploy does not start on a token that dies mid-call.
EXPIRY_SKEW_S = 120


class VercelSetupError(RuntimeError):
    """A credential or project-link problem the user must fix; safe to print."""


@dataclass(frozen=True)
class Link:
    """One resolved ``.vercel/project.json`` plus a usable token."""

    token: str
    org: str
    project_id: str
    project_name: str

    @property
    def label(self) -> str:
        """``projectName/projectId`` for output lines — never the token."""
        return f"{self.project_name or '?'}/{self.project_id}"


def _read_auth(path: Path = AUTH_FILE) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _expired(auth: dict, now: float | None = None) -> bool:
    """True when ``auth`` carries an ``expiresAt`` at or before now (+skew).

    ``expiresAt`` is seconds since the epoch in the current CLI; a value
    that looks like milliseconds is normalized. No ``expiresAt`` (an older
    static token) means "not expiring".
    """
    exp = auth.get("expiresAt")
    if not isinstance(exp, (int, float)):
        return False
    if exp > 1e12:  # milliseconds
        exp /= 1000
    return exp <= (time.time() if now is None else now) + EXPIRY_SKEW_S


def refresh_cli_token(timeout: float = 60) -> bool:
    """Ask the Vercel CLI to refresh its stored token; True when it ran.

    ``vercel whoami`` is read-only and rewrites ``auth.json`` with a fresh
    access token when the refresh token is still valid. Its output is
    discarded — nothing from this call is printed.
    """
    try:
        r = subprocess.run(
            ["vercel", "whoami"], capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def token(auth_file: Path = AUTH_FILE) -> str:
    """Return a usable token or raise :class:`VercelSetupError`.

    ``$VERCEL_TOKEN`` wins and is never expiry-checked (it is the user's
    own static token). Otherwise the CLI's stored token is used, refreshed
    once via :func:`refresh_cli_token` when expired.
    """
    env_tok = os.environ.get("VERCEL_TOKEN")
    if env_tok:
        return env_tok
    auth = _read_auth(auth_file)
    if _expired(auth):
        refresh_cli_token()
        auth = _read_auth(auth_file)
        if _expired(auth):
            raise VercelSetupError(
                "Vercel CLI token is expired and could not be refreshed; "
                "run `vercel whoami` (or `vercel login`) and retry"
            )
    tok = auth.get("token", "")
    if not isinstance(tok, str) or not tok:
        raise VercelSetupError(
            f"no Vercel token: set $VERCEL_TOKEN or run `vercel login` (looked in {auth_file})"
        )
    return tok


def link(cwd: Path, project_id: str | None = None) -> tuple[str, str, str]:
    """Return ``(orgId, projectId, projectName)`` from ``cwd/.vercel/project.json`` ONLY.

    Parents are deliberately NOT searched (see module docstring). A
    ``project_id`` override replaces the linked id but keeps the team.
    """
    path = cwd / ".vercel" / "project.json"
    if not path.exists():
        raise VercelSetupError(
            f"{cwd} is not linked (no {path.relative_to(cwd)}); parents are not searched. "
            f"Pass --cwd <linked dir> or run `vercel link --cwd {cwd}`"
        )
    try:
        j = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise VercelSetupError(f"unreadable {path}: {exc}") from exc
    org = str(j.get("orgId") or "")
    pid = str(project_id or j.get("projectId") or "")
    if not (org and pid):
        raise VercelSetupError(f"{path} lacks orgId/projectId")
    name = str(j.get("projectName") or "")
    if project_id and project_id != j.get("projectId"):
        name = ""  # the override is not the linked project; do not mislabel it
    return org, pid, name


def resolve(cwd: Path, project_id: str | None = None) -> Link:
    """Token + link in one call; raises :class:`VercelSetupError` on either."""
    org, pid, name = link(cwd, project_id)
    return Link(token=token(), org=org, project_id=pid, project_name=name)
