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


def env_report(env: str, cwd: Path, expect: list[str]) -> tuple[list[str], int]:
    values = pull_env(env, cwd)
    lines = [f"env [{env}]: {len(values)} variables"]
    rc = 0
    for name in sorted(values):
        s = shape(values[name])
        flag = ""
        if s["len"] == 0:
            flag = "  <-- EMPTY"
        elif s["quoted"] or s["whitespace"]:
            flag = "  <-- quoted/whitespace"
        lines.append(
            f"  {name:<36} len={s['len']:<4} prefix={s['prefix']:<4} sha={s['sha12']}{flag}"
        )
    for name in expect:
        if not shape(values.get(name, ""))["len"]:
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
        lines.append(f"  {p['name']:<20} {rendered or '-'}")
    return lines


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", default="production")
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--domains", action="store_true")
    ap.add_argument("--cwd", default=".")
    args = ap.parse_args(argv[1:])

    cwd = Path(args.cwd).resolve()
    lines, rc = env_report(args.env, cwd, args.expect)
    print("\n".join(lines))

    if args.domains:
        token = _token()
        org, _ = _link(cwd)
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
