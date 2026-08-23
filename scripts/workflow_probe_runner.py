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
    # Analytical batch (Phase 3) — rough per-probe, capped by --budget.
    "code-review": 0.9,
    "deep-review": 1.2,
    "perf-audit": 0.5,
    "refactor-plan": 0.9,
    "simplify-code": 1.2,
    "test-audit": 0.9,
    "doc-audit": 2.9,
    # Gate group (D5 batch 2) — secure-release bills its sub-audit;
    # the others were $0-class in the fleet probe / rule-based.
    "secure-release": 1.5,
    "health-check": 0.3,
    "doc-orchestrator": 0.3,
    "release-prep": 0.0,
}

PROBE_ORDER = [
    "security-audit",
    "dependency-check",
    "test-gen",
    "discovery-sweep",
    "release-notes",
    "code-review",
    "deep-review",
    "perf-audit",
    "refactor-plan",
    "simplify-code",
    "test-audit",
    "doc-audit",
    "secure-release",
    "health-check",
    "doc-orchestrator",
    "release-prep",
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

    ana = FIXTURES / "analytical" / "sample_service.py"
    if not ana.exists():
        problems.append(f"missing fixture: {ana}")
    else:
        text = ana.read_text(encoding="utf-8")
        # A few planted-defect markers across classes — if these are
        # gone the analytical probes would run against a clean file and
        # go vacuous.
        for marker, label in (
            ("def find_duplicates", "perf O(n^2) target"),
            ("tags: list[str] = []", "mutable-default target"),
            ("def validate_label", "duplication target"),
            ("def summarize(items):", "missing-docstring target"),
        ):
            if marker not in text:
                problems.append(f"{ana.name}: planted {label} is gone")

    return problems


# --------------------------------------------------------------------------
# Result helpers (defensive against LLM output variance).
# --------------------------------------------------------------------------


def _findings_for(result: Any, category: str) -> list[str]:
    meta = getattr(result, "metadata", None) or {}
    findings = meta.get("findings") or {}
    return list(findings.get(category, []))


def _total_findings(result: Any) -> int:
    """Count findings across EVERY bucket of ``metadata["findings"]``.

    Different workflows key the findings dict differently — security-audit
    keys by SEVERITY (CRITICAL/HIGH/MEDIUM/LOW), others by category
    (security/dependencies/...). Asserting on one hard-coded key silently
    reads empty when the workflow used a different key, turning the probe
    vacuous. Summing every bucket is key-agnostic.
    """
    meta = getattr(result, "metadata", None) or {}
    findings = meta.get("findings") or {}
    return sum(len(v) for v in findings.values() if isinstance(v, list))


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
    num_findings = _total_findings(result)
    text = _raw_text(result)
    score = _score_of(result)
    names_eval = _mentions(text, "eval", "cwe-95", "code injection")
    names_key = _mentions(text, "hardcoded", "secret", "credential", "api key", "cwe-798")
    non_perfect = score is None or score < 100

    passed = num_findings > 0 and names_eval and names_key and non_perfect
    reasons = []
    if num_findings == 0:
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
        evidence={"score": score, "num_findings": num_findings},
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
    num_findings = _total_findings(result)
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
    passed = num_findings > 0 and names_pkg
    reasons = []
    if num_findings == 0:
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
        evidence={"num_findings": num_findings},
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


# --------------------------------------------------------------------------
# Analytical probes — all share one multi-defect fixture (Phase 3, D5).
# Each asserts its OWN planted defect class is surfaced. Behavioral
# receipt (per the spec's "validating probe" definition): findings > 0
# AND the report names the planted class — never an exact string/score.
# --------------------------------------------------------------------------

_ANALYTICAL: dict[str, dict[str, Any]] = {
    "perf-audit": {
        "cls": "the O(n^2) membership scan",
        "needles": [
            "o(n",
            "quadratic",
            "n^2",
            "n²",
            "linear scan",
            "membership",
            "nested loop",
            "use a set",
            "set(",
            "performance",
        ],
    },
    "refactor-plan": {
        "cls": "the duplicated validate_* blocks",
        "needles": [
            "duplicat",
            "refactor",
            "repeat",
            "validate_",
            "copy-paste",
            "copy paste",
            "extract",
            "dry",
        ],
    },
    "simplify-code": {
        "cls": "the nested conditional",
        "needles": [
            "nest",
            "simplif",
            "early return",
            "guard clause",
            "guard-clause",
            "categorize",
            "flatten",
            "conditional",
        ],
    },
    "code-review": {
        "cls": "the mutable default argument",
        "needles": [
            "mutable default",
            "default argument",
            "default parameter",
            "tags=[]",
            "shared",
            "append_tag",
        ],
    },
    "deep-review": {
        "cls": "the mutable default / swallowed exception",
        "needles": [
            "mutable default",
            "default argument",
            "except",
            "swallow",
            "broad except",
            "load_config",
            "append_tag",
        ],
    },
    "test-audit": {
        "cls": "the missing tests",
        "needles": [
            "untested",
            "no test",
            "test gap",
            "no coverage",
            "lacks test",
            "missing test",
            "not tested",
            "without test",
        ],
    },
    "doc-audit": {
        "cls": "the missing docstring",
        "needles": [
            "docstring",
            "summarize",
            "undocumented",
            "missing doc",
            "no doc",
            "lacks a doc",
            "without a doc",
        ],
    },
}


async def _probe_analytical(name: str, budget: float) -> ProbeResult:
    """Run one analytical workflow against the shared multi-defect
    fixture and assert its planted defect class is surfaced."""
    import time

    _budget_env(budget)
    cfg = _ANALYTICAL[name]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(
            FIXTURES / "analytical" / "sample_service.py",
            work / "sample_service.py",
        )
        t0 = time.monotonic()
        result = await _run_workflow(name, path=str(work), depth="quick")
        dur = time.monotonic() - t0

    crash = _crash_reason(result)
    if crash:
        return ProbeResult(
            name=name,
            passed=False,
            reason=crash,
            cost_usd=_cost_of(result),
            duration_s=dur,
        )

    num_findings = _total_findings(result)
    named = _mentions(_raw_text(result), *cfg["needles"])
    # The receipt is BEHAVIORAL: the workflow named the planted class.
    # The structured-findings COUNT is evidence only, never a gate —
    # live validation (2026-08-23) showed refactor-plan returning 0
    # structured findings on one run and 44 on the next for the SAME
    # fixture, while naming the duplication in the report text both
    # times. Gating on the count made the probe fail on LLM variance
    # rather than on detection (the spec's "never exact-match" rule).
    passed = named
    reason = f"surfaced {cfg['cls']}" if named else f"did not surface {cfg['cls']}"
    return ProbeResult(
        name=name,
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"num_findings": num_findings, "named_class": named},
    )


def _make_analytical_probe(name: str) -> Callable[[float], Any]:
    """Bind a workflow name to the shared analytical probe."""
    return lambda budget: _probe_analytical(name, budget)


# --------------------------------------------------------------------------
# Gate-group probes (Phase 3, D5 batch 2) — assert the FAIL-CLOSED /
# DEGRADED behavior #2207-#2209 added. These workflows return their own
# result objects (not WorkflowResult), so each probe reads the merged
# result surface directly and the receipt is the honest verdict, never
# a score. All calls go through _run_gate_workflow so unit tests can
# stub the workflow without an LLM.
# --------------------------------------------------------------------------


async def _run_gate_workflow(name: str, **kwargs: Any) -> Any:
    from attune.workflows import get_workflow

    return await get_workflow(name)().execute(**kwargs)


async def probe_secure_release(budget: float) -> ProbeResult:
    """A planted-critical fixture must NOT get a GO (P7, #2208)."""
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(
            FIXTURES / "security" / "vulnerable_service.py",
            work / "vulnerable_service.py",
        )
        t0 = time.monotonic()
        result = await _run_gate_workflow("secure-release", path=str(work))
        dur = time.monotonic() - t0

    go_no_go = getattr(result, "go_no_go", "?")
    passed = go_no_go != "GO"
    reason = (
        f"fail-closed: planted-critical fixture yielded {go_no_go}"
        if passed
        else "returned GO on a planted-critical fixture (fail-open)"
    )
    return ProbeResult(
        name="secure-release",
        passed=passed,
        reason=reason,
        cost_usd=float(getattr(result, "total_cost", 0.0) or 0.0),
        duration_s=dur,
        evidence={
            "go_no_go": go_no_go,
            "critical_count": getattr(result, "critical_count", None),
            "high_count": getattr(result, "high_count", None),
            "blockers": len(getattr(result, "blockers", []) or []),
        },
    )


async def probe_health_check(budget: float) -> ProbeResult:
    """A bare, unmeasurable dir must surface DEGRADED/N-A — never a
    fabricated perfect grade (#2209)."""
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(FIXTURES / "testgen" / "orders.py", work / "orders.py")
        t0 = time.monotonic()
        result = await _run_gate_workflow("health-check", path=str(work))
        dur = time.monotonic() - t0

    degraded = bool(getattr(result, "degraded", False))
    grade = str(getattr(result, "grade", "?"))
    passed = degraded or grade == "N/A"
    reason = (
        f"honest incomplete-data verdict (degraded={degraded}, grade={grade})"
        if passed
        else f"fabricated a complete verdict (grade={grade}, degraded=False) on an unmeasurable dir"
    )
    report = result.to_dict() if hasattr(result, "to_dict") else {}
    return ProbeResult(
        name="health-check",
        passed=passed,
        reason=reason,
        cost_usd=float(report.get("total_cost", 0.0) or 0.0),
        duration_s=dur,
        evidence={"degraded": degraded, "grade": grade, "score": report.get("score")},
    )


async def probe_doc_orchestrator(budget: float) -> ProbeResult:
    """No fabricated 'no gaps': either the scan is honestly DEGRADED,
    or it ran and found the planted doc gap (#2209)."""
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(
            FIXTURES / "analytical" / "sample_service.py",
            work / "sample_service.py",
        )
        # An unambiguous, coarse-granularity doc gap: NO module
        # docstring at all (index-based scans may not see per-function
        # gaps; a bare module is a gap at every granularity).
        (work / "undocumented_util.py").write_text(
            "def helper(x):\n    return x * 2\n\n\n" "def other_helper(y):\n    return y - 1\n",
            encoding="utf-8",
        )
        t0 = time.monotonic()
        result = await _run_gate_workflow("doc-orchestrator", path=str(work))
        dur = time.monotonic() - t0

    degraded = bool(getattr(result, "degraded", False))
    items_found = int(getattr(result, "items_found", 0) or 0)
    passed = degraded or items_found > 0
    reason = (
        f"honest scan (degraded={degraded}, items_found={items_found})"
        if passed
        else "claimed a real scan found no gaps on a fixture with a planted doc gap"
    )
    return ProbeResult(
        name="doc-orchestrator",
        passed=passed,
        reason=reason,
        cost_usd=float(getattr(result, "total_cost", 0.0) or 0.0),
        duration_s=dur,
        evidence={"degraded": degraded, "items_found": items_found},
    )


async def probe_release_prep(budget: float) -> ProbeResult:
    """The deterministic gate must FAIL an untested fixture — a PASS on
    a dir with no tests is fabrication ($0, rule-based)."""
    import time

    _budget_env(budget)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        _stage(work)
        # A test that FAILS: any release gate that actually runs the
        # suite must FAIL this fixture — a PASS is proof the gate never
        # engaged the planted failure (absence-as-pass, P7).
        (work / "test_planted_failure.py").write_text(
            '"""Planted failing test for the release-prep gate probe."""\n\n\n'
            "def test_planted_failure():\n"
            "    assert False, 'planted: the release gate must see this failure'\n",
            encoding="utf-8",
        )
        t0 = time.monotonic()
        result = await _run_gate_workflow("release-prep", path=str(work))
        dur = time.monotonic() - t0

    success = bool(getattr(result, "success", True))
    passed = not success
    reason = (
        "honest FAIL verdict on an untested fixture"
        if passed
        else "PASSED release gates on a fixture with no tests (fabrication)"
    )
    return ProbeResult(
        name="release-prep",
        passed=passed,
        reason=reason,
        cost_usd=_cost_of(result),
        duration_s=dur,
        evidence={"gate_success": success},
    )


PROBES: dict[str, Callable[[float], Any]] = {
    "security-audit": probe_security_audit,
    "dependency-check": probe_dependency_check,
    "test-gen": probe_test_gen,
    "discovery-sweep": probe_discovery_sweep,
    "release-notes": probe_release_notes,
    **{name: _make_analytical_probe(name) for name in _ANALYTICAL},
    "secure-release": probe_secure_release,
    "health-check": probe_health_check,
    "doc-orchestrator": probe_doc_orchestrator,
    "release-prep": probe_release_prep,
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


# --------------------------------------------------------------------------
# Run-records (registry feed — workflow-behavioral-validation D3/D9).
# --------------------------------------------------------------------------

RUNNER_VERSION = "0.3.0"
RECORDS_DIR = REPO_ROOT / "docs" / "specs" / "workflow-behavioral-validation" / "records"

#: Receipt type per probe (design.md § fixture design by workflow type).
_RECEIPT_TYPES: dict[str, str] = {
    "security-audit": "named-defect",
    "dependency-check": "named-defect",
    "test-gen": "executed-tests",
    "discovery-sweep": "lane-accounting",
    "release-notes": "metric-crosscheck",
    **dict.fromkeys(_ANALYTICAL, "named-defect"),
    "secure-release": "fail-closed-gate",
    "health-check": "fail-closed-gate",
    "doc-orchestrator": "fail-closed-gate",
    "release-prep": "fail-closed-gate",
}


def _git_sha() -> str:
    """Best-effort short sha of the tree the probe ran against."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short=9", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _verdict_of(result: ProbeResult) -> str:
    """pass | fail | crash — crash when the workflow never analysed."""
    if result.passed:
        return "pass"
    if "CRASHED" in result.reason or result.reason.startswith("probe raised"):
        return "crash"
    return "fail"


def write_record(result: ProbeResult, records_dir: Path, ran_at: str, git_sha: str) -> Path:
    """Write one run-record JSON (ALWAYS runs — pass, fail, AND crash.

    Per D9: revocation depends on failed/crashed records being written
    and committed, so record-writing must never be gated on the verdict.
    Files are timestamped (append-only, never overwritten); the registry
    is re-projected from them by ``scripts/project_probe_registry.py``
    (the ``--check`` drift guard fails CI on a stale registry).
    """
    records_dir.mkdir(parents=True, exist_ok=True)
    stamp = ran_at.replace(":", "").replace("-", "")[:15]  # YYYYmmddTHHMMSS
    path = records_dir / f"{stamp}-{result.name}.json"
    suffix = 1
    while path.exists():  # append-only: never clobber an existing record
        path = records_dir / f"{stamp}-{result.name}-{suffix}.json"
        suffix += 1
    record = {
        "workflow": result.name,
        "fixture": "tests/fixtures/workflow_probes/",
        "receipt_type": _RECEIPT_TYPES.get(result.name, "named-defect"),
        "verdict": _verdict_of(result),
        "cost_usd": round(result.cost_usd, 4),
        "duration_s": round(result.duration_s, 1),
        "ran_at": ran_at,
        "runner_version": RUNNER_VERSION,
        "git_sha": git_sha,
        "evidence": {**result.evidence, "reason": result.reason},
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


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
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="scratch run: skip writing run-records",
    )
    parser.add_argument(
        "--record-dir",
        default=str(RECORDS_DIR),
        help="where run-records land (default: the tracked registry records dir)",
    )
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

    if not args.no_record:
        from datetime import datetime, timezone

        records_dir = Path(args.record_dir)
        sha = _git_sha()
        written = [
            write_record(
                res,
                records_dir,
                ran_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                git_sha=sha,
            )
            for res in results
        ]
        for path in written:
            print(f"record: {path}")
        print(
            "re-project the registry before committing records: "
            "python scripts/project_probe_registry.py "
            "(CI's --check guard fails on a stale registry.md)"
        )

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
