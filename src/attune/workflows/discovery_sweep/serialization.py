"""Output serialization for the discovery-sweep workflow.

Three artifacts are emitted per sweep:
- ``<sweep_id>.jsonl``           — ACCEPTed findings (queue)
- ``<sweep_id>.rejected.jsonl``  — REJECTed findings (audit log)
- ``<sweep_id>.questions.md``    — UNSURE findings (human review)

JSONL is used for tool-consumed artifacts (jq-friendly,
streaming-friendly); markdown for the questions file so Patrick
can review cold without needing a tool to render it.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from attune.security.path_validation import _validate_file_path

from .schema import Finding, VerificationStatus


def write_jsonl(path: str | Path, findings: Iterable[Finding]) -> Path:
    """Write findings to a JSONL file (one Finding per line).

    Path is validated; parent directories are created if missing.
    """
    validated = _validate_file_path(str(path))
    validated.parent.mkdir(parents=True, exist_ok=True)
    with validated.open("w", encoding="utf-8") as fp:
        for finding in findings:
            fp.write(json.dumps(finding.to_jsonl_dict(), sort_keys=True))
            fp.write("\n")
    return validated


def read_jsonl(path: str | Path) -> list[Finding]:
    """Read findings from a JSONL file written by ``write_jsonl``."""
    validated = _validate_file_path(str(path))
    findings: list[Finding] = []
    with validated.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            findings.append(Finding.from_jsonl_dict(json.loads(line)))
    return findings


def _format_question_block(finding: Finding, index: int) -> str:
    """Render one UNSURE finding as a reviewable-cold markdown block."""
    location = finding.file_path
    if finding.line is not None:
        location = f"{finding.file_path}:{finding.line}"

    lines = [
        f"## {index}. {finding.source_workflow} — {location}",
        "",
        f"- **Severity:** {finding.severity.value}",
        f"- **Sweep:** `{finding.sweep_id}`",
        f"- **Captured:** {finding.timestamp_utc}",
        "",
        "### Finding",
        "",
        finding.message.strip() or "_(no message)_",
        "",
        "### Why verification was unsure",
        "",
        finding.verification_reasoning.strip()
        or "_No verification reasoning recorded — no rule fired._",
        "",
        "### Raw finding (from sub-workflow)",
        "",
        "```json",
        json.dumps(finding.raw_finding, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def write_questions_markdown(
    path: str | Path,
    findings: Iterable[Finding],
    sweep_id: str,
    scope: str,
) -> Path:
    """Write UNSURE findings as a reviewable-cold markdown file.

    Only findings with ``verification_status == UNSURE`` are included.
    Other statuses are silently filtered (call sites should pass a
    pre-filtered list, but the filter here is defense in depth).
    """
    validated = _validate_file_path(str(path))
    validated.parent.mkdir(parents=True, exist_ok=True)

    unsure = [f for f in findings if f.verification_status == VerificationStatus.UNSURE]

    lines = [
        f"# Discovery sweep — UNSURE findings ({sweep_id})",
        "",
        f"- **Scope:** `{scope}`",
        f"- **Sweep id:** `{sweep_id}`",
        f"- **Count:** {len(unsure)}",
        "",
        "These findings could not be confidently classified by the",
        "verification rule engine. Each block below captures the",
        "original finding, the sub-workflow that raised it, and what",
        "made verification ambiguous — enough context to review cold.",
        "",
        "---",
        "",
    ]

    if not unsure:
        lines.append("_No UNSURE findings in this sweep._")
        lines.append("")
    else:
        for idx, finding in enumerate(unsure, start=1):
            lines.append(_format_question_block(finding, idx))
            lines.append("---")
            lines.append("")

    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"
    validated.write_text(content, encoding="utf-8")
    return validated


__all__ = [
    "read_jsonl",
    "write_jsonl",
    "write_questions_markdown",
]
