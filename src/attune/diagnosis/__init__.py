"""Advanced debugging plugin — the diagnose stage of the self-healing
loop (docs/specs/advanced-debugging-plugin/).

Phase A ships the substrate (the ``DiagnosisRecord`` store and
loader); Phase B ships the engine: lesson priors, the bounded
evidence pack, the seat panel, and ``diagnose()`` — the one entry
point the CLI, the ops endpoint (Phase C), and the triage routine
(Phase D) all call.
"""

from .annotate import (  # noqa: E402  — ordered after store imports
    ORIGINS,
    retag_origin,
)
from .config import DiagnosisConfig
from .engine import DiagnosisSourceError, diagnose, find_source_run
from .panel import PanelResult, convene_panel
from .priors import PriorsResult, extract_error_terms, recall_priors
from .store import (
    DIAGNOSIS_CUTOVER,
    DiagnosisLoadStats,
    load_diagnoses,
    records_for_run,
)

__all__ = [
    "DIAGNOSIS_CUTOVER",
    "DiagnosisConfig",
    "DiagnosisLoadStats",
    "DiagnosisSourceError",
    "PanelResult",
    "PriorsResult",
    "convene_panel",
    "diagnose",
    "extract_error_terms",
    "find_source_run",
    "ORIGINS",
    "load_diagnoses",
    "recall_priors",
    "records_for_run",
    "retag_origin",
]
