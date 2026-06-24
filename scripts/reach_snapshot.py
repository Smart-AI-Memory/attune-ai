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


class RateLimitedError(RuntimeError):
    """pypistats returned 429 — stop immediately, retrying makes it worse."""


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
            raise RateLimitedError(
                f"pypistats rate-limited on {package}. Wait 15 minutes, "
                "then rerun with --spacing 60 (the penalty outlasts "
                "short retries)."
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


def _load_seed(path: Path) -> dict[str, dict[str, int]]:
    """Load already-captured pypi_recent from today's day file, if any.

    Best-effort: a missing or malformed file degrades to an empty seed
    (a fresh full run), never an error.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("could not load existing snapshot %s: %s", path, e)
        return {}
    pypi = data.get("pypi_recent", {})
    if not isinstance(pypi, dict):
        return {}
    return {pkg: stats for pkg, stats in pypi.items() if isinstance(stats, dict)}


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
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    args.out.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = args.out / f"{date}.json"
    seed = _load_seed(out_path)

    def persist(snapshot: dict[str, object]) -> None:
        _atomic_write_json(out_path, snapshot)

    try:
        snapshot = build_snapshot(
            args.packages, args.spacing, seed=seed, date=date, persist=persist
        )
    except RateLimitedError as e:
        captured = len(_load_seed(out_path))
        total = len(args.packages)
        print(f"error: {e}", file=sys.stderr)
        print(
            f"captured {captured}/{total} today; rerun after the cooldown " "to finish the rest.",
            file=sys.stderr,
        )
        return 1
    except (urllib.error.URLError, OSError) as e:
        print(f"error: network failure: {e}", file=sys.stderr)
        return 1

    _atomic_write_json(out_path, snapshot)
    print(render_table(snapshot))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
