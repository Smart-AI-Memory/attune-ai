"""CLI command for the diagnosis engine (advanced-debugging-plugin T4).

``attune diagnose <run_id>`` diagnoses one failed run from the
canonical stream end-to-end (priors -> evidence -> panel) and persists
the DiagnosisRecord. Exit codes: 0 diagnosis persisted, 1 source run
not diagnosable, 2 unexpected engine failure.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from argparse import Namespace


def cmd_diagnose(args: Namespace) -> int:
    """Diagnose a failed workflow run and print the receipted summary."""
    from attune.diagnosis.engine import DiagnosisSourceError, diagnose

    try:
        record = diagnose(args.run_id)
    except DiagnosisSourceError as exc:
        print(f"cannot diagnose: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary, report and exit
        print(f"diagnosis failed unexpectedly: {type(exc).__name__}: {exc}")
        return 2

    print(f"diagnosis {record.diagnosis_id} for run {record.source_run_id}")
    print(f"  workflow: {record.workflow_name}")
    print(f"  symptom:  {record.symptom}")
    if record.priors_degraded:
        print(f"  priors:   degraded ({record.priors_degraded})")
    else:
        print(f"  priors:   {len(record.prior_lessons)} lesson(s) recalled")
    panel = record.panel or {}
    print(
        f"  panel:    {len(panel.get('seats_invoked', []))} seat(s), "
        f"{len(panel.get('absences', []))} absent, "
        f"{panel.get('invocations', 0)} invocation(s)"
    )
    if record.synthesis:
        print("\n" + record.synthesis)
    if record.dissent:
        print(f"\n{len(record.dissent)} unresolved dissent line(s) retained")
    print("\npersisted to the canonical diagnosis stream")
    return 0
