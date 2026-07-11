#!/usr/bin/env python
"""Spec status audit — flag specs whose deliverables shipped but status didn't.

On-demand / CI companion to the always-on ``spec_orient`` SessionStart
hint. Discovers every spec (including terminal ones), classifies each
against its declared ``## Deliverables`` block, and prints a matrix:

    Spec | Layer | Status | Staleness | Unresolved

D-7 — **warn by default, gate opt-in.** Exits ``0`` even when stale
specs exist; ``--strict`` exits ``1`` on any ``suspected-stale`` (or,
with ``--pr-links``, any ``drifted``) so a repo can wire a hard CI
gate. Crash-proof: any unexpected error prints what we have and still
exits ``0`` (warn-by-default never hard-fails).

spec-status-integrity additions (workspace design §2):

- ``--pr-links`` — the PRIMARY drift signal. For each in-flight spec,
  extract PR citations from its phase files and resolve them via
  ``gh`` (merged PRs only; bounded + cached per run). ≥1 merged
  implementing PR + in-flight status ⇒ **drifted**. Results are
  written to ``<root>/.attune/spec-drift.json`` for the offline
  ``spec_orient`` annotation.
- ``--offline`` — skip all ``gh`` calls (the deliverable-existence
  signal still runs). A missing/failing ``gh`` degrades the same way —
  the audit never blocks on network state.
- ``--json`` — machine-readable output for the weekly CI's
  tracking-issue upsert.

Run via ``make spec-audit`` or ``python plugin/hooks/spec_audit.py``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

# Force utf-8 on stdout/stderr — the table uses ⚠ and an em-dash rule
# that Windows cp1252 can't encode (matches spec_orient.py).
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Hooks are invoked as standalone scripts; ensure sibling helpers resolve.
_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _state import (  # noqa: E402 — sys.path bootstrap above
    PrRef,
    _is_in_flight,
    _resolve_entry,
    discover_specs,
    extract_pr_refs,
    workspace_roots,
)

# Display order — drifted (merged-PR evidence) outranks even
# suspected-stale; ``ok`` sinks last.
_STALENESS_ORDER = {
    "drifted": 0,
    "suspected-stale": 1,
    "partial": 2,
    "unknown": 3,
    "docs-only": 4,
    "opted-out": 5,
    "ok": 6,
}
# Only the actionable verdicts get a glyph; the rest render verbatim.
_STALENESS_LABEL = {"suspected-stale": "⚠ suspected-stale", "drifted": "⚠ drifted"}

_HEADERS = ("Spec", "Layer", "Status", "Staleness", "Unresolved")

# ── PR-link resolution (workspace design §2) ──────────────────

# Bound gh calls per run — same discipline as session_recall.py's
# _MAX_PR_CHECKS, sized for an audit sweep rather than a session start.
_MAX_GH_CALLS = 30
_GH_TIMEOUT_SECONDS = 6.0
# All three phase files are scanned for citations, not just the
# highest-priority one — a requirements.md often carries the approval
# trail ("shipped in #N") even when tasks.md exists.
_PHASE_FILENAMES = ("tasks.md", "design.md", "requirements.md")


def _run_gh(args: list[str], cwd: Path | None) -> subprocess.CompletedProcess[str] | None:
    """Invoke ``gh`` — the subprocess boundary tests patch.

    Returns ``None`` when the binary is missing or the call times out;
    callers treat that as "unknown", never as evidence.
    """
    try:
        return subprocess.run(  # noqa: S603, S607 — fixed argv, no shell
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GH_TIMEOUT_SECONDS,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError:
        raise
    except (OSError, subprocess.TimeoutExpired):
        return None


class _PrResolver:
    """Resolves PR refs to merged/not-merged via ``gh``, bounded + cached.

    - Results are cached per ``(repo-or-layer, number)`` for the run, so
      a PR cited from three phase files costs one call.
    - At most ``max_calls`` gh invocations per run; past the cap every
      further ref is "unknown" (not merged) — conservative, no false
      drift claims.
    - A missing ``gh`` binary marks the resolver dead: all subsequent
      lookups short-circuit to "unknown" (offline degradation, design
      §2 — never blocks).
    """

    def __init__(self, max_calls: int = _MAX_GH_CALLS) -> None:
        self.calls = 0
        self.dead = False
        self._cache: dict[tuple[str, int], bool] = {}

    def merged(self, ref: PrRef, spec_dir: Path, layer: str) -> bool:
        """True iff ``ref`` resolves to a MERGED pull request."""
        key = (ref.repo or f"local:{layer}", ref.number)
        if key in self._cache:
            return self._cache[key]
        if self.dead or self.calls >= _MAX_GH_CALLS:
            return False
        self.calls += 1
        try:
            verdict = self._check(ref, spec_dir)
        except FileNotFoundError:
            # gh binary absent — go dead for the rest of the run
            # (offline degradation; the deliverable signal still stands).
            self.dead = True
            return False
        self._cache[key] = verdict
        return verdict

    def _check(self, ref: PrRef, spec_dir: Path) -> bool:
        # Explicit cross-repo slug → REST pulls endpoint ("merged" is a
        # single-PR-GET field; an issue number 404s here, which is
        # exactly the merged-only filter the design wants). Local refs
        # resolve through the spec dir's own git context, so the right
        # repo is picked per layer without any hardcoded slug map.
        if ref.repo:
            proc = _run_gh(["api", f"repos/{ref.repo}/pulls/{ref.number}"], cwd=None)
        else:
            proc = _run_gh(
                ["pr", "view", str(ref.number), "--json", "state"],
                cwd=spec_dir,
            )
        if proc is None or proc.returncode != 0:
            return False
        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return False
        if not isinstance(data, dict):
            return False
        if ref.repo:
            return bool(data.get("merged"))
        return data.get("state") == "MERGED"


def _collect_refs(spec_dir: Path) -> list[PrRef]:
    """Union of PR citations across a spec's phase files, deduped."""
    seen: set[tuple[str | None, int]] = set()
    refs: list[PrRef] = []
    for fname in _PHASE_FILENAMES:
        fpath = spec_dir / fname
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ref in extract_pr_refs(text):
            key = (ref.repo, ref.number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return refs


def _pr_label(ref: PrRef, layer: str) -> str:
    """Human label for a merged PR — ``attune-author #95`` / ``#67``."""
    if ref.repo:
        return f"{ref.repo.rsplit('/', 1)[-1]} #{ref.number}"
    if layer and layer != "workspace":
        return f"{layer} #{ref.number}"
    return f"#{ref.number}"


@dataclass(frozen=True)
class AuditResult:
    """One spec's audit row."""

    slug: str
    layer: str
    status: str
    staleness: str
    resolved: int  # entries that resolve on disk
    total: int  # entries declared
    # spec-status-integrity additions — defaults keep older callers
    # (and the pre-existing tests) constructing rows unchanged.
    in_flight: bool = False
    drifted: bool = False
    merged_prs: tuple[str, ...] = ()
    signal: str = "deliverables"
    cache_key: str = ""  # "<layer>/<slug>" — the drift-cache key
    root: str = ""  # workspace root the spec lives under


def _root_for(spec_path: Path, roots: list[Path]) -> str:
    """The workspace root ``spec_path`` lives under (no symlink resolve —
    spec paths are built by prefixing the root, so prefix-match holds)."""
    for root in roots:
        try:
            if spec_path.is_relative_to(root):
                return str(root)
        except (TypeError, ValueError):
            continue
    return ""


def audit_specs(
    roots: list[Path] | None = None,
    *,
    pr_links: bool = False,
    resolver: _PrResolver | None = None,
) -> list[AuditResult]:
    """Classify every discovered spec (terminal included) into a row.

    Resolution counts are recomputed per spec so the report can show how
    many declared deliverables are present. Per-spec failures degrade to
    a zero-count row rather than aborting the whole audit.

    With ``pr_links`` (and a resolver), each IN-FLIGHT spec's phase
    files are additionally scanned for PR citations; ≥1 merged
    implementing PR marks the row ``drifted`` (workspace design §2).
    Terminal/parked specs are never queried — no gh spend on settled
    specs.
    """
    if roots is None:
        roots = workspace_roots()
    results: list[AuditResult] = []
    for spec in discover_specs(roots, include_terminal=True):
        total = len(spec.deliverables)
        resolved = 0
        # Counts only matter where resolution actually ran (partial shows
        # "N of M"; suspected-stale/ok are all-resolve by definition).
        if total and spec.staleness in ("partial", "suspected-stale", "ok"):
            try:
                resolved = sum(1 for e in spec.deliverables if _resolve_entry(e, roots))
            except Exception:  # noqa: BLE001 — one bad spec must not abort the audit
                resolved = 0
        in_flight = _is_in_flight(spec.phase, spec.effective_status)
        drifted = False
        merged_prs: tuple[str, ...] = ()
        checked = pr_links and resolver is not None and in_flight
        if checked:
            try:
                merged_prs = tuple(
                    _pr_label(ref, spec.layer)
                    for ref in _collect_refs(spec.path)
                    if resolver.merged(ref, spec.path, spec.layer)
                )
            except Exception:  # noqa: BLE001 — one bad spec must not abort the audit
                merged_prs = ()
            drifted = bool(merged_prs)
        results.append(
            AuditResult(
                slug=spec.slug,
                layer=spec.layer,
                status=spec.status or "—",
                staleness=spec.staleness,
                resolved=resolved,
                total=total,
                in_flight=in_flight,
                drifted=drifted,
                merged_prs=merged_prs,
                signal="pr-links" if checked else "deliverables",
                cache_key=f"{spec.layer}/{spec.slug}",
                root=_root_for(spec.path, roots),
            )
        )
    return results


def write_drift_cache(results: list[AuditResult], roots: list[Path]) -> list[Path]:
    """Write ``.attune/spec-drift.json`` under each workspace root.

    Schema (workspace design §2):
    ``{generated_at, specs: {"<layer>/<slug>": {verdict, prs, signal}}}``.
    Only in-flight specs are recorded — terminal/parked rows carry no
    drift signal. A clean (empty) specs map is still written so
    ``spec_orient`` can tell "checked and clean" from "never checked".
    Per-root write failures are swallowed: the cache is an optimization,
    never a blocker.
    """
    now = time.time()
    written: list[Path] = []
    for root in roots:
        entries = {
            r.cache_key: {
                "verdict": "drifted" if r.drifted else "ok",
                "prs": list(r.merged_prs),
                "signal": r.signal,
            }
            for r in results
            if r.in_flight and r.root == str(root)
        }
        cache_path = Path(root) / ".attune" / "spec-drift.json"
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"generated_at": now, "specs": entries}, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            continue
        written.append(cache_path)
    return written


def format_json(results: list[AuditResult]) -> str:
    """Machine-readable audit payload for the tracking-issue upsert."""
    drifted = sorted(r.cache_key for r in results if r.drifted)
    payload = {
        "generated_at": time.time(),
        "counts": {
            "specs": len(results),
            "drifted": len(drifted),
            "suspected_stale": sum(1 for r in results if r.staleness == "suspected-stale"),
        },
        "drifted": drifted,
        "specs": {
            r.cache_key: {
                "layer": r.layer,
                "slug": r.slug,
                "status": r.status,
                "staleness": r.staleness,
                "in_flight": r.in_flight,
                "drifted": r.drifted,
                "prs": list(r.merged_prs),
                "signal": r.signal,
            }
            for r in results
        },
    }
    return json.dumps(payload, indent=2)


def _truncate(text: str, limit: int) -> str:
    """Clip ``text`` to ``limit`` chars, ellipsizing the overflow."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _detail(result: AuditResult) -> str:
    """Render the ``Unresolved`` column for one row."""
    if result.drifted:
        return ", ".join(result.merged_prs) + " merged"
    if result.staleness == "opted-out":
        return "(opt-out)"
    if result.staleness == "docs-only":
        return "(N/A)"
    if result.staleness == "unknown":
        return "(no block)" if result.total == 0 else f"0 of {result.total}"
    if result.staleness == "partial":
        return f"{result.total - result.resolved} of {result.total}"
    # suspected-stale / ok — every declared deliverable resolves.
    return "—"


def _verdict(result: AuditResult) -> str:
    """Displayed verdict — merged-PR evidence outranks the staleness
    heuristic for the same row."""
    return "drifted" if result.drifted else result.staleness


def format_report(results: list[AuditResult]) -> str:
    """Render the full audit matrix as a string."""
    stale = [r for r in results if r.staleness == "suspected-stale" and not r.drifted]
    drifted = [r for r in results if r.drifted]
    noun = "spec" if len(results) == 1 else "specs"
    counts = f"{len(drifted)} drifted, {len(stale)} suspected-stale"
    title = f"SPEC STATUS AUDIT — {len(results)} {noun} ({counts})"
    if not results:
        return f"{title}\n\n(no specs found)"

    ordered = sorted(results, key=lambda r: (_STALENESS_ORDER.get(_verdict(r), 9), r.slug))
    rows = [
        (
            _truncate(r.slug, 44),
            _truncate(r.layer, 14),
            # Status lines are written informatively and can run to a
            # whole paragraph — truncate so one long status doesn't blow
            # the column out (e.g. integration-coverage's 1k-char line).
            _truncate(r.status, 32),
            _STALENESS_LABEL.get(_verdict(r), _verdict(r)),
            _detail(r),
        )
        for r in ordered
    ]
    widths = [max(len(_HEADERS[i]), *(len(row[i]) for row in rows)) for i in range(len(_HEADERS))]

    def _line(cells: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    out = [title, "", _line(_HEADERS), "─" * len(_line(_HEADERS))]
    out.extend(_line(row) for row in rows)
    out.append("")
    if drifted:
        out.append(
            f"⚠ {len(drifted)} spec(s) have merged implementing PRs but an "
            "in-flight status — flip the status or mark them parked."
        )
    if stale:
        out.append(
            f"⚠ {len(stale)} spec(s) have shipped deliverables but a "
            "non-terminal status — verify & update."
        )
    if not drifted and not stale:
        out.append("✓ No drifted or suspected-stale specs.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Print the audit report; exit per ``--strict``. Never hard-crashes."""
    try:
        args = sys.argv[1:] if argv is None else argv
        strict = "--strict" in args
        offline = "--offline" in args
        pr_links = "--pr-links" in args and not offline
        as_json = "--json" in args
        roots = workspace_roots()
        resolver = _PrResolver() if pr_links else None
        results = audit_specs(roots, pr_links=pr_links, resolver=resolver)
        if pr_links:
            # The cache is what lets the offline SessionStart hook
            # annotate drift without network calls (design §3).
            write_drift_cache(results, roots)
        print(format_json(results) if as_json else format_report(results))
        if strict and any(r.drifted or r.staleness == "suspected-stale" for r in results):
            return 1
        return 0
    except Exception:  # noqa: BLE001 — warn-by-default: report and exit 0
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
