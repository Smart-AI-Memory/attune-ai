#!/usr/bin/env python3
"""Record a reach snapshot: PyPI downloads + GitHub traffic.

usage-signals R4: the release ritual records a baseline snapshot at
tag time so every release has a before/after pair. Reads public
zero-instrumentation signals only:

- pypistats.org ``/api/packages/<pkg>/recent`` for each attune
  package (mirror-corrected per the Phase 0 finding).
- GitHub repo signals via ``gh api`` (stars; traffic clones/views
  when the token has push access). Degrades gracefully without gh.

Writes ``<out>/<YYYY-MM-DD>.json`` and prints a markdown table.

Rate-limit discipline (Phase 0 lesson): pypistats 429-penalizes
bursts and the penalty outlasts minutes of retrying — this script
spaces requests (default 60s) and ABORTS on the first 429 with a
"wait 15 minutes" message instead of hammering.

Resumable partial progress (reach-snapshot-resilience): each
package is persisted to the day file *as it succeeds* (atomic
temp+rename). On rerun the same day, already-captured packages are
loaded and skipped, so a 429 degrades to "rerun later to finish the
remainder" instead of discarding the packages already fetched. The
GitHub line stays best-effort and is filled in on the run that
completes the set.

Usage:
    python scripts/reach_snapshot.py
    python scripts/reach_snapshot.py --spacing 60 --out docs/specs/usage-signals/snapshots
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PACKAGES = [
    "attune-ai",
    "attune-rag",
    "attune-help",
    "attune-author",
    "attune-verify",
]
REPO = "Smart-AI-Memory/attune-ai"


#: US-4: the manifest names its data source explicitly.
SOURCE = "pypistats.org/api/recent"

#: US-4 attempt budget: one initial attempt plus at most two
#: additional attempts per day, separated by >= 60 minutes.
MAX_ATTEMPTS_PER_DAY = 3
MIN_ATTEMPT_GAP_SECONDS = 60 * 60


class RateLimitedError(RuntimeError):
    """pypistats returned 429 — stop immediately, retrying makes it worse."""


class AttemptBudgetError(RuntimeError):
    """The US-4 per-day attempt budget is exhausted or the gap unmet."""


def build_manifest(
    expected: list[str],
    captured: dict[str, dict[str, int]],
    observed_at: str,
) -> dict[str, object]:
    """The US-4 completeness contract: expected vs captured vs missing.

    A snapshot is complete only when every allowlisted package has a
    valid observation; the status travels with the artifact so an
    incomplete snapshot is unmistakable downstream (dashboard, release
    ritual) rather than silently shaped like a complete one.
    """
    missing = [pkg for pkg in expected if pkg not in captured]
    return {
        "expected": list(expected),
        "captured": [pkg for pkg in expected if pkg in captured],
        "missing": missing,
        "source": SOURCE,
        "observed_at": observed_at,
        "complete": not missing,
    }


def fetch_pypistats_recent(package: str) -> dict[str, int]:
    """Fetch last_day/last_week/last_month for one package.

    Raises RateLimitedError on HTTP 429 (caller must abort, not
    retry — see module docstring).
    """
    url = f"https://pypistats.org/api/packages/{package}/recent"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # US-4: honor server-provided retry guidance when present.
            retry_after = e.headers.get("Retry-After") if e.headers else None
            guidance = (
                f"server says retry after {retry_after}s"
                if retry_after
                else "wait at least 60 minutes (the penalty outlasts short retries)"
            )
            raise RateLimitedError(
                f"pypistats rate-limited on {package}; {guidance}. "
                "Rerun later — already-captured packages are reused, "
                "and at most two additional attempts are budgeted today."
            ) from e
        raise
    data = payload.get("data", {})
    return {
        "last_day": int(data.get("last_day", 0)),
        "last_week": int(data.get("last_week", 0)),
        "last_month": int(data.get("last_month", 0)),
    }


def fetch_github_signals(repo: str = REPO) -> dict[str, object]:
    """Best-effort GitHub signals via gh CLI; {} when unavailable."""
    signals: dict[str, object] = {}
    try:
        out = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}",
                "--jq",
                "{stars: .stargazers_count, forks: .forks_count}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=True,
        )
        signals.update(json.loads(out.stdout))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        logger.warning("GitHub repo signals unavailable: %s", e)
        return signals
    # Traffic endpoints need push access; degrade per-endpoint.
    for key, endpoint, jq in [
        ("clones_14d", f"repos/{repo}/traffic/clones", ".count"),
        ("views_14d", f"repos/{repo}/traffic/views", ".count"),
    ]:
        try:
            out = subprocess.run(
                ["gh", "api", endpoint, "--jq", jq],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=True,
            )
            signals[key] = int(out.stdout.strip())
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            logger.warning("GitHub traffic %s unavailable: %s", key, e)
    return signals


def build_snapshot(
    packages: list[str],
    spacing_seconds: float,
    *,
    seed: dict[str, dict[str, int]] | None = None,
    date: str | None = None,
    fetcher=None,
    sleeper=None,
    persist=None,
) -> dict[str, object]:
    """Fetch package stats with rate-limit spacing, preserving progress.

    fetcher/sleeper default to the module-level functions, resolved
    at CALL time (not def time) so tests can monkeypatch the module
    attributes — a def-time default would bind the original function
    object and silently bypass patches.

    seed pre-loads already-captured packages (from today's day file);
    those are skipped, so a rerun only fetches the remainder. persist,
    if given, is called with the current snapshot after EACH successful
    fetch — so a later 429 (raised by fetcher) leaves the packages
    fetched so far durably written. The GitHub line is fetched once at
    the end (on the run that completes the set); partial writes carry
    an empty github until then.
    """
    fetcher = fetcher or fetch_pypistats_recent
    sleeper = sleeper or time.sleep
    now = datetime.now(timezone.utc)
    date = date or now.strftime("%Y-%m-%d")
    taken_at = now.isoformat()
    pypi: dict[str, dict[str, int]] = dict(seed or {})

    def snapshot(github: dict[str, object]) -> dict[str, object]:
        return {
            "date": date,
            "taken_at": taken_at,
            "pypi_recent": pypi,
            "github": github,
            # US-4: the completeness contract travels with the artifact.
            "manifest": build_manifest(list(packages), pypi, taken_at),
        }

    remaining = [pkg for pkg in packages if pkg not in pypi]
    for i, pkg in enumerate(remaining):
        if i:
            sleeper(spacing_seconds)
        pypi[pkg] = fetcher(pkg)
        if persist is not None:
            persist(snapshot({}))
    return snapshot(fetch_github_signals())


def render_table(snapshot: dict[str, object]) -> str:
    """Markdown table for the snapshot (paste-ready for decisions.md)."""
    lines = [
        f"Reach snapshot — {snapshot['date']}",
        "",
        "| Package | last_day | last_week | last_month |",
        "|---|---|---|---|",
    ]
    pypi = snapshot.get("pypi_recent", {})
    assert isinstance(pypi, dict)
    for pkg, stats in pypi.items():
        lines.append(
            f"| {pkg} | {stats['last_day']} | {stats['last_week']} | {stats['last_month']} |"
        )
    gh = snapshot.get("github") or {}
    assert isinstance(gh, dict)
    if gh:
        parts = ", ".join(f"{k}={v}" for k, v in gh.items())
        lines += ["", f"GitHub: {parts}"]
    return "\n".join(lines) + "\n"


def _load_day(path: Path) -> dict[str, object]:
    """Load today's day file; missing/malformed degrades to empty."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("could not load existing snapshot %s: %s", path, e)
        return {}
    return data if isinstance(data, dict) else {}


def _load_seed(path: Path) -> dict[str, dict[str, int]]:
    """Load already-captured pypi_recent from today's day file, if any.

    Best-effort: a missing or malformed file degrades to an empty seed
    (a fresh full run), never an error.
    """
    pypi = _load_day(path).get("pypi_recent", {})
    if not isinstance(pypi, dict):
        return {}
    return {pkg: stats for pkg, stats in pypi.items() if isinstance(stats, dict)}


def check_attempt_budget(
    attempts: list[dict[str, object]],
    now: datetime,
    *,
    remaining: int,
) -> None:
    """Enforce the US-4 per-day attempt budget BEFORE any request.

    One initial attempt + at most two additional per day, separated by
    at least 60 minutes. Only enforced when packages remain — a rerun
    on an already-complete snapshot costs no pypistats request.

    Raises:
        AttemptBudgetError: budget exhausted or the gap unmet.
    """
    if remaining <= 0 or not attempts:
        return
    if len(attempts) >= MAX_ATTEMPTS_PER_DAY:
        raise AttemptBudgetError(
            f"attempt budget exhausted ({MAX_ATTEMPTS_PER_DAY}/day). Proceed "
            "with the incomplete receipt — do not keep retrying (US-4)."
        )
    last_raw = attempts[-1].get("at")
    try:
        last_at = datetime.fromisoformat(str(last_raw))
    except ValueError:
        return  # malformed ledger entry — do not block on it
    gap = (now - last_at).total_seconds()
    if gap < MIN_ATTEMPT_GAP_SECONDS:
        wait_min = int((MIN_ATTEMPT_GAP_SECONDS - gap) // 60) + 1
        raise AttemptBudgetError(
            f"last attempt was {int(gap // 60)} minutes ago; attempts must be "
            f">= 60 minutes apart — wait ~{wait_min} more minutes (US-4)."
        )


def _atomic_write_json(path: Path, data: dict[str, object]) -> None:
    """Write JSON via temp+rename so a partial file is never observed."""
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/specs/usage-signals/snapshots"),
        help="directory for the dated snapshot JSON",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=60.0,
        help="seconds between pypistats requests (default 60 — do not lower after a 429)",
    )
    parser.add_argument(
        "--packages",
        nargs="*",
        default=PACKAGES,
        help="packages to snapshot",
    )
    parser.add_argument(
        "--verify-before",
        metavar="TAG_DATE",
        help=(
            "verify a complete before-snapshot exists 24-72h before the "
            "planned tag date (ISO date or datetime); exits non-zero with "
            "an unmistakable warning otherwise. Makes no network requests."
        ),
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    if args.verify_before:
        return verify_before(args.out, args.verify_before, list(args.packages))

    args.out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    out_path = args.out / f"{date}.json"
    day = _load_day(out_path)
    seed = _load_seed(out_path)
    attempts = day.get("attempts") if isinstance(day.get("attempts"), list) else []

    remaining = [pkg for pkg in args.packages if pkg not in seed]
    try:
        check_attempt_budget(attempts, now, remaining=len(remaining))
    except AttemptBudgetError as e:
        print(f"error: {e}", file=sys.stderr)
        _warn_if_incomplete(args.packages, seed)
        return 1

    def persist(snapshot: dict[str, object]) -> None:
        snapshot["attempts"] = attempts
        _atomic_write_json(out_path, snapshot)

    outcome = "complete"
    snapshot: dict[str, object] = {}
    try:
        snapshot = build_snapshot(
            args.packages, args.spacing, seed=seed, date=date, persist=persist
        )
    except RateLimitedError as e:
        outcome = "rate-limited"
        print(f"error: {e}", file=sys.stderr)
    except (urllib.error.URLError, OSError) as e:
        outcome = "error"
        print(f"error: network failure: {e}", file=sys.stderr)

    if remaining:  # a pypistats request was actually made — log the attempt
        captured_now = len(args.packages) if outcome == "complete" else len(_load_seed(out_path))
        attempts.append({"at": now.isoformat(), "captured": captured_now, "outcome": outcome})

    if outcome != "complete":
        # ALWAYS persist the day file on failure — even a zero-capture
        # run must durably log its attempt, or the US-4 budget could
        # never engage and retries would be unbounded.
        partial = _load_day(out_path) or {
            "date": date,
            "taken_at": now.isoformat(),
            "pypi_recent": dict(seed),
            "github": {},
            "manifest": build_manifest(list(args.packages), seed, now.isoformat()),
        }
        partial["attempts"] = attempts
        _atomic_write_json(out_path, partial)
        _warn_if_incomplete(args.packages, _load_seed(out_path))
        return 1

    snapshot["attempts"] = attempts
    _atomic_write_json(out_path, snapshot)
    print(render_table(snapshot))
    print(f"wrote {out_path}")
    return 0


#: US-4 pre-tag window: the before snapshot must be captured 24-72
#: hours before the planned tag, persisted before release activity.
BEFORE_WINDOW_MIN_HOURS = 24
BEFORE_WINDOW_MAX_HOURS = 72


def find_before_snapshot(
    out_dir: Path,
    tag_at: datetime,
    expected: list[str],
) -> tuple[Path, dict[str, object]] | None:
    """Return the newest COMPLETE snapshot inside the pre-tag window.

    A qualifying snapshot has a manifest with ``complete: true`` for
    the expected allowlist and an ``observed_at`` between 24 and 72
    hours before ``tag_at``. Returns ``None`` when no day file
    qualifies (missing dir, malformed files, incomplete or
    out-of-window snapshots all degrade to None — the caller renders
    the unmistakable warning, per US-4).
    """
    if not out_dir.is_dir():
        return None
    best: tuple[datetime, Path, dict[str, object]] | None = None
    for path in sorted(out_dir.glob("*.json")):
        day = _load_day(path)
        manifest = day.get("manifest")
        if not isinstance(manifest, dict) or not manifest.get("complete"):
            continue
        if sorted(manifest.get("expected", [])) != sorted(expected):
            continue
        try:
            observed = datetime.fromisoformat(str(manifest.get("observed_at")))
        except ValueError:
            continue
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        age = (tag_at - observed).total_seconds() / 3600
        if BEFORE_WINDOW_MIN_HOURS <= age <= BEFORE_WINDOW_MAX_HOURS:
            if best is None or observed > best[0]:
                best = (observed, path, day)
    return (best[1], best[2]) if best else None


def verify_before(out_dir: Path, tag_raw: str, expected: list[str]) -> int:
    """CLI mode: exit 0 iff a complete before-snapshot is in-window.

    ``tag_raw`` is the planned tag instant — a full ISO datetime, or a
    bare date (interpreted as 00:00 UTC of that day).
    """
    try:
        tag_at = datetime.fromisoformat(tag_raw)
    except ValueError:
        print(f"error: --verify-before got unparseable date {tag_raw!r}", file=sys.stderr)
        return 2
    if tag_at.tzinfo is None:
        tag_at = tag_at.replace(tzinfo=timezone.utc)
    found = find_before_snapshot(out_dir, tag_at, expected)
    if found:
        path, day = found
        manifest = day["manifest"]
        assert isinstance(manifest, dict)
        print(f"before-snapshot OK: {path} (observed_at {manifest['observed_at']}, complete 5/5)")
        return 0
    now = datetime.now(timezone.utc)
    hours_left = (tag_at - now).total_seconds() / 3600
    if hours_left > BEFORE_WINDOW_MIN_HOURS:
        remedy = (
            "the window is still open — run `python scripts/reach_snapshot.py` "
            f"NOW (planned tag is ~{int(hours_left)}h away)"
        )
    else:
        remedy = (
            "the 24h window floor has passed — the release may continue only "
            "with this incomplete-receipt warning attached (US-4); do not "
            "capture a substitute at tag time"
        )
    print(
        "WARNING: NO COMPLETE BEFORE-SNAPSHOT in the 24-72h pre-tag window "
        f"(planned tag {tag_at.isoformat()}). {remedy}.",
        file=sys.stderr,
    )
    return 1


def _warn_if_incomplete(expected: list[str], captured: dict[str, dict[str, int]]) -> None:
    """US-4: an incomplete snapshot must be UNMISTAKABLE, never silent."""
    missing = [pkg for pkg in expected if pkg not in captured]
    if missing:
        print(
            "WARNING: INCOMPLETE SNAPSHOT — missing packages: "
            + ", ".join(missing)
            + f" ({len(captured)}/{len(expected)} captured). A release may "
            "continue only with this incomplete-receipt warning attached.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
