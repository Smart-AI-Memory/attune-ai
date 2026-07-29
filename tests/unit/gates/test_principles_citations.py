"""Drift guard: every enforcer cited in the Principles section exists.

The principles document's whole claim is that each principle names a real
ratchet/gate/hook/drift-guard. This test keeps that claim true: it parses
the numbered principles, extracts every backtick-cited repo path (including
``path::test_name`` forms), and fails if a cited enforcer file no longer
exists or a cited test name no longer appears in its file.

TARGET note: while the section is a draft under chair review it lives in
the feature-lead-governance spec; on ratification the section moves into
``content/collaboration/contract.md`` and TARGET must be re-pointed there
in the same PR (the draft file is deleted).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
TARGET = REPO_ROOT / "docs/specs/feature-lead-governance/principles-section-draft.md"

#: A collapsed backtick span that looks like a repo file path.
_PATH_RE = re.compile(r"^[\w./-]+\.(?:py|yml|yaml|md)$")


def _principles_text() -> str:
    text = TARGET.read_text(encoding="utf-8")
    # Anchor to the heading at line start — the literal string also appears
    # inside a backtick span in the draft's preamble.
    match = re.search(r"^### Principles$", text, re.MULTILINE)
    assert match, f"no '### Principles' heading in {TARGET}"
    # The numbered list ends at the horizontal rule before the chair notes.
    end = text.index("\n---", match.start())
    return text[match.start() : end]


def _cited_enforcers() -> list[str]:
    """Backtick spans that collapse to a repo path (or path::test_name)."""
    spans = re.findall(r"`([^`]+)`", _principles_text(), re.DOTALL)
    cited = []
    for span in spans:
        collapsed = re.sub(r"\s+", "", span)
        path_part = collapsed.split("::")[0]
        if _PATH_RE.match(path_part):
            cited.append(collapsed)
    return cited


def test_target_document_exists():
    assert TARGET.exists(), (
        f"{TARGET} is gone. If the Principles section was ratified into the "
        "contract master, re-point TARGET at content/collaboration/contract.md."
    )


def test_extraction_is_not_vacuous():
    # A regex regression that extracts nothing must fail loudly, not pass.
    assert len(_cited_enforcers()) >= 10


def test_every_cited_enforcer_path_exists():
    missing = []
    for citation in _cited_enforcers():
        path_part = citation.split("::")[0]
        if not (REPO_ROOT / path_part).exists():
            missing.append(citation)
    assert not missing, (
        f"Principles section cites enforcers that no longer exist: {missing}. "
        "Fix the citation or restore the enforcer — the section may not cite "
        "fiction (its own principle 8)."
    )


def test_every_cited_test_name_exists_in_its_file():
    stale = []
    for citation in _cited_enforcers():
        if "::" not in citation:
            continue
        path_part, test_name = citation.split("::", 1)
        enforcer = REPO_ROOT / path_part
        if enforcer.exists() and test_name not in enforcer.read_text(encoding="utf-8"):
            stale.append(citation)
    assert not stale, f"Principles section cites test names absent from their files: {stale}"
