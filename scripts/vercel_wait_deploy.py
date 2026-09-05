#!/usr/bin/env python3
"""Wait for a Vercel production deployment of a given commit — via the API.

Why this exists (retro 2026-09-04, item 9)
------------------------------------------
Every ad-hoc deploy-waiter loop that day parsed ``vercel ls`` / ``vercel
inspect`` text with a regex that silently never matched, so each ran to
its timeout and printed only a final probe — indistinguishable from
"still building". A parser that can fail to match looks exactly like
waiting. This script asks the deployments API for the state field
directly, prints every transition, and exits by outcome:

    0  READY (and, with ``--probe``, the URL answered ``--expect``)
    1  ERROR or CANCELED (build log error lines are printed)
    2  timeout, or no deployment for that commit appeared

Usage::

    python scripts/vercel_wait_deploy.py --commit <sha-prefix>
        [--cwd website] [--timeout 900] [--interval 20]
        [--probe https://smartaimemory.com/api/cron/usage-digest/ --expect 401]

Credentials: the Vercel CLI's stored token (or ``$VERCEL_TOKEN``; expiry
checked, refreshed via ``vercel whoami``) and the ``.vercel/project.json``
link of ``--cwd`` ITSELF — parents are never searched (see
``vercel_common.py``). The token goes in a header only.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from vercel_common import VercelSetupError, resolve

API = "https://api.vercel.com"
TERMINAL_OK = {"READY"}
TERMINAL_BAD = {"ERROR", "CANCELED"}


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed https host
        return json.load(r)


def find_deployment(token: str, org: str, project_id: str, commit: str) -> dict | None:
    """Newest production deployment whose git commit starts with ``commit``."""
    data = _get(
        f"/v6/deployments?projectId={project_id}&teamId={org}&target=production&limit=20",
        token,
    )
    for d in data.get("deployments", []):
        sha = (d.get("meta") or {}).get("githubCommitSha", "")
        if sha.startswith(commit):
            return d
    return None


def http_status(url: str) -> int:
    """GET ``url`` without following redirects; return the status code."""

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # noqa: D401 - protocol
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(url, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def wait(
    token: str,
    org: str,
    project_id: str,
    commit: str,
    timeout: float,
    interval: float,
    sleep=time.sleep,
    clock=time.monotonic,
    out=print,
) -> tuple[int, dict | None]:
    """Poll until the commit's deployment reaches a terminal state.

    Returns ``(exit_code, deployment)``. Every state change is printed
    once, so a hung build shows as a stalled BUILDING line, not silence.
    """
    start = clock()
    last_state = None
    while True:
        dep = find_deployment(token, org, project_id, commit)
        state = (dep or {}).get("readyState") or (dep or {}).get("state") or "NOT-FOUND"
        if state != last_state:
            url = (dep or {}).get("url", "")
            out(
                f"[{int(clock() - start):4d}s] {commit[:9]} -> {state}{'  https://' + url if url else ''}"
            )
            last_state = state
        if state in TERMINAL_OK:
            return 0, dep
        if state in TERMINAL_BAD:
            return 1, dep
        if clock() - start > timeout:
            out(f"timeout after {int(timeout)}s in state {state}")
            return 2, dep
        sleep(interval)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--commit", required=True, help="git SHA or prefix of the merge commit")
    ap.add_argument("--cwd", default=".", help="a directory linked with .vercel/project.json")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--interval", type=float, default=20)
    ap.add_argument("--probe", default=None, help="URL to GET once READY (no redirects followed)")
    ap.add_argument("--expect", type=int, default=None, help="status the probe must return")
    args = ap.parse_args(argv[1:])

    try:
        lk = resolve(Path(args.cwd).resolve())
    except VercelSetupError as exc:
        print(f"vercel_wait_deploy: {exc}", file=sys.stderr)
        return 2
    token, org, project_id = lk.token, lk.org, lk.project_id
    print(f"project [{lk.label}] commit {args.commit}")

    try:
        rc, dep = wait(token, org, project_id, args.commit, args.timeout, args.interval)
    except urllib.error.URLError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 2
    if rc == 1 and dep:
        err = (dep.get("errorMessage") or "").strip()
        if err:
            print(f"build error: {err}")
    if rc != 0 or not args.probe:
        return rc

    code = http_status(args.probe)
    if args.expect is not None and code != args.expect:
        print(f"probe {args.probe} -> {code} (expected {args.expect})")
        return 1
    print(f"probe {args.probe} -> {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
