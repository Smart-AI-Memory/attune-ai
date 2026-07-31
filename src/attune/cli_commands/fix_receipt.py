"""Fix receipt — baseline capture, independent probe evaluation,
and the unified truthful receipt (outcome-first-fix Phase 2).

This module owns the ONLY subprocess use in the Fix surface: the
probe runner and the git-plumbing baseline/diff helpers.
``fix_commands.py`` stays subprocess-free (its Phase 1 grep check
narrows to it).

Attribution rule (codex D11 lane finding): the receipt attributes a
change to the run ONLY relative to the pre-run baseline. Paths that
were already dirty before the run are listed separately and are
never named in revert advice — a post-run diff alone would blame
the user's own in-flight work on the agent.
"""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404 — probe runner + git plumbing, argv lists only
import time
from dataclasses import dataclass, field
from pathlib import Path

from attune.cli_commands._exit_codes import (
    EXIT_PLANNED_FAILURE,
    EXIT_SUCCESS,
)
from attune.cli_commands.fix_commands import FixContract, VerificationProbe

_TRAILER = "receipt reflects independently evaluated probes — workflow exit was not trusted"


@dataclass
class ProbeOutcome:
    """One probe's execution evidence (provenance included)."""

    argv: list[str]
    status: str  # "PASS" | "FAIL" | "SKIPPED"
    returncode: int | None = None
    duration_ms: int = 0
    reason: str = ""

    def render(self) -> str:
        detail = f"exit {self.returncode}" if self.returncode is not None else self.reason
        return f"[{self.status}] {' '.join(self.argv)} ({detail}, {self.duration_ms}ms)"


@dataclass
class Baseline:
    """Pre-run snapshot: dirty paths + content hashes of scope files."""

    repo_root: Path
    dirty_paths: set[str] = field(default_factory=set)
    scope_hashes: dict[str, str] = field(default_factory=dict)
    git_available: bool = True


@dataclass
class FixReceipt:
    """The unified execution receipt (spec H2)."""

    attributed_changes: list[str]
    pre_existing_dirty: list[str]
    scope_violations: list[str]
    probe_outcomes: list[ProbeOutcome]
    uncertainty: list[str]
    next_action: str

    def exit_code(self) -> int:
        """0 only when every probe PASSED and scope held — never
        from workflow exit (H2)."""
        all_pass = bool(self.probe_outcomes) and all(
            p.status == "PASS" for p in self.probe_outcomes
        )
        if all_pass and not self.scope_violations:
            return EXIT_SUCCESS
        return EXIT_PLANNED_FAILURE

    def render(self) -> str:
        lines = ["🧾 Fix receipt", ""]
        lines.append("Changes made (attributed to this run):")
        lines += [f"  - {p}" for p in self.attributed_changes]
        if not self.attributed_changes:
            lines.append("  (none detected)")
        if self.pre_existing_dirty:
            lines.append("Pre-existing changes (not attributed, not revert-advised):")
            lines += [f"  - {p}" for p in self.pre_existing_dirty]
        if self.scope_violations:
            lines.append("SCOPE VIOLATIONS (out-of-scope paths changed by this run):")
            lines += [f"  - {p}" for p in self.scope_violations]
        lines.append("Probes (evaluated independently):")
        lines += [f"  - {p.render()}" for p in self.probe_outcomes]
        if self.uncertainty:
            lines.append("Remaining uncertainty:")
            lines += [f"  - {u}" for u in self.uncertainty]
        lines.append(f"Safest next action: {self.next_action}")
        lines.append(_TRAILER)
        return "\n".join(lines)


def _git_dirty_paths(repo_root: Path) -> tuple[set[str], bool]:
    """Return (dirty paths, git_available) via `git status --porcelain`."""
    try:
        proc = subprocess.run(  # nosec B603 B607 — fixed argv, no shell
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set(), False
    if proc.returncode != 0:
        return set(), False
    paths = set()
    for line in proc.stdout.splitlines():
        if len(line) <= 3:
            continue
        payload = line[3:].strip().strip('"')
        # Rename/copy records are `old -> new` — record BOTH real
        # paths, never the literal arrow payload (codex lane finding).
        if " -> " in payload:
            old, _, new = payload.partition(" -> ")
            paths.add(old.strip().strip('"'))
            paths.add(new.strip().strip('"'))
        else:
            paths.add(payload)
    return paths, True


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "<unreadable>"


def capture_baseline(repo_root: Path, scope_paths: list[Path]) -> Baseline:
    """Snapshot pre-run state: dirty set + content hashes.

    Hashes cover the scope files AND every already-dirty file:
    a baseline-dirty file the workflow modifies FURTHER must still
    be attributed (and flagged as a violation when out of scope) —
    the dirty-set subtraction alone would let it escape (codex D11
    lane finding).
    """
    dirty, git_ok = _git_dirty_paths(repo_root)
    to_hash = {str(p) for p in scope_paths} | dirty
    hashes = {p: _hash_file(repo_root / p) for p in sorted(to_hash)}
    return Baseline(
        repo_root=repo_root, dirty_paths=dirty, scope_hashes=hashes, git_available=git_ok
    )


def run_probes(probes: list[VerificationProbe], cwd: Path) -> list[ProbeOutcome]:
    """Execute every probe through a real subprocess boundary.

    Probe processes run with bytecode and pytest-cache writes
    disabled: otherwise the probes' own cache artifacts
    (``__pycache__``, ``.pytest_cache``) appear in the post-run diff
    and get falsely attributed to the fix run as scope violations.
    """
    import os

    probe_env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": "-p no:cacheprovider",
    }
    outcomes: list[ProbeOutcome] = []
    for probe in probes:
        start = time.monotonic()
        try:
            proc = subprocess.run(  # nosec B603 — validated argv, no shell
                probe.argv,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=600,
                env=probe_env,
            )
        except FileNotFoundError:
            outcomes.append(
                ProbeOutcome(
                    argv=probe.argv,
                    status="SKIPPED",
                    reason=f"command not found: {probe.argv[0]}",
                )
            )
            continue
        except (OSError, subprocess.TimeoutExpired) as exc:
            outcomes.append(ProbeOutcome(argv=probe.argv, status="SKIPPED", reason=str(exc)))
            continue
        duration_ms = int((time.monotonic() - start) * 1000)
        status = "PASS" if proc.returncode == probe.expected_exit else "FAIL"
        outcomes.append(
            ProbeOutcome(
                argv=probe.argv,
                status=status,
                returncode=proc.returncode,
                duration_ms=duration_ms,
            )
        )
    return outcomes


def assemble_receipt(
    contract: FixContract,
    baseline: Baseline,
    scope_paths: list[Path],
    probe_outcomes: list[ProbeOutcome],
) -> FixReceipt:
    """Compute the receipt from the baseline diff + probe evidence."""
    dirty_now, git_ok = _git_dirty_paths(baseline.repo_root)
    scope_strs = {str(p) for p in scope_paths}

    attributed: set[str] = set()
    if baseline.git_available and git_ok:
        attributed |= dirty_now - baseline.dirty_paths
    for path_str, old_hash in baseline.scope_hashes.items():
        if _hash_file(baseline.repo_root / path_str) != old_hash:
            attributed.add(path_str)

    # A baseline-dirty file the run modified FURTHER is attributed
    # (hash change above) and moves out of the pre-existing section.
    pre_existing = sorted(baseline.dirty_paths - attributed)
    violations = sorted(p for p in attributed if p not in scope_strs)

    uncertainty: list[str] = []
    if not (baseline.git_available and git_ok):
        uncertainty.append("git unavailable — attribution limited to content hashes of scope files")
    skipped = [p for p in probe_outcomes if p.status == "SKIPPED"]
    for probe in skipped:
        uncertainty.append(f"probe not executed: {' '.join(probe.argv)} ({probe.reason})")
    unhashable = sorted(p for p, h in baseline.scope_hashes.items() if h == "<unreadable>")
    if unhashable:
        uncertainty.append(
            "baseline hash unavailable for: "
            + ", ".join(unhashable)
            + " — further edits to these paths cannot be attributed"
        )

    failed = [p for p in probe_outcomes if p.status == "FAIL"]
    if violations:
        next_action = "revert the out-of-scope paths listed above, then re-run"
    elif failed:
        next_action = f"inspect the diff, then re-run probe: {' '.join(failed[0].argv)}"
    elif skipped:
        next_action = "make the skipped probe runnable, then re-run verification"
    else:
        next_action = "review the attributed diff and commit"

    return FixReceipt(
        attributed_changes=sorted(attributed),
        pre_existing_dirty=pre_existing,
        scope_violations=violations,
        probe_outcomes=probe_outcomes,
        uncertainty=uncertainty,
        next_action=next_action,
    )
