#!/usr/bin/env python3
"""Extract the REAL failures from a GitHub Actions run — never regex raw logs.

Retro ruling 2026-09-06 (R4): a loose ``grep -E 'passed|failed'`` over a
job log matches TEST NAMES that contain those words and reports phantom
failures (eight of them, that night). This script anchors on what pytest
actually prints: the final ``=== N failed, M passed ... ===`` summary line
and the ``FAILED``/``ERROR`` result lines, per job.

Usage:
    python scripts/ci_failures.py <run-id> [--repo OWNER/REPO]
    python scripts/ci_failures.py --log job.log        # a saved job log

Output, per job (or for the saved log): the summary line, then one line
per failed/errored test node with its reason. Exit 0 when no job reports
failures, 1 otherwise. Requires ``gh`` for the run-id form.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: GitHub job logs prefix every line with ``<job>\t<step>\t<timestamp> ``.
_PREFIX = re.compile(r"^[^\t]*\t[^\t]*\t\d{4}-\d{2}-\d{2}T[^ ]+ ?")
_SUMMARY = re.compile(r"^=+ .*\b(\d+) (passed|failed|error)s?\b.* in [\d.]+s.*=+$")
_RESULT = re.compile(r"^(FAILED|ERROR) (\S+)(?: - (.*))?$")
_INTERNAL = re.compile(r"^INTERNALERROR> ([A-Za-z]+Error.*)$")


@dataclass
class JobReport:
    name: str
    summary: str = ""
    results: list[tuple[str, str, str]] = field(default_factory=list)  # kind, node, reason
    internal_errors: list[str] = field(default_factory=list)

    @property
    def red(self) -> bool:
        return bool(self.results or self.internal_errors) or " failed" in self.summary


def parse_log(text: str, name: str = "log") -> JobReport:
    """Anchor on pytest's own result and summary lines; ignore everything else."""
    report = JobReport(name)
    seen: set[str] = set()
    for raw in text.splitlines():
        line = _PREFIX.sub("", raw).rstrip()
        if (m := _RESULT.match(line)) and m.group(2) not in seen:
            seen.add(m.group(2))
            report.results.append((m.group(1), m.group(2), (m.group(3) or "").strip()))
        elif _SUMMARY.match(line):
            report.summary = line.strip("= ").strip()
        elif (m := _INTERNAL.match(line)) and m.group(1) not in report.internal_errors:
            report.internal_errors.append(m.group(1))
    return report


def _gh(args: list[str]) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def run_reports(run_id: str, repo: str | None) -> list[JobReport]:
    """One report per job of the run, fetched through ``gh``."""
    repo_args = ["-R", repo] if repo else []
    jobs = json.loads(_gh(["run", "view", run_id, *repo_args, "--json", "jobs"]))["jobs"]
    reports = []
    for job in jobs:
        if job.get("conclusion") not in {"failure", "cancelled", "timed_out"}:
            continue
        endpoint = f"repos/{repo}/actions/jobs/{job['databaseId']}/logs" if repo else None
        if endpoint is None:
            endpoint = f"{job['url'].split('github.com/')[-1]}/logs".replace(
                "actions/runs", "repos"
            )
        try:
            text = _gh(["api", endpoint])
        except subprocess.CalledProcessError as exc:  # a log can expire or be pending
            reports.append(
                JobReport(job["name"], summary=f"(log unavailable: {exc.stderr.strip()[:80]})")
            )
            continue
        reports.append(parse_log(text, job["name"]))
    return reports


def render(reports: list[JobReport]) -> str:
    lines = []
    for r in reports:
        lines.append(f"## {r.name}")
        lines.append(f"summary: {r.summary or '(no pytest summary line)'}")
        for err in r.internal_errors:
            lines.append(f"INTERNALERROR {err}")
        for kind, node, reason in r.results:
            lines.append(f"{kind} {node}" + (f" - {reason}" if reason else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_id", nargs="?", help="GitHub Actions run id")
    parser.add_argument("--repo", help="OWNER/REPO (defaults to the current repository)")
    parser.add_argument("--log", type=Path, help="parse a saved job log instead of a run")
    args = parser.parse_args(argv)
    if args.log:
        reports = [parse_log(args.log.read_text(encoding="utf-8", errors="replace"), args.log.name)]
    elif args.run_id:
        reports = run_reports(args.run_id, args.repo)
    else:
        parser.error("give a run id or --log")
    sys.stdout.write(render(reports))
    return 1 if any(r.red for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
