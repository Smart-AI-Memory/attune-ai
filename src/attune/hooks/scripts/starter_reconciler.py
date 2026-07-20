#!/usr/bin/env python
"""SessionStart hook: reconcile next_session_starter.md threads vs reality.

The companion to ``starter_prompt_nudge.py``. That hook *surfaces* the
cross-session handoff file; this one *fact-checks* it. A handoff goes
stale on arrival when its headline "do this big thing" item is already
done — e.g. the starter says "merge PR #1118" but #1118 merged hours
ago, or "ship 9.0.0" but 9.0.0 is already on PyPI. Reconciling that by
hand (branch exists? PR merged? version published?) is ~5 minutes of
archaeology every session. This hook turns it into a glance.

It parses the starter's *named threads* — ``#PR`` numbers, branch names,
and ``X.Y.Z`` version strings — and checks each against git / ``gh`` /
PyPI in parallel, then prints a one-block freshness banner:

    [starter-reconcile] ~/.attune/next_session_starter.md
      PRs: #1116 MERGED · #1117 MERGED · #1121 MERGED
      branches: claude/foo GONE
      PyPI attune-ai latest=9.0.0 (starter mentions: 9.0.0, 8.5.0)
      ⚠ main has NEWER merges the starter omits: #1136 #1135 #1134 #1133
        (starter's newest: #1132) — work may have landed since it was written

A MERGED PR / GONE branch / already-published version is the tell that
the headline action is done — read the banner before trusting the lead.
The ``⚠ NEWER merges`` line catches the *other* staleness shape: the
starter is behind reality because PRs landed on ``main`` that it never
names — exactly what a named-thread check can't see (you can't verify a
thread the starter forgot to mention). Newest-PR-on-main > the starter's
highest mentioned PR is the tell.

Bounded for SessionStart: thread counts are capped and all network
checks run concurrently under a hard wall-clock budget; anything that
doesn't finish (or errors) is reported ``unverified`` rather than
blocking. Exit code is always 0 — a reconciler failure must never stop
a session from starting.

Lives under the enforcement framework at
``docs/specs/enforcement-vs-documentation/`` as a soft, informational
surfacing (no exit 2), so it doesn't count against the enforcement cap.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

STARTER_PATH = Path.home() / ".attune" / "next_session_starter.md"

#: Relative location of a per-repo handoff, under the git toplevel.
PROJECT_STARTER_RELPATH = Path(".attune") / "next_session_starter.md"

# --- Bounds (keep SessionStart snappy) -------------------------------
#: Cap how many of each thread we verify, newest-mentioned first.
MAX_PRS = 6
MAX_BRANCHES = 4
#: How many recent ``origin/main`` commits to scan for merged-PR markers.
MAIN_LOG_SCAN = 40
#: Cap how many newer-than-starter merges we list in the banner.
MAX_NEWER_MERGES = 6
#: Per-subprocess timeout for a single git/gh call (seconds).
SUBPROC_TIMEOUT = 4
#: Total wall-clock budget for ALL network checks combined (seconds).
WALL_BUDGET = 8
#: urlopen timeout for the single PyPI lookup (seconds).
HTTP_TIMEOUT = 4

# --- Thread extraction patterns --------------------------------------
#: ``#1121`` PR references (markdown headings always have a space after
#: ``#`` so ``# Heading`` never matches; ``#1121`` does).
PR_RE = re.compile(r"#(\d{1,6})\b")
#: Branch names — restricted to the prefixes this project actually uses
#: for branches, to avoid matching doc paths like ``docs/specs/...``.
BRANCH_RE = re.compile(r"\b(?:release|hotfix|claude|feat|fix)/[A-Za-z0-9._/-]+")
#: ``X.Y.Z`` semantic versions.
VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
#: ``(#NNNN)`` PR markers in squash-merge commit subjects on main, e.g.
#: ``feat(x): thing (#1133)``. The parentheses distinguish a real merge
#: marker from an inline ``#1133`` cross-reference in prose.
MERGE_PR_RE = re.compile(r"\(#(\d{1,6})\)")
#: ``docs/specs/<slug>`` mentions — the starter's work-queue claims.
SPEC_RE = re.compile(r"docs/specs/([a-z0-9][a-z0-9-]+)")
#: Cap spec-status reads (local file reads, but keep the banner short).
MAX_SPECS = 8
#: Status-line pattern — the three conventions recognized by the
#: canonical parser (``attune.ops.specs_data._STATUS_RE``); duplicated
#: here because hooks are standalone-by-design (no attune import).
#: Keep in sync with that module.
STATUS_RE = re.compile(
    r"^\s*\*\*Status(?::\*\*|\*\*:)\s*(.+?)\s*$|^\s*\*\*Status:\s*(.+?)\*\*",
    re.MULTILINE,
)
#: Terminal leading tokens (mirror of the shipped-side of
#: ``attune.ops.spec_lifecycle.STATUS_VOCABULARY``) — a starter that
#: queues work on a spec whose statuses are ALL terminal is repeating
#: the twice-burned 2026-07-20 shipped-and-quiet mistake.
TERMINAL_TOKENS = frozenset({"shipped", "complete", "completed", "done", "superseded"})
SPEC_PHASE_FILES = ("requirements.md", "design.md", "tasks.md", "decisions.md")


def _find_project_starter(start: Path | None = None) -> Path | None:
    """Return ``<git-toplevel>/.attune/next_session_starter.md`` or None.

    Mirrors ``starter_prompt_nudge._find_project_starter`` — walks up
    from ``start`` (default cwd) to the repo root and returns the
    project-local starter if it exists. ``start`` is a parameter so
    tests can pin the search root.
    """
    if start is None:
        start = Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            candidate = parent / PROJECT_STARTER_RELPATH
            return candidate if candidate.is_file() else None
    return None


def _dedupe(items: list[str]) -> list[str]:
    """De-duplicate preserving first-seen order."""
    return list(dict.fromkeys(items))


def extract_threads(text: str) -> tuple[list[int], list[str], list[str]]:
    """Pull (pr_numbers, branches, versions) from starter ``text``.

    PR numbers and branches are capped (``MAX_PRS`` / ``MAX_BRANCHES``)
    so the reconciler's network fan-out stays bounded; versions are not
    capped (no per-version network call — one PyPI lookup serves all).
    """
    prs = [int(n) for n in _dedupe(PR_RE.findall(text))][:MAX_PRS]
    branches = _dedupe(BRANCH_RE.findall(text))[:MAX_BRANCHES]
    versions = _dedupe(VERSION_RE.findall(text))
    return prs, branches, versions


def _package_name(repo_root: Path | None) -> str | None:
    """Best-effort package name from ``pyproject.toml`` (regex, no toml).

    Avoids a ``tomllib`` dependency so the hook runs under the user's
    ``python`` even when that's < 3.11. Returns None if no pyproject /
    no ``name = "..."`` line is found.
    """
    if repo_root is None:
        return None
    pyproject = repo_root / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'(?m)^\s*name\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else None


def _run(cmd: list[str], cwd: Path | None) -> subprocess.CompletedProcess | None:
    """Run ``cmd``, returning the result or None on timeout / OS error."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SUBPROC_TIMEOUT,
            cwd=str(cwd) if cwd else None,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_pr(num: int, cwd: Path | None) -> str:
    """Return a PR's state (``MERGED`` / ``OPEN`` / ``CLOSED``) or ``unverified``."""
    result = _run(["gh", "pr", "view", str(num), "--json", "state", "-q", ".state"], cwd)
    if result is None or result.returncode != 0:
        return "unverified"
    return result.stdout.strip().upper() or "unverified"


def check_branch(name: str, cwd: Path | None) -> str:
    """Return ``exists`` / ``gone`` for a remote branch, or ``unverified``."""
    result = _run(["git", "ls-remote", "--heads", "origin", name], cwd)
    if result is None or result.returncode != 0:
        return "unverified"
    return "exists" if result.stdout.strip() else "gone"


def merged_prs_on_main(cwd: Path | None, limit: int = MAIN_LOG_SCAN) -> list[int]:
    """Return PR numbers squash-merged to ``origin/main``, newest first.

    Parses ``(#NNNN)`` markers from the most recent ``limit``
    ``origin/main`` commit subjects. Pure-git and offline — it reads
    whatever ``origin/main`` the last fetch left, so a stale ref simply
    yields fewer/older numbers (it can never invent a *newer* one, so it
    cannot produce a false staleness warning). Returns ``[]`` on any git
    error — the widening is best-effort and never blocks.
    """
    result = _run(["git", "log", "origin/main", f"-{limit}", "--format=%s"], cwd)
    if result is None or result.returncode != 0:
        return []
    nums: list[int] = []
    for line in result.stdout.splitlines():
        match = MERGE_PR_RE.search(line)
        if match:
            nums.append(int(match.group(1)))
    return nums


def newer_unmentioned(text: str, merged_main_prs: list[int]) -> list[int]:
    """Merged-on-main PRs newer than the starter's highest mentioned PR.

    The named-thread checks can only verify PRs the starter *names*; this
    catches the inverse blind spot — PRs that landed on ``main`` which
    the starter never mentions, the tell that work shipped after it was
    written. ``text`` is the full starter (we read every ``#NNNN``, not
    the capped/extracted subset, so the ceiling is the true frontier).

    Returns the unmentioned numbers above that ceiling, newest first,
    capped at ``MAX_NEWER_MERGES``. Empty when the starter names no PR
    (no frontier to compare) or git yielded nothing.
    """
    mentioned = {int(n) for n in PR_RE.findall(text)}
    if not mentioned or not merged_main_prs:
        return []
    ceiling = max(mentioned)
    newer = {n for n in merged_main_prs if n > ceiling and n not in mentioned}
    return sorted(newer, reverse=True)[:MAX_NEWER_MERGES]


def _spec_leading_token(status: str) -> str:
    """Leading token, mirroring ``spec_lifecycle._normalize``."""
    head = status.strip().lower()
    for sep in (" ", "(", ",", ";", "—", "-"):
        idx = head.find(sep)
        if idx >= 0:
            head = head[:idx]
    return head.strip()


def check_specs(text: str, repo_root: Path | None) -> dict[str, str]:
    """Status summary for each ``docs/specs/<slug>`` the starter mentions.

    Local file reads only (no network). Per slug the value is:
    ``terminal:<token>`` when EVERY parseable status is a terminal
    token; the requirements/first token otherwise; ``no-status`` when
    nothing parses; ``missing`` when the dir doesn't exist. The banner
    warns on ``terminal:`` — a queued item pointing at a closed spec
    is the shipped-and-quiet trap (twice-burned 2026-07-20).
    """
    if repo_root is None:
        return {}
    out: dict[str, str] = {}
    for slug in _dedupe(SPEC_RE.findall(text))[:MAX_SPECS]:
        spec_dir = repo_root / "docs" / "specs" / slug
        if not spec_dir.is_dir():
            out[slug] = "missing"
            continue
        tokens: list[str] = []
        for fname in SPEC_PHASE_FILES:
            try:
                content = (spec_dir / fname).read_text(encoding="utf-8")
            except OSError:
                continue
            match = STATUS_RE.search(content)
            if match:
                value = match.group(1) if match.group(1) is not None else match.group(2)
                tokens.append(_spec_leading_token(value))
        if not tokens:
            out[slug] = "no-status"
        elif all(t in TERMINAL_TOKENS for t in tokens):
            out[slug] = f"terminal:{tokens[0]}"
        else:
            out[slug] = tokens[0]
    return out


def pypi_latest(pkg: str) -> str | None:
    """Return the latest version string for ``pkg`` on PyPI, or None."""
    url = f"https://pypi.org/pypi/{pkg}/json"
    try:
        # noqa: S310 / nosec B310 — hardcoded https PyPI URL, scheme is fixed.
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310  # nosec B310
            data = json.load(resp)
        return data["info"]["version"]
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any PyPI hiccup (offline, 404, parse) is non-fatal
        # — the version line is simply omitted from the banner.
        return None


def reconcile(text: str, pkg: str | None, cwd: Path | None) -> dict:
    """Check every extracted thread concurrently under ``WALL_BUDGET``.

    Returns a dict with ``prs`` / ``branches`` (name → status), the
    ``pypi`` latest version (or None), and the ``versions`` mentioned in
    the starter. Threads whose check doesn't finish within the budget
    are reported ``unverified``.
    """
    prs, branches, versions = extract_threads(text)
    results: dict = {
        "prs": dict.fromkeys(prs, "unverified"),
        "branches": dict.fromkeys(branches, "unverified"),
        "pypi": None,
        "versions": versions,
        "newer_merges": [],
        "pr_ceiling": None,
        # Local file reads — outside the network executor by design.
        "specs": check_specs(text, cwd),
    }
    # Widening: a starter is also stale when newer PRs landed on main that
    # it never names. Only worth a git call if it names *any* PR (else
    # there's no frontier to compare against) — keeps the no-threads path
    # network-free. The ceiling is the true max over ALL mentioned PRs
    # (not the capped extract), matching what newer_unmentioned compares.
    if prs:
        all_mentioned = [int(n) for n in PR_RE.findall(text)]
        results["pr_ceiling"] = max(all_mentioned)
        results["newer_merges"] = newer_unmentioned(text, merged_prs_on_main(cwd))
    if not prs and not branches and not pkg:
        return results

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    futures: dict = {}
    for num in prs:
        futures[executor.submit(check_pr, num, cwd)] = ("pr", num)
    for branch in branches:
        futures[executor.submit(check_branch, branch, cwd)] = ("branch", branch)
    if pkg:
        futures[executor.submit(pypi_latest, pkg)] = ("pypi", None)

    done, _ = concurrent.futures.wait(futures, timeout=WALL_BUDGET)
    for future in done:
        kind, key = futures[future]
        try:
            value = future.result()
        except Exception:  # noqa: BLE001
            # INTENTIONAL: a single check raising must not sink the others.
            continue
        if kind == "pr":
            results["prs"][key] = value
        elif kind == "branch":
            results["branches"][key] = value
        else:  # kind == "pypi" — the only remaining submitted kind
            results["pypi"] = value

    # Don't block the session on stragglers — their subprocesses are
    # already timeout-bounded; abandon any still running.
    executor.shutdown(wait=False, cancel_futures=True)
    return results


def format_banner(results: dict, label: str, path: Path) -> str | None:
    """Render the freshness banner, or None if nothing to report."""
    prs = results["prs"]
    branches = results["branches"]
    pypi = results["pypi"]
    versions = results["versions"]
    newer = results.get("newer_merges") or []
    specs = results.get("specs") or {}
    if not prs and not branches and pypi is None and not newer and not specs:
        return None

    lines = [f"[starter-reconcile:{label}] {path}"]
    if prs:
        joined = " · ".join(f"#{num} {state}" for num, state in prs.items())
        lines.append(f"  PRs: {joined}")
    if branches:
        joined = " · ".join(f"{name} {state}" for name, state in branches.items())
        lines.append(f"  branches: {joined}")
    if newer:
        ceiling = results.get("pr_ceiling")
        listed = " ".join(f"#{n}" for n in newer)
        tail = f" (starter's newest: #{ceiling})" if ceiling is not None else ""
        lines.append(
            f"  ⚠ main has NEWER merges the starter omits: {listed}{tail}"
            " — work may have landed since it was written"
        )
    if specs:
        joined = " · ".join(f"{slug}={status}" for slug, status in specs.items())
        lines.append(f"  specs: {joined}")
        closed = [s2 for s2, st in specs.items() if st.startswith("terminal:")]
        if closed:
            lines.append(
                "  ⚠ starter mentions CLOSED spec(s): "
                + ", ".join(closed)
                + " — cross-read the queue item against the spec's status "
                "line before executing (shipped-and-quiet trap)"
            )
    if pypi is not None:
        suffix = f" (starter mentions: {', '.join(versions)})" if versions else ""
        pkg = results.get("pkg") or ""
        label_pkg = f"PyPI {pkg}".rstrip()
        lines.append(f"  {label_pkg} latest={pypi}{suffix}")
    return "\n".join(lines)


def _reconcile_and_emit(path: Path, label: str, repo_root: Path | None) -> bool:
    """Reconcile a single starter file and print its banner if any.

    Returns True if a banner was printed, False on any no-op.
    """
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    pkg = _package_name(repo_root)
    results = reconcile(text, pkg, repo_root)
    results["pkg"] = pkg or ""
    banner = format_banner(results, label, path)
    if banner is None:
        return False
    print(banner)
    return True


def _repo_root(start: Path | None = None) -> Path | None:
    """Return the git toplevel walking up from ``start`` (default cwd)."""
    if start is None:
        start = Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def main() -> int:
    """Reconcile the project-local then global starter, if present."""
    repo_root = _repo_root()
    project_path = _find_project_starter()
    if project_path is not None:
        _reconcile_and_emit(project_path, "project", repo_root)

    if project_path is None or STARTER_PATH.resolve() != project_path.resolve():
        _reconcile_and_emit(STARTER_PATH, "global", repo_root)
    return 0


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: hook errors must never block session start.
        print(
            f"[starter-reconcile] hook error (continuing): " f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
