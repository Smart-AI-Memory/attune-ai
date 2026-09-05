#!/usr/bin/env python3
"""One Vercel mutation per invocation, through the API, token never printed.

Why this exists (retro 2026-09-04, item 8)
------------------------------------------
The auto-mode classifier blocks bare ``curl``/``vercel`` mutations of
domains and env vars — bundled or one at a time — so a 25-minute domain
outage was fixed by handing the chair curl chains to paste. Allowlisting
``curl`` would be far too broad. This wrapper is the narrow, auditable
entrypoint that CAN be allowlisted: each subcommand performs exactly one
mutation, prints what it will do, supports ``--dry-run``, and reads the
token only into a request header.

Subcommands (one mutation each)::

    env-set NAME (--from-file PATH | --generate) [--env production] [--store PATH]
    env-rm NAME [--env production]
    domain-attach DOMAIN [--redirect TARGET] [--project-id ID]
    domain-detach DOMAIN [--project-id ID]
    domain-redirect DOMAIN (--to TARGET | --clear) [--project-id ID]
    redeploy [--url https://<latest-prod>.vercel.app]

``env-set --generate`` mints ``openssl rand``-equivalent 32 random bytes
(hex) and, with ``--store``, also writes ``NAME=<value>`` to a 0600 file
outside the repo — the generate-once/write-both recipe. Values are never
echoed; the receipt is ``len=`` and ``sha256[:12]``.

Credentials: ``$VERCEL_TOKEN`` or the Vercel CLI's stored token; the
project/team ids come from ``.vercel/project.json`` under ``--cwd``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
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
    for d in (cwd, *cwd.parents):
        p = d / ".vercel" / "project.json"
        if p.exists():
            j = json.loads(p.read_text())
            return j.get("orgId", ""), j.get("projectId", "")
    return "", ""


def _request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed https host
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            err = json.loads(raw)
        except ValueError:
            err = {"error": {"message": raw.decode(errors="replace")[:200]}}
        return {"error": err.get("error", err), "status": e.code}
    return json.loads(raw) if raw else {}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


# --------------------------------------------------------------------------
# operations — each returns (description, method, path, body)
# --------------------------------------------------------------------------


def op_env_set(org: str, pid: str, name: str, value: str, env: str):
    return (
        f"env-set {name} [{env}] len={len(value)} sha={digest(value)}",
        "POST",
        f"/v10/projects/{pid}/env?teamId={org}&upsert=true",
        {"key": name, "value": value, "type": "encrypted", "target": [env]},
    )


def op_env_rm(org: str, pid: str, env_id: str, name: str, env: str):
    return (
        f"env-rm {name} [{env}] id={env_id}",
        "DELETE",
        f"/v9/projects/{pid}/env/{env_id}?teamId={org}",
        None,
    )


def op_domain_attach(org: str, pid: str, domain: str, redirect: str | None):
    body: dict = {"name": domain}
    if redirect:
        body.update({"redirect": redirect, "redirectStatusCode": 308})
    return (
        f"domain-attach {domain} -> project {pid}"
        + (f" (redirect->{redirect})" if redirect else ""),
        "POST",
        f"/v10/projects/{pid}/domains?teamId={org}",
        body,
    )


def op_domain_detach(org: str, pid: str, domain: str):
    return (
        f"domain-detach {domain} from project {pid}",
        "DELETE",
        f"/v9/projects/{pid}/domains/{domain}?teamId={org}",
        None,
    )


def op_domain_redirect(org: str, pid: str, domain: str, target: str | None):
    body = {"redirect": target, "redirectStatusCode": 308} if target else {"redirect": None}
    return (
        f"domain-redirect {domain} -> {target or '(none: primary)'}",
        "PATCH",
        f"/v9/projects/{pid}/domains/{domain}?teamId={org}",
        body,
    )


# --------------------------------------------------------------------------


def find_env_id(token: str, org: str, pid: str, name: str, env: str) -> str | None:
    envs = _request("GET", f"/v9/projects/{pid}/env?teamId={org}", token).get("envs", [])
    for e in envs:
        if e.get("key") == name and env in (e.get("target") or []):
            return e.get("id")
    return None


def store_locally(path: Path, name: str, value: str) -> None:
    """Write ``NAME=value`` to ``path`` with 0600, replacing an existing NAME line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if path.exists():
        lines = [line for line in path.read_text().splitlines() if not line.startswith(name + "=")]
    lines.append(f"{name}={value}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cwd", default=".", help="a directory linked with .vercel/project.json")
    ap.add_argument("--project-id", default=None, help="override the linked projectId")
    ap.add_argument("--dry-run", action="store_true", help="print the call, perform nothing")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("env-set")
    p.add_argument("name")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-file", help="0600 file holding the raw value (first line)")
    g.add_argument("--generate", action="store_true", help="mint 32 random bytes as hex")
    p.add_argument("--env", default="production")
    p.add_argument("--store", help="also write NAME=value to this 0600 file (outside the repo)")

    p = sub.add_parser("env-rm")
    p.add_argument("name")
    p.add_argument("--env", default="production")

    p = sub.add_parser("domain-attach")
    p.add_argument("domain")
    p.add_argument("--redirect", default=None)

    p = sub.add_parser("domain-detach")
    p.add_argument("domain")

    p = sub.add_parser("domain-redirect")
    p.add_argument("domain")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--to")
    g.add_argument("--clear", action="store_true")

    p = sub.add_parser("redeploy")
    p.add_argument(
        "--url", default=None, help="deployment URL; default: newest production deployment"
    )

    args = ap.parse_args(argv[1:])
    cwd = Path(args.cwd).resolve()
    token = _token()
    org, linked_pid = _link(cwd)
    pid = args.project_id or linked_pid
    if not (token and org and pid):
        print("no Vercel token or no .vercel/project.json link in --cwd", file=sys.stderr)
        return 2

    if args.cmd == "redeploy":
        # The CLI's redeploy is the one mutation here; it reuses the source build.
        url = args.url
        if not url:
            deps = _request(
                "GET",
                f"/v6/deployments?projectId={pid}&teamId={org}&target=production&limit=1",
                token,
            )
            url = "https://" + (deps.get("deployments") or [{}])[0].get("url", "")
        print(f"redeploy {url}")
        if args.dry_run:
            return 0
        r = subprocess.run(
            ["vercel", "redeploy", url], cwd=cwd, capture_output=True, text=True, timeout=900
        )
        print((r.stdout + r.stderr).strip()[-400:])
        return 0 if r.returncode == 0 else 1

    if args.cmd == "env-set":
        if args.generate:
            value = secrets.token_hex(32)
        else:
            value = Path(args.from_file).read_text().splitlines()[0].strip()
        if not value:
            print("refusing to set an EMPTY value", file=sys.stderr)
            return 1
        desc, method, path, body = op_env_set(org, pid, args.name, value, args.env)
    elif args.cmd == "env-rm":
        env_id = find_env_id(token, org, pid, args.name, args.env)
        if not env_id:
            print(f"no {args.name} in [{args.env}]", file=sys.stderr)
            return 1
        desc, method, path, body = op_env_rm(org, pid, env_id, args.name, args.env)
    elif args.cmd == "domain-attach":
        desc, method, path, body = op_domain_attach(org, pid, args.domain, args.redirect)
    elif args.cmd == "domain-detach":
        desc, method, path, body = op_domain_detach(org, pid, args.domain)
    else:
        desc, method, path, body = op_domain_redirect(
            org, pid, args.domain, None if args.clear else args.to
        )

    print(f"{'DRY-RUN ' if args.dry_run else ''}{desc}")
    print(f"  {method} {path}")
    if args.dry_run:
        return 0

    result = _request(method, path, token, body)
    if result.get("error"):
        msg = (
            result["error"].get("message") if isinstance(result["error"], dict) else result["error"]
        )
        print(f"  FAILED ({result.get('status')}): {msg}", file=sys.stderr)
        return 1
    print("  ok")
    if args.cmd == "env-set" and args.store:
        store_locally(Path(args.store).expanduser(), args.name, value)
        print(f"  stored {args.name} in {args.store} (0600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
