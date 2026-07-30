#!/usr/bin/env python3
"""Generate the standing modules-needing-work report from Codecov.

Mechanizes the 2026-07-30 hand-built report
(``docs/reports/modules-needing-work-2026-07-30.md``) so the backlog
of coverage lanes stays CURRENT instead of drifting stale (issue
#1569's tracked candidates were 16 points out of date when checked).

Data source: Codecov's public API for the repo's main branch —
per-file totals plus ``line_coverage`` pairs (``0``=hit, ``1``=miss,
``2``=partial), which compress to exact missed-line ranges. This
deliberately avoids both the stale local ``.coverage`` trap and a
full worktree suite run (see the 2026-07-30 lessons batch).

Usage::

    python scripts/modules_needing_work.py                  # write report
    python scripts/modules_needing_work.py --briefs 3       # + print top-3
                                                            #   delegation briefs
    python scripts/modules_needing_work.py --briefs-dir DIR # write briefs

The report lands at ``docs/reports/modules-needing-work.md`` (one
canonical file — regenerate and diff, don't accrete dated copies;
the 2026-07-30 dated file stays as the historical first edition).

Delegation briefs are self-contained lane prompts (miss ranges,
constraints, receipts pre-declared) so independent modules can run
as PARALLEL delegated lanes per the feature-lead model: seats
implement advisory, the lead re-runs receipts centrally, the chair
arms the merge.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "Smart-AI-Memory/attune-ai"
DEFAULT_BAR = 85.0
DEFAULT_OUT = Path("docs") / "reports" / "modules-needing-work.md"

_API_TEMPLATE = "https://api.codecov.io/api/v2/github/{owner}/repos/{name}/report/?branch={branch}"

#: Coverage-list prefixes that count as production code for this report.
_PRODUCTION_PREFIXES = ("src/", "attune_redis/")

#: Omit-list globs that are measurement plumbing, not production entries.
_OMIT_META_MARKERS = ("tests", "__pycache__", "site-packages", "_example", "test_")


@dataclass
class ModuleGap:
    """One module measuring below the bar."""

    path: str
    coverage: float
    lines: int
    misses: int
    miss_ranges: str = ""

    @property
    def short_path(self) -> str:
        return self.path.removeprefix("src/attune/")

    @property
    def cluster(self) -> str:
        rel = self.short_path
        return rel.split("/", 1)[0] if "/" in rel else "(top-level)"


@dataclass
class Report:
    """Everything the renderer needs, decoupled from the fetch."""

    total_coverage: float
    total_files: int
    gaps: list[ModuleGap] = field(default_factory=list)
    omit_entries: list[str] = field(default_factory=list)
    generated_at: str = ""


def compress_ranges(lines: list[int]) -> str:
    """Compress sorted line numbers to ``"a-b, c"`` form."""
    out: list[str] = []
    start = end = None
    for line in lines:
        if start is None:
            start = end = line
        elif line == end + 1:
            end = line
        else:
            out.append(f"{start}" if start == end else f"{start}-{end}")
            start = end = line
    if start is not None:
        out.append(f"{start}" if start == end else f"{start}-{end}")
    return ", ".join(out)


def extract_gaps(payload: dict, bar: float = DEFAULT_BAR) -> list[ModuleGap]:
    """Production files below ``bar``, ascending by coverage."""
    gaps: list[ModuleGap] = []
    for entry in payload.get("files", []):
        name = entry.get("name", "")
        totals = entry.get("totals") or {}
        coverage = totals.get("coverage")
        if coverage is None or coverage >= bar:
            continue
        if not name.startswith(_PRODUCTION_PREFIXES):
            continue
        misses = [line for line, status in entry.get("line_coverage", []) if status == 1]
        gaps.append(
            ModuleGap(
                path=name,
                coverage=round(float(coverage), 2),
                lines=int(totals.get("lines", 0)),
                misses=int(totals.get("misses", 0)),
                miss_ranges=compress_ranges(misses),
            )
        )
    gaps.sort(key=lambda g: (g.coverage, -g.lines))
    return gaps


def extract_omit_entries(pyproject_text: str) -> list[str]:
    """Production globs still in ``[tool.coverage.run] omit``."""
    match = re.search(r"^omit = \[(.*?)^\]", pyproject_text, re.DOTALL | re.MULTILINE)
    if match is None:
        return []
    entries: list[str] = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line.startswith('"'):
            continue
        glob = line.split('"')[1]
        if any(marker in glob for marker in _OMIT_META_MARKERS):
            continue
        comment = raw_line.split("#", 1)[1].strip() if "#" in raw_line else ""
        entries.append(f"`{glob}` — {comment}" if comment else f"`{glob}`")
    return entries


def cluster_summary(gaps: list[ModuleGap]) -> list[tuple[str, int, int]]:
    """``(cluster, module_count, total_misses)`` sorted by miss volume."""
    counts: dict[str, tuple[int, int]] = {}
    for gap in gaps:
        n, m = counts.get(gap.cluster, (0, 0))
        counts[gap.cluster] = (n + 1, m + gap.misses)
    return sorted(
        ((name, n, m) for name, (n, m) in counts.items()),
        key=lambda row: -row[2],
    )


def render_report(report: Report, bar: float = DEFAULT_BAR) -> str:
    """The standing markdown report."""
    lines = [
        "# Modules needing work",
        "",
        f"**Generated:** {report.generated_at} by `scripts/modules_needing_work.py` "
        "— regenerate in place, don't hand-edit (the dated 2026-07-30 report is "
        "the historical first edition).",
        "",
        f"**Source:** Codecov main — project total {report.total_coverage:.2f}% "
        f"across {report.total_files} files. Candidate list for coverage lanes "
        "(test-quality program #1569).",
        "",
        f"## Tier 1 — measured below the {bar:.0f}% bar ({len(report.gaps)} modules)",
        "",
    ]
    if report.gaps:
        clusters = cluster_summary(report.gaps)
        lines += [
            "### Clusters by miss volume",
            "",
            "| Cluster | Modules | Missed lines |",
            "|---|---|---|",
        ]
        lines += [f"| `{name}` | {n} | {m} |" for name, n, m in clusters]
        lines += [
            "",
            "### Full list (ascending coverage)",
            "",
            "| Cover | Lines | Miss | Module |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {g.coverage:.2f}% | {g.lines} | {g.misses} | `{g.path}` |" for g in report.gaps
        ]
    else:
        lines.append(f"Nothing below {bar:.0f}% — the floor is the ceiling today.")
    lines += [
        "",
        "## Tier 2 — omitted from measurement (un-omit-audit candidates)",
        "",
        "Production entries still in the `pyproject.toml` omit list. Every stated "
        "reason is a hypothesis until probed — 12 labels have been falsified so far.",
        "",
    ]
    lines += [f"- {entry}" for entry in report.omit_entries] or ["- (none)"]
    lines += [
        "",
        "## How lanes run (parallel delegation)",
        "",
        "Modules with disjoint files are independent lanes. Emit briefs with "
        "`--briefs N` (or `--briefs-dir`) and dispatch them as PARALLEL delegated "
        "lanes: seats implement advisory on fresh branches, the lead re-runs "
        "every receipt centrally before the chair-armed merge. A lane's "
        "self-report is never the receipt.",
        "",
    ]
    return "\n".join(lines)


def render_brief(gap: ModuleGap, repo: str = DEFAULT_REPO) -> str:
    """A self-contained delegation brief for one coverage lane."""
    slug = gap.short_path.replace("/", "-").removesuffix(".py")
    return "\n".join(
        [
            f"# Lane brief: raise `{gap.path}` from {gap.coverage:.1f}% to >=85%",
            "",
            f"Repo: {repo} — branch off origin/main as `codex/coverage-{slug}`.",
            "",
            "## Target",
            "",
            f"- Module: `{gap.path}` ({gap.lines} lines, {gap.misses} missed)",
            f"- Missed line ranges (Codecov main): {gap.miss_ranges or '(fetch fresh)'}",
            "",
            "## Constraints",
            "",
            "- TESTS-ONLY: no production code changes. If the miss regions reveal a",
            "  production bug, STOP and report it — do not fix it in this lane.",
            "- Keyless: no network, no live Redis, no API keys. Mock at module",
            "  seams (`sys.modules` fakes for optional deps).",
            "- Match the conventions of the nearest existing test directory.",
            "",
            "## Receipts (declared now, re-run centrally by the lead)",
            "",
            "- suite: run the module's test directory SERIALLY",
            '  (`PYTEST_ADDOPTS="-p no:xdist -o addopts=" python -m pytest <dir> -q`)',
            "  and return the exact tail.",
            "- metric: re-measure ONLY this module",
            '  (`cd /tmp && PYTHONPATH=<repo>/src PYTEST_ADDOPTS="-p no:xdist -o addopts="',
            "  python -m coverage run --rcfile=/dev/null --source=<dotted.module>",
            "  -m pytest <repo>/tests/... && python -m coverage report --rcfile=/dev/null`).",
            "  NOTE: the /tmp run's pass/fail tail is NOT the suite receipt — a",
            "  cwd-sensitive test may fail there; the repo-root run is the suite tail.",
            "",
            "## Done when",
            "",
            f"- `{gap.path}` measures >=85% from the recipe above.",
            "- The full surrounding test directory passes from the repo root.",
            "- One commit, pushed, PR opened tests-only with both receipts in the body.",
        ]
    )


def fetch_codecov(repo: str = DEFAULT_REPO, branch: str = "main") -> dict:
    """Fetch the Codecov report payload (public API, read-only)."""
    owner, name = repo.split("/", 1)
    url = _API_TEMPLATE.format(owner=owner, name=name, branch=branch)
    with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310 — fixed https host
        return json.load(resp)


def build_report(payload: dict, pyproject_text: str, bar: float = DEFAULT_BAR) -> Report:
    totals = payload.get("totals") or {}
    return Report(
        total_coverage=round(float(totals.get("coverage", 0.0)), 2),
        total_files=int(totals.get("files", 0)),
        gaps=extract_gaps(payload, bar),
        omit_entries=extract_omit_entries(pyproject_text),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _validated_out_path(out: Path) -> Path:
    """Resolve ``out`` and require it inside the repo (path validation)."""
    resolved = (REPO_ROOT / out).resolve() if not out.is_absolute() else out.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"refusing to write outside the repo: {resolved}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--bar", type=float, default=DEFAULT_BAR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--briefs", type=int, default=0, help="Print top-N lane briefs")
    parser.add_argument("--briefs-dir", type=Path, default=None, help="Write briefs here instead")
    args = parser.parse_args(argv)

    payload = fetch_codecov(args.repo, args.branch)
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    report = build_report(payload, pyproject_text, args.bar)

    out_path = _validated_out_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(report, args.bar), encoding="utf-8")
    print(f"wrote {out_path} ({len(report.gaps)} modules below {args.bar:.0f}%)")

    ranked = sorted(report.gaps, key=lambda g: -g.misses)
    if args.briefs_dir is not None:
        briefs_dir = _validated_out_path(args.briefs_dir)
        briefs_dir.mkdir(parents=True, exist_ok=True)
        for gap in ranked[: args.briefs or len(ranked)]:
            slug = gap.short_path.replace("/", "-").removesuffix(".py")
            (briefs_dir / f"{slug}.md").write_text(render_brief(gap, args.repo) + "\n", "utf-8")
        print(f"wrote {min(args.briefs or len(ranked), len(ranked))} briefs to {briefs_dir}")
    elif args.briefs:
        for gap in ranked[: args.briefs]:
            print("\n" + "=" * 72 + "\n" + render_brief(gap, args.repo))
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry
    sys.exit(main())
