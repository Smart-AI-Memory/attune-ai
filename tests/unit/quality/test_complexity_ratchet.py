"""Complexity ratchet — no new D-or-worse blocks, allowlist only shrinks.

Born from the 2026-07-14 library health report
(``docs/reports/library-health-2026-07-14.md``): the repo carried 30
blocks at cyclomatic-complexity grade D or worse (including 3
F-grade), and nothing stopped the count growing. This gate is the
prevention half of that plan; the allowlist below is the paydown
ledger.

Two directions, both enforced:

- **Ratchet up (blocked):** a PR that introduces a NEW D-or-worse
  block fails ``test_no_new_d_or_worse_blocks``. Refactor it below
  D (score < 21), or — exceptionally, with a justifying comment —
  add it to the allowlist in the same PR.
- **Ratchet down (celebrated, enforced):** a PR that fixes an
  allowlisted block must delete its entry, or
  ``test_allowlist_only_shrinks`` fails. Stale entries would let the
  next regression hide behind an old exemption.

The measurement mirrors ``radon cc -n D src/attune`` (score >= 21,
functions, methods, and classes alike).
"""

from __future__ import annotations

from pathlib import Path

from radon.complexity import cc_visit

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "attune"

#: Cyclomatic-complexity score where radon's grade D begins.
D_THRESHOLD = 21

#: The paydown ledger — every block at D or worse when the ratchet
#: shipped (2026-07-14, post-#1376). DELETE entries as blocks are
#: refactored below D; NEVER add entries without a justifying
#: comment. Batch plan: docs/reports/library-health-2026-07-14.md.
ALLOWLISTED_D_BLOCKS: frozenset[str] = frozenset(
    {
        "authoring/fact_check/python_refs.py::check",
        "cli_commands/workflow_commands.py::cmd_workflow_run",
        "mcp/workflow_handlers.py::_workflow_response",
        "memory/mixins/backend_init_mixin.py::BackendInitMixin._initialize_backends",
        "memory/security/query.py::AuditQueryMixin",
        "memory/security/query.py::AuditQueryMixin.query",
        "memory/security/query.py::_apply_custom_filters",
        "meta_workflows/cli_commands/workflow_commands.py::run_workflow",
        "models/empathy_executor.py::EmpathyLLMExecutor.run",
        "ops/runner.py::RunnerService._validate_recommendation",
        "ops/spec_lifecycle.py::derive_lifecycle",
        "project_index/dependency_analysis.py::DependencyAnalysisMixin._build_summary",
        "project_index/index.py::ProjectIndex.refresh_incremental",
        "voice/formatter.py::_extract_from_workflow_result",
        "workflows/discovery_sweep/board.py::sweep_to_board_html",
        "workflows/document_gen/report_formatter.py::format_doc_gen_report",
        "workflows/documentation_orchestrator.py::DocumentationOrchestrator.execute",
        "workflows/help_maintenance.py::HelpMaintenanceWorkflow.execute",
        "workflows/rag_code_gen.py::RagCodeGenWorkflow.execute",
        "workflows/report_panel.py::_section_html",
        "workflows/secure_release.py::format_secure_release_report",
        "workflows/test_maintenance.py::TestMaintenanceWorkflow._generate_plan",
    }
)


def d_or_worse_blocks(src_root: Path) -> set[str]:
    """Every block in ``src_root`` at complexity score >= D_THRESHOLD.

    Returns ``"<path relative to src_root>::<fullname>"`` entries —
    line numbers are deliberately excluded so unrelated edits above a
    block don't churn the ledger. Files that fail to parse are
    skipped (syntax gates live elsewhere).
    """
    offenders: set[str] = set()
    for py in sorted(src_root.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        try:
            blocks = cc_visit(py.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError):
            continue
        rel = py.relative_to(src_root).as_posix()
        for block in blocks:
            if block.complexity >= D_THRESHOLD:
                name = getattr(block, "fullname", None) or block.name
                offenders.add(f"{rel}::{name}")
    return offenders


def test_no_new_d_or_worse_blocks():
    new = d_or_worse_blocks(SRC_ROOT) - ALLOWLISTED_D_BLOCKS
    assert not new, (
        "New D-or-worse complexity block(s) introduced:\n  "
        + "\n  ".join(sorted(new))
        + "\nRefactor below grade D (score < 21) — see the batch "
        "playbook in docs/reports/library-health-2026-07-14.md. "
        "Adding to ALLOWLISTED_D_BLOCKS is the exception and needs a "
        "justifying comment."
    )


def test_allowlist_only_shrinks():
    stale = ALLOWLISTED_D_BLOCKS - d_or_worse_blocks(SRC_ROOT)
    assert not stale, (
        "Allowlisted block(s) are no longer D-or-worse — delete their "
        "entries in this PR so the ratchet can't hide a future "
        "regression behind them:\n  " + "\n  ".join(sorted(stale))
    )


# --- verify-it-fires receipts ------------------------------------------------


def _deeply_branched_source(branches: int) -> str:
    """A function whose complexity is ``branches + 1``."""
    lines = ["def tangled(x):"]
    for i in range(branches):
        lines.append(f"    if x == {i}:")
        lines.append(f"        return {i}")
    lines.append("    return -1")
    return "\n".join(lines) + "\n"


def test_detector_fires_on_a_d_grade_block(tmp_path):
    (tmp_path / "victim.py").write_text(_deeply_branched_source(D_THRESHOLD), encoding="utf-8")

    offenders = d_or_worse_blocks(tmp_path)

    assert offenders == {"victim.py::tangled"}


def test_detector_ignores_blocks_below_d(tmp_path):
    (tmp_path / "fine.py").write_text(_deeply_branched_source(D_THRESHOLD - 2), encoding="utf-8")

    assert d_or_worse_blocks(tmp_path) == set()


def test_detector_skips_unparseable_files(tmp_path):
    (tmp_path / "broken.py").write_text("def (::\n", encoding="utf-8")
    (tmp_path / "victim.py").write_text(_deeply_branched_source(D_THRESHOLD), encoding="utf-8")

    assert d_or_worse_blocks(tmp_path) == {"victim.py::tangled"}
