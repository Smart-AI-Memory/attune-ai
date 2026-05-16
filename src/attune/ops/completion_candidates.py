"""Detector for spec completion candidates.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T2 in tasks).

Scans configured spec roots for `approved` specs whose work appears
to have shipped, surfacing them as one-click confirmation candidates
on the Specs page. The detector ONLY proposes — it never writes the
status field. The user confirms or dismisses via the dashboard.

A spec is a candidate when **all five** of the following hold:

1. Status (from any phase file, preference order
   decisions → tasks → design → requirements) is ``approved``.
2. ``last_modified`` (newest `.md` mtime in spec dir) is ≥ 24h ago.
3. If ``tasks.md`` exists, every checklist row is checked
   (``- [x]`` or table row marked ``**done**`` / ``**complete**``)
   and at least one such row is present. Missing tasks.md →
   passes with a "decisions-only spec" note. Empty tasks.md → fails.
4. All PR refs from ``decisions.md`` + ``tasks.md`` are merged on
   the host repo. (Discursive files like ``_sequencing.md`` are
   excluded per Q5 — they reference PRs for context more often
   than for closure.)
5. No open issues on the host repo reference the spec slug.

Failed checks suppress the candidate entirely — the user never
sees "almost complete" rows. Zero false positives, accept many
false negatives.

Ordering is "cheapest local check first": status → edit-age →
tasks-parse → PRs → issues. ~80% of specs short-circuit before
any network call fires.

The detector caches results for 5 minutes in-memory, keyed by the
spec-roots tuple. Test fixtures inject ``now`` to bypass the
cache between cases.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attune.ops import dismiss_store
from attune.ops.config import Config
from attune.ops.routes.specs import (
    SpecPhase,
    SpecRecord,
    _list_specs_in_root,
    _resolved_roots,
)

logger = logging.getLogger(__name__)

# Cache TTL in seconds. Phase 2 / Q2: page-load cadence with 5-min cache.
CACHE_TTL_SECONDS = 300

# Cap concurrent gh API calls for PR-merge checks. Higher would burn
# rate limit on noisy specs; 4 is plenty for ~5-PR specs.
GH_PR_CHECK_CONCURRENCY = 4

# Truncate the PR-list in evidence after this many entries.
PR_EVIDENCE_TRUNCATE = 5

# Edit-age floor: specs touched in the last 24h are likely still active.
MIN_EDIT_AGE_HOURS = 24

# Files we extract PR refs from. Discursive files excluded per Q5.
_PR_REF_FILES: tuple[str, ...] = ("decisions.md", "tasks.md")

# Status preference order for "what is this spec's status?"
_STATUS_PREFERENCE: tuple[str, ...] = (
    "decisions",
    "tasks",
    "design",
    "requirements",
)

# PR ref patterns: `#123` or `PR 123`. Numeric-bounded so we don't
# match e.g. issue numbers in arbitrary contexts unrelated to PRs.
_PR_REF_RE = re.compile(r"(?:\bPR\s+|#)(\d+)\b", re.IGNORECASE)

# Tasks.md patterns.
_TASK_OPEN_RE = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
_TASK_CHECKED_RE = re.compile(r"^[ \t]*- \[[xX]\]", re.MULTILINE)
_TABLE_DONE_RE = re.compile(r"\*\*(?:done|complete)\*\*", re.IGNORECASE)

# Three accepted git remote URL shapes per Phase 2 / Q1.
_GIT_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^git@github\.com:([^/\s]+/[^/\s]+?)(?:\.git)?$"),
    re.compile(r"^https?://github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?/?$"),
)


@dataclass(frozen=True)
class Candidate:
    """One completion-candidate spec returned by the detector."""

    slug: str
    path: str  # absolute path of the spec directory
    current_status: str  # always "approved" in V1
    evidence: list[str]
    snapshot_hash: str


@dataclass
class _CacheEntry:
    """Module-level cache entry for ``detect_candidates``."""

    timestamp: float
    candidates: list[Candidate]


# Module-level cache. Keyed by sorted-roots tuple. Tests call
# ``clear_cache()`` between cases.
_cache: dict[tuple[str, ...], _CacheEntry] = {}

# Per-process memo for host-repo resolution. Remotes don't change
# inside a single dashboard session.
_repo_cache: dict[str, str | None] = {}


def clear_cache() -> None:
    """Reset the in-memory caches. Test helper."""
    _cache.clear()
    _repo_cache.clear()


def detect_candidates(
    config: Config,
    *,
    now: float | None = None,
) -> list[Candidate]:
    """Return all completion candidates across the configured spec roots.

    ``now`` is a test injection point for cache TTL behavior; production
    callers leave it ``None`` so we use ``time.time()``.

    Cache hit path: returns the cached list when ``now - timestamp <
    CACHE_TTL_SECONDS``. Cache miss recomputes from scratch.

    Even when the feature is enabled, an empty result is normal —
    surface "Ready to close?" only when ≥1 candidate is returned.
    """
    if now is None:
        now = time.time()

    roots = _resolved_roots(config)
    cache_key = tuple(sorted(str(r) for r in roots))

    cached = _cache.get(cache_key)
    if cached is not None and now - cached.timestamp < CACHE_TTL_SECONDS:
        return cached.candidates

    candidates = _detect_uncached(roots, config)
    _cache[cache_key] = _CacheEntry(timestamp=now, candidates=candidates)
    return candidates


def _detect_uncached(roots: list[Path], config: Config) -> list[Candidate]:
    """The actual detection pass, sans cache."""
    dismissed = dismiss_store.load(config)
    candidates: list[Candidate] = []

    for root in roots:
        repo = _resolve_host_repo(root)
        for spec in _list_specs_in_root(root):
            candidate = _evaluate_spec(spec, repo, dismissed, config)
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _evaluate_spec(
    spec: SpecRecord,
    repo: str | None,
    dismissed: dict[str, dismiss_store.DismissEntry],
    config: Config,
) -> Candidate | None:
    """Run all five checks against one spec; return Candidate or None.

    Short-circuits on the first failed check. Order:
    status → edit-age → tasks → PRs → issues → dismiss.
    """
    # 1. Status check (cheapest — already parsed in spec.phases).
    if not _check_status_is_approved(spec):
        return None

    # 2. Edit-age check (cheapest among remaining — one ISO parse).
    ok_edit, edit_ev = _check_last_edit_age(spec)
    if not ok_edit:
        return None

    # 3. Tasks check (one file read).
    spec_path = Path(spec.path)
    ok_tasks, tasks_ev = _check_tasks_all_done(spec_path)
    if not ok_tasks:
        return None

    # 4. PR check (network — gated on having PR refs).
    pr_numbers = _extract_pr_refs(spec_path)
    if repo is None and pr_numbers:
        # Can't verify PRs without a host repo. Conservative: reject.
        return None

    prs_ev: str | None = None
    iss_ev: str | None = None
    if repo is not None:
        ok_prs, prs_ev = _check_referenced_prs_merged(pr_numbers, repo)
        if not ok_prs:
            return None
        # 5. Issue check.
        ok_iss, iss_ev = _check_no_open_issues(spec.slug, repo)
        if not ok_iss:
            return None

    # All checks passed. Compute snapshot hash and apply dismiss filter.
    snap = _snapshot_hash(spec_path, pr_numbers, spec.last_modified)
    if spec.slug in dismissed and dismiss_store.is_active(spec.slug, snap, config):
        return None

    return Candidate(
        slug=spec.slug,
        path=spec.path,
        current_status="approved",
        evidence=[e for e in (tasks_ev, prs_ev, iss_ev, edit_ev) if e],
        snapshot_hash=snap,
    )


# ---------------------------------------------------------------------------
# Signal checks
# ---------------------------------------------------------------------------


def _check_status_is_approved(spec: SpecRecord) -> bool:
    """True iff the spec's status (in preference order) is 'approved'."""
    status = _preferred_status(spec)
    return status == "approved"


def _preferred_status(spec: SpecRecord) -> str | None:
    """First non-None status across the phase preference order."""
    phases_by_name: dict[str, SpecPhase] = {p.name: p for p in spec.phases}
    for name in _STATUS_PREFERENCE:
        phase = phases_by_name.get(name)
        if phase is not None and phase.status is not None:
            return phase.status.lower().strip()
    return None


def _check_last_edit_age(
    spec: SpecRecord, *, now: datetime | None = None
) -> tuple[bool, str | None]:
    """True iff the newest .md edit is ≥ MIN_EDIT_AGE_HOURS ago.

    Returns ``(False, None)`` when last_modified is missing or
    unparseable — defensive against the existing
    ``_newest_md_mtime`` returning None on OSError.
    """
    if spec.last_modified is None:
        return False, None
    try:
        last = datetime.fromisoformat(spec.last_modified)
    except ValueError:
        return False, None
    if last.tzinfo is None:
        # Tz-naive timestamps can't be safely compared with tz-aware now.
        return False, None
    if now is None:
        now = datetime.now(timezone.utc)
    age = now - last
    if age.total_seconds() < MIN_EDIT_AGE_HOURS * 3600:
        return False, None
    days = max(1, int(age.total_seconds() / 86400))
    return True, f"✓ last edit {days} day{'s' if days != 1 else ''} ago"


def _check_tasks_all_done(spec_dir: Path) -> tuple[bool, str | None]:
    """True iff tasks.md is absent OR all task rows are checked.

    - Missing tasks.md → pass with "no tasks.md" evidence.
    - Empty (zero checked rows AND zero unchecked rows AND zero
      table-done markers) → fail (skeleton file).
    - Any ``- [ ]`` row → fail.
    - All ``- [x]`` or ``**done**`` / ``**complete**`` markers,
      at least one such row → pass with "✓ N task rows complete".
    """
    tasks_path = spec_dir / "tasks.md"
    if not tasks_path.is_file():
        return True, "✓ no tasks.md (decisions-only spec)"
    try:
        text = tasks_path.read_text(encoding="utf-8")
    except OSError:
        return False, None

    if _TASK_OPEN_RE.search(text):
        return False, None

    n_checked = len(_TASK_CHECKED_RE.findall(text))
    n_table_done = len(_TABLE_DONE_RE.findall(text))
    total_done = n_checked + n_table_done

    if total_done == 0:
        return False, None
    return True, f"✓ {total_done} task row{'s' if total_done != 1 else ''} complete"


def _extract_pr_refs(spec_dir: Path) -> list[int]:
    """Extract PR numbers from decisions.md + tasks.md only.

    Per Q5: discursive files (_sequencing.md, audit notes) reference
    PRs for context more often than for closure. Returns a sorted,
    deduplicated list.
    """
    found: set[int] = set()
    for filename in _PR_REF_FILES:
        path = spec_dir / filename
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _PR_REF_RE.finditer(text):
            try:
                found.add(int(match.group(1)))
            except ValueError:
                continue
    return sorted(found)


def _check_referenced_prs_merged(pr_numbers: list[int], repo: str) -> tuple[bool, str | None]:
    """True iff every PR in ``pr_numbers`` is closed AND merged."""
    if not pr_numbers:
        return True, None
    merged_numbers: list[int] = []
    with ThreadPoolExecutor(max_workers=min(GH_PR_CHECK_CONCURRENCY, len(pr_numbers))) as pool:
        results = list(pool.map(lambda n: (n, _run_gh_pr_view(repo, n)), pr_numbers))
    for pr_number, payload in results:
        if payload is None:
            return False, None
        state = payload.get("state")
        merged_at = payload.get("merged_at")
        if state != "closed" or not merged_at:
            return False, None
        merged_numbers.append(pr_number)
    return True, _format_pr_evidence(sorted(merged_numbers))


def _format_pr_evidence(numbers: list[int]) -> str:
    """Render the merged-PRs evidence string, truncated to N entries."""
    if not numbers:
        return "✓ no PR refs to verify"
    head = numbers[:PR_EVIDENCE_TRUNCATE]
    listed = ", ".join(f"#{n}" for n in head)
    extra = len(numbers) - len(head)
    if extra > 0:
        listed += f", …+{extra} more"
    return f"✓ PRs merged: {listed}"


def _check_no_open_issues(slug: str, repo: str) -> tuple[bool, str | None]:
    """True iff no open issues on ``repo`` reference ``slug``."""
    payload = _run_gh_issue_search(slug, repo)
    if payload is None:
        return False, None
    if len(payload) > 0:
        return False, None
    return True, "✓ no open issues reference this spec"


# ---------------------------------------------------------------------------
# Host-repo discovery (Q1)
# ---------------------------------------------------------------------------


def _resolve_host_repo(root: Path) -> str | None:
    """Resolve the GitHub "owner/name" for the repo containing ``root``.

    Returns ``None`` when the directory is not a git repo, has no
    origin remote, or the remote URL doesn't match a recognized
    GitHub shape (per Q1: three URL patterns supported). Memoized
    per-root for the process lifetime.
    """
    key = str(root)
    if key in _repo_cache:
        return _repo_cache[key]
    url = _run_git_remote_origin(root.parent if root.is_dir() else root)
    if not url:
        _repo_cache[key] = None
        return None
    for pattern in _GIT_URL_PATTERNS:
        match = pattern.match(url)
        if match:
            owner_name = match.group(1)
            _repo_cache[key] = owner_name
            return owner_name
    _repo_cache[key] = None
    return None


# ---------------------------------------------------------------------------
# Snapshot hash
# ---------------------------------------------------------------------------


def _snapshot_hash(spec_dir: Path, pr_numbers: list[int], last_modified: str | None) -> str:
    """SHA-256 of (sorted PR numbers, tasks.md mtime, last_modified).

    DELIBERATELY excludes PR merge state. When a PR transitions
    open→merged after dismissal, the snapshot inputs haven't
    changed but the PR check sees new state — ``is_active``
    condition 2 fails, candidate re-surfaces. Correct by design.
    """
    tasks_mtime: float | None = None
    tasks_path = spec_dir / "tasks.md"
    if tasks_path.is_file():
        try:
            tasks_mtime = tasks_path.stat().st_mtime
        except OSError:
            tasks_mtime = None
    payload = json.dumps(
        {
            "prs": sorted(pr_numbers),
            "tasks_mtime": tasks_mtime,
            "last_modified": last_modified,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Subprocess wrappers — easy mock targets for tests
# ---------------------------------------------------------------------------


def _run_git_remote_origin(cwd: Path) -> str | None:
    """Return the origin remote URL for ``cwd``, or None on failure."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("git remote get-url failed for %s: %s", cwd, exc)
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _run_gh_pr_view(repo: str, pr_number: int) -> dict[str, Any] | None:
    """Return the PR JSON for ``repo``/``pr_number`` or None on failure."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("gh pr view failed for %s#%d: %s", repo, pr_number, exc)
        return None
    if result.returncode != 0:
        return None
    try:
        decoded = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def _run_gh_issue_search(slug: str, repo: str) -> list[dict[str, Any]] | None:
    """Return open issues on ``repo`` whose text contains ``slug``.

    Empty list = no matches. ``None`` = the gh call failed.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "search",
                "issues",
                slug,
                "--repo",
                repo,
                "--state",
                "open",
                "--json",
                "number,title",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("gh issue search failed for %s in %s: %s", slug, repo, exc)
        return None
    if result.returncode != 0:
        return None
    try:
        decoded = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, list):
        return None
    return decoded
