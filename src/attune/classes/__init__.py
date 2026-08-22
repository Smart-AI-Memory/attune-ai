"""Class register tooling (release-audit-stage spec).

Phase X ships :mod:`attune.classes.class_m` (receipt-type
declaration checks) and :mod:`attune.classes.mock_worklist` (the
class-M AST worklist detector). Phase 0 adds the rule pack and the
derived register.
"""

from attune.classes.class_m import (
    BOUNDARY_CLASS_IDS,
    RECEIPT_TYPES,
    ReceiptProblem,
    check_commit,
    check_range,
)
from attune.classes.register import GATES, GateRef, derive_register
from attune.classes.rules import (
    RULES,
    Calibration,
    Hit,
    Rule,
    calibrated_here,
    canonical_repo_id,
)
from attune.classes.scan import scan_paths
from attune.classes.teeth import decide, re_exposed

__all__ = [
    "GATES",
    "GateRef",
    "derive_register",
    "BOUNDARY_CLASS_IDS",
    "RECEIPT_TYPES",
    "RULES",
    "Calibration",
    "Hit",
    "ReceiptProblem",
    "Rule",
    "calibrated_here",
    "canonical_repo_id",
    "check_commit",
    "check_range",
    "decide",
    "re_exposed",
    "scan_paths",
]
