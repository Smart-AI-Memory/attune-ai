"""End-to-end smoke test for the discovery-sweep Python API.

Phase 1 ships the engine as a Python API; this is the
documented smoke path: instantiate the workflow with a stub
``FindingSource`` that emits a mix of finding kinds, run the
sweep, and verify the three output artifacts.

Real adapters wrapping bug_predict / security_audit / etc. are
Phase 2 deliverables.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from attune.workflows.discovery_sweep import (
    DiscoverySweepEngine,
    Finding,
    ResolutionComplexity,
    Severity,
    VerificationStatus,
    read_jsonl,
    split_findings_by_complexity,
)


@dataclass
class _StubFindingSource:
    """A canned FindingSource for the smoke test."""

    name: str
    canned: list[Finding]
    estimated_spend_usd: float = 1.5

    def discover(self, scope: Path, budget_usd: float, sweep_id: str) -> Iterable[Finding]:
        return [
            Finding(
                source_workflow=f.source_workflow,
                file_path=f.file_path,
                severity=f.severity,
                message=f.message,
                raw_finding=f.raw_finding,
                sweep_id=sweep_id,
                line=f.line,
            )
            for f in self.canned
        ]


def _seed_walker_module(tmp_path: Path) -> Path:
    """Write a real-looking module so the verification engine has
    source text to inspect for the os.walk dirs[:] rule."""
    target = tmp_path / "walker.py"
    target.write_text(
        "import os\n"
        "\n"
        "def find_py(root):\n"
        "    matches = []\n"
        "    for dirpath, dirs, files in os.walk(root):\n"
        "        dirs[:] = [d for d in dirs if d != '.git']\n"
        "        matches.extend(files)\n"
        "    return matches\n"
    )
    return target


def test_discovery_sweep_smoke_python_api(tmp_path):
    """Engine smoke test: one finding REJECTs (known false positive),
    one stays UNSURE (no rule fires)."""
    walker = _seed_walker_module(tmp_path)

    false_positive = Finding(
        source_workflow="perf_audit",
        file_path=str(walker.relative_to(tmp_path)),
        severity=Severity.LOW,
        message="memory_leak: large_list_copy on dirs[:]",
        raw_finding={"pattern": "large_list_copy"},
        sweep_id="placeholder",
        line=6,
    )

    fresh_unknown = Finding(
        source_workflow="bug_predict",
        file_path=str(walker.relative_to(tmp_path)),
        severity=Severity.MEDIUM,
        message="cyclomatic complexity above threshold",
        raw_finding={"pattern": "cyclomatic", "complexity": 12},
        sweep_id="placeholder",
        line=3,
    )

    source = _StubFindingSource(name="combined", canned=[false_positive, fresh_unknown])
    workflow = DiscoverySweepEngine(
        sources=[source],
        output_dir=tmp_path / "queue",
        project_root=tmp_path,
    )

    result = workflow.run(scope=tmp_path)

    # File contracts: all three exist, sweep_id consistent.
    assert result.queue_path is not None
    assert result.rejected_path is not None
    assert result.questions_path is not None
    queue_path = Path(result.queue_path)
    rejected_path = Path(result.rejected_path)
    questions_path = Path(result.questions_path)
    assert queue_path.exists()
    assert rejected_path.exists()
    assert questions_path.exists()
    assert result.sweep_id in queue_path.name
    assert result.sweep_id in rejected_path.name
    assert result.sweep_id in questions_path.name

    # Classification contract.
    assert result.reject_count == 1
    assert result.unsure_count == 1
    assert result.accept_count == 0

    rejected_findings = read_jsonl(rejected_path)
    assert len(rejected_findings) == 1
    assert rejected_findings[0].verification_status == VerificationStatus.REJECT
    assert "os.walk" in rejected_findings[0].verification_reasoning

    # Questions file is reviewable cold — must mention the
    # fresh finding's message text.
    questions_md = questions_path.read_text(encoding="utf-8")
    assert "cyclomatic complexity above threshold" in questions_md
    assert result.sweep_id in questions_md

    # Budget tracking.
    assert "combined" in result.sub_workflow_spend
    assert result.total_spend_usd == 1.5


def test_discovery_sweep_smoke_accept_is_tagged(tmp_path):
    """When an ACCEPT rule fires (or — Phase 1 — a finding is
    forced ACCEPTed and tagged by the complexity classifier),
    it lands in the queue with a routine vs needs_patrick tag.

    Phase 1 ships no ACCEPT rules, so this test fabricates an
    ACCEPT finding directly to exercise the classifier path
    inside the orchestrator.
    """

    # Stub source emits a finding pre-marked ACCEPTed. The
    # verification engine will overwrite that status — so we
    # bypass verification by constructing the workflow with a
    # pass-through engine.
    from attune.workflows.discovery_sweep.verification import VerificationEngine

    class _NoopAcceptRule:
        name = "noop_accept"

        def classify(self, finding, source_lines):
            if "promote me" in finding.message:
                return (VerificationStatus.ACCEPT, "smoke-test ACCEPT")
            return None

    accept_finding = Finding(
        source_workflow="bug_predict",
        file_path="src/attune/security/auth.py",
        severity=Severity.HIGH,
        message="promote me — touches auth surface",
        raw_finding={"pattern": "smoke"},
        sweep_id="placeholder",
        line=10,
    )
    source = _StubFindingSource(name="bug_predict", canned=[accept_finding])

    workflow = DiscoverySweepEngine(
        sources=[source],
        output_dir=tmp_path / "queue",
        project_root=tmp_path,
        verification_engine=VerificationEngine([_NoopAcceptRule()], project_root=tmp_path),
    )
    result = workflow.run(scope=tmp_path)

    assert result.accept_count == 1
    queue = read_jsonl(result.queue_path)
    assert len(queue) == 1
    assert queue[0].verification_status == VerificationStatus.ACCEPT
    # security_adjacent trigger should fire on the file path.
    assert queue[0].resolution_complexity == ResolutionComplexity.NEEDS_PATRICK

    routine, needs_patrick = split_findings_by_complexity(queue)
    assert routine == []
    assert needs_patrick == queue
