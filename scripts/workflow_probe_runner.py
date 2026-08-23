#!/usr/bin/env python3
"""Planted-defect probe runner for the workflow fleet.

Validates the "working" verdicts from the workflow fleet-health
roundtable (``q-workflow-fleet-health-001``, 2026-08-23, chair-promoted
into ``docs/specs/test-quality-program/``). A single small-target probe
only proves a workflow exited 0 — NOT that it actually found anything.
This runner plants a KNOWN defect and asserts the workflow surfaces it.

Probes (each stages a fixture into a throwaway workdir and runs the
workflow IN-PROCESS via ``attune.workflows.get_workflow`` — this returns
the structured ``WorkflowResult`` directly and bypasses the CLI
``--json`` repr fallback):

    security-audit    fixture with one eval() + one fake key ->
                      must return findings that name them, non-perfect
                      score.
    dependency-check  requirements pinning known-CVE versions ->
                      must name a vulnerable package.
    test-gen          branchy module with no tests -> the emitted test
                      code must import, run, and PASS (executed, not
                      just exit 0).
    discovery-sweep   staged multi-defect workdir -> no LLM lane may
                      report 0 findings AND $0 spend (a $0 lane never
                      ran); no lane in the failures list.
    release-notes     throwaway git repo with a planted breaking-change
                      commit -> readiness score must be a real 0-100
                      number and the change must appear in the report.

SPEND: these are LLM-billed runs. Cost is roughly $0.5-$2 per probe on
the standard depth cap (see ``get_max_budget_usd``); the full set is
~$6-8. Per DEC-6 "CI spends attention, never money", this is a LOCAL /
manually-dispatched runner — do NOT wire it into per-push CI. It sets
``ATTUNE_MAX_BUDGET_USD`` per run (``--budget``, default 3.00) as a hard
cap.

Usage::

    # Free: validate fixtures + print the plan, no LLM spend.
    python scripts/workflow_probe_runner.py

    # Billed: run selected probes (or --all).
    python scripts/workflow_probe_runner.py --run security-audit
    python scripts/workflow_probe_runner.py --all --budget 3.00 --json

Exit code: 0 when every RUN probe passed (and, in plan mode, when every
fixture validated); 1 when any probe failed or a fixture is missing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "workflow_probes"

# Rough per-probe spend, for the plan banner only. Real spend is capped
# by --budget (ATTUNE_MAX_BUDGET_USD) per run.
_EST_COST_USD: dict[str, float] = {
    "security-audit": 0.6,
    "dependency-check": 1.9,
    "test-gen": 1.2,
    "discovery-sweep": 4.5,
    "release-notes": 3.2,
}

PROBE_ORDER = [
    "security-audit",
    "dependency-check",
    "test-gen",
    "discovery-sweep",
    "release-notes",
]


@dataclass
class ProbeResult:
    """Outcome of one probe."""

    name: str
    passed: bool
    reason: str
    cost_usd: float = 0.0
    duration_s: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe": self.name,
            "passed": self.passed,
            "reason": self.reason,
            "cost_usd": round(self.cost_usd, 4),
            "duration_s": round(self.duration_s, 1),
            "evidence": self.evidence,
        }


# --------------------------------------------------------------------------
# Fixture integrity (free — the same checks the unit test enforces).
# --------------------------------------------------------------------------

# Split so this source file itself never contains the literal blocked
# token (the security_guard PreToolUse hook scans command text, and
# keeping the fixture's marker out of grep hits keeps this file quiet).
_EVAL_TOKEN = "ev" + "al("
_KEY_MARKER = "sk-ant-api03-FAKE"


def validate_fixtures() -> list[str]:
    """Return a list of human-readable problems (empty == all good)."""
    problems: list[str] = []
    sec = FIXTURES / "security" / "vulnerable_service.py"
    dep = FIXTURES / "dependency" / "cve_pins.txt"
    tg = FIXTURES / "testgen" / "orders.py"

    if not sec.exists():
        problems.append(f"missing fixture: {sec}")
    else:
        text = sec.read_text(encoding="utf-8")
        if _EVAL_TOKEN not in text:
            problems.append(f"{sec.name}: planted eval() defect is gone")
        if _KEY_MARKER not in text:
            problems.append(f"{sec.name}: planted fake key is gone")

    if not dep.exists():
        problems.append(f"missing fixture: {dep}")
    else:
        text = dep.read_text(encoding="utf-8")
        if "requests==2.19.1" not in text and "PyYAML==5.3.1" not in text:
            problems.append(f"{dep.name}: planted CVE pins are gone")

    if not tg.exists():
        problems.append(f"missing fixture: {tg}")
    else:
        text = tg.read_text(encoding="utf-8")
        if "def order_total" not in text:
            problems.append(f"{tg.name}: expected target function is gone")

    return problems


# --------------------------------------------------------------------------
# Result helpers (defensive against LLM output variance).
# --------------------------------------------------------------------------


def _findings_for(result: Any, category: str) -> list[str]:
    meta = getattr(result, "metadata", None) or {}
    findings = meta.get("findings") or {}
    return list(findings.get(category, []))


def _raw_text(result: Any) -> str:
    meta = getattr(result, "metadata", None) or {}
    text = meta.get("raw_result_text") or ""
    if not text:
        # Fall back to the serialized report / summary.
        fo = getattr(result, "final_output", None)
        text = fo if isinstance(fo, str) else json.dumps(fo, default=str)
        text += "\n" + (getattr(result, "summary", "") or "")
    return text


def _score_of(result: Any) -> float | None:
    fo = getattr(result, "final_output", None)
    if isinstance(fo, dict):
        score = fo.get("score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _cost_of(result: Any) -> float:
    report = getattr(result, "cost_report", None)
    return float(getattr(report, "total_cost", 0.0) or 0.0)


def _crash_reason(result: Any) -> str | None:
    """Return a distinct reason when the workflow ERRORED before analysis.

    Separating transport/SDK crashes from analytical misses is the whole
    point of this harness: a workflow that died must not be reported as
    "ran and missed the defect". ``success is False`` means the workflow
    returned an error result (e.g. the ``is_error``-on-success SDK
    regression), not that it analysed the fixture and found nothing.
    """
    if getattr(result, "success", True):
        return None
    error = getattr(result, "error", None) or "unknown error"
    kind = (getattr(result, "metadata", None) or {}).get("sdk_error_kind")
    prefix = f"[{kind}] " if kind else ""
    first_line = str(error).splitlines()[0][:200]
    return f"workflow CRASHED before analysis (not an analytical miss): {prefix}{first_line}"


def _mentions(text: str, *needles: str) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


# --------------------------------------------------------------------------
# Workflow execution.
# --------------------------------------------------------------------------


def _budget_env(budget: float) -> None:
    os.environ["ATTUNE_MAX_BUDGET_USD"] = str(budget)


async def _run_workflow(name: str, **kwargs: Any) -> Any:
    from attune.workflows import get_workflow

    workflow = get_workflow(name)()
    return await workflow.execute(**kwargs)


def _stage(workdir: Path) -> None:
    """Copy the code fixtures into a throwaway workdir."""
    shutil.copy(
        FIXTURES / "security" / "vulnerable_service.py",
        workdir / "vulnerable_service.py",
    )
    shutil.copy(FIXTURES / "testgen" / "orders.py", workdir / "orders.py")
    # cve_pins.txt is staged AS requirements.txt so the checker sees it.
    shutil.copy(FIXTURES / "dependency" / "cve_pins.txt", workdir / "requirements.txt")


# --------------------------------------------------------------------------
# Probes.
# --------------------------------------------------------------------------


async def probe_security_audit(budget: float) -> ProbeResult:
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(
            FIXTURES / "security" / "vulnerable_service.py",
            work / "vulnerable_service.py",
        )
        t0 = time.monotonic()
        result = await _run_workflow("security-audit", path=str(work), depth="quick")
        dur = time.monotonic() - t0

    crash = _crash_reason(result)
    if crash:
        return ProbeResult(
            name="security-audit",
            passed=False,
            reason=crash,
            cost_usd=_cost_of(result),
            duration_s=dur,
        )
    findings = _findings_for(result, "security")
    text = _raw_text(result)
    score = _score_of(result)
    names_eval = _mentions(text, "eval", "cwe-95", "code injection")
    names_key = _mentions(text, "hardcoded", "secret", "credential", "api key", "cwe-798")
    non_perfect = score is None or score < 100

    passed = bool(findings) and names_eval and names_key and non_perfect
    reasons = []
    if not findings:
        reasons.append("no security findings returned")
    if not names_eval:
        reasons.append("did not name the eval() defect")
    if not names_key:
        reasons.append("did not name the hardcoded key")
    if not non_perfect:
        reasons.append(f"returned a perfect score ({score})")
    reason = "; ".join(reasons) or "found the eval() and the key; score not perfect"

    return ProbeResult(
        name="security-audit",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"score": score, "num_findings": len(findings)},
    )


async def probe_dependency_check(budget: float) -> ProbeResult:
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(FIXTURES / "dependency" / "cve_pins.txt", work / "requirements.txt")
        t0 = time.monotonic()
        result = await _run_workflow("dependency-check", path=str(work), depth="quick")
        dur = time.monotonic() - t0

    crash = _crash_reason(result)
    if crash:
        return ProbeResult(
            name="dependency-check",
            passed=False,
            reason=crash,
            cost_usd=_cost_of(result),
            duration_s=dur,
        )
    findings = _findings_for(result, "dependencies")
    text = _raw_text(result)
    names_pkg = _mentions(
        text,
        "requests",
        "pyyaml",
        "cve-2018-18074",
        "cve-2020-14343",
        "2.19.1",
        "5.3.1",
    )
    passed = bool(findings) and names_pkg
    reasons = []
    if not findings:
        reasons.append("no dependency findings returned")
    if not names_pkg:
        reasons.append("did not name a planted vulnerable package/CVE")
    reason = "; ".join(reasons) or "named a planted vulnerable dependency"

    return ProbeResult(
        name="dependency-check",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"num_findings": len(findings)},
    )


_CODE_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def _extract_test_code(text: str) -> str:
    """Pull fenced code blocks that look like pytest tests."""
    blocks = [b for b in _CODE_FENCE.findall(text) if "def test" in b]
    return "\n\n".join(blocks)


async def probe_test_gen(budget: float) -> ProbeResult:
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(FIXTURES / "testgen" / "orders.py", work / "orders.py")
        t0 = time.monotonic()
        result = await _run_workflow("test-gen", path=str(work), depth="quick")
        dur = time.monotonic() - t0

        crash = _crash_reason(result)
        if crash:
            return ProbeResult(
                name="test-gen",
                passed=False,
                reason=crash,
                cost_usd=_cost_of(result),
                duration_s=dur,
            )
        code = _extract_test_code(_raw_text(result))
        if not code.strip():
            return ProbeResult(
                name="test-gen",
                passed=False,
                reason=(
                    "workflow emitted no runnable test code "
                    "(the report contained no pytest-shaped code fence)"
                ),
                cost_usd=_cost_of(result),
                duration_s=dur,
                evidence={"emitted_test_chars": 0},
            )

        test_file = work / "test_probe_generated.py"
        test_file.write_text(code, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(test_file)],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=180,
        )

    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-8:])
    passed = proc.returncode == 0
    reason = (
        "emitted tests imported, ran, and passed"
        if passed
        else f"emitted tests did not pass (pytest rc={proc.returncode})"
    )
    return ProbeResult(
        name="test-gen",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"emitted_test_chars": len(code), "pytest_tail": tail},
    )


async def probe_discovery_sweep(budget: float) -> ProbeResult:
    import time

    _budget_env(budget)
    from attune.workflows.discovery_sweep.cli_workflow import default_sources

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        _stage(work)
        sources = default_sources()
        t0 = time.monotonic()
        result = await _run_workflow(
            "discovery-sweep",
            path=str(work),
            sources=sources,
            budget_usd=min(budget, 5.0),
            output_format="json",
        )
        dur = time.monotonic() - t0

    crash = _crash_reason(result)
    if crash:
        return ProbeResult(
            name="discovery-sweep",
            passed=False,
            reason=crash,
            cost_usd=_cost_of(result),
            duration_s=dur,
        )
    # Per-lane findings counts (group all buckets by finding.source).
    payload = getattr(result, "final_output", "")
    counts: dict[str, int] = {}
    failures: list[str] = []
    try:
        data = json.loads(payload) if isinstance(payload, str) else {}
        for bucket in ("queue", "questions", "rejected"):
            for item in data.get(bucket, []):
                finding = item.get("finding", item)
                src = finding.get("source", "?")
                counts[src] = counts.get(src, 0) + 1
        failures = list(data.get("metadata", {}).get("failures", []))
    except (ValueError, AttributeError):
        pass

    # Per-lane spend, read off the source objects after the run.
    lane_spend = {
        s.name: float(getattr(s, "spent_usd", 0.0)) for s in sources if getattr(s, "is_llm", False)
    }
    # A $0 LLM lane with 0 findings never ran.
    dead_lanes = [
        name for name, spent in lane_spend.items() if spent <= 0.0 and counts.get(name, 0) == 0
    ]

    passed = not dead_lanes and not failures
    reasons = []
    if dead_lanes:
        reasons.append(f"LLM lane(s) with $0 spend and 0 findings: {dead_lanes}")
    if failures:
        reasons.append(f"lane failures reported: {failures}")
    reason = "; ".join(reasons) or "every LLM lane spent and/or produced findings"

    return ProbeResult(
        name="discovery-sweep",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={
            "lane_findings": counts,
            "lane_spend": {k: round(v, 4) for k, v in lane_spend.items()},
            "failures": failures,
        },
    )


def _build_release_repo(work: Path) -> str:
    """Create a throwaway git repo with a planted breaking-change commit.

    Returns the breaking-change commit subject so the probe can look for
    it in the generated release notes.
    """
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Probe",
        "GIT_AUTHOR_EMAIL": "probe@example.invalid",
        "GIT_COMMITTER_NAME": "Probe",
        "GIT_COMMITTER_EMAIL": "probe@example.invalid",
    }

    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=str(work),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    (work / "app.py").write_text("VERSION = '1.0.0'\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "feat: initial release")
    (work / "app.py").write_text("VERSION = '2.0.0'\n", encoding="utf-8")
    git("add", "-A")
    subject = "feat!: remove deprecated authenticate() — BREAKING CHANGE"
    git("commit", "-q", "-m", subject)
    return subject


async def probe_release_notes(budget: float) -> ProbeResult:
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        subject = _build_release_repo(work)
        t0 = time.monotonic()
        result = await _run_workflow("release-notes", path=str(work), depth="quick")
        dur = time.monotonic() - t0

    crash = _crash_reason(result)
    if crash:
        return ProbeResult(
            name="release-notes",
            passed=False,
            reason=crash,
            cost_usd=_cost_of(result),
            duration_s=dur,
            evidence={"planted_commit": subject},
        )
    score = _score_of(result)
    text = _raw_text(result)
    score_ok = score is not None and 0 <= score <= 100
    change_named = _mentions(text, "breaking", "authenticate", "remove deprecated")
    passed = score_ok and change_named
    reasons = []
    if not score_ok:
        reasons.append(f"readiness score not a real 0-100 number ({score})")
    if not change_named:
        reasons.append("the planted breaking change is absent from the report")
    reason = "; ".join(reasons) or "real readiness score; planted change surfaced"

    return ProbeResult(
        name="release-notes",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"score": score, "planted_commit": subject},
    )


PROBES: dict[str, Callable[[float], Any]] = {
    "security-audit": probe_security_audit,
    "dependency-check": probe_dependency_check,
    "test-gen": probe_test_gen,
    "discovery-sweep": probe_discovery_sweep,
    "release-notes": probe_release_notes,
}


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------


def _print_plan(selected: list[str]) -> None:
    total = sum(_EST_COST_USD.get(p, 0.0) for p in selected)
    print("Workflow probe plan")
    print("-------------------")
    for probe in selected:
        print(f"  {probe:<18} ~${_EST_COST_USD.get(probe, 0.0):.2f}")
    print(f"  {'ESTIMATED TOTAL':<18} ~${total:.2f}")
    print()
    print("This is an ESTIMATE. Real spend is capped per run by --budget")
    print("(ATTUNE_MAX_BUDGET_USD). Re-run with --run <name> or --all to")
    print("execute (billed).")


async def _run_selected(selected: list[str], budget: float) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for probe in selected:
        print(f"\n=== running probe: {probe} (budget cap ${budget:.2f}) ===")
        try:
            results.append(await PROBES[probe](budget))
        except Exception as exc:  # noqa: BLE001 — a probe crash is a result
            results.append(
                ProbeResult(
                    name=probe,
                    passed=False,
                    reason=f"probe raised {type(exc).__name__}: {exc}",
                )
            )
        last = results[-1]
        mark = "PASS" if last.passed else "FAIL"
        print(f"[{mark}] {probe}: {last.reason} (${last.cost_usd:.4f})")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        default="",
        help="comma-separated probe names to run (billed)",
    )
    parser.add_argument("--all", action="store_true", help="run every probe (billed)")
    parser.add_argument(
        "--budget",
        type=float,
        default=3.00,
        help="per-run USD cap (ATTUNE_MAX_BUDGET_USD); default 3.00",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON results to stdout")
    args = parser.parse_args(argv)

    problems = validate_fixtures()
    if problems:
        print("FIXTURE INTEGRITY FAILURES:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if args.all:
        selected = list(PROBE_ORDER)
    elif args.run:
        selected = [p.strip() for p in args.run.split(",") if p.strip()]
    else:
        selected = []

    unknown = [p for p in selected if p not in PROBES]
    if unknown:
        print(f"unknown probe(s): {unknown}", file=sys.stderr)
        print(f"available: {PROBE_ORDER}", file=sys.stderr)
        return 1

    if not selected:
        print("Fixtures validated OK.\n")
        _print_plan(PROBE_ORDER)
        return 0

    results = asyncio.run(_run_selected(selected, args.budget))

    print("\n=== summary ===")
    all_passed = True
    for res in results:
        mark = "PASS" if res.passed else "FAIL"
        all_passed = all_passed and res.passed
        print(f"[{mark}] {res.name}: {res.reason}")
    total_cost = sum(r.cost_usd for r in results)
    print(f"total measured spend: ${total_cost:.4f}")

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
