"""Advanced debugging plugin — the diagnose stage of the self-healing
loop (docs/specs/advanced-debugging-plugin/).

Phase A ships the substrate: the ``DiagnosisRecord`` store and loader.
The engine (priors, evidence, panel) arrives in Phase B.
"""

from .store import (
    DIAGNOSIS_CUTOVER,
    DiagnosisLoadStats,
    load_diagnoses,
    records_for_run,
)

__all__ = [
    "DIAGNOSIS_CUTOVER",
    "DiagnosisLoadStats",
    "load_diagnoses",
    "records_for_run",
]
