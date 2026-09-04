#!/usr/bin/env python3
"""Read-only Vercel probe: env-var SHAPES and domain ATTACHMENT, never values.

Why this exists (retro 2026-09-04, item 1)
------------------------------------------
Three production faults that day were invisible to every green test and
to ``vercel env ls``: ``ADMIN_SECRET`` had existed EMPTY for 80 days,
``RESEND_API_KEY`` was pasted empty at the CLI prompt, and
``smartaimemory.com`` had been silently ATTACHED to a sibling project.
Each took ten-plus ad-hoc probes. ``vercel domains inspect`` reports
domain OWNERSHIP, not attachment; only the project-domains API tells the
truth. This script answers all three in one call and prints nothing a
transcript could leak: for every env var it prints the name, targets,
value LENGTH, a 3-char prefix, a quoted/whitespace flag, and a 12-hex
digest; for every project it prints attached domains and redirects.

Usage::

    python scripts/vercel_probe.py [--project website] [--env production]
                                   [--expect NAME ...] [--domains]

``--expect`` names variables that MUST be non-empty in the chosen
environment; the exit code is 1 when any is missing or blank, so the
probe can gate a deploy step. ``--domains`` lists domain attachment
for every project in the team.

Credentials: the Vercel CLI's own token
(``~/Library/Application Support/com.vercel.cli/auth.json`` or
``$VERCEL_TOKEN``) and the ``.vercel/project.json`` link of the cwd.
The token is sent in a header and never written anywhere.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.vercel.com"


def _token() -> str:
    tok = os.environ.get("VERCEL_TOKEN")
    if tok:
        return tok
    auth = Path.home() / "Library" / "Application Support" / "com.vercel.cli" / "auth.json"
    if auth.exists():
        return json.loads(auth.read_text()).get("token", "")
    return ""


def _link(cwd: Path) -> tuple[str, str]:
    """Return (orgId, projectId) from the cwd's ``.vercel/project.json``."""
    for d in (cwd, *cwd.parents):
        p = d / ".vercel" / "project.json"
        if p.exists():
            j = json.loads(p.read_text())
            return j.get("orgId", ""), j.get("projectId", "")
    return "", ""


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed https host
        return json.load(r)


def shape(value: str) -> dict:
    """Describe a secret without revealing it."""
    inner = value.strip().strip('"').strip("'")
    return {
        "len": len(inner),
        "prefix": inner[:3] if inner else "",
        "quoted": value[:1] in ('"', "'"),
        "whitespace": value != value.strip(),
        "sha12": hashlib.sha256(inner.encode()).hexdigest()[:12] if inner else "-",
    }


def pull_env(env: str, cwd: Path) -> dict[str, str]:
    """``vercel env pull`` into a fresh 0600 temp file, parse, delete.

    A path that already EXISTS makes the CLI block on an overwrite prompt
    (``mktemp`` creates the file — so this uses a fresh name under a
    private directory and passes ``--yes``).
    """
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / f"vercel-{env}.env"
        subprocess.run(
            ["vercel", "env", "pull", "--yes", "--environment", env, str(target)],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if not target.exists():
            return {}
        out: dict[str, str] = {}
        for line in target.read_text().splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
        return out


#: Vercel env-var types whose values ``vercel env pull`` CAN return. A
#: ``sensitive`` variable (integrations such as Neon set these) pulls back
#: blank by design, and ``VERCEL_*`` system variables are injected at
#: build time and never listed by the API — neither is "empty".
PULLABLE_TYPES = {"encrypted", "plain"}


def env_types(token: str, org: str, project_id: str) -> dict[str, str]:
    """Map variable name -> Vercel type from the project env listing."""
    if not (token and org and project_id):
        return {}
    try:
        envs = _get(f"/v9/projects/{project_id}/env?teamId={org}", token).get("envs", [])
    except (urllib.error.URLError, OSError, ValueError):
        return {}
    return {e.get("key", ""): e.get("type", "") for e in envs}


def env_report(
    env: str, cwd: Path, expect: list[str], types: dict[str, str] | None = None
) -> tuple[list[str], int]:
    """Describe every pulled variable; flag blanks only where a value was possible.

    ``types`` (name -> Vercel type) comes from :func:`env_types`. Without
    it every blank is flagged, which over-reports on projects with
    integration-managed variables.
    """
    values = pull_env(env, cwd)
    types = types or {}
    lines = [f"env [{env}]: {len(values)} variables"]
    rc = 0

    def pullable(name: str) -> bool:
        if not types:
            return True
        return types.get(name, "system") in PULLABLE_TYPES

    for name in sorted(values):
        s = shape(values[name])
        flag = ""
        if s["len"] == 0:
            if not types or pullable(name):
                flag = "  <-- EMPTY"
            elif name in types:
                flag = f"  ({types[name]}: not pullable)"
            else:
                flag = "  (system)"
        elif s["quoted"] or s["whitespace"]:
            flag = "  <-- quoted/whitespace"
        lines.append(
            f"  {name:<36} len={s['len']:<4} prefix={s['prefix']:<4} sha={s['sha12']}{flag}"
        )
    for name in expect:
        if shape(values.get(name, ""))["len"]:
            continue
        if types and not pullable(name) and name in types:
            lines.append(f"  UNVERIFIABLE ({types[name]}): {name}")
            continue
        lines.append(f"  MISSING OR EMPTY: {name}")
        rc = 1
    return lines, rc


def domains_report(token: str, org: str) -> list[str]:
    lines = ["domain attachment (project -> domains):"]
    projects = _get(f"/v9/projects?teamId={org}&limit=100", token).get("projects", [])
    for p in projects:
        doms = _get(f"/v9/projects/{p['id']}/domains?teamId={org}", token).get("domains", [])
        rendered = ", ".join(
            d["name"] + (f"(->{d['redirect']})" if d.get("redirect") else " [primary]")
            for d in doms
        )
        # The API's ``name`` is the display name (it can differ from the
        # CLI slug — attune-ai's "website" project is named after its
        # domain), so the id is printed alongside for unambiguous matching.
        lines.append(f"  {p['name']:<20} ({p['id'][:12]}) {rendered or '-'}")
    return lines


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", default="production")
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--domains", action="store_true")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args(argv[1:])

    cwd = Path(args.cwd).resolve()
    token = _token()
    org, project_id = _link(cwd)
    lines, rc = env_report(args.env, cwd, args.expect, env_types(token, org, project_id))
    print("\n".join(lines))

    if args.domains:
        if not token or not org:
            print("domains: no token or no .vercel/project.json link in cwd", file=sys.stderr)
            return max(rc, 1)
        try:
            print("\n".join(domains_report(token, org)))
        except urllib.error.URLError as exc:
            print(f"domains: API error {exc}", file=sys.stderr)
            return max(rc, 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
