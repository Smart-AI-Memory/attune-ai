"""Acceptance scaffolding (pipeline-learner RR-7).

On explicit acceptance ONLY, scaffold `<name>.yaml` + `<name>.evidence.json`
under `docs/specs/pipelines/` — atomically (both or neither), with the
member workflow names VALIDATED against the live registry
(`_DEFAULT_WORKFLOW_NAMES`) and never written to it: a pipeline is a
composition of EXISTING workflows; nothing is registered (RR-7,
contested→resolved).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .mining import WINDOW, Candidate

#: Chair-supplied pipeline names: lowercase slug, no path metacharacters
#: (RR-7 name sanitization / containment).
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ScaffoldError(ValueError):
    """A scaffold request that cannot be safely written."""


def _registry_names() -> set[str]:
    from attune.workflows import _DEFAULT_WORKFLOW_NAMES

    return set(_DEFAULT_WORKFLOW_NAMES)


def _pipeline_yaml(name: str, candidate: Candidate) -> str:
    """Render the pipeline YAML (composition of EXISTING workflows)."""
    return (
        f"name: {name}\n"
        "kind: pipeline\n"
        "# Mined by pipeline-learner v1; members must exist in the\n"
        "# workflow registry — nothing is registered by acceptance (RR-7).\n"
        "members:\n"
        f"  - {candidate.a}\n"
        f"  - {candidate.b}\n"
        f"window_minutes: {int(WINDOW.total_seconds() // 60)}\n"
        f"evidence: {name}.evidence.json\n"
    )


def scaffold_acceptance(
    candidate: Candidate,
    name: str,
    pipelines_dir: Path,
) -> tuple[Path, Path]:
    """Write `<name>.yaml` + `<name>.evidence.json` atomically (RR-7).

    Raises:
        ScaffoldError: Invalid/escaping name, unknown member workflow,
            or a collision with an existing scaffold (collision
            behavior: refuse — the chair picks a new name; nothing is
            overwritten).
        OSError: Filesystem failure after rollback of any partial write.
    """
    if not _NAME_RE.match(name):
        raise ScaffoldError(f"invalid pipeline name {name!r} (need ^[a-z0-9][a-z0-9-]*$)")
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    yaml_dest = pipelines_dir / f"{name}.yaml"
    evidence_dest = pipelines_dir / f"{name}.evidence.json"
    # Containment: the sanitized name must resolve inside pipelines_dir.
    root = pipelines_dir.resolve()
    if yaml_dest.resolve().parent != root or evidence_dest.resolve().parent != root:
        raise ScaffoldError(f"pipeline name escapes the pipelines directory: {name!r}")
    unknown = {candidate.a, candidate.b} - _registry_names()
    if unknown:
        raise ScaffoldError(f"pipeline references unknown workflows: {sorted(unknown)}")
    if yaml_dest.exists() or evidence_dest.exists():
        raise ScaffoldError(f"pipeline {name!r} already scaffolded — pick a new name")

    evidence = {
        "fingerprint": candidate.fingerprint(),
        "support": candidate.support,
        "ratio": round(candidate.ratio, 4),
        "members": [candidate.a, candidate.b],
        "sample_run_ids": candidate.sample_run_ids,
        "provenance_mix": {
            "manual_pairs": candidate.manual_pairs,
            "auto_or_unknown_pairs": candidate.support - candidate.manual_pairs,
        },
        "last_pair_at": candidate.last_pair_at.isoformat(),
        "scaffolded_at": datetime.now(timezone.utc).isoformat(),
    }

    yaml_tmp = pipelines_dir / f"{name}.yaml.tmp"
    evidence_tmp = pipelines_dir / f"{name}.evidence.json.tmp"
    written: list[Path] = []
    try:
        yaml_tmp.write_text(_pipeline_yaml(name, candidate), encoding="utf-8")
        evidence_tmp.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        yaml_tmp.replace(yaml_dest)
        written.append(yaml_dest)
        evidence_tmp.replace(evidence_dest)
        written.append(evidence_dest)
    except OSError:
        # Both-or-neither: roll back any half-landed artifact (RR-7).
        for path in (yaml_tmp, evidence_tmp, *written):
            try:
                path.unlink(missing_ok=True)
            except OSError:  # pragma: no cover - best-effort rollback
                pass
        raise
    return yaml_dest, evidence_dest
