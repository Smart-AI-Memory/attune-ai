"""Regression guard: generated docs must not carry attune-less imports.

The attune-author polish pass once emitted example imports from the
directory basename (``from pipeline import ...``, ``from spec import
...``) instead of the real package path (``from attune.pipeline import
...``, ``from attune.spec.runner import ...``). The fact-check pass
then published false ``## Unresolved references`` blocks into 7
spec-engine docs.

The generator-side fix lives in attune-author
(``fact_check/import_repair.py``). This guard protects the *artifact*
in this repo: if a future regen against an old attune-author — or a
hand edit — reintroduces the bare form, this test fails. ``pipeline``
and ``spec`` are always attune subpackages here, so the attune-less
form is unconditionally wrong regardless of code-fence vs inline
context.
"""

from __future__ import annotations

import re
from pathlib import Path

# repo_root/tests/unit/this_file.py -> parents[2] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories holding attune-author-generated documentation.
_DOC_ROOTS = (
    ".help/templates",
    "docs/how-to",
    "docs/tutorials",
    "docs/architecture",
)

# ``from pipeline import``, ``from pipeline.x import``, ``from spec
# import``, ``from spec.runner import`` — i.e. the two attune
# subpackage names used WITHOUT the ``attune.`` prefix. Matches in any
# context (code fence, inline span, table cell).
_BARE_IMPORT = re.compile(r"\bfrom\s+(pipeline|spec)(\.[a-z_]+)?\s+import\b")


def _generated_docs() -> list[Path]:
    docs: list[Path] = []
    for rel in _DOC_ROOTS:
        root = _REPO_ROOT / rel
        if root.exists():
            docs.extend(root.rglob("*.md"))
    return docs


def test_no_attune_less_pipeline_or_spec_imports() -> None:
    """No generated doc may reference ``pipeline``/``spec`` un-prefixed."""
    offenders: list[str] = []
    for doc in _generated_docs():
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            if _BARE_IMPORT.search(line):
                rel = doc.relative_to(_REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Generated docs contain attune-less imports (use "
        "`from attune.pipeline ...` / `from attune.spec ...`):\n" + "\n".join(offenders)
    )


def test_guard_sees_documentation_to_scan() -> None:
    """Sanity: the guard actually found docs (paths didn't go stale)."""
    assert _generated_docs(), "No generated docs found — check _DOC_ROOTS"
