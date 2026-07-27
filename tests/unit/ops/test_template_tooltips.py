"""D1 tooltip-system gate (ops-dashboard-polish, PL-P3-1).

The dashboard's hover feedback uses the fast CSS tooltip system
(``data-tooltip`` + the ``[data-tooltip]::after`` rules in
``main.css``), not the native ``title`` attribute — native title has
a 500-1500ms browser-dependent delay that reads as "no tooltip" when
scanning a table.

This gate greps every dashboard template for native ``title=``
attributes so the converted surface can't silently regress. The ONE
sanctioned exception: ``<option>`` elements. CSS pseudo-element
tooltips cannot render on ``<option>`` (browsers paint native list
controls), so native ``title`` is the only tooltip mechanism there —
converting those would delete the tooltip outright.
"""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "templates"

# An attribute-position `title="` — not `data-tooltip=` (different
# attribute) and not a Jinja variable named title.
_TITLE_ATTR_RE = re.compile(r'(?<![\w-])title="')


def test_template_dir_exists() -> None:
    assert TEMPLATE_DIR.is_dir(), f"template dir moved? {TEMPLATE_DIR}"


def test_no_native_title_attributes_outside_option_tags() -> None:
    violations: list[str] = []
    for template in sorted(TEMPLATE_DIR.glob("*.html")):
        for lineno, line in enumerate(template.read_text(encoding="utf-8").splitlines(), start=1):
            if not _TITLE_ATTR_RE.search(line):
                continue
            # Sanctioned: native title on <option> — CSS tooltips
            # cannot render there (see module docstring).
            if "<option" in line:
                continue
            violations.append(f"{template.name}:{lineno}: {line.strip()[:100]}")
    assert not violations, (
        "Native title= attribute(s) found in dashboard templates — use "
        "data-tooltip (+ aria-label) instead; native title is only "
        "allowed on <option> elements:\n" + "\n".join(violations)
    )
