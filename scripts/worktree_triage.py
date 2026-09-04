#!/usr/bin/env python3
"""Worktree + branch triage: classify, then emit a removal script. Read-only.

Why this exists (retro 2026-09-04, item 2)
------------------------------------------
The 2026-09-04 sweep took attune-ai from 42 worktrees / 239 branches to
15 / 58 with zero content lost, using two scratch scripts. The
classifier that made it safe is the part worth keeping:

* ``git cherry -v origin/main <ref>`` marks single-commit branches
  whose patch is on main with ``-`` — safe.
* A SQUASH-merged multi-commit branch shows every commit as ``+``, so
  cherry alone would hold it forever. The verifier: the whole branch's
  patch-id (``git diff <merge-base> <branch> | git patch-id --stable``)
  equals the PR merge commit's patch-id (``git show <merge-commit>
  --format= | git patch-id --stable``) ⇒ fully merged, regardless of
  commit count. Merge commits come from ``gh pr list --state all``.
* A worktree with uncommitted changes is HELD, never removed, and its
  dirty file NAMES are listed (never contents — filename smell test).
* This session's own worktree and every branch with an OPEN PR are
  excluded by construction.

Nothing here mutates the repository. The ``script`` subcommand writes a
shell script of ``git worktree remove`` / ``git branch -D`` lines for the
chair to read and run — the auto-mode classifier blocks removals run
by an agent even one at a time, and that is the correct boundary.

Usage::

    python scripts/worktree_triage.py worktrees [--repo PATH] [--self PATH]
    python scripts/worktree_triage.py branches  [--repo PATH]
    python scripts/worktree_triage.py script    [--repo PATH] [--self PATH] -o sweep.sh

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE = "origin/main"


# --------------------------------------------------------------------------
# git / gh plumbing (thin, injectable for tests)
# --------------------------------------------------------------------------


def git(repo: Path, *args: str, inp: str | None = None) -> tuple[str, int]:
    r = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, input=inp, timeout=120
    )
    return r.stdout.strip(), r.returncode


def patch_id(diff: str) -> str:
    """Stable patch-id of a diff; ``(empty)`` when there is nothing to hash.

    Two empties must never compare equal by accident — callers treat
    ``(empty)`` as "no evidence", not "identical".
    """
    if not diff.strip():
        return "(empty)"
    out = subprocess.run(
        ["git", "patch-id", "--stable"], capture_output=True, text=True, input=diff, timeout=60
    ).stdout.split()
    return out[0] if out else "(empty)"


def merged_prs(repo: str) -> dict[str, list[tuple[int, str]]]:
    """Map head branch -> [(pr number, merge commit oid)] for MERGED PRs."""
    r = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "merged",
            "--limit",
            "1000",
            "--json",
            "number,headRefName,mergeCommit",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out: dict[str, list[tuple[int, str]]] = {}
    for p in json.loads(r.stdout or "[]"):
        mc = p.get("mergeCommit") or {}
        if mc.get("oid"):
            out.setdefault(p["headRefName"], []).append((p["number"], mc["oid"]))
    return out


def open_pr_branches(repo: str) -> set[str]:
    r = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "200",
            "--json",
            "headRefName",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {p["headRefName"] for p in json.loads(r.stdout or "[]")}


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


@dataclass
class Row:
    path: str
    branch: str
    head: str
    dirty: list[str] = field(default_factory=list)
    ahead: int = 0
    cherry_minus: int = 0
    cherry_plus: int = 0
    squash_pr: int | None = None
    is_self: bool = False
    has_open_pr: bool = False
    exists: bool = True
    verdict: str = ""


def squash_verified(repo: Path, ref: str, prs: list[tuple[int, str]]) -> int | None:
    """Return the PR number whose merge commit's patch-id equals the branch's, else None."""
    mb, rc = git(repo, "merge-base", BASE, ref)
    if rc != 0:
        return None
    branch_pid = patch_id(git(repo, "diff", mb, ref)[0])
    if branch_pid == "(empty)":
        return None
    for num, oid in prs:
        merge_pid = patch_id(git(repo, "show", oid, "--format=")[0])
        if merge_pid != "(empty)" and merge_pid == branch_pid:
            return num
    return None


def classify(row: Row) -> str:
    if row.is_self:
        return "KEEP (this session)"
    if not row.exists:
        return "PRUNE-ENTRY (dir missing)"
    if row.has_open_pr:
        return "KEEP (open PR)"
    if row.dirty:
        return f"HOLD (dirty {len(row.dirty)})"
    if row.ahead == 0:
        return "REMOVE (nothing ahead)"
    if row.cherry_plus == 0:
        return "REMOVE (all patches on main)"
    if row.squash_pr is not None:
        return f"REMOVE (squash-verified #{row.squash_pr})"
    return f"REVIEW (+{row.cherry_plus} unverified)"


def fill(repo: Path, row: Row, merged: dict[str, list[tuple[int, str]]]) -> Row:
    ref = row.head
    ahead, _ = git(repo, "rev-list", "--count", f"{BASE}..{ref}")
    row.ahead = int(ahead or 0)
    ch, _ = git(repo, "cherry", BASE, ref)
    row.cherry_minus = sum(1 for line in ch.splitlines() if line.startswith("-"))
    row.cherry_plus = sum(1 for line in ch.splitlines() if line.startswith("+"))
    if row.cherry_plus and row.branch in merged:
        row.squash_pr = squash_verified(repo, ref, merged[row.branch])
    row.verdict = classify(row)
    return row


def worktree_rows(repo: Path, self_path: Path | None, merged, open_prs) -> list[Row]:
    porcelain, _ = git(repo, "worktree", "list", "--porcelain")
    rows: list[Row] = []
    cur: dict[str, str] = {}
    for line in porcelain.splitlines() + [""]:
        if not line:
            if cur:
                path = Path(cur["worktree"])
                if path.resolve() != repo.resolve():
                    branch = cur.get("branch", "").replace("refs/heads/", "") or "(detached)"
                    row = Row(
                        path=str(path),
                        branch=branch,
                        head=cur.get("HEAD", ""),
                        is_self=(self_path is not None and path.resolve() == self_path.resolve()),
                        has_open_pr=branch in open_prs,
                        exists=path.exists(),
                    )
                    if row.exists:
                        st, _ = git(path, "status", "--porcelain")
                        row.dirty = [line[3:] for line in st.splitlines() if line.strip()]
                        fill(repo, row, merged)
                    else:
                        row.verdict = classify(row)
                    rows.append(row)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v
    return rows


def branch_rows(repo: Path, merged, open_prs) -> list[Row]:
    """Local branches not checked out anywhere, with a gone or absent upstream."""
    checked_out = {r.branch for r in worktree_rows(repo, None, {}, set())}
    fmt = "%(refname:short)|%(upstream:short)|%(upstream:track)"
    out, _ = git(repo, "for-each-ref", f"--format={fmt}", "refs/heads/")
    rows: list[Row] = []
    for line in out.splitlines():
        br, up, track = line.split("|")
        if br == "main" or br in checked_out:
            continue
        if up and track != "[gone]":
            continue  # live upstream: not ours to judge
        head, _ = git(repo, "rev-parse", br)
        row = Row(path="", branch=br, head=head, has_open_pr=br in open_prs)
        fill(repo, row, merged)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def render_table(rows: list[Row]) -> str:
    lines = [
        "| verdict | path/branch | dirty | ahead | cherry | squash PR |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (r.verdict, r.path or r.branch)):
        where = r.path or r.branch
        if r.path:
            where = f"{r.path} [{r.branch}]"
        lines.append(
            f"| {r.verdict} | {where} | {len(r.dirty)} | {r.ahead} | -{r.cherry_minus}/+{r.cherry_plus} | {r.squash_pr or '-'} |"
        )
    return "\n".join(lines)


def render_script(repo: Path, wt_rows: list[Row], br_rows: list[Row]) -> str:
    lines = [
        "#!/bin/zsh",
        "# Generated by scripts/worktree_triage.py — read every line before running.",
        "# Only REMOVE verdicts appear here; HOLD/REVIEW/KEEP rows are deliberately absent.",
        f'R="{repo}"',
        "",
    ]
    freed: list[str] = []
    for r in wt_rows:
        if r.verdict.startswith("REMOVE"):
            lines.append(f'git -C "$R" worktree remove "{r.path}" || echo "FAILED: {r.path}"')
            if r.branch != "(detached)":
                freed.append(r.branch)
    lines += ["", 'git -C "$R" worktree prune', ""]
    for b in freed:
        lines.append(f'git -C "$R" branch -D "{b}" || echo "FAILED: {b}"')
    lines.append("")
    for r in br_rows:
        if r.verdict.startswith("REMOVE"):
            lines.append(f'git -C "$R" branch -D "{r.branch}"  # {r.verdict}')
    lines += [
        "",
        'echo "remaining worktrees:"; git -C "$R" worktree list',
        'echo "remaining local branches: $(git -C "$R" branch --list | wc -l | tr -d \' \')"',
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["worktrees", "branches", "script"])
    ap.add_argument("--repo", default=".")
    ap.add_argument(
        "--self", dest="self_path", default=None, help="this session's worktree (never removed)"
    )
    ap.add_argument("--gh-repo", default="Smart-AI-Memory/attune-ai")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args(argv[1:])

    repo = Path(args.repo).resolve()
    self_path = Path(args.self_path).resolve() if args.self_path else None
    merged = merged_prs(args.gh_repo)
    open_prs = open_pr_branches(args.gh_repo)

    if args.cmd == "worktrees":
        print(render_table(worktree_rows(repo, self_path, merged, open_prs)))
    elif args.cmd == "branches":
        print(render_table(branch_rows(repo, merged, open_prs)))
    else:
        text = render_script(
            repo,
            worktree_rows(repo, self_path, merged, open_prs),
            branch_rows(repo, merged, open_prs),
        )
        if args.out:
            Path(args.out).write_text(text)
            print(f"wrote {args.out}")
        else:
            print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
