"""RR-9 full-seam integration (spec-lifecycle-gates T7).

Fixture spec dir → ``run_boundary`` → REAL ledger write →
decisions.md citing the receipt id → linkage asserted back through
``latest_for``. Nothing mocked; the ledger is a real file under the
test's isolated ``ATTUNE_HOME``.
"""

from __future__ import annotations

import json

from attune.gates.lifecycle import GateReceipt, append, latest_for, run_boundary


def test_full_seam_event_to_ruling_linkage(tmp_path):
    # 1. A real spec dir whose requirements cite one dead path.
    spec_dir = tmp_path / "docs" / "specs" / "seam-spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "requirements.md").write_text(
        "# Seam spec\n\n**Status: draft**\n\n" "- implemented in `src/real/module.py` per plan.\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "real").mkdir(parents=True)

    ledger = tmp_path / "verdicts.jsonl"

    # 2. Boundary run — receipt lands in the real ledger file.
    receipts = run_boundary(
        "requirements",
        "seam-spec",
        project_root=tmp_path,
        tier="sub-spec",
        changed_paths=["docs/x.md"],
        ledger_file=ledger,
    )
    sym = next(r for r in receipts if r.gate_id == "symbol-reality")
    assert sym.state == "BLOCKED"  # src/real/module.py does not exist
    raw_rows = [json.loads(x) for x in ledger.read_text(encoding="utf-8").splitlines()]
    assert any(row["receipt_id"] == sym.receipt_id for row in raw_rows)

    # 3. The author fixes the citation; the boundary re-runs green.
    (tmp_path / "src" / "real" / "module.py").write_text("x = 1\n", encoding="utf-8")
    rerun = run_boundary(
        "requirements",
        "seam-spec",
        project_root=tmp_path,
        tier="sub-spec",
        changed_paths=["docs/x.md"],
        ledger_file=ledger,
    )
    assert next(r for r in rerun if r.gate_id == "symbol-reality").state == "PASS"

    # 4. A chair ruling cites the ORIGINAL receipt id; the citation
    #    round-trips through the ledger read side.
    ruling_receipt = GateReceipt.from_dict(sym.to_dict())
    ruling_receipt.decisions_ref = "G-TEST-1"
    append(ruling_receipt, path=ledger)
    (spec_dir / "decisions.md").write_text(
        f"# Decisions\n\n## G-TEST-1\n\nRuled on gate receipt `{sym.receipt_id}`.\n",
        encoding="utf-8",
    )
    latest = {r.gate_id: r for r in latest_for("seam-spec", path=ledger)}
    # latest symbol-reality row is the ruling-cited one (appended last).
    assert latest["symbol-reality"].decisions_ref == "G-TEST-1"
    assert sym.receipt_id in (spec_dir / "decisions.md").read_text(encoding="utf-8")


def test_full_ledger_default_path_round_trip(tmp_path, monkeypatch):
    """The CLI-shaped path: default ledger under ATTUNE_HOME."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
    spec_dir = tmp_path / "docs" / "specs" / "clean-spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "requirements.md").write_text(
        "# Clean\n\n- verified by a suite test that fails on regression.\n",
        encoding="utf-8",
    )
    receipts = run_boundary(
        "requirements",
        "clean-spec",
        project_root=tmp_path,
        tier="sub-spec",
        changed_paths=["docs/x.md"],
    )
    assert all(r.state == "PASS" for r in receipts)
    default_ledger = tmp_path / "home" / "ops" / "gates" / "verdicts.jsonl"
    assert default_ledger.is_file()
    assert len(latest_for("clean-spec")) == 2
