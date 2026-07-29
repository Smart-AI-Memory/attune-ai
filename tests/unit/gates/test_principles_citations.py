"""Drift guard: every enforcer cited in the Principles section exists.

The principles document's whole claim is that each principle names a real
ratchet/gate/hook/drift-guard. This test keeps that claim true: it parses
the numbered principles, extracts every backtick-cited repo path (including
``path::test_name`` forms), and fails if a cited enforcer file no longer
exists or a cited test name no longer appears in its file.

TARGET note: the section was ratified 2026-07-29 and lives in the
collaboration-contract MASTER (the projector copies it to the provider
surfaces, so validating the master validates them all).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
TARGET = REPO_ROOT / "content/collaboration/contract.md"

#: A collapsed backtick span that looks like a repo file path: any known
#: config/code/doc extension, or a slash-containing path (covers shell
#: scripts, extensionless hooks, and directories). Dotted module names
#: (no slash, unknown extension) stay excluded.
_PATH_RE = re.compile(r"^[\w./-]+\.(?:py|yml|yaml|md|toml|json|sh|cfg|ini|txt)$")
_DIR_RE = re.compile(r"^[\w.-]+(?:/[\w.-]+)+/?$")


def _is_repo_path(token: str) -> bool:
    return bool(_PATH_RE.match(token) or _DIR_RE.match(token))


def _principles_text() -> str:
    text = TARGET.read_text(encoding="utf-8")
    # Anchor to the heading at line start, not a backtick mention of it.
    match = re.search(r"^### Principles$", text, re.MULTILINE)
    assert match, f"no '### Principles' heading in {TARGET}"
    # The section ends at the master's next heading (### Shared truth today).
    nxt = re.search(r"^#{2,3} ", text[match.end() :], re.MULTILINE)
    end = match.end() + nxt.start() if nxt else len(text)
    return text[match.start() : end]


def _cited_enforcers() -> list[str]:
    """Backtick spans that collapse to a repo path (or path::test_name)."""
    spans = re.findall(r"`([^`]+)`", _principles_text(), re.DOTALL)
    cited = []
    for span in spans:
        collapsed = re.sub(r"\s+", "", span)
        path_part = collapsed.split("::")[0]
        if _is_repo_path(path_part):
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
        if not enforcer.exists():
            continue  # already reported by the path-existence test
        # A real def/class at line start — a stale name surviving in a
        # comment or docstring must not count (codex lane 3 finding).
        defined = re.search(
            rf"^\s*(?:def|class)\s+{re.escape(test_name)}\b",
            enforcer.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if not defined:
            stale.append(citation)
    assert not stale, f"Principles section cites test names absent from their files: {stale}"
